# Final Memory Optimization

## Issue
Training killed during dataset tokenization with full 1,912 sample dataset.

## Additional Optimizations Applied

### 1. Reduced Sequence Length
- **Max Length**: 1024 → **512 tokens**
- Reduces memory per sample significantly
- Still sufficient for training

### 2. Dataset Processing Optimization
- **Batch processing**: Smaller batches (32 samples) during tokenization
- **Garbage collection**: Force GC before/after tokenization
- **Memory cleanup**: Delete datasets after processing

### 3. Limited Dataset Size
- **Max samples**: 1,000 (configurable)
- Can train on subset first, then expand
- Prevents memory overflow

### 4. Chunked Training Option
- **Script**: `train_phase1_chunked.py`
- Trains in chunks of 500 samples
- Merges results after
- Alternative if full training still fails

## Current Settings

```yaml
max_length: 512 tokens
max_samples: 1000 (can adjust)
batch_size: 1
gradient_accumulation: 8
CPU threads: 2
Max memory: 16GB
```

## Try Again

### Option 1: Limited Dataset (Recommended)
```bash
cd mishka/training
bash scripts/run_phase1.sh
```

This will use 1,000 samples (configurable in config file).

### Option 2: Further Reduce
Edit `configs/training_config.yaml`:
```yaml
data:
  max_samples: 500  # Even smaller
```

### Option 3: Chunked Training
```bash
cd mishka/training
source venv/bin/activate
python3 scripts/train_phase1_chunked.py --chunk-size 500
```

## Memory Usage Estimate

With optimizations:
- **Model (8-bit)**: ~7-8GB
- **Dataset (1000 samples, 512 tokens)**: ~2-3GB
- **Training overhead**: ~3-4GB
- **Total**: ~12-15GB (should fit in 16GB limit)

## If Still Failing

1. **Reduce max_samples further**: 500, 300, 200
2. **Reduce max_length**: 256 tokens
3. **Use chunked training**: Process in smaller pieces
4. **Check actual memory**: `free -h` during training

The optimizations should now work. Try running again!
