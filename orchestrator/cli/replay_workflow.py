#!/usr/bin/env python3
"""
RansomEye Orchestrator - Replay Workflow CLI
AUTHORITATIVE: Command-line tool for replaying workflow executions
"""

import sys
import json
from pathlib import Path
import argparse

# Add parent directory to path for imports
_orchestrator_dir = Path(__file__).parent.parent
sys.path.insert(0, str(_orchestrator_dir))

from api.orchestrator_api import OrchestratorAPI, OrchestratorAPIError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Replay workflow execution'
    )
    parser.add_argument(
        '--workflow-id',
        required=True,
        help='Workflow identifier'
    )
    parser.add_argument(
        '--jobs-store',
        type=Path,
        required=True,
        help='Path to job records store'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Path to output job records JSON (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize replay engine
        from engine.replay_engine import ReplayEngine
        replay_engine = ReplayEngine(args.jobs_store)
        
        # Replay workflow
        job_records = replay_engine.replay_workflow(args.workflow_id)
        
        if not job_records:
            print(f"No job records found for workflow: {args.workflow_id}")
            sys.exit(0)
        
        # Output result
        if args.output:
            args.output.write_text(json.dumps(job_records, indent=2, ensure_ascii=False))
            print(f"Workflow replayed. Result written to: {args.output}")
        else:
            print(json.dumps(job_records, indent=2, ensure_ascii=False))
        
        print(f"\nWorkflow Replay Summary:")
        print(f"  Workflow ID: {args.workflow_id}")
        print(f"  Jobs Replayed: {len(job_records)}")
        print(f"  Completed: {len([j for j in job_records if j.get('status') == 'COMPLETED'])}")
        print(f"  Failed: {len([j for j in job_records if j.get('status') == 'FAILED'])}")
        print(f"  Timeout: {len([j for j in job_records if j.get('status') == 'TIMEOUT'])}")
        
    except Exception as e:
        print(f"Replay failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
