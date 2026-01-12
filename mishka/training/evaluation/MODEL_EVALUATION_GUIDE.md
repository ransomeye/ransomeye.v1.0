# Base Model Evaluation Guide

## Overview

Model evaluation downloads and tests large models (7B+ parameters), which can take significant time and disk space. This guide explains how to run evaluations.

## Recommended Models to Evaluate

1. **Mistral 7B** (`mistralai/Mistral-7B-v0.1`)
   - Good balance of performance and size
   - Strong reasoning capabilities
   - CPU-friendly

2. **Llama 2 7B** (`meta-llama/Llama-2-7b-hf`)
   - Requires HuggingFace access token
   - Good general performance
   - Well-documented

3. **Llama 2 13B** (`meta-llama/Llama-2-13b-hf`)
   - Larger, better performance
   - Requires more memory
   - Slower on CPU

## Running Evaluation

### Quick Evaluation (Single Model)
```bash
cd mishka/training
source venv/bin/activate
python3 scripts/evaluate_all_models.py \
    --models mistralai/Mistral-7B-v0.1 \
    --output-dir evaluation
```

### Full Evaluation (Multiple Models)
```bash
python3 scripts/evaluate_all_models.py \
    --models mistralai/Mistral-7B-v0.1 \
             meta-llama/Llama-2-7b-hf \
    --output-dir evaluation
```

**Note**: This will download models (14GB+ each) and may take 30+ minutes.

## Evaluation Metrics

The script evaluates:
- **Memory Usage**: Model size, parameter count
- **Inference Speed**: Tokens per second on CPU
- **Knowledge Test**: Basic cybersecurity knowledge

## Expected Results

For CPU inference on a modern CPU:
- **Mistral 7B**: ~1-3 tokens/sec
- **Llama 2 7B**: ~1-2 tokens/sec
- **Llama 2 13B**: ~0.5-1 tokens/sec

## Selection Criteria

Choose model based on:
1. **Speed**: Tokens/sec (higher is better)
2. **Size**: Must fit in available RAM
3. **Quality**: Knowledge test results

## Recommendation

For MISHKA Phase 1, **Mistral 7B** is recommended:
- Good CPU performance
- Strong reasoning
- Reasonable size (~14GB)
- No special access required

## Next Steps

After evaluation:
1. Review `evaluation/base_model_evaluation.json`
2. Update `configs/training_config.yaml` with selected model
3. Proceed to Phase 1 training
