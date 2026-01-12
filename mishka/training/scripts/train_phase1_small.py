#!/usr/bin/env python3
"""
MISHKA Training - Phase 1 (Small Dataset Test)
AUTHORITATIVE: Test training with small dataset to verify memory usage
"""

import json
from pathlib import Path
import argparse
import subprocess
import sys

def create_small_dataset(input_file: Path, output_file: Path, num_samples: int = 100):
    """Create a small test dataset."""
    print(f"Creating small test dataset with {num_samples} samples...")
    
    samples = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            if line.strip():
                samples.append(json.loads(line))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"Created test dataset with {len(samples)} samples: {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Test Phase 1 training with small dataset')
    parser.add_argument(
        '--input-file',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_expanded.jsonl',
        help='Input training file'
    )
    parser.add_argument(
        '--num-samples',
        type=int,
        default=100,
        help='Number of samples for test'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'configs' / 'training_config.yaml',
        help='Training config file'
    )
    
    args = parser.parse_args()
    
    # Create small test dataset
    test_file = args.input_file.parent / 'train_test_small.jsonl'
    create_small_dataset(args.input_file, test_file, args.num_samples)
    
    # Temporarily update config
    import yaml
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    original_file = config['data']['train_file']
    config['data']['train_file'] = str(test_file)
    config['training']['num_train_epochs'] = 1  # Just 1 epoch for test
    config['training']['save_steps'] = 50
    config['training']['eval_steps'] = 50
    
    test_config = args.config.parent / 'training_config_test.yaml'
    with open(test_config, 'w') as f:
        yaml.dump(config, f)
    
    print(f"\nRunning test training with {args.num_samples} samples...")
    print("This will verify memory usage and training pipeline.")
    print()
    
    # Run training
    try:
        subprocess.run([
            sys.executable,
            Path(__file__).parent / 'train_phase1.py',
            '--config', str(test_config)
        ], check=True)
        
        print("\n" + "="*60)
        print("Test training successful!")
        print("You can now run full training with:")
        print(f"  bash scripts/run_phase1.sh")
        print("="*60)
        
    except subprocess.CalledProcessError as e:
        print(f"\nTest training failed: {e}")
        print("Check memory usage and consider further optimizations.")
        sys.exit(1)
    finally:
        # Cleanup
        if test_config.exists():
            test_config.unlink()

if __name__ == '__main__':
    main()
