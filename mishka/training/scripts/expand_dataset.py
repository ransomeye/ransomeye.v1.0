#!/usr/bin/env python3
"""
MISHKA Training - Expand Training Dataset
AUTHORITATIVE: Add more cybersecurity sources to reach 10,000+ Q&A pairs
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import argparse


class DatasetExpander:
    """Expand training dataset with additional cybersecurity sources."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize expander.
        
        Args:
            output_dir: Directory to save expanded training data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_nist_framework_qa(self) -> List[Dict[str, Any]]:
        """Generate NIST Cybersecurity Framework Q&A pairs."""
        qa_pairs = []
        
        # NIST Framework Functions
        functions = {
            'Identify': 'Develop organizational understanding to manage cybersecurity risk',
            'Protect': 'Develop and implement safeguards to ensure delivery of critical services',
            'Detect': 'Develop and implement activities to identify cybersecurity events',
            'Respond': 'Develop and implement activities to take action regarding detected events',
            'Recover': 'Develop and implement activities to maintain plans for resilience'
        }
        
        for func, desc in functions.items():
            qa_pairs.append({
                'instruction': f'What is the {func} function in the NIST Cybersecurity Framework?',
                'input': '',
                'output': f'The {func} function in the NIST Cybersecurity Framework: {desc}. This function helps organizations manage cybersecurity risk through systematic approaches.'
            })
        
        # Security Controls
        controls = [
            ('Access Control', 'Restrict access to authorized users, processes, and devices'),
            ('Awareness and Training', 'Provide cybersecurity awareness and training to personnel'),
            ('Data Security', 'Protect data-at-rest and data-in-transit'),
            ('Incident Response', 'Establish incident response capabilities'),
            ('Risk Assessment', 'Identify and assess cybersecurity risks'),
        ]
        
        for control, desc in controls:
            qa_pairs.append({
                'instruction': f'What is {control} in cybersecurity?',
                'input': '',
                'output': f'{control} is a cybersecurity control that: {desc}. It is part of the NIST Cybersecurity Framework and helps organizations protect their information systems.'
            })
        
        print(f"Generated {len(qa_pairs)} NIST Framework Q&A pairs")
        return qa_pairs
    
    def generate_incident_response_qa(self) -> List[Dict[str, Any]]:
        """Generate Incident Response Q&A pairs."""
        qa_pairs = []
        
        # IR Phases
        ir_phases = [
            ('Preparation', 'Establish incident response capabilities, policies, and procedures'),
            ('Detection and Analysis', 'Identify and analyze security incidents'),
            ('Containment', 'Limit the scope and impact of security incidents'),
            ('Eradication', 'Remove threats and restore systems to normal operations'),
            ('Recovery', 'Restore systems and services to normal operations'),
            ('Post-Incident Activity', 'Review and improve incident response processes')
        ]
        
        for phase, desc in ir_phases:
            qa_pairs.append({
                'instruction': f'What is the {phase} phase of incident response?',
                'input': '',
                'output': f'The {phase} phase of incident response involves: {desc}. This phase is critical for effective security incident management.'
            })
        
        # Common IR Questions
        ir_qa = [
            ('How do you detect a security incident?', 'Security incidents are detected through monitoring, alerts, user reports, and automated detection systems. Indicators include unusual network traffic, unauthorized access attempts, malware detection, and system anomalies.'),
            ('What is the first step in incident response?', 'The first step in incident response is preparation - establishing an incident response team, defining procedures, and preparing tools and resources before an incident occurs.'),
            ('How do you contain a security incident?', 'Incident containment involves isolating affected systems, blocking malicious network traffic, disabling compromised accounts, and preventing further damage while preserving evidence for analysis.'),
            ('What is a playbook in incident response?', 'An incident response playbook is a documented set of procedures and steps to follow when responding to specific types of security incidents. It provides standardized response actions for common scenarios.'),
        ]
        
        for question, answer in ir_qa:
            qa_pairs.append({
                'instruction': question,
                'input': '',
                'output': answer
            })
        
        print(f"Generated {len(qa_pairs)} Incident Response Q&A pairs")
        return qa_pairs
    
    def generate_threat_intelligence_qa(self) -> List[Dict[str, Any]]:
        """Generate Threat Intelligence Q&A pairs."""
        qa_pairs = []
        
        # Threat Types
        threat_types = [
            ('APT', 'Advanced Persistent Threat - sophisticated, long-term cyber attacks by nation-states or organized groups'),
            ('Malware', 'Malicious software designed to damage, disrupt, or gain unauthorized access to computer systems'),
            ('Phishing', 'Social engineering attack that uses email or messaging to trick users into revealing sensitive information'),
            ('Ransomware', 'Malware that encrypts files and demands payment for decryption'),
            ('DDoS', 'Distributed Denial of Service - attack that overwhelms systems with traffic to make them unavailable'),
        ]
        
        for threat, desc in threat_types:
            qa_pairs.append({
                'instruction': f'What is {threat}?',
                'input': '',
                'output': f'{threat} ({desc}) is a type of cybersecurity threat that organizations must defend against through security controls and monitoring.'
            })
        
        # IOC Types
        ioc_types = [
            ('IP Address', 'Internet Protocol address that can be used to identify malicious network activity'),
            ('Domain Name', 'Domain names used by attackers for command and control or phishing'),
            ('File Hash', 'Cryptographic hash (MD5, SHA256) of malicious files for identification'),
            ('URL', 'Uniform Resource Locator used in malicious activities'),
        ]
        
        for ioc, desc in ioc_types:
            qa_pairs.append({
                'instruction': f'What is an IOC {ioc}?',
                'input': '',
                'output': f'An IOC (Indicator of Compromise) {ioc} is {desc}. IOCs help security teams identify and respond to security threats.'
            })
        
        print(f"Generated {len(qa_pairs)} Threat Intelligence Q&A pairs")
        return qa_pairs
    
    def generate_vulnerability_management_qa(self) -> List[Dict[str, Any]]:
        """Generate Vulnerability Management Q&A pairs."""
        qa_pairs = []
        
        # Vulnerability Types
        vuln_types = [
            ('Buffer Overflow', 'Memory corruption vulnerability where data exceeds buffer boundaries'),
            ('SQL Injection', 'Code injection attack that exploits SQL database vulnerabilities'),
            ('Cross-Site Scripting (XSS)', 'Attack that injects malicious scripts into web pages'),
            ('Privilege Escalation', 'Exploitation of vulnerabilities to gain higher access levels'),
            ('Remote Code Execution', 'Vulnerability that allows attackers to execute code remotely'),
        ]
        
        for vuln, desc in vuln_types:
            qa_pairs.append({
                'instruction': f'What is {vuln}?',
                'input': '',
                'output': f'{vuln} is a type of cybersecurity vulnerability: {desc}. Understanding these vulnerabilities helps in detection and mitigation.'
            })
        
        # CVSS Scoring
        cvss_qa = [
            ('What does CVSS score 9.8 mean?', 'A CVSS score of 9.8 indicates a Critical severity vulnerability. This means the vulnerability is easily exploitable and has high impact on confidentiality, integrity, and availability. Immediate patching is recommended.'),
            ('What is the difference between CVSS v2 and v3?', 'CVSS v3 introduced more granular scoring, better reflects modern attack scenarios, and includes additional metrics like Scope. CVSS v3 scores are generally more accurate for current threat landscapes.'),
            ('What CVSS score is considered critical?', 'CVSS scores of 9.0-10.0 are considered Critical. Scores of 7.0-8.9 are High, 4.0-6.9 are Medium, 0.1-3.9 are Low, and 0.0 is None.'),
        ]
        
        for question, answer in cvss_qa:
            qa_pairs.append({
                'instruction': question,
                'input': '',
                'output': answer
            })
        
        print(f"Generated {len(qa_pairs)} Vulnerability Management Q&A pairs")
        return qa_pairs
    
    def generate_forensics_qa(self) -> List[Dict[str, Any]]:
        """Generate Digital Forensics Q&A pairs."""
        qa_pairs = []
        
        forensics_qa = [
            ('What is digital forensics?', 'Digital forensics is the process of collecting, preserving, analyzing, and presenting digital evidence from computer systems, networks, and storage devices in a legally admissible manner.'),
            ('What is a forensic image?', 'A forensic image is an exact bit-by-bit copy of a storage device created using specialized tools to preserve evidence integrity. It includes all data, deleted files, and unallocated space.'),
            ('What is the order of volatility in digital forensics?', 'The order of volatility prioritizes evidence collection from most to least volatile: CPU registers, cache, RAM, network connections, disk, remote logging, and archived media.'),
            ('What is timeline analysis in forensics?', 'Timeline analysis reconstructs the chronological sequence of events on a system by correlating timestamps from file systems, logs, and registry entries to understand what happened and when.'),
            ('What is memory forensics?', 'Memory forensics analyzes RAM contents to find evidence of running processes, network connections, encryption keys, and malware that may not be present on disk.'),
        ]
        
        for question, answer in forensics_qa:
            qa_pairs.append({
                'instruction': question,
                'input': '',
                'output': answer
            })
        
        print(f"Generated {len(qa_pairs)} Digital Forensics Q&A pairs")
        return qa_pairs
    
    def expand_mitre_qa(self, existing_file: Path) -> List[Dict[str, Any]]:
        """Expand MITRE ATT&CK Q&A with more variations."""
        qa_pairs = []
        
        if not existing_file.exists():
            return qa_pairs
        
        # Load existing MITRE data
        with open(existing_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        techniques = data.get('techniques', [])[:100]  # Use first 100 for expansion
        
        for technique in techniques:
            tech_id = technique.get('id', '')
            name = technique.get('name', '')
            
            if not tech_id:
                continue
            
            # Additional Q&A variations
            qa_pairs.append({
                'instruction': f'How do attackers use {tech_id}?',
                'input': '',
                'output': f'Attackers use MITRE ATT&CK technique {tech_id} ({name}) as part of their attack chain. This technique is commonly used in {", ".join(technique.get("tactics", [])[:3])} tactics.'
            })
            
            qa_pairs.append({
                'instruction': f'What platforms are affected by {tech_id}?',
                'input': '',
                'output': f'MITRE ATT&CK technique {tech_id} ({name}) affects the following platforms: {", ".join(technique.get("platforms", [])[:5])}.'
            })
        
        print(f"Generated {len(qa_pairs)} additional MITRE ATT&CK Q&A pairs")
        return qa_pairs
    
    def combine_and_save(self, all_qa_pairs: List[Dict[str, Any]], output_file: str):
        """Combine all Q&A pairs and save."""
        output_path = self.output_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for qa in all_qa_pairs:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        print(f"\nSaved {len(all_qa_pairs)} total training examples to {output_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Expand training dataset')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed',
        help='Output directory for expanded data'
    )
    parser.add_argument(
        '--mitre-file',
        type=Path,
        help='Path to MITRE ATT&CK file for expansion'
    )
    parser.add_argument(
        '--existing-file',
        type=Path,
        help='Path to existing train.jsonl to append to'
    )
    
    args = parser.parse_args()
    
    expander = DatasetExpander(args.output_dir)
    all_qa_pairs = []
    
    # Load existing data if provided
    if args.existing_file and args.existing_file.exists():
        print(f"Loading existing data from {args.existing_file}...")
        with open(args.existing_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_qa_pairs.append(json.loads(line))
        print(f"Loaded {len(all_qa_pairs)} existing examples")
    
    # Generate new Q&A pairs
    print("\nGenerating new Q&A pairs...")
    
    all_qa_pairs.extend(expander.generate_nist_framework_qa())
    all_qa_pairs.extend(expander.generate_incident_response_qa())
    all_qa_pairs.extend(expander.generate_threat_intelligence_qa())
    all_qa_pairs.extend(expander.generate_vulnerability_management_qa())
    all_qa_pairs.extend(expander.generate_forensics_qa())
    
    # Expand MITRE if file provided
    if args.mitre_file:
        all_qa_pairs.extend(expander.expand_mitre_qa(args.mitre_file))
    
    # Save combined dataset
    expander.combine_and_save(all_qa_pairs, 'train_expanded.jsonl')
    
    print(f"\n{'='*60}")
    print(f"Dataset Expansion Complete!")
    print(f"Total training examples: {len(all_qa_pairs)}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
