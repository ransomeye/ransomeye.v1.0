#!/usr/bin/env python3
"""
RansomEye Mishka — SOC Assistant (Basic, Read-Only)
AUTHORITATIVE: Command-line tool for querying Mishka
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_mishka_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_mishka_dir))

from api.mishka_api import MishkaAPI, MishkaAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Query Mishka — SOC Assistant'
    )
    parser.add_argument(
        '--query',
        required=True,
        help='Query text'
    )
    parser.add_argument(
        '--vector-store',
        type=Path,
        required=True,
        help='Path to FAISS vector store'
    )
    parser.add_argument(
        '--model',
        type=Path,
        required=True,
        help='Path to GGUF model file'
    )
    parser.add_argument(
        '--feedback-store',
        type=Path,
        required=True,
        help='Path to feedback store'
    )
    parser.add_argument(
        '--incident-id',
        help='Incident ID (optional context)'
    )
    parser.add_argument(
        '--subject-id',
        help='Subject ID (optional context)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output response JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Build query context
        query_context = {}
        if args.incident_id:
            query_context['incident_id'] = args.incident_id
        if args.subject_id:
            query_context['subject_id'] = args.subject_id
        
        # Initialize Mishka API
        api = MishkaAPI(
            vector_store_path=args.vector_store,
            model_path=args.model,
            feedback_store_path=args.feedback_store
        )
        
        # Process query
        response = api.ask(args.query, query_context)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(response, indent=2, ensure_ascii=False))
            print(f"Response generated. Result written to: {args.output}")
        else:
            print(json.dumps(response, indent=2, ensure_ascii=False))
        
        print(f"\nResponse Summary:")
        print(f"  Response ID: {response.get('response_id')}")
        print(f"  Confidence: {response.get('confidence_level')}")
        print(f"  Facts: {len(response.get('answer', {}).get('facts', []))}")
        print(f"  Citations: {len(response.get('citations', []))}")
        print(f"  Sources: {len(response.get('source_references', []))}")
        if response.get('uncertainty_indicators'):
            print(f"  Uncertainty: {len(response.get('uncertainty_indicators'))} indicators")
        
    except MishkaAPIError as e:
        print(f"Query failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
