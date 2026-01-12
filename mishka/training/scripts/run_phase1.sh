#!/bin/bash
# MISHKA Training - Phase 1 Execution Script
# Cybersecurity Domain Foundation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "MISHKA Phase 1: Cybersecurity Domain Foundation"
echo "=========================================="
echo ""

# Activate environment
cd "$TRAINING_DIR"
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Run Phase 0 first."
    exit 1
fi

source venv/bin/activate

# Check if training data exists
if [ ! -f "data/processed/train_expanded.jsonl" ]; then
    echo "Warning: Expanded training data not found."
    echo "Using basic training data if available..."
    
    if [ ! -f "data/processed/train.jsonl" ]; then
        echo "Error: No training data found. Run data collection first."
        exit 1
    fi
fi

# Update config to use expanded dataset
CONFIG_FILE="configs/training_config.yaml"
if [ -f "data/processed/train_expanded.jsonl" ]; then
    # Update config to use expanded dataset
    sed -i.bak "s|train_file:.*|train_file: \"./data/processed/train_expanded.jsonl\"|" "$CONFIG_FILE"
    echo "Using expanded training dataset"
else
    sed -i.bak "s|train_file:.*|train_file: \"./data/processed/train.jsonl\"|" "$CONFIG_FILE"
    echo "Using basic training dataset"
fi

# Check required libraries
echo "Checking required libraries..."
python3 -c "import transformers, peft, datasets" 2>/dev/null || {
    echo "Installing required libraries..."
    pip install -q transformers peft datasets accelerate bitsandbytes
}

# Run training
echo ""
echo "Starting Phase 1 training..."
echo "This may take several hours depending on dataset size and hardware."
echo ""

python3 scripts/train_phase1.py --config "$CONFIG_FILE"

echo ""
echo "=========================================="
echo "Phase 1 Training Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review training logs in: models/phase1/"
echo "2. Evaluate model performance"
echo "3. Proceed to Phase 2: RansomEye Platform Knowledge"
