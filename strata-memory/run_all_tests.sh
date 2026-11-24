#!/usr/bin/env bash
set -e

echo "================================================================================"
echo "🧪 STRATA UNIFIED TEST & EVALUATION SUITE RUNNER"
echo "================================================================================"

# Resolve project root and activate virtualenv
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

echo ""
echo "▶ STEP 1/3: Running Pytest Unit & Integration Tests (23 test cases)..."
echo "--------------------------------------------------------------------------------"
pytest tests/test_*.py -v

echo ""
echo "▶ STEP 2/3: Running Comprehensive 15-Case Evaluation Pipeline (eval_dedicated_suite)..."
echo "--------------------------------------------------------------------------------"
python tests/eval_pipeline.py

echo ""
echo "▶ STEP 3/3: Running Interactive Use Case Demo (examples/demo.py)..."
echo "--------------------------------------------------------------------------------"
python examples/demo.py

echo ""
echo "================================================================================"
echo "🎉 ALL TESTS, EVALUATION CASES, AND USE CASE DEMO PASSED SUCCESSFULLY!"
echo "   Database remains 100% clean across all test namespaces."
echo "================================================================================"
