#!/usr/bin/env python3
"""
Test runner for Facebook Messenger Export Viewer.
Run all tests or specific test modules.
"""

import sys
import os
import unittest
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests():
    """Run all unit tests."""
    loader = unittest.TestLoader()
    suite = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def run_specific_test(test_module):
    """Run a specific test module."""
    loader = unittest.TestLoader()
    try:
        suite = loader.loadTestsFromName(test_module)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
    except Exception as e:
        print(f"Error running test: {e}")
        return False


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description='Run tests for FB Messenger Viewer')
    parser.add_argument(
        'test',
        nargs='?',
        help='Specific test to run (e.g., test_messenger_server)'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run with coverage report'
    )

    args = parser.parse_args()

    if args.coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
        except ImportError:
            print("Coverage not installed. Install with: pip install coverage")
            return 1

    # Run tests
    if args.test:
        success = run_specific_test(f"tests.{args.test}")
    else:
        success = run_all_tests()

    if args.coverage:
        cov.stop()
        cov.save()
        print("\n" + "=" * 60)
        print("Coverage Report:")
        print("=" * 60)
        cov.report()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())