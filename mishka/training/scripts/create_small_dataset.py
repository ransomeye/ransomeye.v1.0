#!/usr/bin/env python3
"""
MISHKA Training - Create Small Training Dataset
AUTHORITATIVE: Create small dataset for quick training (1-hour sessions)
"""

import json
from pathlib import Path
import argparse
import random


def create_small_dataset(input_file: Path, output_file: Path, num_samples: int = 200):
    """
    Create small training dataset.
    
    Args:
        input_file: Input training file
        output_file: Output file for small dataset
        num_samples: Number of samples to include
    """
    print(f"Creating small training dataset with {num_samples} samples...")
    
    # Read all samples
    all_samples = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    all_samples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    print(f"Loaded {len(all_samples)} total samples")
    
    # Select random sample (or first N if fewer available)
    if len(all_samples) <= num_samples:
        selected = all_samples
        print(f"Using all {len(selected)} samples (less than requested)")
    else:
        # Random selection for diversity
        selected = random.sample(all_samples, num_samples)
        print(f"Randomly selected {len(selected)} samples")
    
    # Write small dataset
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in selected:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"✅ Created small dataset: {output_file}")
    print(f"   Samples: {len(selected)}")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Create small training dataset')
    parser.add_argument(
        '--input-file',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_expanded.jsonl',
        help='Input training file'
    )
    parser.add_argument(
        '--output-file',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_small.jsonl',
        help='Output small dataset file'
    )
    parser.add_argument(
        '--num-samples',
        type=int,
        default=200,
        help='Number of samples (default: 200)'
    )
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1
    
    create_small_dataset(args.input_file, args.output_file, args.num_samples)
    
    print(f"\n💡 To use this dataset, update config:")
    print(f"   train_file: \"{args.output_file.relative_to(Path.cwd())}\"")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
