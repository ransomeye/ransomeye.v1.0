#!/usr/bin/env python3
"""
RansomEye LLM Summarizer - Register Template CLI
AUTHORITATIVE: Register immutable prompt templates with validation
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from prompts.template_registry import TemplateRegistry, TemplateRegistryError
from prompts.prompt_hasher import PromptHasher
from jinja2 import Template, TemplateSyntaxError


def main():
    """Register a prompt template."""
    parser = argparse.ArgumentParser(
        description='Register immutable prompt template',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --template-file templates/soc_narrative_v1.0.0.jinja2 \\
           --narrative-type SOC_NARRATIVE \\
           --version 1.0.0 \\
           --registered-by admin@example.com

Environment Variables:
  RANSOMEYE_TEMPLATE_REGISTRY_PATH - Path to template registry store
        """
    )
    
    parser.add_argument(
        '--template-file',
        type=Path,
        required=True,
        help='Path to Jinja2 template file'
    )
    
    parser.add_argument(
        '--narrative-type',
        type=str,
        required=True,
        choices=['SOC_NARRATIVE', 'EXECUTIVE_SUMMARY', 'LEGAL_NARRATIVE'],
        help='Narrative type (SOC_NARRATIVE | EXECUTIVE_SUMMARY | LEGAL_NARRATIVE)'
    )
    
    parser.add_argument(
        '--version',
        type=str,
        required=True,
        help='Template version (semver, e.g., 1.0.0)'
    )
    
    parser.add_argument(
        '--registered-by',
        type=str,
        required=True,
        help='Entity registering template (e.g., admin@example.com)'
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
    
    # Validate template file exists
    if not args.template_file.exists():
        print(f"ERROR: Template file not found: {args.template_file}", file=sys.stderr)
        sys.exit(1)
    
    # Read template content
    try:
        with open(args.template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except Exception as e:
        print(f"ERROR: Failed to read template file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate Jinja2 syntax
    try:
        Template(template_content)
    except TemplateSyntaxError as e:
        print(f"ERROR: Jinja2 syntax error in template: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Template validation failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Calculate template hash
    try:
        template_hash = PromptHasher.hash_template(template_content)
    except Exception as e:
        print(f"ERROR: Failed to calculate template hash: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize registry
    try:
        registry = TemplateRegistry(registry_path)
    except Exception as e:
        print(f"ERROR: Failed to initialize template registry: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if template with same hash already exists
    try:
        # Try to find existing template by narrative type and version
        existing = registry.find_template_by_narrative_type(args.narrative_type, args.version)
        if existing:
            existing_hash = existing.get('template_hash', '')
            if existing_hash == template_hash:
                print(f"ERROR: Template with same hash already exists: {existing.get('template_id')}", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"ERROR: Template with same narrative type and version exists but hash differs", file=sys.stderr)
                print(f"  Existing hash: {existing_hash}", file=sys.stderr)
                print(f"  New hash: {template_hash}", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        # If lookup fails, continue with registration
        pass
    
    # Register template
    try:
        template_record = registry.register_template(
            template_content=template_content,
            template_version=args.version,
            narrative_type=args.narrative_type,
            registered_by=args.registered_by
        )
    except TemplateRegistryError as e:
        print(f"ERROR: Template registration failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during registration: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Print success
    print("SUCCESS: Template registered")
    print(f"  Template ID: {template_record['template_id']}")
    print(f"  Version: {template_record['template_version']}")
    print(f"  Narrative Type: {template_record['narrative_type']}")
    print(f"  Template Hash: {template_record['template_hash']}")
    print(f"  Registered At: {template_record['registered_at']}")
    print(f"  Registered By: {template_record['registered_by']}")
    
    sys.exit(0)


if __name__ == '__main__':
    main()
