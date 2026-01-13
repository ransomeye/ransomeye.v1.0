#!/usr/bin/env python3
"""
MISHKA Training - Dataset Issue Diagnosis
AUTHORITATIVE: Diagnose why 1000 samples become 29 training examples
"""

import json
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer

def diagnose_dataset():
    """Diagnose dataset tokenization issue."""
    print("="*60)
    print("Dataset Issue Diagnosis")
    print("="*60)
    
    # Load dataset
    dataset_file = Path(__file__).parent.parent / 'data' / 'processed' / 'train_expanded.jsonl'
    print(f"\n1. Loading dataset from: {dataset_file}")
    
    dataset = load_dataset('json', data_files=str(dataset_file), split='train')
    print(f"   Total samples in file: {len(dataset)}")
    
    # Check sample structure
    print(f"\n2. Checking sample structure...")
    sample = dataset[0]
    print(f"   Sample keys: {sample.keys()}")
    print(f"   Instruction length: {len(sample.get('instruction', ''))}")
    print(f"   Output length: {len(sample.get('output', ''))}")
    
    # Try tokenization
    print(f"\n3. Testing tokenization...")
    try:
        tokenizer = AutoTokenizer.from_pretrained('mistralai/Mistral-7B-v0.1', trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        max_length = 512
        valid_samples = 0
        invalid_samples = 0
        too_long_samples = 0
        
        for i, example in enumerate(dataset[:100]):  # Test first 100
            instruction = example.get('instruction', '')
            input_text = example.get('input', '')
            output = example.get('output', '')
            
            if input_text:
                prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
            else:
                prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            
            # Tokenize
            tokens = tokenizer(prompt, truncation=True, max_length=max_length, return_length=True)
            token_length = tokens['length'][0]
            
            if token_length == 0:
                invalid_samples += 1
                if i < 5:
                    print(f"   Sample {i}: INVALID (empty after tokenization)")
            elif token_length >= max_length:
                too_long_samples += 1
                if i < 5:
                    print(f"   Sample {i}: TOO LONG ({token_length} tokens, truncated)")
            else:
                valid_samples += 1
                if i < 5:
                    print(f"   Sample {i}: OK ({token_length} tokens)")
        
        print(f"\n   Results from first 100 samples:")
        print(f"   - Valid: {valid_samples}")
        print(f"   - Too long (truncated): {too_long_samples}")
        print(f"   - Invalid: {invalid_samples}")
        
    except Exception as e:
        print(f"   Error during tokenization test: {e}")
    
    # Check for empty/invalid samples
    print(f"\n4. Checking for empty samples...")
    empty_instructions = sum(1 for ex in dataset if not ex.get('instruction', '').strip())
    empty_outputs = sum(1 for ex in dataset if not ex.get('output', '').strip())
    print(f"   Empty instructions: {empty_instructions}")
    print(f"   Empty outputs: {empty_outputs}")
    
    # Check sample lengths
    print(f"\n5. Checking sample lengths...")
    instruction_lengths = [len(ex.get('instruction', '')) for ex in dataset[:100]]
    output_lengths = [len(ex.get('output', '')) for ex in dataset[:100]]
    print(f"   Instruction lengths: min={min(instruction_lengths)}, max={max(instruction_lengths)}, avg={sum(instruction_lengths)/len(instruction_lengths):.0f}")
    print(f"   Output lengths: min={min(output_lengths)}, max={max(output_lengths)}, avg={sum(output_lengths)/len(output_lengths):.0f}")
    
    print("\n" + "="*60)
    print("Diagnosis Complete")
    print("="*60)

if __name__ == '__main__':
    diagnose_dataset()
