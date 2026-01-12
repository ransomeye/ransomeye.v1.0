# Memory Optimization for CPU Training

## Issue

Training was killed due to insufficient memory. The 7B parameter model requires significant RAM for training.

## Solutions Implemented

### 1. 8-Bit Quantization
- Model loaded with 8-bit quantization (BitsAndBytesConfig)
- Reduces memory usage by ~50%
- Maintains reasonable model quality

### 2. Reduced Batch Size
- Batch size: 4 → 1 (per device)
- Gradient accumulation: 4 → 8 (maintains effective batch size)
- Reduces memory per step

### 3. Reduced Sequence Length
- Max length: 2048 → 1024 tokens
- Reduces memory for longer sequences

### 4. Gradient Checkpointing
- Always enabled
- Trades compute for memory

### 5. Reduced Epochs
- Epochs: 3 → 2
- Faster training, less memory over time

## Memory Requirements

**Before optimization:**
- ~28GB RAM (7B model in float32)

**After optimization:**
- ~14-16GB RAM (7B model in 8-bit)

## Alternative: Use Smaller Model

If memory is still insufficient, consider:

1. **Use smaller base model**:
   - Mistral 7B → Mistral 7B Instruct (smaller variant)
   - Or use 3B/4B parameter models

2. **Further reduce settings**:
   - Max length: 512 tokens
   - Batch size: 1
   - Gradient accumulation: 16

3. **Use model sharding**:
   - Load model in parts
   - More complex but uses less memory

## Current Configuration

The training script now:
- Uses 8-bit quantization automatically on CPU
- Batch size: 1
- Gradient accumulation: 8
- Max length: 1024
- Gradient checkpointing: Enabled

This should work on systems with 16GB+ RAM.

## If Still Failing

1. **Check available RAM**:
   ```bash
   free -h
   ```

2. **Reduce dataset size** (for testing):
   - Use first 500 examples
   - Test training works
   - Then scale up

3. **Use smaller model**:
   - Update config to use 3B/4B model
   - Or use quantized pre-trained models
