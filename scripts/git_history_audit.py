#!/usr/bin/env python3
"""
RansomEye v1.0 Git History Credential Audit
AUTHORITATIVE: Scan git history for exposed credentials
Phase-9: Complete git history audit
"""

import subprocess
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional


class CredentialPattern:
    """Credential pattern matcher."""
    
    PATTERNS = [
        # Password patterns
        (r"password\s*=\s*['\"]([^'\"]{4,})['\"]", "password"),
        (r"PASSWORD\s*=\s*['\"]([^'\"]{4,})['\"]", "PASSWORD"),
        # Secret patterns
        (r"secret\s*=\s*['\"]([^'\"]{4,})['\"]", "secret"),
        (r"SECRET\s*=\s*['\"]([^'\"]{4,})['\"]", "SECRET"),
        # Token patterns
        (r"token\s*=\s*['\"]([^'\"]{4,})['\"]", "token"),
        (r"TOKEN\s*=\s*['\"]([^'\"]{4,})['\"]", "TOKEN"),
        # API key patterns
        (r"api_key\s*=\s*['\"]([^'\"]{4,})['\"]", "api_key"),
        (r"API_KEY\s*=\s*['\"]([^'\"]{4,})['\"]", "API_KEY"),
        # Known weak credentials
        (r"['\"]gagan['\"]", "weak_password"),
        (r"['\"]test_password[^'\"]*['\"]", "test_password"),
        (r"['\"]test_signing_key[^'\"]*['\"]", "test_signing_key"),
        (r"['\"]changeme['\"]", "weak_password"),
        (r"['\"]password['\"]", "weak_password"),
        (r"['\"]12345678['\"]", "weak_password"),
    ]
    
    @classmethod
    def match(cls, line: str) -> List[tuple]:
        """Match credential patterns in line."""
        matches = []
        for pattern, cred_type in cls.PATTERNS:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                matches.append((cred_type, match.group(0), match.start()))
        return matches


def scan_commit(commit_hash: str, project_root: Path) -> List[Dict[str, Any]]:
    """Scan a single commit for credentials."""
    findings = []
    
    try:
        # Get commit details
        commit_info = subprocess.run(
            ['git', 'show', '--stat', '--format=%H|%an|%ae|%ad|%s', commit_hash],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root
        )
        
        commit_lines = commit_info.stdout.split('\n')
        if not commit_lines:
            return findings
        
        header = commit_lines[0].split('|')
        commit_hash_actual = header[0]
        author = header[1] if len(header) > 1 else "unknown"
        email = header[2] if len(header) > 2 else "unknown"
        date = header[3] if len(header) > 3 else "unknown"
        message = header[4] if len(header) > 4 else "unknown"
        
        # Get file changes
        file_changes = subprocess.run(
            ['git', 'show', '--name-only', '--format=', commit_hash],
            capture_output=True,
            text=True,
            check=True,
            cwd=project_root
        )
        
        changed_files = [f.strip() for f in file_changes.stdout.split('\n') if f.strip()]
        
        # Scan each changed file
        for file_path in changed_files:
            try:
                # Get file content at this commit
                file_content = subprocess.run(
                    ['git', 'show', f'{commit_hash}:{file_path}'],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=project_root
                )
                
                # Scan each line
                for line_num, line in enumerate(file_content.stdout.split('\n'), 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                    
                    matches = CredentialPattern.match(line)
                    for cred_type, match_text, pos in matches:
                        findings.append({
                            'commit_hash': commit_hash_actual,
                            'file_path': file_path,
                            'line_number': line_num,
                            'credential_type': cred_type,
                            'match_text': match_text[:50],  # Truncate for safety
                            'author': author,
                            'email': email,
                            'date': date,
                            'commit_message': message[:100]
                        })
            except subprocess.CalledProcessError:
                # File may have been deleted or path invalid
                continue
                
    except subprocess.CalledProcessError:
        # Commit may not exist or be inaccessible
        pass
    
    return findings


def scan_all_commits(project_root: Path) -> List[Dict[str, Any]]:
    """Scan all commits in git history."""
    all_findings = []
    
    # Get all commit hashes
    commits = subprocess.run(
        ['git', 'log', '--all', '--format=%H'],
        capture_output=True,
        text=True,
        check=True,
        cwd=project_root
    )
    
    commit_hashes = [h.strip() for h in commits.stdout.split('\n') if h.strip()]
    
    print(f"Scanning {len(commit_hashes)} commits...")
    
    for i, commit_hash in enumerate(commit_hashes, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(commit_hashes)} commits scanned")
        
        findings = scan_commit(commit_hash, project_root)
        all_findings.extend(findings)
    
    return all_findings


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Git History Credential Audit'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('security/git-history-audit.json'),
        help='Output path for audit report'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=Path('.'),
        help='Project root directory'
    )
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("RansomEye v1.0 Git History Credential Audit")
    print("=" * 70)
    print(f"Project root: {project_root}")
    print(f"Output: {output_path}")
    print("")
    
    # Scan all commits
    findings = scan_all_commits(project_root)
    
    # Generate report
    report = {
        'audit_date': datetime.now(timezone.utc).isoformat(),
        'total_commits_scanned': len(set(f['commit_hash'] for f in findings)),
        'total_findings': len(findings),
        'findings': findings,
        'summary': {
            'by_type': {},
            'by_file': {},
            'by_commit': {}
        }
    }
    
    # Generate summary
    for finding in findings:
        cred_type = finding['credential_type']
        file_path = finding['file_path']
        commit_hash = finding['commit_hash']
        
        report['summary']['by_type'][cred_type] = report['summary']['by_type'].get(cred_type, 0) + 1
        report['summary']['by_file'][file_path] = report['summary']['by_file'].get(file_path, 0) + 1
        report['summary']['by_commit'][commit_hash] = report['summary']['by_commit'].get(commit_hash, 0) + 1
    
    # Write report
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Audit complete: {len(findings)} findings")
    print(f"   Report written to: {output_path}")
    print("")
    print("Summary by type:")
    for cred_type, count in sorted(report['summary']['by_type'].items()):
        print(f"  {cred_type}: {count}")
    print("")
    print("Top 10 files with findings:")
    for file_path, count in sorted(report['summary']['by_file'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {file_path}: {count}")


if __name__ == '__main__':
    main()
