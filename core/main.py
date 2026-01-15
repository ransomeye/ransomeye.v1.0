#!/usr/bin/env python3
"""
RansomEye v1.0 Core Runtime Main Entry Point
AUTHORITATIVE: Main entry point for Core runtime
Phase 10.1 requirement: Single Core runtime for all components
"""

import sys
import os

# Add core to path
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.runtime import run_core, ExitCode, logger, exit_config_error, exit_startup_error, exit_fatal
from common.config import ConfigError
from common.shutdown import ShutdownHandler

if __name__ == "__main__":
    try:
        exit_code = run_core()
        logger.shutdown("Core runtime completed successfully")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.shutdown("Received interrupt, shutting down")
        sys.exit(ExitCode.SUCCESS)
    except ConfigError as e:
        exit_config_error(str(e))
    except Exception as e:
        exit_fatal(f"Fatal error in Core runtime: {e}", ExitCode.FATAL_ERROR)
