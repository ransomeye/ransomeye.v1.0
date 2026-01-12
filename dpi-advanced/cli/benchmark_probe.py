#!/usr/bin/env python3
"""
RansomEye DPI Advanced - Benchmark Probe CLI
AUTHORITATIVE: Command-line tool for benchmarking DPI probe performance
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_dpi_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_dpi_dir))

from performance.throughput_benchmark import ThroughputBenchmark
from performance.latency_benchmark import LatencyBenchmark


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark DPI probe performance'
    )
    parser.add_argument(
        '--benchmark-type',
        choices=['throughput', 'latency', 'both'],
        default='both',
        help='Type of benchmark to run'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Benchmark duration in seconds (for throughput)'
    )
    parser.add_argument(
        '--packet-size',
        type=int,
        default=64,
        help='Packet size in bytes (for throughput)'
    )
    parser.add_argument(
        '--num-packets',
        type=int,
        default=100000,
        help='Number of packets (for latency)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output benchmark results JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        results = {}
        
        # Run throughput benchmark
        if args.benchmark_type in ['throughput', 'both']:
            print("Running throughput benchmark...")
            throughput_bench = ThroughputBenchmark()
            throughput_results = throughput_bench.run_benchmark(
                duration_seconds=args.duration,
                packet_size=args.packet_size
            )
            throughput_verification = throughput_bench.verify_targets(throughput_results)
            results['throughput'] = {
                'results': throughput_results,
                'verification': throughput_verification
            }
            print(f"Throughput: {throughput_results.get('throughput_gbps', 0.0):.2f} Gbps")
            print(f"CPU: {throughput_results.get('cpu_percent', 0.0):.2f}%")
            print(f"Packet drops: {throughput_results.get('packet_drops', 0)}")
        
        # Run latency benchmark
        if args.benchmark_type in ['latency', 'both']:
            print("Running latency benchmark...")
            latency_bench = LatencyBenchmark()
            latency_results = latency_bench.run_benchmark(num_packets=args.num_packets)
            results['latency'] = latency_results
            print(f"Average latency: {latency_results.get('avg_latency_us', 0.0):.2f} microseconds")
            print(f"P95 latency: {latency_results.get('p95_latency_us', 0.0):.2f} microseconds")
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            print(f"\nBenchmark results written to: {args.output}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Benchmark failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
