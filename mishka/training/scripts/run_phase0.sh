#!/bin/bash
# MISHKA Training - Phase 0 Execution Script
# Foundation & Infrastructure Setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "MISHKA Phase 0: Foundation & Infrastructure"
echo "=========================================="
echo ""

# Step 1: Set up environment
echo "Step 1: Setting up training environment..."
cd "$TRAINING_DIR"
if [ ! -d "venv" ]; then
    bash scripts/setup_environment.sh
else
    echo "Virtual environment already exists"
fi

source venv/bin/activate
echo "✓ Environment ready"
echo ""

# Step 2: Collect MITRE ATT&CK data
echo "Step 2: Collecting MITRE ATT&CK data..."
python3 scripts/collect_mitre_attck.py \
    --output-dir data/raw/mitre_attck
echo "✓ MITRE ATT&CK data collected"
echo ""

# Step 3: Collect NVD CVE data (sample for training)
echo "Step 3: Collecting NVD CVE data (sample)..."
python3 scripts/collect_nvd_cve.py \
    --output-dir data/raw/nvd \
    --limit 1000
echo "✓ NVD CVE data collected"
echo ""

# Step 4: Create test datasets
echo "Step 4: Creating test datasets..."
python3 scripts/create_test_datasets.py \
    --output-dir data/test
echo "✓ Test datasets created"
echo ""

# Step 5: Prepare training data
echo "Step 5: Preparing training data..."
if [ -f "data/raw/mitre_attck/mitre_attck_techniques.json" ]; then
    python3 scripts/prepare_training_data.py \
        --mitre-file data/raw/mitre_attck/mitre_attck_techniques.json \
        --cve-file data/raw/nvd/nvd_cves_sample.json \
        --output-dir data/processed
    echo "✓ Training data prepared"
else
    echo "⚠ MITRE ATT&CK file not found, skipping data preparation"
fi
echo ""

# Step 6: Evaluate base models (if transformers available)
echo "Step 6: Base model evaluation..."
echo "Note: This requires transformers library and may take time"
echo "Skipping for now - run manually with:"
echo "  python3 scripts/evaluate_base_model.py --model mistralai/Mistral-7B-v0.1"
echo ""

echo "=========================================="
echo "Phase 0 Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review collected data in: data/raw/"
echo "2. Review prepared training data in: data/processed/"
echo "3. Review test datasets in: data/test/"
echo "4. Evaluate base models: python3 scripts/evaluate_base_model.py"
echo "5. Proceed to Phase 1: Cybersecurity Domain Foundation"
