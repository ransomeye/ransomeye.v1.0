#!/usr/bin/env python3
"""
MISHKA Training - Fix Dataset Tokenization
AUTHORITATIVE: Fix tokenization to preserve all valid samples
"""

import json
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer
import argparse

def fix_tokenization(input_file: Path, output_file: Path, max_length: int = 512):
    """Fix dataset tokenization to preserve all samples."""
    print(f"Loading dataset from: {input_file}")
    dataset = load_dataset('json', data_files=str(input_file), split='train')
    print(f"Loaded {len(dataset)} samples")
    
    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained('mistralai/Mistral-7B-v0.1', trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Process and filter
    valid_samples = []
    invalid_count = 0
    
    for i, example in enumerate(dataset):
        instruction = example.get('instruction', '').strip()
        input_text = example.get('input', '').strip()
        output = example.get('output', '').strip()
        
        # Skip if missing required fields
        if not instruction or not output:
            invalid_count += 1
            continue
        
        # Format prompt
        if input_text:
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
        else:
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
        
        # Check token length
        tokens = tokenizer(prompt, truncation=False, return_length=True)
        token_length = tokens['length'][0]
        
        # Keep if reasonable length (even if needs truncation)
        if token_length > 0 and token_length <= max_length * 2:  # Allow some overflow for truncation
            valid_samples.append({
                'instruction': instruction,
                'input': input_text,
                'output': output
            })
        else:
            invalid_count += 1
            if i < 10:
                print(f"  Skipping sample {i}: token length {token_length} (max: {max_length})")
    
    print(f"\nValid samples: {len(valid_samples)}")
    print(f"Invalid/removed: {invalid_count}")
    
    # Save fixed dataset
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample in valid_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"\nSaved {len(valid_samples)} valid samples to: {output_file}")
    return len(valid_samples)

def main():
    parser = argparse.ArgumentParser(description='Fix dataset tokenization')
    parser.add_argument(
        '--input',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_expanded.jsonl',
        help='Input dataset file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path(__file__).parent.parent / 'data' / 'processed' / 'train_fixed.jsonl',
        help='Output fixed dataset file'
    )
    parser.add_argument(
        '--max-length',
        type=int,
        default=512,
        help='Maximum token length'
    )
    
    args = parser.parse_args()
    
    count = fix_tokenization(args.input, args.output, args.max_length)
    print(f"\n✅ Fixed dataset ready with {count} samples")
    print(f"Update config to use: {args.output}")

if __name__ == '__main__':
    main()
