import os

if os.getenv("COVERAGE_PROCESS_START") and not os.getenv("PYTEST_CURRENT_TEST"):
    try:
        import coverage

        coverage.process_startup()
    except Exception:
        pass
