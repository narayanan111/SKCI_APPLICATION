import pytest
import coverage
import os

def run_tests():
    # Start coverage
    cov = coverage.Coverage()
    cov.start()

    # Run tests
    pytest.main(['-v', 'tests/'])

    # Stop coverage
    cov.stop()
    cov.save()

    # Generate coverage report
    print('\nCoverage Report:')
    cov.report()

    # Generate HTML coverage report
    cov.html_report(directory='coverage_html')
    print('\nHTML coverage report generated in coverage_html/ directory')

if __name__ == '__main__':
    run_tests() 