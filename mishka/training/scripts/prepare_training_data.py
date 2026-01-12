#!/usr/bin/env python3
"""
MISHKA Training - Training Data Preparation
AUTHORITATIVE: Convert raw data to training format (Q&A pairs)
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import argparse


class TrainingDataPreparator:
    """Prepare training data from raw sources."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize preparator.
        
        Args:
            output_dir: Directory to save processed training data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_mitre_attck_qa(self, mitre_file: Path) -> List[Dict[str, Any]]:
        """
        Convert MITRE ATT&CK techniques to Q&A format.
        
        Args:
            mitre_file: Path to MITRE ATT&CK JSON file
        
        Returns:
            List of Q&A dictionaries
        """
        qa_pairs = []
        
        if not mitre_file.exists():
            print(f"MITRE ATT&CK file not found: {mitre_file}")
            return qa_pairs
        
        with open(mitre_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        techniques = data.get('techniques', [])
        
        for technique in techniques:
            tech_id = technique.get('id', '')
            name = technique.get('name', '')
            description = technique.get('description', '')
            
            if not tech_id or not description:
                continue
            
            # Q&A: What is this technique?
            qa_pairs.append({
                'instruction': f"What is MITRE ATT&CK technique {tech_id}?",
                'input': '',
                'output': f"{name} ({tech_id}): {description[:500]}"
            })
            
            # Q&A: How to detect this technique?
            if technique.get('detection'):
                qa_pairs.append({
                    'instruction': f"How do I detect MITRE ATT&CK technique {tech_id}?",
                    'input': '',
                    'output': f"To detect {name} ({tech_id}), monitor for: {', '.join(technique.get('detection', []))[:300]}"
                })
            
            # Q&A: What tactics does this belong to?
            if technique.get('tactics'):
                qa_pairs.append({
                    'instruction': f"What MITRE ATT&CK tactics does {tech_id} belong to?",
                    'input': '',
                    'output': f"Technique {tech_id} ({name}) belongs to the following tactics: {', '.join(technique.get('tactics', []))}"
                })
        
        print(f"Generated {len(qa_pairs)} Q&A pairs from MITRE ATT&CK")
        return qa_pairs
    
    def prepare_cve_qa(self, cve_file: Path) -> List[Dict[str, Any]]:
        """
        Convert CVE data to Q&A format (for understanding structure).
        
        Args:
            cve_file: Path to CVE JSON file
        
        Returns:
            List of Q&A dictionaries
        """
        qa_pairs = []
        
        if not cve_file.exists():
            print(f"CVE file not found: {cve_file}")
            return qa_pairs
        
        with open(cve_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cves = data.get('cves', [])
        
        # General CVE structure Q&A
        qa_pairs.append({
            'instruction': 'What is a CVE and how is it structured?',
            'input': '',
            'output': 'CVE (Common Vulnerabilities and Exposures) is a standardized identifier for publicly known cybersecurity vulnerabilities. The format is CVE-YYYY-NNNNN where YYYY is the year and NNNNN is a sequential number. CVEs include a description, affected products, CVSS scores, and references.'
        })
        
        qa_pairs.append({
            'instruction': 'What is CVSS and how are scores calculated?',
            'input': '',
            'output': 'CVSS (Common Vulnerability Scoring System) provides severity scores from 0.0 to 10.0. CVSS v3.x considers attack vector, attack complexity, privileges required, user interaction, scope, and impact (confidentiality, integrity, availability). Scores are categorized as: None (0.0), Low (0.1-3.9), Medium (4.0-6.9), High (7.0-8.9), Critical (9.0-10.0).'
        })
        
        # Example CVE Q&A (using first few CVEs)
        for cve in cves[:10]:  # Just a few examples
            cve_id = cve.get('cve_id', '')
            if cve_id:
                qa_pairs.append({
                    'instruction': f'What is {cve_id}?',
                    'input': '',
                    'output': f"{cve_id}: {cve.get('description', '')[:300]} CVSS v3 Score: {cve.get('cvss_v3', {}).get('score', 'N/A')}"
                })
        
        print(f"Generated {len(qa_pairs)} Q&A pairs from CVE data")
        return qa_pairs
    
    def save_training_data(self, qa_pairs: List[Dict[str, Any]], filename: str):
        """
        Save Q&A pairs to JSONL format.
        
        Args:
            qa_pairs: List of Q&A dictionaries
            filename: Output filename
        """
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for qa in qa_pairs:
                f.write(json.dumps(qa, ensure_ascii=False) + '\n')
        
        print(f"Saved {len(qa_pairs)} training examples to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Prepare training data from raw sources')
    parser.add_argument(
        '--mitre-file',
        type=Path,
        help='Path to MITRE ATT&CK JSON file'
    )
    parser.add_argument(
        '--cve-file',
        type=Path,
        help='Path to CVE JSON file'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed',
        help='Output directory for processed data'
    )
    
    args = parser.parse_args()
    
    preparator = TrainingDataPreparator(args.output_dir)
    all_qa_pairs = []
    
    # Process MITRE ATT&CK
    if args.mitre_file:
        mitre_qa = preparator.prepare_mitre_attck_qa(args.mitre_file)
        all_qa_pairs.extend(mitre_qa)
    
    # Process CVE data
    if args.cve_file:
        cve_qa = preparator.prepare_cve_qa(args.cve_file)
        all_qa_pairs.extend(cve_qa)
    
    # Save combined training data
    if all_qa_pairs:
        preparator.save_training_data(all_qa_pairs, 'train.jsonl')
        print(f"\nTotal training examples prepared: {len(all_qa_pairs)}")
    else:
        print("No training data prepared. Provide --mitre-file and/or --cve-file")


if __name__ == '__main__':
    main()
