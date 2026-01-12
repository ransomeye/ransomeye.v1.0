# RansomEye DPI Advanced - CPU Profile

**AUTHORITATIVE:** CPU performance profile documentation

## Performance Targets

- **10 Gbps sustained throughput**
- **<5% CPU per 1 Gbps**
- **Zero packet drops at 64-byte packets (AF_PACKET)**
- **Bounded memory (ring buffers only)**
- **Backpressure under congestion (no OOM)**

## CPU Affinity

- **Core pinning**: DPI probe threads pinned to dedicated CPU cores
- **NUMA awareness**: Memory allocation aligned with CPU cores
- **Interrupt balancing**: IRQ affinity configured for optimal distribution

## Memory Management

- **Ring buffers only**: Bounded memory using ring buffers
- **No dynamic allocation**: All memory pre-allocated
- **Backpressure**: Flow control under congestion

## Benchmark Results

### Throughput Benchmark

- **Target**: 10 Gbps sustained
- **Method**: Reproducible packet generation and processing
- **Measurement**: Actual throughput, packet drops, CPU usage

### Latency Benchmark

- **Target**: <100 microseconds per packet
- **Method**: High-resolution timing measurements
- **Measurement**: P50, P95, P99 latencies

## Profiling Tools

- **perf**: Linux perf tool for CPU profiling
- **eBPF**: eBPF-based performance monitoring
- **System metrics**: CPU, memory, network statistics

## Reproducibility

All benchmarks must be:
- **Reproducible**: Same conditions = same results
- **Documented**: Full test environment documented
- **Verifiable**: Results can be independently verified

---

**AUTHORITATIVE**: This is the single authoritative source for DPI Advanced CPU profile documentation.
