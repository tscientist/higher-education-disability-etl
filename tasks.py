"""Makefile-like commands for development"""

import subprocess
import sys


def run_tests():
    """Run test suite"""
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--cov=src"], check=True)


def lint():
    """Run code linting"""
    subprocess.run([sys.executable, "-m", "flake8", "src/", "tests/", "main.py"], check=True)


def format_code():
    """Format code with black and isort"""
    subprocess.run([sys.executable, "-m", "black", "src/", "tests/", "main.py"], check=True)
    subprocess.run([sys.executable, "-m", "isort", "src/", "tests/", "main.py"], check=True)


def type_check():
    """Run type checking with mypy"""
    subprocess.run([sys.executable, "-m", "mypy", "src/"], check=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "tests":
            run_tests()
        elif command == "lint":
            lint()
        elif command == "format":
            format_code()
        elif command == "type-check":
            type_check()
        else:
            print(f"Unknown command: {command}")
    else:
        print("Usage: python tasks.py [tests|lint|format|type-check]")
