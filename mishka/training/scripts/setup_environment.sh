#!/bin/bash
# MISHKA Training Environment Setup
# CPU-first training environment

set -e

echo "Setting up MISHKA training environment..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install CPU-optimized PyTorch
echo "Installing CPU-optimized PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install training requirements
echo "Installing training requirements..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Install additional CPU-optimized packages
pip install faiss-cpu  # CPU-optimized FAISS

echo "Environment setup complete!"
echo "Activate with: source venv/bin/activate"
