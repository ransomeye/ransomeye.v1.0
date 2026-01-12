#!/usr/bin/env python3
"""
MISHKA Training - MITRE ATT&CK Data Collection
AUTHORITATIVE: Collect MITRE ATT&CK framework data for training
"""

import json
import requests
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class MITRECollector:
    """Collect MITRE ATT&CK framework data."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize MITRE collector.
        
        Args:
            output_dir: Directory to save collected data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # MITRE ATT&CK GitHub repository
        self.base_url = "https://raw.githubusercontent.com/mitre/cti/master"
        
    def download_techniques(self) -> List[Dict[str, Any]]:
        """
        Download MITRE ATT&CK techniques.
        
        Returns:
            List of technique dictionaries
        """
        techniques = []
        
        # Enterprise techniques
        enterprise_url = f"{self.base_url}/enterprise-attack/enterprise-attack.json"
        
        try:
            print(f"Downloading MITRE ATT&CK Enterprise techniques...")
            response = requests.get(enterprise_url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract techniques
            for obj in data.get('objects', []):
                if obj.get('type') == 'attack-pattern':
                    technique = {
                        'id': obj.get('external_references', [{}])[0].get('external_id', ''),
                        'name': obj.get('name', ''),
                        'description': obj.get('description', ''),
                        'tactics': [ref.get('external_id', '') for ref in obj.get('kill_chain_phases', [])],
                        'platforms': obj.get('x_mitre_platforms', []),
                        'detection': obj.get('x_mitre_detection', []),
                        'mitigation': obj.get('x_mitre_mitigations', []),
                    }
                    if technique['id']:  # Only add if has valid ID
                        techniques.append(technique)
            
            print(f"Downloaded {len(techniques)} techniques")
            
        except Exception as e:
            print(f"Error downloading MITRE ATT&CK: {e}")
            print("Falling back to local file if available...")
            
        return techniques
    
    def save_techniques(self, techniques: List[Dict[str, Any]]) -> Path:
        """
        Save techniques to JSON file.
        
        Args:
            techniques: List of technique dictionaries
        
        Returns:
            Path to saved file
        """
        output_file = self.output_dir / "mitre_attck_techniques.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': 'MITRE ATT&CK',
                    'collected_at': datetime.now().isoformat(),
                    'count': len(techniques)
                },
                'techniques': techniques
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(techniques)} techniques to {output_file}")
        return output_file


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect MITRE ATT&CK data')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'raw' / 'mitre_attck',
        help='Output directory for collected data'
    )
    
    args = parser.parse_args()
    
    collector = MITRECollector(args.output_dir)
    techniques = collector.download_techniques()
    
    if techniques:
        collector.save_techniques(techniques)
        print("MITRE ATT&CK data collection complete!")
    else:
        print("No techniques collected. Check network connection or use local file.")


if __name__ == '__main__':
    main()
