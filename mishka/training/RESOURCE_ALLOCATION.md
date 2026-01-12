# Resource Allocation - 50% Limit

## System Resources
- **Total CPU Cores**: 4
- **Total RAM**: 32GB
- **Allocation**: 50% maximum
  - **CPU**: 2 cores
  - **RAM**: 16GB

## Configuration Applied

### CPU Threads
- **Max Threads**: 2 (50% of 4 cores)
- Set via `torch.set_num_threads(2)`
- Prevents overloading system

### Memory Limits
- **Max Memory**: 16GB (50% of 32GB)
- Model loading limited to 16GB
- Training overhead stays within limit

### Training Settings
- **Batch Size**: 1 (minimal memory)
- **Gradient Accumulation**: 8 (maintains effective batch size)
- **DataLoader Workers**: 1 (reduced for 2-core limit)
- **Sequence Length**: 1024 tokens (memory efficient)

## Expected Resource Usage

### During Training
- **CPU**: ~2 cores (50%)
- **RAM**: ~12-14GB (within 16GB limit)
- **Model**: ~7-8GB (8-bit quantized)
- **Training Overhead**: ~4-6GB

### System Remains Responsive
- 2 CPU cores free for other tasks
- 16GB+ RAM free for system
- Training runs in background

## Monitoring

Check resource usage:
```bash
# CPU usage
htop  # Press '1' to see per-core usage

# Memory usage
free -h

# During training
watch -n 1 'free -h && echo "---" && ps aux | grep python | grep train'
```

## Optimization Notes

- **8-bit quantization**: Reduces model memory by ~50%
- **Small batch size**: Minimizes memory spikes
- **Gradient checkpointing**: Trades compute for memory
- **Limited threads**: Prevents CPU overload

Training will be slower but stable and won't impact system performance.
