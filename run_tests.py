"""
Test Runner Script

Convenient script to run all tests with various options.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --unit       # Run only unit tests
    python run_tests.py --integration  # Run only integration tests
    python run_tests.py --verbose    # Run with verbose output
    python run_tests.py --coverage   # Run with coverage report
    python run_tests.py --help       # Show help
"""
import subprocess
import sys
from pathlib import Path


def run_tests(
    test_paths=None,
    verbose=False,
    coverage=False,
    html_report=False,
    fail_under=None,
):
    """Run pytest with specified options.
    
    Args:
        test_paths: List of test paths (default: all tests)
        verbose: Enable verbose output
        coverage: Generate coverage report
        html_report: Generate HTML coverage report
        fail_under: Fail if coverage below this percentage
    """
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add test paths
    if test_paths is None:
        test_paths = [
            "src/tests/unit",
            "src/tests/integration",
        ]
    
    cmd.extend(test_paths)
    
    # Add coverage options
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
        ])
        
        if html_report:
            cmd.append("--cov-report=html")
        
        if fail_under:
            cmd.extend(["--cov-fail-under", str(fail_under)])
    
    print(f"Running tests: {' '.join(cmd)}")
    print("=" * 60)
    
    # Run tests
    result = subprocess.run(cmd)
    
    return result.returncode == 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests for the bot")
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--fail-under",
        type=int,
        default=70,
        help="Fail if coverage below percentage (default: 70)"
    )
    parser.add_argument(
        "test_path",
        nargs="*",
        help="Specific test file or directory to run"
    )
    
    args = parser.parse_args()
    
    # Determine test paths
    if args.test_path:
        test_paths = args.test_path
    elif args.unit:
        test_paths = ["src/tests/unit"]
    elif args.integration:
        test_paths = ["src/tests/integration"]
    else:
        test_paths = None
    
    # Run tests
    success = run_tests(
        test_paths=test_paths,
        verbose=args.verbose,
        coverage=args.coverage or args.html,
        html_report=args.html,
        fail_under=args.fail_under,
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
