#!/bin/bash
#
# RansomEye Pytest Gate
# AUTHORITATIVE: Fail-closed if pytest missing
#

set -euo pipefail

python3 - << 'EOF'
import sys
try:
    import pytest
    print(f"pytest OK: {pytest.__version__}")
except ImportError:
    print("FATAL: pytest not installed. Activate .venv and install requirements-dev.txt")
    sys.exit(1)
EOF
