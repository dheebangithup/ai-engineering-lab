"""
CLI Test Runner for Support Ticket Classification System.
Runs the E2E test suite from test_cases.py.
"""

import sys
import logging
from support_ticket_classification_system.graph.graph import app
from support_ticket_classification_system.tests.test_cases import TEST_CASES

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s | %(levelname)s | %(message)s",
)

DIVIDER = "=" * 65

def _print_result(name: str, result: dict, expected: dict) -> bool:
    """Pretty-print one test result and return True if all assertions pass."""
    output = result.get("llm_output", {})
    is_injection = result.get("injection_detected", False)

    print(f"\n{'─' * 65}")
    print(f"  📋 {name}")
    print(f"{'─' * 65}")

    if is_injection:
        print(f"  🚫 Blocked    : {output.get('summary', 'N/A')}")
        print(f"  ⚠️  Injection  : {is_injection}")
    else:
        print(f"  📂 Category   : {output.get('category', 'N/A')}")
        print(f"  🔺 Priority   : {output.get('priority', 'N/A')}")
        print(f"  👥 Team       : {output.get('assigned_team', 'N/A')}")
        print(f"  😊 Sentiment  : {output.get('sentiment', 'N/A')}")
        print(f"  📊 Confidence : {output.get('confidence_score', 'N/A')}")
        print(f"  ✅ Validated  : {result.get('validated', 'N/A')}")
        print(f"  🔍 PII Found  : {result.get('pii_detected', 'N/A')}")
        print(f"  📜 Prompt Ver : {result.get('prompt_version', 'N/A')}")
        print(f"  🔁 Retries    : {result.get('retry_count', 'N/A')}")
        print(f"  💰 Cost       : {result.get('cost', 'N/A')}")

    passed = True
    for key, expected_val in expected.items():
        actual_val = result.get(key)
        status = "PASS" if actual_val == expected_val else "FAIL"
        if actual_val != expected_val:
            passed = False
        print(f"  [{status}] Assert {key} = {expected_val} (got: {actual_val})")

    return passed

def run_tests():
    print(f"\n{DIVIDER}")
    print("  SUPPORT TICKET CLASSIFICATION SYSTEM - E2E TEST SUITE")
    print(DIVIDER)

    total = len(TEST_CASES)
    passed = 0
    failed_names = []

    for tc in TEST_CASES:
        name = tc["name"]
        test_input = tc["input"]
        expected = tc["expect"]

        result = app.invoke(test_input)
        ok = _print_result(name, result, expected)

        if ok:
            passed += 1
        else:
            failed_names.append(name)

    print(f"\n{DIVIDER}")
    print(f"  RESULTS: {passed}/{total} passed")
    if failed_names:
        print(f"  FAILED: {', '.join(failed_names)}")
    else:
        print("  ALL TESTS PASSED!")
    print(DIVIDER)

if __name__ == "__main__":
    run_tests()
