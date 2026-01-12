#!/usr/bin/env python3
"""
RansomEye Orchestrator - Run Workflow CLI
AUTHORITATIVE: Command-line tool for executing workflows
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_orchestrator_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_orchestrator_dir))

from api.orchestrator_api import OrchestratorAPI, OrchestratorAPIError


def load_workflow(workflow_path: Path) -> dict:
    """Load workflow from file."""
    if not workflow_path.exists():
        return {}
    
    try:
        return json.loads(workflow_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load workflow: {e}", file=sys.stderr)
        return {}


def load_input_data(input_path: Path) -> dict:
    """Load input data from file."""
    if not input_path.exists():
        return {}
    
    try:
        return json.loads(input_path.read_text())
    except Exception as e:
        print(f"Warning: Failed to load input data: {e}", file=sys.stderr)
        return {}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Execute workflow'
    )
    parser.add_argument(
        '--workflow',
        type=Path,
        required=True,
        help='Path to workflow JSON file'
    )
    parser.add_argument(
        '--trigger-type',
        choices=['manual', 'alert', 'validator'],
        required=True,
        help='Trigger type'
    )
    parser.add_argument(
        '--input-data',
        type=Path,
        help='Path to input data JSON file (optional)'
    )
    parser.add_argument(
        '--authority-state',
        choices=['NONE', 'REQUIRED', 'VERIFIED'],
        default='NONE',
        help='Authority state (default: NONE)'
    )
    parser.add_argument(
        '--explanation-bundle-id',
        required=True,
        help='Explanation bundle identifier (SEE)'
    )
    parser.add_argument(
        '--workflows-store',
        type=Path,
        required=True,
        help='Path to workflows store'
    )
    parser.add_argument(
        '--jobs-store',
        type=Path,
        required=True,
        help='Path to job records store'
    )
    parser.add_argument(
        '--ledger',
        type=Path,
        required=True,
        help='Path to audit ledger file'
    )
    parser.add_argument(
        '--ledger-key-dir',
        type=Path,
        required=True,
        help='Directory containing ledger signing keys'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output job records JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Load workflow
        workflow = load_workflow(args.workflow)
        if not workflow:
            print("Error: Failed to load workflow", file=sys.stderr)
            sys.exit(1)
        
        # Load input data
        input_data = load_input_data(args.input_data) if args.input_data else {}
        
        # Initialize orchestrator API
        api = OrchestratorAPI(
            workflows_store_path=args.workflows_store,
            jobs_store_path=args.jobs_store,
            ledger_path=args.ledger,
            ledger_key_dir=args.ledger_key_dir
        )
        
        # Register workflow if not already registered
        workflow_id = workflow.get('workflow_id', '')
        existing = api.workflow_registry.get_workflow(workflow_id)
        if not existing:
            api.register_workflow(workflow)
        
        # Execute workflow
        job_records = api.execute_workflow(
            workflow_id=workflow_id,
            trigger_type=args.trigger_type,
            input_data=input_data,
            authority_state=args.authority_state,
            explanation_bundle_id=args.explanation_bundle_id
        )
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(job_records, indent=2, ensure_ascii=False))
            print(f"Workflow executed. Result written to: {args.output}")
        else:
            print(json.dumps(job_records, indent=2, ensure_ascii=False))
        
        print(f"\nWorkflow Execution Summary:")
        print(f"  Workflow ID: {workflow_id}")
        print(f"  Trigger Type: {args.trigger_type}")
        print(f"  Jobs Executed: {len(job_records)}")
        print(f"  Completed: {len([j for j in job_records if j.get('status') == 'COMPLETED'])}")
        print(f"  Failed: {len([j for j in job_records if j.get('status') == 'FAILED'])}")
        print(f"  Timeout: {len([j for j in job_records if j.get('status') == 'TIMEOUT'])}")
        
    except OrchestratorAPIError as e:
        print(f"Workflow execution failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
