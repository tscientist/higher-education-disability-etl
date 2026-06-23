"""
Master setup script for all test resources.

This script runs all setup scripts (BigQuery and MongoDB) to validate
the complete ETL infrastructure.

Usage:
    python src/setup/run_all_setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Get the setup directory
SETUP_DIR = Path(__file__).parent


def run_bigquery_setup():
    """Run BigQuery setup script."""
    print("\n" + "=" * 60)
    print("Running BigQuery Setup...")
    print("=" * 60 + "\n")
    
    script_path = SETUP_DIR / "setup_bigquery_test_resources.py"
    result = subprocess.run([sys.executable, str(script_path)], cwd=SETUP_DIR.parent.parent)
    return result.returncode == 0


def run_mongodb_setup():
    """Run MongoDB setup script."""
    print("\n" + "=" * 60)
    print("Running MongoDB Setup...")
    print("=" * 60 + "\n")
    
    script_path = SETUP_DIR / "setup_mongodb_test_resources.py"
    result = subprocess.run([sys.executable, str(script_path)], cwd=SETUP_DIR.parent.parent)
    return result.returncode == 0


def main():
    """Run all setup scripts."""
    print("=" * 60)
    print("ETL Test Resources Setup - All Systems")
    print("=" * 60)
    
    results = {}
    
    # Run BigQuery setup
    results['BigQuery'] = run_bigquery_setup()
    
    # Run MongoDB setup
    results['MongoDB'] = run_mongodb_setup()
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    for system, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{system}: {status}")
    
    all_success = all(results.values())
    
    print("=" * 60)
    
    if all_success:
        print("\nAll setup scripts completed successfully!")
        return 0
    else:
        print("\nSome setup scripts failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
