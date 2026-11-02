#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "Running Bucketing & Tests Smoke Test"
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Activate virtual environment if present
if [ -d ".venv" ]; then
    PYTHON_EXEC="${PROJECT_ROOT}/.venv/bin/python"
    PYTEST_EXEC="${PROJECT_ROOT}/.venv/bin/pytest"
else
    PYTHON_EXEC="python3"
    PYTEST_EXEC="pytest"
fi

echo "1. Running unit tests..."
PYTHONPATH=. "${PYTEST_EXEC}" tests/ -v

echo "2. Running end-to-end smoke test..."
PYTHONPATH=. "${PYTHON_EXEC}" run_pipeline.py --smoke-test

echo "=========================================================="
echo "Smoke test completed successfully!"
echo "=========================================================="
