#!/bin/bash
# MISHKA Training - Phase 1 with Session Limits
# 5 hours per session, 5 hours per day maximum

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "MISHKA Phase 1: Cybersecurity Domain Foundation"
echo "Session Limits: 5 hours/session, 5 hours/day"
echo "=========================================="
echo ""

cd "$TRAINING_DIR"

# Activate environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run Phase 0 first."
    exit 1
fi

source venv/bin/activate

# Check training status
echo "Checking training status..."
python3 scripts/train_with_limits.py --status

echo ""
read -p "Continue with training? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Training cancelled."
    exit 0
fi

# Run training with limits
echo ""
echo "Starting training with session limits..."
echo "Training will automatically stop at 5 hours or daily limit."
echo ""

python3 scripts/train_with_limits.py --config configs/training_config.yaml

echo ""
echo "=========================================="
echo "Training Session Complete"
echo "=========================================="
echo ""
echo "Check status with: python3 scripts/train_with_limits.py --status"
