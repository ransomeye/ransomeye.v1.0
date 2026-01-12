#!/usr/bin/env python3
"""
MISHKA Training - Comprehensive Base Model Evaluation
AUTHORITATIVE: Evaluate multiple base models and select best for CPU inference
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
import argparse

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available. Install for model evaluation.")


class ModelEvaluator:
    """Evaluate a single model."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        
    def load_model(self, use_cpu: bool = True):
        """Load model for evaluation."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library required")
        
        print(f"  Loading {self.model_name}...")
        
        device_map = "cpu" if use_cpu else "auto"
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Set pad token if not set
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=device_map,
                torch_dtype=torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            print(f"  ✓ Loaded successfully")
            
        except Exception as e:
            print(f"  ✗ Error loading: {e}")
            raise
    
    def evaluate_speed(self, prompt: str = "What is cybersecurity?", num_runs: int = 3) -> Dict[str, Any]:
        """Evaluate inference speed."""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        times = []
        tokens_generated = []
        
        for i in range(num_runs):
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            start_time = time.time()
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=50,
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            end_time = time.time()
            
            elapsed = end_time - start_time
            tokens = len(outputs[0]) - len(inputs.input_ids[0])
            
            times.append(elapsed)
            tokens_generated.append(tokens)
        
        avg_time = sum(times) / len(times)
        avg_tokens = sum(tokens_generated) / len(tokens_generated)
        avg_tokens_per_sec = avg_tokens / avg_time if avg_time > 0 else 0
        
        return {
            'avg_time_seconds': avg_time,
            'avg_tokens': avg_tokens,
            'avg_tokens_per_second': avg_tokens_per_sec
        }
    
    def evaluate_memory(self) -> Dict[str, Any]:
        """Evaluate memory usage."""
        if not self.model:
            raise ValueError("Model not loaded")
        
        param_count = sum(p.numel() for p in self.model.parameters())
        model_size_mb = param_count * 4 / (1024 * 1024)  # float32
        
        return {
            'parameter_count': param_count,
            'estimated_size_mb': model_size_mb,
            'estimated_size_gb': model_size_mb / 1024
        }
    
    def test_knowledge(self, test_queries: List[str]) -> List[Dict[str, Any]]:
        """Test basic knowledge."""
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        results = []
        
        for query in test_queries:
            try:
                inputs = self.tokenizer(query, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs.input_ids,
                        max_new_tokens=100,
                        temperature=0.0,
                        do_sample=False,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                results.append({
                    'query': query,
                    'response': response[len(query):].strip()[:200]  # First 200 chars
                })
            except Exception as e:
                results.append({
                    'query': query,
                    'response': f"Error: {e}"
                })
        
        return results


def evaluate_models(models: List[str], output_dir: Path, use_cpu: bool = True):
    """Evaluate multiple models."""
    if not TRANSFORMERS_AVAILABLE:
        print("Error: transformers library required")
        print("Install with: pip install transformers torch")
        return
    
    test_queries = [
        "What is a firewall?",
        "Explain what malware is.",
        "What is the difference between authentication and authorization?",
        "What is lateral movement in cybersecurity?",
        "What is MITRE ATT&CK?"
    ]
    
    all_results = {}
    
    for model_name in models:
        print(f"\n{'='*60}")
        print(f"Evaluating: {model_name}")
        print(f"{'='*60}")
        
        try:
            evaluator = ModelEvaluator(model_name)
            evaluator.load_model(use_cpu=use_cpu)
            
            # Memory evaluation
            print("  Evaluating memory...")
            memory = evaluator.evaluate_memory()
            print(f"    Parameters: {memory['parameter_count']:,}")
            print(f"    Size: {memory['estimated_size_gb']:.2f} GB")
            
            # Speed evaluation
            print("  Evaluating speed...")
            speed = evaluator.evaluate_speed(num_runs=3)
            print(f"    Speed: {speed['avg_tokens_per_second']:.2f} tokens/sec")
            
            # Knowledge test
            print("  Testing knowledge...")
            knowledge = evaluator.test_knowledge(test_queries)
            
            results = {
                'model_name': model_name,
                'memory': memory,
                'speed': speed,
                'knowledge_test': knowledge,
                'evaluation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            all_results[model_name] = results
            
            # Clean up
            del evaluator.model
            del evaluator.tokenizer
            del evaluator
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            print(f"  ✓ Evaluation complete")
            
        except Exception as e:
            print(f"  ✗ Evaluation failed: {e}")
            all_results[model_name] = {
                'model_name': model_name,
                'error': str(e),
                'evaluation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    # Save results
    output_file = output_dir / "base_model_evaluation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'evaluation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'models_evaluated': len(models),
                'cpu_only': use_cpu
            },
            'results': all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print("Evaluation Summary")
    print(f"{'='*60}")
    
    for model_name, result in all_results.items():
        if 'error' not in result:
            print(f"\n{model_name}:")
            print(f"  Size: {result['memory']['estimated_size_gb']:.2f} GB")
            print(f"  Speed: {result['speed']['avg_tokens_per_second']:.2f} tokens/sec")
        else:
            print(f"\n{model_name}: ERROR - {result['error']}")
    
    print(f"\nResults saved to: {output_file}")
    
    # Recommendation
    print(f"\n{'='*60}")
    print("Recommendation")
    print(f"{'='*60}")
    
    valid_results = {k: v for k, v in all_results.items() if 'error' not in v}
    if valid_results:
        # Sort by speed (tokens/sec)
        sorted_models = sorted(
            valid_results.items(),
            key=lambda x: x[1]['speed']['avg_tokens_per_second'],
            reverse=True
        )
        
        if sorted_models:
            best_model = sorted_models[0]
            print(f"\nRecommended base model: {best_model[0]}")
            print(f"  Speed: {best_model[1]['speed']['avg_tokens_per_second']:.2f} tokens/sec")
            print(f"  Size: {best_model[1]['memory']['estimated_size_gb']:.2f} GB")
    else:
        print("\nNo valid evaluations. Check errors above.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Evaluate base models for CPU inference')
    parser.add_argument(
        '--models',
        nargs='+',
        default=[
            'mistralai/Mistral-7B-v0.1',
            # Note: Llama models require HuggingFace access token
            # 'meta-llama/Llama-2-7b-hf',
        ],
        help='List of HuggingFace model names to evaluate'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'evaluation',
        help='Output directory for evaluation results'
    )
    parser.add_argument(
        '--use-cpu',
        action='store_true',
        default=True,
        help='Force CPU usage'
    )
    
    args = parser.parse_args()
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    evaluate_models(args.models, args.output_dir, use_cpu=args.use_cpu)


if __name__ == '__main__':
    main()
