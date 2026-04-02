#!/usr/bin/env python3
"""
Run all regression tests for the pattern registry.

This script runs all test suites and provides a summary report.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent

def run_test_suite(test_file, description):
    """Run a single test suite and return results."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"{'='*70}")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return {
        "file": test_file.name,
        "description": description,
        "returncode": result.returncode,
        "passed": result.returncode == 0
    }

def main():
    """Run all test suites."""
    print(f"Pattern Registry Regression Tests")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")

    tests_dir = Path(__file__).parent

    # Define test suites in order of execution
    test_suites = [
        (tests_dir / "test_schema_compliance.py", "Schema Compliance Tests"),
        (tests_dir / "test_pattern_schema_validation.py", "Schema Validation Tests"),
        (tests_dir / "test_nfr_constraint_logic.py", "NFR & Constraint Logic Tests"),
        (tests_dir / "test_pattern_conflicts.py", "Pattern Conflict Tests"),
        (tests_dir / "test_pattern_quality.py", "Pattern Quality Tests"),
    ]

    results = []

    for test_file, description in test_suites:
        if not test_file.exists():
            print(f"WARNING: Test file not found: {test_file}")
            continue

        result = run_test_suite(test_file, description)
        results.append(result)

    # Print summary
    print(f"\n{'='*70}")
    print(f"Test Summary")
    print(f"{'='*70}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    for result in results:
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        print(f"{status:12} {result['description']}")

    print(f"\n{'='*70}")
    print(f"Total: {total} test suites")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"{'='*70}")

    if failed > 0:
        print("\n⚠️  REGRESSION TESTS FAILED")
        print("Please fix the failing tests before committing changes.")
        sys.exit(1)
    else:
        print("\n✅ ALL REGRESSION TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
