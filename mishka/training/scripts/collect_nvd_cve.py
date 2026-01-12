#!/usr/bin/env python3
"""
MISHKA Training - NIST NVD CVE Data Collection
AUTHORITATIVE: Collect CVE data for understanding (not for RAG - that's separate)
"""

import json
import requests
import gzip
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class NVDCollector:
    """Collect NIST NVD CVE data for training (understanding CVE structure)."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize NVD collector.
        
        Args:
            output_dir: Directory to save collected data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # NIST NVD API
        self.base_url = "https://nvd.nist.gov/feeds/json/cve/1.1"
        
    def download_recent_cves(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Download recent CVEs for training (understanding structure).
        
        Note: Full CVE database goes to RAG, not training.
        This is just for teaching model CVE structure.
        
        Args:
            limit: Maximum number of CVEs to download
        
        Returns:
            List of CVE dictionaries
        """
        cves = []
        
        try:
            print(f"Downloading recent CVEs from NIST NVD...")
            url = f"{self.base_url}/nvdcve-1.1-recent.json.gz"
            
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Decompress
            data = json.loads(gzip.decompress(response.content).decode('utf-8'))
            
            # Extract CVEs
            for item in data.get('CVE_Items', [])[:limit]:
                cve_id = item.get('cve', {}).get('CVE_data_meta', {}).get('ID', '')
                if not cve_id:
                    continue
                
                descriptions = item.get('cve', {}).get('description', {}).get('description_data', [])
                description = descriptions[0].get('value', '') if descriptions else ''
                
                # Extract CVSS
                cvss_v3 = item.get('impact', {}).get('baseMetricV3', {})
                cvss_v2 = item.get('impact', {}).get('baseMetricV2', {})
                
                cve = {
                    'cve_id': cve_id,
                    'description': description,
                    'published_date': item.get('publishedDate', ''),
                    'cvss_v3': {
                        'score': cvss_v3.get('cvssV3', {}).get('baseScore', 0.0),
                        'severity': cvss_v3.get('cvssV3', {}).get('baseSeverity', ''),
                    },
                    'cvss_v2': {
                        'score': cvss_v2.get('cvssV2', {}).get('baseScore', 0.0),
                    }
                }
                cves.append(cve)
            
            print(f"Downloaded {len(cves)} CVEs")
            
        except Exception as e:
            print(f"Error downloading NVD data: {e}")
            print("Note: CVE data for RAG should be collected separately")
            
        return cves
    
    def save_cves(self, cves: List[Dict[str, Any]]) -> Path:
        """
        Save CVEs to JSON file.
        
        Args:
            cves: List of CVE dictionaries
        
        Returns:
            Path to saved file
        """
        output_file = self.output_dir / "nvd_cves_sample.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': 'NIST NVD',
                    'collected_at': datetime.now().isoformat(),
                    'count': len(cves),
                    'purpose': 'Training - CVE structure understanding (not for RAG)'
                },
                'cves': cves
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(cves)} CVEs to {output_file}")
        return output_file


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect NIST NVD CVE data for training')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'raw' / 'nvd',
        help='Output directory for collected data'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Maximum number of CVEs to download'
    )
    
    args = parser.parse_args()
    
    collector = NVDCollector(args.output_dir)
    cves = collector.download_recent_cves(limit=args.limit)
    
    if cves:
        collector.save_cves(cves)
        print("NVD CVE data collection complete!")
    else:
        print("No CVEs collected. Check network connection.")


if __name__ == '__main__':
    main()
