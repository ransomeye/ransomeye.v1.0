#!/usr/bin/env python3
"""
MISHKA Training - Phase 1 (Chunked Training)
AUTHORITATIVE: Train in chunks to manage memory
"""

import json
import yaml
from pathlib import Path
import argparse
import subprocess
import sys

def split_dataset(input_file: Path, chunk_size: int = 500):
    """Split large dataset into chunks."""
    chunks = []
    current_chunk = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                current_chunk.append(line)
                if len(current_chunk) >= chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
    
    return chunks

def train_chunk(chunk_data: list, chunk_num: int, config_path: Path, output_base: Path):
    """Train on a single chunk."""
    chunk_file = output_base / f'train_chunk_{chunk_num}.jsonl'
    
    # Write chunk to file
    with open(chunk_file, 'w', encoding='utf-8') as f:
        for line in chunk_data:
            f.write(line)
    
    # Update config for this chunk
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['data']['train_file'] = str(chunk_file)
    config['training']['num_train_epochs'] = 1  # 1 epoch per chunk
    config['training']['output_dir'] = str(output_base / f'chunk_{chunk_num}')
    
    chunk_config = config_path.parent / f'training_config_chunk_{chunk_num}.yaml'
    with open(chunk_config, 'w') as f:
        yaml.dump(config, f)
    
    # Run training
    print(f"\nTraining chunk {chunk_num} ({len(chunk_data)} samples)...")
    result = subprocess.run([
        "python3",
        Path(__file__).parent / 'train_phase1.py',
        '--config', str(chunk_config)
    ])
    
    # Cleanup
    if chunk_config.exists():
        chunk_config.unlink()
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description='Train Phase 1 in chunks')
    parser.add_argument(
        '--input-file',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_expanded.jsonl',
        help='Input training file'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Samples per chunk'
    )
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'configs' / 'training_config.yaml',
        help='Base training config'
    )
    
    args = parser.parse_args()
    
    print("Splitting dataset into chunks...")
    chunks = split_dataset(args.input_file, args.chunk_size)
    print(f"Created {len(chunks)} chunks")
    
    output_base = Path(args.config).parent.parent / 'models' / 'phase1_chunked'
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Train each chunk
    for i, chunk in enumerate(chunks, 1):
        success = train_chunk(chunk, i, args.config, output_base)
        if not success:
            print(f"Chunk {i} training failed. Stopping.")
            return 1
    
    print(f"\nAll chunks trained successfully!")
    print(f"Models saved in: {output_base}")
    print("\nNote: You'll need to merge/combine the chunk models for final use.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
