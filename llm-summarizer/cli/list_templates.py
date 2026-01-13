#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - List Templates CLI
AUTHORITATIVE: Read-only template listing
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from prompts.template_registry import TemplateRegistry, TemplateRegistryError


def main():
    """List registered templates."""
    parser = argparse.ArgumentParser(
        description='List registered prompt templates (read-only)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --narrative-type SOC_NARRATIVE
  %(prog)s --json

Environment Variables:
  RANSOMEYE_TEMPLATE_REGISTRY_PATH - Path to template registry store
        """
    )
    
    parser.add_argument(
        '--narrative-type',
        type=str,
        choices=['SOC_NARRATIVE', 'EXECUTIVE_SUMMARY', 'LEGAL_NARRATIVE'],
        help='Filter by narrative type'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    
    parser.add_argument(
        '--registry-path',
        type=Path,
        default=None,
        help='Path to template registry store (overrides RANSOMEYE_TEMPLATE_REGISTRY_PATH)'
    )
    
    args = parser.parse_args()
    
    # Get registry path from env or arg
    registry_path = args.registry_path
    if not registry_path:
        registry_path_str = os.getenv('RANSOMEYE_TEMPLATE_REGISTRY_PATH')
        if not registry_path_str:
            print("ERROR: Template registry path not provided. Set RANSOMEYE_TEMPLATE_REGISTRY_PATH or use --registry-path", file=sys.stderr)
            sys.exit(1)
        registry_path = Path(registry_path_str)
    
    # Initialize registry
    try:
        registry = TemplateRegistry(registry_path)
    except Exception as e:
        print(f"ERROR: Failed to initialize template registry: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Load templates
    try:
        registry._load_templates()
    except Exception as e:
        print(f"ERROR: Failed to load templates: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Filter templates
    templates = []
    for template_id, template_record in registry._templates.items():
        if args.narrative_type and template_record.get('narrative_type') != args.narrative_type:
            continue
        templates.append(template_record)
    
    # Sort by narrative type, then version
    templates.sort(key=lambda t: (t.get('narrative_type', ''), t.get('template_version', '')))
    
    # Output
    if args.json:
        # JSON output
        print(json.dumps(templates, indent=2))
    else:
        # Human-readable output
        if not templates:
            print("No templates found.")
            if args.narrative_type:
                print(f"  (Filtered by narrative type: {args.narrative_type})")
            sys.exit(0)
        
        print(f"Found {len(templates)} template(s):")
        print()
        
        for template in templates:
            print(f"Template ID: {template.get('template_id', 'N/A')}")
            print(f"  Version: {template.get('template_version', 'N/A')}")
            print(f"  Narrative Type: {template.get('narrative_type', 'N/A')}")
            print(f"  Hash: {template.get('template_hash', 'N/A')}")
            print(f"  Registered At: {template.get('registered_at', 'N/A')}")
            print(f"  Registered By: {template.get('registered_by', 'N/A')}")
            print()
    
    sys.exit(0)


if __name__ == '__main__':
    main()
