#!/bin/bash
# MISHKA Quick Training - 1 Hour Sessions, Small Dataset
# Fast training for testing and iteration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "MISHKA Quick Training"
echo "1 Hour Sessions | Small Dataset (200 samples)"
echo "=========================================="
echo ""

cd "$TRAINING_DIR"

# Activate environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    exit 1
fi

source venv/bin/activate

# Check status
echo "Training Status:"
python3 scripts/train_with_limits.py --status

echo ""
echo "Starting quick training session (1 hour limit, 200 samples)..."
echo ""

# Run with 1-hour limit
python3 scripts/train_with_limits.py --config configs/training_config.yaml

echo ""
echo "=========================================="
echo "Quick Training Session Complete"
echo "=========================================="
