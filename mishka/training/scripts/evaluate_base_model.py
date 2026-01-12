#!/usr/bin/env python3
"""
MISHKA Training - Base Model Evaluation
AUTHORITATIVE: Evaluate base models for CPU inference suitability
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


class BaseModelEvaluator:
    """Evaluate base models for CPU inference."""
    
    def __init__(self, model_name: str, output_dir: Path):
        """
        Initialize evaluator.
        
        Args:
            model_name: HuggingFace model name
            output_dir: Directory to save evaluation results
        """
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.tokenizer = None
        
    def load_model(self, use_cpu: bool = True):
        """Load model for evaluation."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library required for evaluation")
        
        print(f"Loading model: {self.model_name}")
        
        # Force CPU if requested
        device_map = "cpu" if use_cpu else "auto"
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=device_map,
                torch_dtype=torch.float32,  # CPU uses float32
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            print(f"Model loaded successfully on {device_map}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def evaluate_inference_speed(self, prompt: str = "What is cybersecurity?", num_runs: int = 5) -> Dict[str, Any]:
        """
        Evaluate inference speed on CPU.
        
        Args:
            prompt: Test prompt
            num_runs: Number of runs for averaging
        
        Returns:
            Performance metrics
        """
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        print(f"Evaluating inference speed ({num_runs} runs)...")
        
        times = []
        tokens_generated = []
        
        for i in range(num_runs):
            # Tokenize
            inputs = self.tokenizer(prompt, return_tensors="pt")
            
            # Generate
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
            
            # Calculate metrics
            elapsed = end_time - start_time
            tokens = len(outputs[0]) - len(inputs.input_ids[0])
            
            times.append(elapsed)
            tokens_generated.append(tokens)
            
            print(f"Run {i+1}: {elapsed:.2f}s, {tokens} tokens, {tokens/elapsed:.2f} tokens/sec")
        
        avg_time = sum(times) / len(times)
        avg_tokens = sum(tokens_generated) / len(tokens_generated)
        avg_tokens_per_sec = avg_tokens / avg_time
        
        return {
            'avg_time_seconds': avg_time,
            'avg_tokens': avg_tokens,
            'avg_tokens_per_second': avg_tokens_per_sec,
            'runs': num_runs
        }
    
    def evaluate_memory_usage(self) -> Dict[str, Any]:
        """Evaluate memory usage."""
        if not self.model:
            raise ValueError("Model not loaded")
        
        # Estimate model size
        param_count = sum(p.numel() for p in self.model.parameters())
        model_size_mb = param_count * 4 / (1024 * 1024)  # Assuming float32
        
        return {
            'parameter_count': param_count,
            'estimated_size_mb': model_size_mb,
            'estimated_size_gb': model_size_mb / 1024
        }
    
    def test_cybersecurity_knowledge(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Test basic cybersecurity knowledge.
        
        Args:
            test_queries: List of test queries
        
        Returns:
            Test results
        """
        if not self.model or not self.tokenizer:
            raise ValueError("Model not loaded")
        
        results = []
        
        for query in test_queries:
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
                'response': response[len(query):].strip()
            })
        
        return {
            'test_queries': len(test_queries),
            'results': results
        }
    
    def run_full_evaluation(self) -> Dict[str, Any]:
        """Run full evaluation suite."""
        print(f"\n{'='*60}")
        print(f"Evaluating: {self.model_name}")
        print(f"{'='*60}\n")
        
        results = {
            'model_name': self.model_name,
            'evaluation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Memory usage
        print("Evaluating memory usage...")
        memory = self.evaluate_memory_usage()
        results['memory'] = memory
        print(f"  Parameters: {memory['parameter_count']:,}")
        print(f"  Estimated size: {memory['estimated_size_gb']:.2f} GB\n")
        
        # Inference speed
        print("Evaluating inference speed...")
        speed = self.evaluate_inference_speed()
        results['speed'] = speed
        print(f"  Average: {speed['avg_tokens_per_second']:.2f} tokens/sec\n")
        
        # Basic knowledge test
        test_queries = [
            "What is a firewall?",
            "Explain what malware is.",
            "What is the difference between authentication and authorization?"
        ]
        print("Testing basic cybersecurity knowledge...")
        knowledge = self.test_cybersecurity_knowledge(test_queries)
        results['knowledge_test'] = knowledge
        
        return results
    
    def save_results(self, results: Dict[str, Any]):
        """Save evaluation results."""
        output_file = self.output_dir / f"evaluation_{self.model_name.replace('/', '_')}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Evaluate base models for CPU inference')
    parser.add_argument(
        '--model',
        type=str,
        default='mistralai/Mistral-7B-v0.1',
        help='HuggingFace model name to evaluate'
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
    
    if not TRANSFORMERS_AVAILABLE:
        print("Error: transformers library required")
        print("Install with: pip install transformers torch")
        return
    
    evaluator = BaseModelEvaluator(args.model, args.output_dir)
    
    try:
        evaluator.load_model(use_cpu=args.use_cpu)
        results = evaluator.run_full_evaluation()
        evaluator.save_results(results)
        
        print("\n" + "="*60)
        print("Evaluation Summary:")
        print(f"  Model: {results['model_name']}")
        print(f"  Size: {results['memory']['estimated_size_gb']:.2f} GB")
        print(f"  Speed: {results['speed']['avg_tokens_per_second']:.2f} tokens/sec")
        print("="*60)
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        raise


if __name__ == '__main__':
    main()
