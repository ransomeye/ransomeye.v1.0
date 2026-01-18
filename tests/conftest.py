import os
from pathlib import Path


def pytest_configure(config):
    if os.getenv("COVERAGE_PROCESS_START"):
        return
    repo_root = Path(__file__).resolve().parent.parent
    os.environ["COVERAGE_PROCESS_START"] = str(repo_root / ".coveragerc")
