#!/bin/bash
# MISHKA Training - Resume Training from Checkpoint
# Resumes from last checkpoint if training was interrupted

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"

cd "$TRAINING_DIR"
source venv/bin/activate

echo "Checking for checkpoints..."
CHECKPOINT_DIR="models/phase1"

if [ -d "$CHECKPOINT_DIR" ]; then
    # Find latest checkpoint
    LATEST_CHECKPOINT=$(find "$CHECKPOINT_DIR" -name "checkpoint-*" -type d | sort -V | tail -1)
    
    if [ -n "$LATEST_CHECKPOINT" ]; then
        echo "Found checkpoint: $LATEST_CHECKPOINT"
        echo "Resuming training..."
        
        # Update config to resume from checkpoint
        python3 -c "
import yaml
from pathlib import Path

config_path = Path('configs/training_config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

config['training']['resume_from_checkpoint'] = '$LATEST_CHECKPOINT'

with open(config_path, 'w') as f:
    yaml.dump(config, f)

print('Config updated to resume from checkpoint')
"
        
        # Run training
        python3 scripts/train_with_limits.py --config configs/training_config.yaml
    else
        echo "No checkpoint found. Starting fresh training..."
        python3 scripts/train_with_limits.py --config configs/training_config.yaml
    fi
else
    echo "No checkpoint directory. Starting fresh training..."
    python3 scripts/train_with_limits.py --config configs/training_config.yaml
fi
