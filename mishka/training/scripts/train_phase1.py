#!/usr/bin/env python3
"""
MISHKA Training - Phase 1: Cybersecurity Domain Foundation
AUTHORITATIVE: Fine-tune model on cybersecurity domain knowledge
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import argparse
import os

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        BitsAndBytesConfig
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import load_dataset
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: Required libraries not available. Install with:")
    print("  pip install transformers peft datasets accelerate bitsandbytes")


class Phase1Trainer:
    """Phase 1 trainer for cybersecurity domain foundation."""
    
    def __init__(self, config_path: Path):
        """
        Initialize trainer.
        
        Args:
            config_path: Path to training configuration YAML
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.model = None
        self.tokenizer = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load training configuration."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_model_and_tokenizer(self):
        """Load base model and tokenizer with memory optimization."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Required libraries not installed")
        
        model_name = self.config['base_model']['name']
        print(f"Loading model: {model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Memory-optimized loading for CPU
        use_cpu = self.config['cpu']['use_cpu']
        use_qlora = self.config['lora']['method'] == 'qlora'
        
        if use_cpu:
            # For CPU, try 8-bit quantization first, fallback to float32 if it fails
            print("Attempting 8-bit quantization for CPU training (memory optimization)")
            
            try:
                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    llm_int8_threshold=6.0,
                )
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
                print("Model loaded with 8-bit quantization")
            except Exception as e:
                print(f"8-bit quantization failed: {e}")
                print("Falling back to float32 with aggressive memory settings...")
                
                # Fallback: Use float32 with memory limits (50% of 32GB = 16GB)
                max_memory_gb = self.config['cpu'].get('max_memory_gb', 16)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="cpu",
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                    max_memory={"cpu": f"{max_memory_gb}GiB"}  # Limit memory usage
                )
                print(f"Model loaded in float32 (memory-limited to {max_memory_gb}GB)")
        else:
            # GPU path
            device_map = "auto"
            dtype = torch.float16 if self.config['optimization']['fp16'] else torch.float32
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map=device_map,
                torch_dtype=dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            print(f"Model loaded on {device_map}")
    
    def setup_lora(self):
        """Setup LoRA/QLoRA configuration."""
        lora_config_dict = self.config['lora']
        
        lora_config = LoraConfig(
            r=lora_config_dict['r'],
            lora_alpha=lora_config_dict['alpha'],
            target_modules=lora_config_dict['target_modules'],
            lora_dropout=lora_config_dict['dropout'],
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        # Prepare model for QLoRA if using QLoRA
        if lora_config_dict['method'] == 'qlora':
            self.model = prepare_model_for_kbit_training(self.model)
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
        
        print("LoRA configuration applied")
    
    def load_dataset(self) -> Any:
        """Load training dataset."""
        train_file = Path(self.config['data']['train_file'])
        
        if not train_file.exists():
            raise FileNotFoundError(f"Training file not found: {train_file}")
        
        print(f"Loading dataset from {train_file}")
        
        # Load JSONL file
        dataset = load_dataset('json', data_files=str(train_file), split='train')
        
        # Limit samples if specified
        max_samples = self.config['data'].get('max_samples')
        if max_samples:
            dataset = dataset.select(range(min(max_samples, len(dataset))))
        
        print(f"Loaded {len(dataset)} training examples")
        
        return dataset
    
    def format_prompt(self, example: Dict[str, Any]) -> str:
        """Format training example as prompt."""
        instruction = example.get('instruction', '')
        input_text = example.get('input', '')
        output = example.get('output', '')
        
        if input_text:
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
        else:
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
        
        return prompt
    
    def tokenize_function(self, examples: Dict[str, Any]) -> Dict[str, Any]:
        """Tokenize examples."""
        # When batched=True, examples is a dict with lists as values
        # Convert to list of dicts first
        if isinstance(examples, dict) and all(isinstance(v, list) for v in examples.values()):
            # Batched mode: convert dict of lists to list of dicts
            num_examples = len(examples.get('instruction', []))
            example_list = [
                {key: examples[key][i] for key in examples.keys()}
                for i in range(num_examples)
            ]
        else:
            # Single example mode
            example_list = [examples] if not isinstance(examples, list) else examples
        
        # Format prompts
        prompts = [self.format_prompt(ex) for ex in example_list]
        
        tokenized = self.tokenizer(
            prompts,
            truncation=True,
            max_length=self.config['training']['max_length'],
            padding=False,
            return_tensors=None
        )
        
        # For causal LM, labels are the same as input_ids
        # Create labels by copying input_ids
        labels = []
        for input_ids in tokenized['input_ids']:
            labels.append(input_ids.copy())
        tokenized['labels'] = labels
        
        return tokenized
    
    def prepare_dataset(self, dataset: Any) -> Any:
        """Prepare dataset for training with memory optimization."""
        # Process in smaller batches to reduce memory spikes
        batch_size = 32  # Smaller batches for memory efficiency
        
        print(f"Tokenizing {len(dataset)} samples...")
        
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            batch_size=batch_size,
            remove_columns=dataset.column_names,
            desc="Tokenizing dataset"
        )
        
        print(f"Tokenized dataset has {len(tokenized_dataset)} samples")
        
        # Filter out any empty or invalid samples
        def filter_empty(example):
            return len(example.get('input_ids', [])) > 0
        
        original_len = len(tokenized_dataset)
        tokenized_dataset = tokenized_dataset.filter(filter_empty)
        filtered_len = len(tokenized_dataset)
        
        if filtered_len < original_len:
            print(f"Filtered out {original_len - filtered_len} empty samples")
        
        print(f"Final dataset size: {len(tokenized_dataset)} samples")
        
        return tokenized_dataset
    
    def train(self):
        """Run training."""
        # Load model and tokenizer
        self.load_model_and_tokenizer()
        
        # Setup LoRA
        self.setup_lora()
        
        # Load and prepare dataset with memory management
        print("Loading dataset...")
        dataset = self.load_dataset()
        
        # Limit dataset size if too large (for memory management)
        max_samples = self.config['data'].get('max_samples')
        if max_samples and len(dataset) > max_samples:
            print(f"Limiting dataset to {max_samples} samples for memory efficiency")
            dataset = dataset.select(range(max_samples))
        
        print("Tokenizing dataset (this may take a while and use memory)...")
        # Force garbage collection before tokenization
        import gc
        gc.collect()
        
        tokenized_dataset = self.prepare_dataset(dataset)
        
        # Clear original dataset from memory
        del dataset
        gc.collect()
        
        print("Splitting dataset...")
        # Split into train/validation
        # For small datasets, ensure minimum samples
        min_test_samples = max(1, len(tokenized_dataset) // 10)
        test_size = min(0.1, min_test_samples / len(tokenized_dataset))
        
        if len(tokenized_dataset) < 10:
            # Very small dataset - use all for training, create minimal eval
            train_dataset = tokenized_dataset
            eval_dataset = tokenized_dataset.select(range(min(1, len(tokenized_dataset))))
        else:
            split_dataset = tokenized_dataset.train_test_split(test_size=test_size)
            train_dataset = split_dataset['train']
            eval_dataset = split_dataset['test']
        
        # Clear tokenized dataset from memory
        del tokenized_dataset
        gc.collect()
        
        # Training arguments with memory optimization
        use_cpu = self.config['cpu']['use_cpu']
        
        training_args = TrainingArguments(
            output_dir=str(Path(self.config['training']['output_dir']) / 'phase1'),
            num_train_epochs=self.config['training']['num_train_epochs'],
            # Reduce batch size for CPU to save memory
            per_device_train_batch_size=1 if use_cpu else self.config['training']['per_device_train_batch_size'],
            gradient_accumulation_steps=8 if use_cpu else self.config['training']['gradient_accumulation_steps'],
            learning_rate=self.config['training']['learning_rate'],
            warmup_steps=self.config['training']['warmup_steps'],
            logging_steps=self.config['training']['logging_steps'],
            save_steps=self.config['training']['save_steps'],
            eval_steps=self.config['training']['eval_steps'],
            eval_strategy="steps",  # Changed from evaluation_strategy to eval_strategy
            save_total_limit=self.config['training']['save_total_limit'],
            load_best_model_at_end=self.config['training']['load_best_model_at_end'],
            metric_for_best_model=self.config['training']['metric_for_best_model'],
            greater_is_better=self.config['training']['greater_is_better'],
            # Disable fp16/bf16 on CPU (not supported)
            fp16=False if use_cpu else self.config['optimization']['fp16'],
            bf16=False,  # CPU doesn't support bf16
            gradient_checkpointing=True,  # Always enable for memory savings
            dataloader_num_workers=0 if use_cpu else self.config['optimization']['dataloader_num_workers'],
            dataloader_pin_memory=False,  # CPU doesn't need pinning
            report_to=None,  # Disable wandb/mlflow for now
            # Additional memory optimizations
            max_grad_norm=1.0,
            remove_unused_columns=False,
        )
        
        # Set CPU thread limit if specified
        if use_cpu and self.config['cpu'].get('max_threads'):
            max_threads = self.config['cpu']['max_threads']
            torch.set_num_threads(max_threads)
            print(f"Limited to {max_threads} CPU threads (50% resource allocation)")
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )
        
        # Train
        print("\nStarting training...")
        print(f"Training examples: {len(train_dataset)}")
        print(f"Validation examples: {len(eval_dataset)}")
        print(f"Epochs: {self.config['training']['num_train_epochs']}")
        print(f"Batch size: {self.config['training']['per_device_train_batch_size']}")
        print(f"Learning rate: {self.config['training']['learning_rate']}")
        print()
        
        trainer.train()
        
        # Save final model
        final_model_path = Path(training_args.output_dir) / 'final'
        trainer.save_model(str(final_model_path))
        self.tokenizer.save_pretrained(str(final_model_path))
        
        print(f"\nTraining complete! Model saved to: {final_model_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Phase 1: Cybersecurity Domain Foundation Training')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'configs' / 'training_config.yaml',
        help='Path to training configuration file'
    )
    
    args = parser.parse_args()
    
    if not TRANSFORMERS_AVAILABLE:
        print("Error: Required libraries not installed")
        print("Install with: pip install transformers peft datasets accelerate bitsandbytes")
        return
    
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}")
        return
    
    trainer = Phase1Trainer(args.config)
    
    try:
        trainer.train()
    except Exception as e:
        print(f"Training failed: {e}")
        raise


if __name__ == '__main__':
    main()
