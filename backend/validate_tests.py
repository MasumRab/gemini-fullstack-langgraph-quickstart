#!/usr/bin/env python3
"""
Test Suite Validation Script

This script validates that all test files are properly structured
and can be discovered by pytest.
"""

import os
import sys
import importlib.util
from pathlib import Path

def validate_test_file(filepath):
    """Validate a single test file."""
    try:
        # Try to import the module
        spec = importlib.util.spec_from_file_location("test_module", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Count test classes and functions
        test_classes = [name for name in dir(module) if name.startswith('Test')]
        test_functions = [name for name in dir(module) if name.startswith('test_')]
        
        return {
            'success': True,
            'classes': len(test_classes),
            'functions': len(test_functions),
            'error': None
        }
    except Exception as e:
        return {
            'success': False,
            'classes': 0,
            'functions': 0,
            'error': str(e)
        }

def main():
    """Main validation function."""
    tests_dir = Path(__file__).parent / 'tests'
    test_files = sorted(tests_dir.glob('test_*.py'))
    
    print("=" * 60)
    print("Test Suite Validation")
    print("=" * 60)
    print()
    
    total_classes = 0
    total_functions = 0
    failed_files = []
    
    for test_file in test_files:
        print(f"Validating: {test_file.name}...", end=" ")
        result = validate_test_file(test_file)
        
        if result['success']:
            print(f"✅ ({result['classes']} classes, {result['functions']} functions)")
            total_classes += result['classes']
            total_functions += result['functions']
        else:
            print(f"❌")
            print(f"  Error: {result['error']}")
            failed_files.append(test_file.name)
    
    print()
    print("=" * 60)
    print(f"Total Test Classes: {total_classes}")
    print(f"Total Test Functions: {total_functions}")
    print(f"Files Validated: {len(test_files)}")
    print(f"Failed Files: {len(failed_files)}")
    print("=" * 60)
    
    if failed_files:
        print("\n❌ Validation FAILED for:")
        for filename in failed_files:
            print(f"  - {filename}")
        sys.exit(1)
    else:
        print("\n✅ All test files validated successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()