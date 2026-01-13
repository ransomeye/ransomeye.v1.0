#!/usr/bin/env python3
"""
MISHKA Training - Phase 1 (Fixed Dataset Processing)
AUTHORITATIVE: Fixed tokenization to preserve all samples
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
    from datasets import load_dataset, Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: Required libraries not available.")


class Phase1TrainerFixed:
    """Phase 1 trainer with fixed dataset processing."""
    
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.model = None
        self.tokenizer = None
        
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_model_and_tokenizer(self):
        """Load model and tokenizer."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Required libraries not installed")
        
        model_name = self.config['base_model']['name']
        print(f"Loading model: {model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        use_cpu = self.config['cpu']['use_cpu']
        
        if use_cpu:
            try:
                from transformers import BitsAndBytesConfig
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
                print(f"8-bit failed: {e}, using float32")
                import torch
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="cpu",
                    torch_dtype=torch.float32,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
        else:
            import torch
            dtype = torch.float16 if self.config['optimization']['fp16'] else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto",
                torch_dtype=dtype,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
    
    def setup_lora(self):
        """Setup LoRA."""
        lora_config = LoraConfig(
            r=self.config['lora']['r'],
            lora_alpha=self.config['lora']['alpha'],
            target_modules=self.config['lora']['target_modules'],
            lora_dropout=self.config['lora']['dropout'],
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        if self.config['lora']['method'] == 'qlora':
            self.model = prepare_model_for_kbit_training(self.model)
        
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()
    
    def prepare_dataset_simple(self, dataset_path: Path) -> tuple:
        """Prepare dataset with simple, reliable approach."""
        print(f"Loading dataset from {dataset_path}...")
        
        # Load JSONL directly
        examples = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    examples.append(json.loads(line))
        
        print(f"Loaded {len(examples)} examples")
        
        # Limit if needed
        max_samples = self.config['data'].get('max_samples')
        if max_samples and len(examples) > max_samples:
            examples = examples[:max_samples]
            print(f"Limited to {len(examples)} samples")
        
        # Format and tokenize
        print("Tokenizing examples...")
        tokenized_examples = []
        
        for i, example in enumerate(examples):
            # Format prompt
            instruction = example.get('instruction', '')
            input_text = example.get('input', '')
            output = example.get('output', '')
            
            if input_text:
                prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
            else:
                prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
            
            # Tokenize
            tokenized = self.tokenizer(
                prompt,
                truncation=True,
                max_length=self.config['training']['max_length'],
                padding=False,
                return_tensors=None
            )
            
            # Only add if has tokens
            if len(tokenized['input_ids']) > 0:
                tokenized['labels'] = tokenized['input_ids'].copy()
                tokenized_examples.append(tokenized)
            
            if (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(examples)} examples...")
        
        print(f"Tokenized {len(tokenized_examples)} valid examples")
        
        # Create dataset from tokenized examples
        dataset = Dataset.from_list(tokenized_examples)
        
        return dataset
    
    def train(self):
        """Run training."""
        self.load_model_and_tokenizer()
        self.setup_lora()
        
        # Prepare dataset
        train_file = Path(self.config['data']['train_file'])
        tokenized_dataset = self.prepare_dataset_simple(train_file)
        
        # Split
        print("Splitting dataset...")
        if len(tokenized_dataset) < 10:
            train_dataset = tokenized_dataset
            eval_dataset = tokenized_dataset.select(range(min(1, len(tokenized_dataset))))
        else:
            split = tokenized_dataset.train_test_split(test_size=0.1)
            train_dataset = split['train']
            eval_dataset = split['test']
        
        print(f"Training examples: {len(train_dataset)}")
        print(f"Validation examples: {len(eval_dataset)}")
        
        # Training args
        use_cpu = self.config['cpu']['use_cpu']
        
        training_args = TrainingArguments(
            output_dir=str(Path(self.config['training']['output_dir']) / 'phase1'),
            num_train_epochs=self.config['training']['num_train_epochs'],
            per_device_train_batch_size=1 if use_cpu else self.config['training']['per_device_train_batch_size'],
            gradient_accumulation_steps=8 if use_cpu else self.config['training']['gradient_accumulation_steps'],
            learning_rate=self.config['training']['learning_rate'],
            warmup_steps=self.config['training']['warmup_steps'],
            logging_steps=self.config['training']['logging_steps'],
            save_steps=self.config['training']['save_steps'],
            eval_steps=self.config['training']['eval_steps'],
            eval_strategy="steps",
            save_total_limit=self.config['training']['save_total_limit'],
            load_best_model_at_end=self.config['training']['load_best_model_at_end'],
            metric_for_best_model=self.config['training']['metric_for_best_model'],
            greater_is_better=self.config['training']['greater_is_better'],
            fp16=False if use_cpu else self.config['optimization']['fp16'],
            bf16=False,
            gradient_checkpointing=True,
            dataloader_num_workers=0,
            dataloader_pin_memory=False,
            report_to=None,
            max_grad_norm=1.0,
            remove_unused_columns=False,
        )
        
        if use_cpu and self.config['cpu'].get('max_threads'):
            import torch
            torch.set_num_threads(self.config['cpu']['max_threads'])
            print(f"Limited to {self.config['cpu']['max_threads']} CPU threads")
        
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator,
        )
        
        print(f"\nStarting training...")
        print(f"Epochs: {self.config['training']['num_train_epochs']}")
        print(f"Batch size: 1")
        print(f"Learning rate: {self.config['training']['learning_rate']}")
        print()
        
        trainer.train()
        
        final_model_path = Path(training_args.output_dir) / 'final'
        trainer.save_model(str(final_model_path))
        self.tokenizer.save_pretrained(str(final_model_path))
        
        print(f"\n✅ Training complete! Model saved to: {final_model_path}")


def main():
    parser = argparse.ArgumentParser(description='Phase 1 training (fixed)')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'configs' / 'training_config.yaml',
        help='Training config file'
    )
    
    args = parser.parse_args()
    
    if not TRANSFORMERS_AVAILABLE:
        print("Error: Required libraries not installed")
        return 1
    
    trainer = Phase1TrainerFixed(args.config)
    
    try:
        trainer.train()
    except Exception as e:
        print(f"Training failed: {e}")
        raise


if __name__ == '__main__':
    import sys
    sys.exit(main())
