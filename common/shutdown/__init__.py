# Common shutdown utilities for RansomEye v1.0
from .handler import (
    ShutdownHandler, ExitCode,
    exit_fatal, exit_config_error, exit_startup_error, exit_runtime_error
)

__all__ = [
    'ShutdownHandler', 'ExitCode',
    'exit_fatal', 'exit_config_error', 'exit_startup_error', 'exit_runtime_error'
]
