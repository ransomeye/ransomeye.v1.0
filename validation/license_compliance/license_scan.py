#!/usr/bin/env python3
"""
RansomEye License Scanner

Scans Python, Rust, and Node.js dependencies and maps them to LICENSE_POLICY.json.
Emits JSON report. Fails on forbidden licenses.

OFFLINE ONLY - No network access required.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class Dependency:
    """Represents a scanned dependency."""
    name: str
    version: str
    source_file: str
    language: str
    license: Optional[str] = None
    license_type: Optional[str] = None
    risk_level: Optional[str] = None
    in_inventory: bool = False
    inventory_entry: Optional[Dict] = None


class LicenseScanner:
    """Scans dependencies and validates against license policy."""
    
    def __init__(self, repo_root: Path, policy_path: Path, inventory_path: Path):
        self.repo_root = repo_root
        self.policy_path = policy_path
        self.inventory_path = inventory_path
        self.policy = self._load_policy()
        self.inventory = self._load_inventory()
        self.scanned_deps: List[Dependency] = []
        self.violations: List[Dict] = []
        
    def _load_policy(self) -> Dict:
        """Load LICENSE_POLICY.json."""
        with open(self.policy_path, 'r') as f:
            return json.load(f)
    
    def _load_inventory(self) -> Dict[str, Dict]:
        """Load THIRD_PARTY_INVENTORY.json and index by name."""
        with open(self.inventory_path, 'r') as f:
            entries = json.load(f)
        return {entry['name']: entry for entry in entries}
    
    def scan_python_requirements(self, requirements_path: Path) -> List[Dependency]:
        """Scan Python requirements.txt file."""
        deps = []
        if not requirements_path.exists():
            return deps
        
        with open(requirements_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse package specification
                # Format: package==version or package>=version or package~=version
                match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)([<>=!~]+)?([\d.]+.*)?$', line)
                if match:
                    name = match.group(1).split('[')[0]  # Remove extras like [standard]
                    version = match.group(3) if match.group(3) else "unknown"
                    if not version or version == "unknown":
                        # Try to extract version constraint
                        version_match = re.search(r'([<>=!~]+)([\d.]+.*)', line)
                        if version_match:
                            version = version_match.group(1) + version_match.group(2)
                        else:
                            version = "unpinned"
                    
                    dep = Dependency(
                        name=name,
                        version=version,
                        source_file=str(requirements_path.relative_to(self.repo_root)),
                        language="python"
                    )
                    deps.append(dep)
        
        return deps
    
    def scan_rust_cargo(self, cargo_path: Path) -> List[Dependency]:
        """Scan Rust Cargo.toml file."""
        deps = []
        if not cargo_path.exists():
            return deps
        
        # Simple TOML parser for dependencies section
        in_deps = False
        with open(cargo_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '[dependencies]':
                    in_deps = True
                    continue
                if line.startswith('[') and in_deps:
                    break
                if in_deps and line and not line.startswith('#'):
                    # Parse: name = "version" or name = { version = "x", features = [...] }
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*=\s*', line)
                    if match:
                        name = match.group(1)
                        # Extract version
                        version_match = re.search(r'version\s*=\s*"([^"]+)"', line)
                        if version_match:
                            version = version_match.group(1)
                        else:
                            # Try simple format: name = "version"
                            simple_match = re.search(r'=\s*"([^"]+)"', line)
                            if simple_match:
                                version = simple_match.group(1)
                            else:
                                version = "unknown"
                        
                        dep = Dependency(
                            name=name,
                            version=version,
                            source_file=str(cargo_path.relative_to(self.repo_root)),
                            language="rust"
                        )
                        deps.append(dep)
        
        return deps
    
    def scan_node_package(self, package_path: Path) -> List[Dependency]:
        """Scan Node.js package.json file."""
        deps = []
        if not package_path.exists():
            return deps
        
        with open(package_path, 'r') as f:
            data = json.load(f)
        
        # Scan dependencies and devDependencies
        for dep_type in ['dependencies', 'devDependencies']:
            if dep_type in data:
                for name, version in data[dep_type].items():
                    dep = Dependency(
                        name=name,
                        version=version,
                        source_file=str(package_path.relative_to(self.repo_root)),
                        language="javascript"
                    )
                    deps.append(dep)
        
        return deps
    
    def scan_all(self) -> List[Dependency]:
        """Scan all dependency files in repository."""
        all_deps = []
        
        # Scan Python requirements.txt files
        for req_file in self.repo_root.rglob('requirements.txt'):
            deps = self.scan_python_requirements(req_file)
            all_deps.extend(deps)
        
        # Scan Rust Cargo.toml files
        for cargo_file in self.repo_root.rglob('Cargo.toml'):
            deps = self.scan_rust_cargo(cargo_file)
            all_deps.extend(deps)
        
        # Scan Node.js package.json files
        for package_file in self.repo_root.rglob('package.json'):
            # Skip node_modules
            if 'node_modules' in str(package_file):
                continue
            deps = self.scan_node_package(package_file)
            all_deps.extend(deps)
        
        self.scanned_deps = all_deps
        return all_deps
    
    def match_to_inventory(self, dep: Dependency) -> bool:
        """Match dependency to inventory entry."""
        # Try exact name match
        if dep.name in self.inventory:
            dep.in_inventory = True
            dep.inventory_entry = self.inventory[dep.name]
            dep.license = self.inventory[dep.name].get('license')
            dep.license_type = self.inventory[dep.name].get('license_type')
            dep.risk_level = self.inventory[dep.name].get('risk_level')
            return True
        
        # Try normalized name matches (handle @scoped packages, etc.)
        normalized_name = dep.name.replace('@', '').replace('/', '-')
        for inv_name, inv_entry in self.inventory.items():
            if normalized_name == inv_name or dep.name.lower() == inv_name.lower():
                dep.in_inventory = True
                dep.inventory_entry = inv_entry
                dep.license = inv_entry.get('license')
                dep.license_type = inv_entry.get('license_type')
                dep.risk_level = inv_entry.get('risk_level')
                return True
        
        return False
    
    def validate_license(self, dep: Dependency) -> Optional[Dict]:
        """Validate dependency license against policy. Returns violation dict if invalid."""
        if not dep.license:
            return {
                "type": "missing_license",
                "dependency": dep.name,
                "version": dep.version,
                "source": dep.source_file,
                "message": f"Dependency {dep.name} not found in inventory - license unknown"
            }
        
        # Check forbidden licenses
        forbidden = self.policy.get('forbidden_licenses', [])
        for forbidden_license in forbidden:
            if forbidden_license.lower() in dep.license.lower():
                return {
                    "type": "forbidden_license",
                    "dependency": dep.name,
                    "version": dep.version,
                    "source": dep.source_file,
                    "license": dep.license,
                    "message": f"Dependency {dep.name} uses FORBIDDEN license: {dep.license}"
                }
        
        # Check conditionally allowed
        conditionally_allowed = self.policy.get('conditionally_allowed', [])
        for cond in conditionally_allowed:
            if cond.get('license') == dep.license:
                # Verify condition is met (e.g., dynamic linking)
                # For now, we assume conditionally allowed are OK if in inventory
                if dep.in_inventory:
                    return None  # OK - conditionally allowed and in inventory
                else:
                    return {
                        "type": "conditional_license_not_approved",
                        "dependency": dep.name,
                        "version": dep.version,
                        "source": dep.source_file,
                        "license": dep.license,
                        "message": f"Dependency {dep.name} uses conditionally allowed license {dep.license} but is not properly documented in inventory"
                    }
        
        return None
    
    def validate_all(self) -> List[Dict]:
        """Validate all scanned dependencies."""
        violations = []
        
        for dep in self.scanned_deps:
            # Match to inventory
            self.match_to_inventory(dep)
            
            # Validate license
            violation = self.validate_license(dep)
            if violation:
                violations.append(violation)
        
        self.violations = violations
        return violations
    
    def generate_report(self) -> Dict:
        """Generate JSON report."""
        report = {
            "scan_timestamp": None,  # Would use datetime, but keeping offline
            "repo_root": str(self.repo_root),
            "total_dependencies_scanned": len(self.scanned_deps),
            "dependencies_in_inventory": sum(1 for d in self.scanned_deps if d.in_inventory),
            "dependencies_not_in_inventory": sum(1 for d in self.scanned_deps if not d.in_inventory),
            "violations_count": len(self.violations),
            "violations": self.violations,
            "dependencies": [asdict(dep) for dep in self.scanned_deps]
        }
        
        return report


def main():
    """Main entry point."""
    # Determine repository root (assume script is in validation/license_compliance/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent  # Go up to rebuild/
    
    policy_path = script_dir / "LICENSE_POLICY.json"
    inventory_path = script_dir / "THIRD_PARTY_INVENTORY.json"
    
    if not policy_path.exists():
        print(f"ERROR: LICENSE_POLICY.json not found at {policy_path}", file=sys.stderr)
        sys.exit(1)
    
    if not inventory_path.exists():
        print(f"ERROR: THIRD_PARTY_INVENTORY.json not found at {inventory_path}", file=sys.stderr)
        sys.exit(1)
    
    scanner = LicenseScanner(repo_root, policy_path, inventory_path)
    
    # Scan all dependencies
    print("Scanning dependencies...", file=sys.stderr)
    scanner.scan_all()
    
    # Validate licenses
    print("Validating licenses...", file=sys.stderr)
    violations = scanner.validate_all()
    
    # Generate report
    report = scanner.generate_report()
    
    # Output JSON report
    print(json.dumps(report, indent=2))
    
    # Exit with error if violations found
    if violations:
        print(f"\nERROR: Found {len(violations)} license violations:", file=sys.stderr)
        for v in violations:
            print(f"  - {v['message']}", file=sys.stderr)
        sys.exit(1)
    
    # Check for dependencies not in inventory
    missing = [d for d in scanner.scanned_deps if not d.in_inventory]
    if missing:
        print(f"\nWARNING: {len(missing)} dependencies not found in inventory:", file=sys.stderr)
        for d in missing:
            print(f"  - {d.name} ({d.version}) from {d.source_file}", file=sys.stderr)
        # Don't fail on missing - validate_licenses.py will catch this
        sys.exit(0)
    
    print("SUCCESS: All dependencies validated", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
