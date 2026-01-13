#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Generate Summary CLI
AUTHORITATIVE: Generate summary from JSON request file
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Add project root to path for imports
_project_root = _parent_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from api.summarizer_api import SummarizerAPI, SummarizerAPIError
import importlib.util

# Import RegistryAPI for model registry
_model_registry_dir = _project_root / "ai-model-registry"
if str(_model_registry_dir) not in sys.path:
    sys.path.insert(0, str(_model_registry_dir))

_registry_api_spec = importlib.util.spec_from_file_location("registry_api", _model_registry_dir / "api" / "registry_api.py")
_registry_api_module = importlib.util.module_from_spec(_registry_api_spec)
_registry_api_spec.loader.exec_module(_registry_api_module)
RegistryAPI = _registry_api_module.RegistryAPI


def main():
    """Generate summary from JSON request file."""
    parser = argparse.ArgumentParser(
        description='Generate summary from JSON request file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --request-file request.json
  %(prog)s --request-file request.json --output-file summary.json

Environment Variables:
  RANSOMEYE_TEMPLATE_REGISTRY_PATH - Path to template registry store
  RANSOMEYE_SUMMARY_STORE_PATH - Path to summary store
  RANSOMEYE_AUDIT_LEDGER_PATH - Path to audit ledger file
  RANSOMEYE_AUDIT_LEDGER_KEY_DIR - Directory containing ledger signing keys
  RANSOMEYE_LLM_MODEL_PATH - Path to GGUF model file
  RANSOMEYE_LLM_MODEL_ID - Model identifier from registry
  RANSOMEYE_LLM_MODEL_VERSION - Model version from registry
        """
    )
    
    parser.add_argument(
        '--request-file',
        type=Path,
        required=True,
        help='Path to summary request JSON file'
    )
    
    parser.add_argument(
        '--output-file',
        type=Path,
        default=None,
        help='Path to write summary output JSON (optional)'
    )
    
    parser.add_argument(
        '--template-registry-path',
        type=Path,
        default=None,
        help='Path to template registry (overrides RANSOMEYE_TEMPLATE_REGISTRY_PATH)'
    )
    
    parser.add_argument(
        '--summary-store-path',
        type=Path,
        default=None,
        help='Path to summary store (overrides RANSOMEYE_SUMMARY_STORE_PATH)'
    )
    
    parser.add_argument(
        '--ledger-path',
        type=Path,
        default=None,
        help='Path to audit ledger (overrides RANSOMEYE_AUDIT_LEDGER_PATH)'
    )
    
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        default=None,
        help='Directory containing ledger keys (overrides RANSOMEYE_AUDIT_LEDGER_KEY_DIR)'
    )
    
    parser.add_argument(
        '--signing-key-path',
        type=Path,
        default=None,
        help='Path to output signing key (optional)'
    )
    
    parser.add_argument(
        '--signing-key-id',
        type=str,
        default=None,
        help='Signing key identifier (optional)'
    )
    
    parser.add_argument(
        '--model-registry-path',
        type=Path,
        default=None,
        help='Path to model registry (for model verification)'
    )
    
    parser.add_argument(
        '--model-key-dir',
        type=Path,
        default=None,
        help='Directory containing model signing keys'
    )
    
    args = parser.parse_args()
    
    # Validate request file exists
    if not args.request_file.exists():
        print(f"ERROR: Request file not found: {args.request_file}", file=sys.stderr)
        sys.exit(1)
    
    # Read request file
    try:
        with open(args.request_file, 'r', encoding='utf-8') as f:
            request = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in request file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read request file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get paths from env or args
    template_registry_path = args.template_registry_path or Path(os.getenv('RANSOMEYE_TEMPLATE_REGISTRY_PATH', ''))
    summary_store_path = args.summary_store_path or Path(os.getenv('RANSOMEYE_SUMMARY_STORE_PATH', ''))
    ledger_path = args.ledger_path or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_PATH', ''))
    ledger_key_dir = args.ledger_key_dir or Path(os.getenv('RANSOMEYE_AUDIT_LEDGER_KEY_DIR', ''))
    output_schema_path = _parent_dir / "schema" / "summary-output.schema.json"
    
    # Validate required paths
    if not template_registry_path:
        print("ERROR: Template registry path not provided. Set RANSOMEYE_TEMPLATE_REGISTRY_PATH or use --template-registry-path", file=sys.stderr)
        sys.exit(1)
    if not summary_store_path:
        print("ERROR: Summary store path not provided. Set RANSOMEYE_SUMMARY_STORE_PATH or use --summary-store-path", file=sys.stderr)
        sys.exit(1)
    if not ledger_path:
        print("ERROR: Audit ledger path not provided. Set RANSOMEYE_AUDIT_LEDGER_PATH or use --ledger-path", file=sys.stderr)
        sys.exit(1)
    if not ledger_key_dir:
        print("ERROR: Audit ledger key directory not provided. Set RANSOMEYE_AUDIT_LEDGER_KEY_DIR or use --ledger-key-dir", file=sys.stderr)
        sys.exit(1)
    
    # Initialize model registry API (if provided)
    model_registry_api = None
    if args.model_registry_path and args.model_key_dir:
        try:
            model_registry_api = RegistryAPI(
                registry_path=args.model_registry_path,
                model_key_dir=args.model_key_dir,
                ledger_path=ledger_path,
                ledger_key_dir=ledger_key_dir
            )
        except Exception as e:
            print(f"WARNING: Failed to initialize model registry API: {e}", file=sys.stderr)
            print("WARNING: Model verification will be skipped", file=sys.stderr)
    
    # Initialize summarizer API
    try:
        api = SummarizerAPI(
            template_registry_path=template_registry_path,
            summary_store_path=summary_store_path,
            output_schema_path=output_schema_path,
            ledger_path=ledger_path,
            ledger_key_dir=ledger_key_dir,
            model_registry_api=model_registry_api,
            signing_key_path=args.signing_key_path,
            signing_key_id=args.signing_key_id
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize summarizer API: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate summary
    try:
        summary = api.generate_summary(request)
    except SummarizerAPIError as e:
        print(f"ERROR: Summary generation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during summary generation: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print summary info
    print("SUCCESS: Summary generated")
    print(f"  Summary ID: {summary.get('summary_id', 'N/A')}")
    print(f"  Narrative Type: {summary.get('narrative_type', 'N/A')}")
    print(f"  Output Hash: {summary.get('output_hash', 'N/A')}")
    print(f"  Signature: {summary.get('signature', 'N/A')[:64]}..." if summary.get('signature') else "  Signature: N/A")
    print(f"  Generated At: {summary.get('generated_at', 'N/A')}")
    
    # Write output file if requested
    if args.output_file:
        try:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            print(f"  Output written to: {args.output_file}")
        except Exception as e:
            print(f"WARNING: Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
