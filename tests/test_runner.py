#!/usr/bin/env python3
"""Test runner script for Sure Finance Home Assistant Integration."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Test runner for the Sure Finance integration."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        
    def run_unit_tests(self, verbose: bool = False, coverage: bool = True) -> int:
        """Run unit tests."""
        cmd = ["pytest", str(self.tests_dir)]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=custom_components.sure_finance",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        # Exclude integration tests
        cmd.extend(["-m", "not integration"])
        
        print(f"Running unit tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_integration_tests(self, verbose: bool = False) -> int:
        """Run integration tests."""
        cmd = ["pytest", str(self.tests_dir), "-m", "integration"]
        
        if verbose:
            cmd.append("-v")
        
        print(f"Running integration tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_specific_test(self, test_path: str, verbose: bool = False) -> int:
        """Run a specific test file or test function."""
        cmd = ["pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        print(f"Running specific test: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_performance_tests(self, verbose: bool = False) -> int:
        """Run performance tests."""
        cmd = ["pytest", str(self.tests_dir), "-m", "performance"]
        
        if verbose:
            cmd.append("-v")
        
        # Add benchmark options
        cmd.extend([
            "--benchmark-only",
            "--benchmark-sort=mean",
            "--benchmark-columns=min,max,mean,stddev,median,ops,rounds"
        ])
        
        print(f"Running performance tests: {' '.join(cmd)}")
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_linting(self) -> int:
        """Run code linting and formatting checks."""
        print("Running code quality checks...")
        
        # Black formatting check
        print("\n1. Checking code formatting with Black...")
        black_result = subprocess.run([
            "black", "--check", "--diff", 
            str(self.project_root / "custom_components"),
            str(self.tests_dir)
        ], cwd=self.project_root).returncode
        
        # isort import sorting check
        print("\n2. Checking import sorting with isort...")
        isort_result = subprocess.run([
            "isort", "--check-only", "--diff",
            str(self.project_root / "custom_components"),
            str(self.tests_dir)
        ], cwd=self.project_root).returncode
        
        # Flake8 linting
        print("\n3. Running flake8 linting...")
        flake8_result = subprocess.run([
            "flake8", 
            str(self.project_root / "custom_components"),
            str(self.tests_dir)
        ], cwd=self.project_root).returncode
        
        # MyPy type checking
        print("\n4. Running MyPy type checking...")
        mypy_result = subprocess.run([
            "mypy", 
            str(self.project_root / "custom_components")
        ], cwd=self.project_root).returncode
        
        # Return non-zero if any check failed
        return max(black_result, isort_result, flake8_result, mypy_result)
    
    def run_security_checks(self) -> int:
        """Run security vulnerability checks."""
        print("Running security checks...")
        
        # Bandit security linting
        print("\n1. Running Bandit security analysis...")
        bandit_result = subprocess.run([
            "bandit", "-r", 
            str(self.project_root / "custom_components"),
            "-f", "json",
            "-o", "bandit-report.json"
        ], cwd=self.project_root).returncode
        
        # Safety dependency vulnerability check
        print("\n2. Checking dependencies for vulnerabilities...")
        safety_result = subprocess.run([
            "safety", "check", "--json", "--output", "safety-report.json"
        ], cwd=self.project_root).returncode
        
        return max(bandit_result, safety_result)
    
    def generate_coverage_report(self) -> int:
        """Generate detailed coverage report."""
        print("Generating coverage report...")
        
        # Run tests with coverage
        test_result = subprocess.run([
            "pytest", 
            str(self.tests_dir),
            "--cov=custom_components.sure_finance",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            "--cov-fail-under=85"
        ], cwd=self.project_root).returncode
        
        if test_result == 0:
            print(f"\nCoverage report generated:")
            print(f"  - HTML: {self.project_root / 'htmlcov' / 'index.html'}")
            print(f"  - XML: {self.project_root / 'coverage.xml'}")
        
        return test_result
    
    def run_all_checks(self, verbose: bool = False) -> int:
        """Run all tests and checks."""
        print("Running complete test suite...")
        
        results = []
        
        # 1. Linting and formatting
        print("\n" + "="*50)
        print("STEP 1: Code Quality Checks")
        print("="*50)
        results.append(self.run_linting())
        
        # 2. Security checks
        print("\n" + "="*50)
        print("STEP 2: Security Checks")
        print("="*50)
        results.append(self.run_security_checks())
        
        # 3. Unit tests
        print("\n" + "="*50)
        print("STEP 3: Unit Tests")
        print("="*50)
        results.append(self.run_unit_tests(verbose=verbose, coverage=True))
        
        # 4. Integration tests
        print("\n" + "="*50)
        print("STEP 4: Integration Tests")
        print("="*50)
        results.append(self.run_integration_tests(verbose=verbose))
        
        # 5. Performance tests
        print("\n" + "="*50)
        print("STEP 5: Performance Tests")
        print("="*50)
        results.append(self.run_performance_tests(verbose=verbose))
        
        # Summary
        print("\n" + "="*50)
        print("TEST SUITE SUMMARY")
        print("="*50)
        
        step_names = [
            "Code Quality", 
            "Security", 
            "Unit Tests", 
            "Integration Tests", 
            "Performance Tests"
        ]
        
        all_passed = True
        for i, (name, result) in enumerate(zip(step_names, results)):
            status = "PASS" if result == 0 else "FAIL"
            print(f"{i+1}. {name}: {status}")
            if result != 0:
                all_passed = False
        
        print("\n" + "="*50)
        if all_passed:
            print("🎉 ALL CHECKS PASSED!")
            return 0
        else:
            print("❌ SOME CHECKS FAILED!")
            return 1
    
    def setup_test_environment(self) -> int:
        """Set up the test environment."""
        print("Setting up test environment...")
        
        # Install test dependencies
        print("Installing test dependencies...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", 
            str(self.project_root / "requirements-test.txt")
        ], cwd=self.project_root).returncode
        
        if result == 0:
            print("✅ Test environment setup complete!")
        else:
            print("❌ Failed to set up test environment!")
        
        return result
    
    def clean_test_artifacts(self) -> None:
        """Clean up test artifacts and cache files."""
        print("Cleaning test artifacts...")
        
        artifacts = [
            ".pytest_cache",
            "__pycache__",
            ".coverage",
            "htmlcov",
            "coverage.xml",
            "bandit-report.json",
            "safety-report.json",
            ".mypy_cache"
        ]
        
        for artifact in artifacts:
            artifact_path = self.project_root / artifact
            if artifact_path.exists():
                if artifact_path.is_file():
                    artifact_path.unlink()
                    print(f"  Removed file: {artifact}")
                else:
                    import shutil
                    shutil.rmtree(artifact_path)
                    print(f"  Removed directory: {artifact}")
        
        # Clean __pycache__ directories recursively
        for pycache in self.project_root.rglob("__pycache__"):
            import shutil
            shutil.rmtree(pycache)
            print(f"  Removed: {pycache}")
        
        print("✅ Cleanup complete!")


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for Sure Finance Home Assistant Integration"
    )
    
    parser.add_argument(
        "command",
        choices=[
            "unit", "integration", "performance", "lint", "security", 
            "coverage", "all", "setup", "clean", "test"
        ],
        help="Test command to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "-t", "--test-path",
        help="Specific test file or function to run (for 'test' command)"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage reporting for unit tests"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    try:
        if args.command == "unit":
            return runner.run_unit_tests(
                verbose=args.verbose, 
                coverage=not args.no_coverage
            )
        elif args.command == "integration":
            return runner.run_integration_tests(verbose=args.verbose)
        elif args.command == "performance":
            return runner.run_performance_tests(verbose=args.verbose)
        elif args.command == "lint":
            return runner.run_linting()
        elif args.command == "security":
            return runner.run_security_checks()
        elif args.command == "coverage":
            return runner.generate_coverage_report()
        elif args.command == "all":
            return runner.run_all_checks(verbose=args.verbose)
        elif args.command == "setup":
            return runner.setup_test_environment()
        elif args.command == "clean":
            runner.clean_test_artifacts()
            return 0
        elif args.command == "test":
            if not args.test_path:
                print("Error: --test-path is required for 'test' command")
                return 1
            return runner.run_specific_test(args.test_path, verbose=args.verbose)
        else:
            print(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ Test run interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test run failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
