#!/usr/bin/env python3
"""
MISHKA Training - Test Dataset Creation
AUTHORITATIVE: Create evaluation test datasets
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import argparse


class TestDatasetCreator:
    """Create test datasets for evaluation."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize creator.
        
        Args:
            output_dir: Directory to save test datasets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_cybersecurity_test_set(self) -> List[Dict[str, Any]]:
        """Create cybersecurity concept test set."""
        test_queries = [
            {
                'query': 'What is lateral movement in cybersecurity?',
                'expected_topics': ['lateral movement', 'network', 'authentication', 'MITRE ATT&CK'],
                'category': 'cybersecurity_concept'
            },
            {
                'query': 'Explain what a zero-day vulnerability is.',
                'expected_topics': ['zero-day', 'vulnerability', 'exploit', 'patch'],
                'category': 'cybersecurity_concept'
            },
            {
                'query': 'What is the difference between authentication and authorization?',
                'expected_topics': ['authentication', 'authorization', 'access control'],
                'category': 'cybersecurity_concept'
            },
            {
                'query': 'What is a killchain in cybersecurity?',
                'expected_topics': ['killchain', 'attack stages', 'Lockheed Martin', 'MITRE ATT&CK'],
                'category': 'cybersecurity_concept'
            },
            {
                'query': 'How does ransomware work?',
                'expected_topics': ['ransomware', 'encryption', 'extortion', 'malware'],
                'category': 'cybersecurity_concept'
            },
            {
                'query': 'What is MITRE ATT&CK technique T1055?',
                'expected_topics': ['T1055', 'Process Injection', 'MITRE ATT&CK'],
                'category': 'mitre_attck'
            },
            {
                'query': 'What is a CVE and how is it structured?',
                'expected_topics': ['CVE', 'vulnerability', 'identifier', 'structure'],
                'category': 'vulnerability_management'
            },
            {
                'query': 'What does CVSS score 9.8 mean?',
                'expected_topics': ['CVSS', '9.8', 'critical', 'severity'],
                'category': 'vulnerability_management'
            },
            {
                'query': 'What is digital forensics?',
                'expected_topics': ['forensics', 'evidence', 'investigation', 'analysis'],
                'category': 'forensics'
            },
            {
                'query': 'How do you detect SQL injection attacks?',
                'expected_topics': ['SQL injection', 'detection', 'web application', 'database'],
                'category': 'detection'
            }
        ]
        
        return test_queries
    
    def create_ransomeye_test_set(self) -> List[Dict[str, Any]]:
        """Create RansomEye platform test set."""
        test_queries = [
            {
                'query': 'What is the Audit Ledger in RansomEye?',
                'expected_topics': ['audit ledger', 'system actions', 'immutable', 'append-only'],
                'category': 'ransomeye_architecture'
            },
            {
                'query': 'How does the Threat Graph work?',
                'expected_topics': ['threat graph', 'entities', 'relationships', 'correlation'],
                'category': 'ransomeye_architecture'
            },
            {
                'query': 'What is the Risk Index?',
                'expected_topics': ['risk index', 'risk score', 'confidence', 'computation'],
                'category': 'ransomeye_architecture'
            },
            {
                'query': 'How do I check the risk score for an incident?',
                'expected_topics': ['risk score', 'incident', 'query', 'confidence_score'],
                'category': 'ransomeye_workflow'
            },
            {
                'query': 'What are the incident stages in RansomEye?',
                'expected_topics': ['incident stages', 'CLEAN', 'SUSPICIOUS', 'PROBABLE', 'CONFIRMED'],
                'category': 'ransomeye_concepts'
            }
        ]
        
        return test_queries
    
    def create_conversational_test_set(self) -> List[Dict[str, Any]]:
        """Create conversational test set."""
        conversations = [
            {
                'conversation': [
                    {'role': 'user', 'content': 'Hey, what is lateral movement?'},
                    {'role': 'assistant', 'content': 'Lateral movement is...'},
                    {'role': 'user', 'content': 'How do I detect it?'},
                    {'role': 'assistant', 'content': 'To detect lateral movement...'}
                ],
                'category': 'multi_turn'
            },
            {
                'conversation': [
                    {'role': 'user', 'content': "What's up with incident abc-123?"},
                    {'role': 'assistant', 'content': 'Incident abc-123...'},
                ],
                'category': 'casual_query'
            }
        ]
        
        return conversations
    
    def save_test_sets(self):
        """Save all test sets."""
        # Cybersecurity test set
        cybersec_test = self.create_cybersecurity_test_set()
        with open(self.output_dir / 'cybersecurity_test.json', 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'name': 'Cybersecurity Concept Test Set',
                    'count': len(cybersec_test),
                    'purpose': 'Evaluate cybersecurity domain knowledge'
                },
                'test_queries': cybersec_test
            }, f, indent=2, ensure_ascii=False)
        print(f"Created cybersecurity test set: {len(cybersec_test)} queries")
        
        # RansomEye test set
        ransomeye_test = self.create_ransomeye_test_set()
        with open(self.output_dir / 'ransomeye_test.json', 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'name': 'RansomEye Platform Test Set',
                    'count': len(ransomeye_test),
                    'purpose': 'Evaluate RansomEye platform knowledge'
                },
                'test_queries': ransomeye_test
            }, f, indent=2, ensure_ascii=False)
        print(f"Created RansomEye test set: {len(ransomeye_test)} queries")
        
        # Conversational test set
        conversational_test = self.create_conversational_test_set()
        with open(self.output_dir / 'conversational_test.json', 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'name': 'Conversational Test Set',
                    'count': len(conversational_test),
                    'purpose': 'Evaluate conversational quality'
                },
                'conversations': conversational_test
            }, f, indent=2, ensure_ascii=False)
        print(f"Created conversational test set: {len(conversational_test)} conversations")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Create test datasets for evaluation')
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'test',
        help='Output directory for test datasets'
    )
    
    args = parser.parse_args()
    
    creator = TestDatasetCreator(args.output_dir)
    creator.save_test_sets()
    print("\nTest datasets created successfully!")


if __name__ == '__main__':
    main()
