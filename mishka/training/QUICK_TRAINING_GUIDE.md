# Quick Training Guide - 1 Hour Sessions

## Quick Training Setup

- **Session Limit**: 1 hour per session
- **Dataset Size**: 200 samples (small, fast)
- **Sequence Length**: 256 tokens (reduced)
- **Epochs**: 1 (single epoch for speed)

## Why Quick Training?

1. **Faster Iteration**: Test training pipeline quickly
2. **Resource Friendly**: Uses minimal resources
3. **Quick Validation**: Verify everything works
4. **Easy Testing**: Can run multiple sessions per day

## Usage

### Create Small Dataset
```bash
cd mishka/training
source venv/bin/activate
python3 scripts/create_small_dataset.py --num-samples 200
```

### Start Quick Training
```bash
bash scripts/quick_train.sh
```

This will:
- Use 200 samples
- Train for max 1 hour
- Save checkpoint
- Complete quickly

## Expected Times

### With 200 Samples
- **Dataset loading**: ~10 seconds
- **Tokenization**: ~5 seconds
- **Training**: ~15-30 minutes (1 epoch)
- **Total**: ~20-40 minutes per session

### Multiple Sessions
- **Session 1**: 200 samples, 1 epoch (20-40 min)
- **Session 2**: Another 200 samples, 1 epoch (20-40 min)
- **Can do 5-10 sessions per day** (within 5-hour limit)

## Training Strategy

### Option 1: Multiple Small Sessions
- Run 200 samples per session
- Each session ~20-40 minutes
- Can do multiple sessions per day
- Accumulates training over time

### Option 2: Gradual Increase
- Start: 200 samples
- Once working: 500 samples
- Then: 1000 samples
- Finally: Full dataset

## Configuration

Current quick training config:
```yaml
max_samples: 200
max_length: 256 tokens
num_epochs: 1
session_limit: 1 hour
```

## Benefits

1. **Fast**: Complete in 20-40 minutes
2. **Testable**: Verify pipeline quickly
3. **Iterative**: Can run many sessions
4. **Low Risk**: Small resource usage
5. **Flexible**: Easy to adjust

## Commands

```bash
# Create small dataset
python3 scripts/create_small_dataset.py --num-samples 200

# Quick training (1 hour limit)
bash scripts/quick_train.sh

# Check status
python3 scripts/train_with_limits.py --status
```

## Next Steps

1. **Test with 200 samples**: Verify everything works
2. **If successful**: Increase to 500 samples
3. **Then**: 1000 samples
4. **Finally**: Full dataset when ready

Quick training makes it easy to test and iterate!
