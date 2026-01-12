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
        DataCollatorForLanguageModeling
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from datasets import load_dataset
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
        """Load base model and tokenizer."""
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
        
        # Load model
        device_map = "cpu" if self.config['cpu']['use_cpu'] else "auto"
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map=device_map,
            torch_dtype="float32" if self.config['cpu']['use_cpu'] else "float16",
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
        prompts = [self.format_prompt(ex) for ex in examples]
        
        tokenized = self.tokenizer(
            prompts,
            truncation=True,
            max_length=self.config['training']['max_length'],
            padding=False,
            return_tensors=None
        )
        
        # For causal LM, labels are the same as input_ids
        tokenized['labels'] = tokenized['input_ids'].copy()
        
        return tokenized
    
    def prepare_dataset(self, dataset: Any) -> Any:
        """Prepare dataset for training."""
        tokenized_dataset = dataset.map(
            self.tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        return tokenized_dataset
    
    def train(self):
        """Run training."""
        # Load model and tokenizer
        self.load_model_and_tokenizer()
        
        # Setup LoRA
        self.setup_lora()
        
        # Load and prepare dataset
        dataset = self.load_dataset()
        tokenized_dataset = self.prepare_dataset(dataset)
        
        # Split into train/validation
        split_dataset = tokenized_dataset.train_test_split(test_size=0.1)
        train_dataset = split_dataset['train']
        eval_dataset = split_dataset['test']
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(Path(self.config['training']['output_dir']) / 'phase1'),
            num_train_epochs=self.config['training']['num_train_epochs'],
            per_device_train_batch_size=self.config['training']['per_device_train_batch_size'],
            gradient_accumulation_steps=self.config['training']['gradient_accumulation_steps'],
            learning_rate=self.config['training']['learning_rate'],
            warmup_steps=self.config['training']['warmup_steps'],
            logging_steps=self.config['training']['logging_steps'],
            save_steps=self.config['training']['save_steps'],
            eval_steps=self.config['training']['eval_steps'],
            evaluation_strategy="steps",
            save_total_limit=self.config['training']['save_total_limit'],
            load_best_model_at_end=self.config['training']['load_best_model_at_end'],
            metric_for_best_model=self.config['training']['metric_for_best_model'],
            greater_is_better=self.config['training']['greater_is_better'],
            fp16=self.config['optimization']['fp16'],
            bf16=self.config['optimization']['bf16'],
            gradient_checkpointing=self.config['optimization']['gradient_checkpointing'],
            dataloader_num_workers=self.config['optimization']['dataloader_num_workers'],
            dataloader_pin_memory=self.config['optimization']['dataloader_pin_memory'],
            report_to=None,  # Disable wandb/mlflow for now
        )
        
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
