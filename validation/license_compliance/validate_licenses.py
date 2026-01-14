#!/usr/bin/env python3
"""
RansomEye License Validator

Strict validator that:
- Verifies inventory completeness
- Ensures no forbidden licenses exist
- Ensures every dependency is declared
- Exits non-zero on violation

OFFLINE ONLY - No network access required.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set


class LicenseValidator:
    """Validates license compliance against policy and inventory."""
    
    def __init__(self, repo_root: Path, policy_path: Path, inventory_path: Path):
        self.repo_root = repo_root
        self.policy_path = policy_path
        self.inventory_path = inventory_path
        self.policy = self._load_policy()
        self.inventory = self._load_inventory()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def _load_policy(self) -> Dict:
        """Load LICENSE_POLICY.json."""
        with open(self.policy_path, 'r') as f:
            return json.load(f)
    
    def _load_inventory(self) -> Dict[str, Dict]:
        """Load THIRD_PARTY_INVENTORY.json and index by name."""
        with open(self.inventory_path, 'r') as f:
            entries = json.load(f)
        return {entry['name']: entry for entry in entries}
    
    def collect_python_dependencies(self) -> Set[str]:
        """Collect all Python dependencies from requirements.txt files."""
        deps = set()
        
        for req_file in self.repo_root.rglob('requirements.txt'):
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse package name
                    match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[^\]]+\])?)', line)
                    if match:
                        name = match.group(1).split('[')[0]  # Remove extras
                        deps.add(name.lower())
        
        return deps
    
    def collect_rust_dependencies(self) -> Set[str]:
        """Collect all Rust dependencies from Cargo.toml files."""
        deps = set()
        
        for cargo_file in self.repo_root.rglob('Cargo.toml'):
            in_deps = False
            with open(cargo_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line == '[dependencies]':
                        in_deps = True
                        continue
                    if line.startswith('[') and in_deps:
                        break
                    if in_deps and line and not line.startswith('#'):
                        match = re.match(r'^([a-zA-Z0-9_-]+)\s*=', line)
                        if match:
                            deps.add(match.group(1).lower())
        
        return deps
    
    def collect_node_dependencies(self) -> Set[str]:
        """Collect all Node.js dependencies from package.json files."""
        deps = set()
        
        for package_file in self.repo_root.rglob('package.json'):
            if 'node_modules' in str(package_file):
                continue
            
            with open(package_file, 'r') as f:
                data = json.load(f)
            
            for dep_type in ['dependencies', 'devDependencies']:
                if dep_type in data:
                    for name in data[dep_type].keys():
                        # Normalize scoped packages
                        normalized = name.replace('@', '').replace('/', '-').lower()
                        deps.add(normalized)
        
        return deps
    
    def collect_all_dependencies(self) -> Set[str]:
        """Collect all dependencies from all sources."""
        all_deps = set()
        all_deps.update(self.collect_python_dependencies())
        all_deps.update(self.collect_rust_dependencies())
        all_deps.update(self.collect_node_dependencies())
        return all_deps
    
    def get_inventory_names(self) -> Set[str]:
        """Get all dependency names from inventory."""
        return {name.lower() for name in self.inventory.keys()}
    
    def validate_completeness(self) -> bool:
        """Verify that all dependencies are in inventory."""
        actual_deps = self.collect_all_dependencies()
        inventory_names = self.get_inventory_names()
        
        missing = actual_deps - inventory_names
        
        # Try fuzzy matching for known variations
        # (e.g., @vitejs/plugin-react vs vitejs-plugin-react)
        still_missing = set()
        for dep in missing:
            # Try various normalizations
            variations = [
                dep,
                dep.replace('-', '_'),
                dep.replace('_', '-'),
            ]
            # For scoped packages, try both formats
            if '/' in dep or '@' in dep:
                variations.append(dep.replace('@', '').replace('/', '-'))
            
            found = False
            for var in variations:
                if var in inventory_names:
                    found = True
                    break
            
            if not found:
                still_missing.add(dep)
        
        if still_missing:
            self.errors.append(
                f"INVENTORY INCOMPLETE: {len(still_missing)} dependencies not in inventory: "
                + ", ".join(sorted(still_missing))
            )
            return False
        
        return True
    
    def validate_forbidden_licenses(self) -> bool:
        """Verify no forbidden licenses exist in inventory."""
        forbidden = {f.lower() for f in self.policy.get('forbidden_licenses', [])}
        violations = []
        
        for name, entry in self.inventory.items():
            license_str = entry.get('license', '').lower()
            license_type = entry.get('license_type', '')
            
            # Check if license contains forbidden terms
            for forbidden_license in forbidden:
                if forbidden_license in license_str:
                    violations.append(f"{name}: {entry.get('license')}")
            
            # Also check license_type
            if license_type == 'strong-copyleft':
                violations.append(f"{name}: license_type is strong-copyleft")
        
        if violations:
            self.errors.append(
                f"FORBIDDEN LICENSES: {len(violations)} violations found: " + "; ".join(violations)
            )
            return False
        
        return True
    
    def validate_required_fields(self) -> bool:
        """Verify all inventory entries have required fields."""
        required_fields = ['name', 'version', 'component', 'language', 'license', 
                          'license_type', 'static_or_dynamic', 'distribution_scope', 
                          'risk_level', 'notes']
        violations = []
        
        for name, entry in self.inventory.items():
            missing = [field for field in required_fields if field not in entry or not entry[field]]
            if missing:
                violations.append(f"{name}: missing fields {missing}")
        
        if violations:
            self.errors.append(
                f"MISSING REQUIRED FIELDS: {len(violations)} entries incomplete: " + "; ".join(violations)
            )
            return False
        
        return True
    
    def validate_license_types(self) -> bool:
        """Verify license_type values are valid."""
        valid_types = ['permissive', 'weak-copyleft', 'strong-copyleft', 'proprietary']
        violations = []
        
        for name, entry in self.inventory.items():
            license_type = entry.get('license_type', '')
            if license_type not in valid_types:
                violations.append(f"{name}: invalid license_type '{license_type}'")
        
        if violations:
            self.errors.append(
                f"INVALID LICENSE TYPES: {len(violations)} violations: " + "; ".join(violations)
            )
            return False
        
        return True
    
    def validate_conditionally_allowed(self) -> bool:
        """Verify conditionally allowed licenses are properly documented."""
        conditionally_allowed = self.policy.get('conditionally_allowed', [])
        violations = []
        
        for cond_entry in conditionally_allowed:
            license_name = cond_entry.get('license')
            components = cond_entry.get('components', [])
            
            # Find all inventory entries with this license
            matching = [name for name, entry in self.inventory.items() 
                       if entry.get('license') == license_name]
            
            # Verify all matching entries are in the components list
            for name in matching:
                entry = self.inventory[name]
                if entry.get('name') not in components:
                    violations.append(
                        f"{name}: uses conditionally allowed license {license_name} "
                        f"but not listed in conditionally_allowed.components"
                    )
        
        if violations:
            self.errors.append(
                f"CONDITIONALLY ALLOWED VIOLATIONS: {len(violations)} violations: " + "; ".join(violations)
            )
            return False
        
        return True
    
    def validate_all(self) -> bool:
        """Run all validations. Returns True if all pass."""
        results = [
            self.validate_required_fields(),
            self.validate_license_types(),
            self.validate_forbidden_licenses(),
            self.validate_conditionally_allowed(),
            self.validate_completeness(),
        ]
        
        return all(results)


def main():
    """Main entry point."""
    # Determine repository root
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
    
    validator = LicenseValidator(repo_root, policy_path, inventory_path)
    
    print("Validating license compliance...", file=sys.stderr)
    success = validator.validate_all()
    
    if validator.errors:
        print("\nVALIDATION FAILED:", file=sys.stderr)
        for error in validator.errors:
            print(f"  ERROR: {error}", file=sys.stderr)
    
    if validator.warnings:
        print("\nWARNINGS:", file=sys.stderr)
        for warning in validator.warnings:
            print(f"  WARNING: {warning}", file=sys.stderr)
    
    if success:
        print("\nSUCCESS: All license validations passed", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"\nFAILURE: {len(validator.errors)} validation error(s)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
