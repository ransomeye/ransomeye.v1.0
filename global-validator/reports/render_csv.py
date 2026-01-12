#!/usr/bin/env python3
"""
RansomEye Global Validator - CSV Report Renderer
AUTHORITATIVE: Render validation reports as CSV for regulatory ingestion
"""

import csv
from pathlib import Path
from typing import Dict, Any, List


class CSVRenderError(Exception):
    """Base exception for CSV rendering errors."""
    pass


def render_csv(report: Dict[str, Any], output_path: Path) -> None:
    """
    Render validation report as CSV.
    
    Args:
        report: Validation report dictionary
        output_path: Path to output CSV file
    
    Raises:
        CSVRenderError: If CSV rendering fails
    """
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow([
                'Field',
                'Value'
            ])
            
            # Report metadata
            writer.writerow(['Report ID', report.get('report_id', '')])
            writer.writerow(['Timestamp', report.get('timestamp', '')])
            writer.writerow(['Validator Version', report.get('validator_version', '')])
            writer.writerow(['Validation Status', report.get('validation_status', '')])
            writer.writerow(['Failure Classification', report.get('failure_classification', '')])
            
            # Validation scope
            scope = report.get('validation_scope', {})
            writer.writerow(['Ledger Path', scope.get('ledger_path', '')])
            writer.writerow(['Key Directory', scope.get('key_dir', '')])
            writer.writerow(['Release Checksums', scope.get('release_checksums_path', '')])
            
            # Check results
            checks = [
                ('Ledger Checks', report.get('ledger_checks', {})),
                ('Integrity Checks', report.get('integrity_checks', {})),
                ('Custody Checks', report.get('custody_checks', {})),
                ('Config Checks', report.get('config_checks', {})),
                ('Simulation Checks', report.get('simulation_checks', {}))
            ]
            
            for check_name, check_result in checks:
                if not check_result:
                    continue
                
                writer.writerow([f'{check_name} - Status', check_result.get('status', '')])
                
                # Write check details
                for key, value in check_result.items():
                    if key not in ('status', 'failures'):
                        writer.writerow([f'{check_name} - {key}', str(value)])
                
                # Write failures
                failures = check_result.get('failures', [])
                if failures:
                    for i, failure in enumerate(failures):
                        writer.writerow([f'{check_name} - Failure {i+1}', str(failure)])
            
            # First failure
            first_failure = report.get('first_failure')
            if first_failure:
                writer.writerow(['First Failure - Check Type', first_failure.get('check_type', '')])
                writer.writerow(['First Failure - Location', first_failure.get('location', '')])
                writer.writerow(['First Failure - Error', first_failure.get('error', '')])
            
            # Signature
            writer.writerow(['Report Hash', report.get('report_hash', '')])
            writer.writerow(['Signing Key ID', report.get('signing_key_id', '')])
            writer.writerow(['Signature', report.get('signature', '')])
    
    except Exception as e:
        raise CSVRenderError(f"Failed to render CSV: {e}") from e
