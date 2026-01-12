#!/usr/bin/env python3
"""
RansomEye Global Validator - Validation Runner
AUTHORITATIVE: Command-line tool for running deterministic validation
"""

import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import argparse

# Add parent directory to path for imports
_validator_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_validator_dir))

from crypto.validator_key_manager import ValidatorKeyManager, ValidatorKeyManagerError
from crypto.signer import ValidatorSigner, ValidatorSignerError
from checks.ledger_checks import LedgerChecks
from checks.integrity_checks import IntegrityChecks
from checks.custody_checks import CustodyChecks
from checks.config_checks import ConfigChecks
from checks.simulation_checks import SimulationChecks


VALIDATOR_VERSION = "1.0.0"


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


def determine_failure_classification(report: Dict[str, Any]) -> str:
    """
    Determine failure classification from check results.
    
    Args:
        report: Validation report dictionary
    
    Returns:
        Failure classification string
    """
    if report['validation_status'] == 'PASS':
        return 'NONE'
    
    # Check first failure
    first_failure = report.get('first_failure')
    if not first_failure:
        return 'INTEGRITY_BREACH'
    
    check_type = first_failure.get('check_type', '')
    error = first_failure.get('error', '').lower()
    
    if 'tamper' in error or 'hash' in error:
        return 'TAMPERING_DETECTED'
    elif 'missing' in error or 'gap' in error:
        return 'MISSING_LEDGER_ENTRY'
    elif 'config' in error or 'drift' in error:
        return 'CONFIGURATION_DRIFT'
    elif 'chain' in error or 'custody' in error:
        return 'INCOMPLETE_CHAIN_OF_CUSTODY'
    elif 'simulation' in error:
        return 'SIMULATION_FAILURE'
    else:
        return 'INTEGRITY_BREACH'


def find_first_failure(report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find first failure across all checks.
    
    Args:
        report: Validation report dictionary
    
    Returns:
        First failure dictionary, or None if PASS
    """
    checks = [
        ('ledger', report.get('ledger_checks', {})),
        ('integrity', report.get('integrity_checks', {})),
        ('custody', report.get('custody_checks', {})),
        ('config', report.get('config_checks', {})),
        ('simulation', report.get('simulation_checks', {}))
    ]
    
    for check_type, check_result in checks:
        if check_result.get('status') == 'FAIL':
            failures = check_result.get('failures', [])
            if failures:
                first_failure = failures[0]
                return {
                    'check_type': check_type,
                    'location': first_failure.get('entry_id') or first_failure.get('component') or first_failure.get('config_path') or first_failure.get('chain_type') or first_failure.get('simulation_step', 'unknown'),
                    'error': first_failure.get('error', 'Unknown error')
                }
    
    return None


def run_validation(
    ledger_path: Path,
    ledger_key_dir: Path,
    validator_key_dir: Path,
    release_checksums_path: Optional[Path] = None,
    component_manifests: Optional[List[Path]] = None,
    config_snapshots: Optional[List[Path]] = None,
    run_simulation: bool = False
) -> Dict[str, Any]:
    """
    Run complete validation.
    
    Args:
        ledger_path: Path to audit ledger file
        ledger_key_dir: Directory containing ledger public keys
        validator_key_dir: Directory containing validator signing keys
        release_checksums_path: Optional path to release SHA256SUMS file
        component_manifests: Optional list of component manifest paths
        config_snapshots: Optional list of config snapshot paths
        run_simulation: Whether to run attack simulation
    
    Returns:
        Complete signed validation report
    """
    # Initialize report structure
    report = {
        'report_id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'validator_version': VALIDATOR_VERSION,
        'validation_status': 'PASS',
        'validation_scope': {
            'ledger_path': str(ledger_path),
            'key_dir': str(ledger_key_dir),
            'release_checksums_path': str(release_checksums_path) if release_checksums_path else '',
            'component_manifests': [str(p) for p in (component_manifests or [])],
            'config_snapshots': [str(p) for p in (config_snapshots or [])]
        },
        'ledger_checks': {},
        'integrity_checks': {},
        'custody_checks': {},
        'config_checks': {},
        'simulation_checks': {},
        'failure_classification': 'NONE',
        'first_failure': None
    }
    
    # Run ledger checks (mandatory)
    try:
        ledger_checks = LedgerChecks(ledger_path, ledger_key_dir)
        report['ledger_checks'] = ledger_checks.run_checks()
        if report['ledger_checks']['status'] == 'FAIL':
            report['validation_status'] = 'FAIL'
    except Exception as e:
        report['validation_status'] = 'FAIL'
        report['ledger_checks'] = {
            'status': 'FAIL',
            'total_entries': 0,
            'verified_entries': 0,
            'hash_chain_valid': False,
            'signatures_valid': False,
            'key_continuity_valid': False,
            'failures': [{'entry_id': '', 'error': f"Ledger check error: {e}"}]
        }
    
    # Fail-fast: if ledger checks fail, stop
    if report['validation_status'] == 'FAIL':
        report['failure_classification'] = determine_failure_classification(report)
        report['first_failure'] = find_first_failure(report)
        # Sign report even on failure
        return sign_report(report, validator_key_dir)
    
    # Run integrity checks (if checksums and manifests provided)
    if release_checksums_path and component_manifests:
        try:
            integrity_checks = IntegrityChecks(release_checksums_path, component_manifests)
            report['integrity_checks'] = integrity_checks.run_checks()
            if report['integrity_checks']['status'] == 'FAIL':
                report['validation_status'] = 'FAIL'
        except Exception as e:
            report['validation_status'] = 'FAIL'
            report['integrity_checks'] = {
                'status': 'FAIL',
                'components_checked': 0,
                'components_valid': 0,
                'checksum_matches': False,
                'tampering_detected': True,
                'failures': [{'component': 'system', 'error': f"Integrity check error: {e}"}]
            }
    
    # Fail-fast: if integrity checks fail, stop
    if report['validation_status'] == 'FAIL':
        report['failure_classification'] = determine_failure_classification(report)
        report['first_failure'] = find_first_failure(report)
        return sign_report(report, validator_key_dir)
    
    # Run custody checks (mandatory)
    try:
        custody_checks = CustodyChecks(ledger_path)
        report['custody_checks'] = custody_checks.run_checks()
        if report['custody_checks']['status'] == 'FAIL':
            report['validation_status'] = 'FAIL'
    except Exception as e:
        report['validation_status'] = 'FAIL'
        report['custody_checks'] = {
            'status': 'FAIL',
            'chains_verified': 0,
            'gaps_detected': True,
            'silent_transitions_detected': True,
            'failures': [{'chain_type': 'system', 'error': f"Custody check error: {e}"}]
        }
    
    # Fail-fast: if custody checks fail, stop
    if report['validation_status'] == 'FAIL':
        report['failure_classification'] = determine_failure_classification(report)
        report['first_failure'] = find_first_failure(report)
        return sign_report(report, validator_key_dir)
    
    # Run config checks (if config snapshots provided)
    if config_snapshots:
        try:
            config_checks = ConfigChecks(config_snapshots, ledger_path)
            report['config_checks'] = config_checks.run_checks()
            if report['config_checks']['status'] == 'FAIL':
                report['validation_status'] = 'FAIL'
        except Exception as e:
            report['validation_status'] = 'FAIL'
            report['config_checks'] = {
                'status': 'FAIL',
                'configs_checked': 0,
                'configs_valid': 0,
                'unauthorized_changes_detected': True,
                'failures': [{'config_path': 'system', 'error': f"Config check error: {e}"}]
            }
    
    # Fail-fast: if config checks fail, stop
    if report['validation_status'] == 'FAIL':
        report['failure_classification'] = determine_failure_classification(report)
        report['first_failure'] = find_first_failure(report)
        return sign_report(report, validator_key_dir)
    
    # Run simulation checks (if requested)
    if run_simulation:
        try:
            simulation_checks = SimulationChecks(ledger_path, ledger_key_dir)
            report['simulation_checks'] = simulation_checks.run_simulation()
            if report['simulation_checks']['status'] == 'FAIL':
                report['validation_status'] = 'FAIL'
        except Exception as e:
            report['validation_status'] = 'FAIL'
            report['simulation_checks'] = {
                'status': 'FAIL',
                'simulation_executed': False,
                'detection_verified': False,
                'response_verified': False,
                'ledger_entries_created': 0,
                'failures': [{'simulation_step': 'initialization', 'error': f"Simulation error: {e}"}]
            }
    
    # Determine final status
    report['failure_classification'] = determine_failure_classification(report)
    report['first_failure'] = find_first_failure(report)
    
    # Sign report
    return sign_report(report, validator_key_dir)


def sign_report(report: Dict[str, Any], validator_key_dir: Path) -> Dict[str, Any]:
    """
    Sign validation report.
    
    Args:
        report: Validation report dictionary (without report_hash and signature)
        validator_key_dir: Directory containing validator signing keys
    
    Returns:
        Signed validation report
    """
    try:
        key_manager = ValidatorKeyManager(validator_key_dir)
        private_key, public_key, key_id = key_manager.get_or_create_keypair()
        signer = ValidatorSigner(private_key, key_id)
        return signer.sign_complete_report(report)
    except ValidatorKeyManagerError as e:
        raise ValidationError(f"Failed to initialize validator keys: {e}") from e
    except ValidatorSignerError as e:
        raise ValidationError(f"Failed to sign report: {e}") from e


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Run RansomEye Global Validator'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger public keys'
    )
    parser.add_argument(
        '--validator-key-dir',
        type=Path,
        required=True,
        help='Directory containing validator signing keys'
    )
    parser.add_argument(
        '--release-checksums',
        type=Path,
        help='Path to release SHA256SUMS file (optional)'
    )
    parser.add_argument(
        '--component-manifests',
        type=Path,
        nargs='+',
        help='Paths to component installation manifests (optional)'
    )
    parser.add_argument(
        '--config-snapshots',
        type=Path,
        nargs='+',
        help='Paths to configuration snapshot files (optional)'
    )
    parser.add_argument(
        '--run-simulation',
        action='store_true',
        help='Run synthetic attack simulation'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Path to output validation report JSON'
    )
    
    args = parser.parse_args()
    
    try:
        report = run_validation(
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir,
            validator_key_dir=args.validator_key_dir,
            release_checksums_path=args.release_checksums,
            component_manifests=args.component_manifests,
            config_snapshots=args.config_snapshots,
            run_simulation=args.run_simulation
        )
        
        # Write report
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        
        # Print summary
        print(f"Validation Status: {report['validation_status']}")
        print(f"Report written to: {args.output}")
        
        if report['validation_status'] == 'FAIL':
            first_failure = report.get('first_failure')
            if first_failure:
                print(f"First Failure: {first_failure['check_type']} - {first_failure['error']}")
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
