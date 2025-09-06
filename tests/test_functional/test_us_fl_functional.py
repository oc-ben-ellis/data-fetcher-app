"""Functional tests for US Florida (US-FL) SFTP fetcher.

This module contains functional tests that run the US Florida SFTP fetcher
against mock environments to verify end-to-end functionality.
"""

from pathlib import Path

import pytest

from tests.test_functional.test_case_helper import TestCaseHelper


class TestUsFlFunctional:
    """Functional tests for US Florida SFTP fetcher."""

    @pytest.fixture
    def test_helper(self) -> TestCaseHelper:
        """Create a test case helper instance."""
        project_root = Path(__file__).parent.parent.parent
        return TestCaseHelper(project_root)

    def test_us_fl_basic_functional(self, test_helper: TestCaseHelper) -> None:
        """Test basic US Florida SFTP fetcher functionality.

        This test runs the US Florida SFTP fetcher against a mock environment
        and validates that it produces the expected output structure.
        """
        # Discover test cases for us_fl recipe
        test_cases = test_helper.discover_test_cases("us_fl")

        # Should have at least one test case
        assert len(test_cases) > 0, "No test cases found for us_fl recipe"

        # Run the first test case
        test_case_dir = test_cases[0]
        success = test_helper.run_test_case(test_case_dir, "us_fl")

        assert success, f"Test case {test_case_dir.name} failed"

    def test_us_fl_all_test_cases(self, test_helper: TestCaseHelper) -> None:
        """Test all available US Florida SFTP test cases.

        This test runs all available test cases for the US Florida SFTP fetcher
        to ensure comprehensive coverage.
        """
        # Discover all test cases for us_fl recipe
        test_cases = test_helper.discover_test_cases("us_fl")

        # Should have at least one test case
        assert len(test_cases) > 0, "No test cases found for us_fl recipe"

        # Run all test cases
        failed_cases = []
        for test_case_dir in test_cases:
            success = test_helper.run_test_case(test_case_dir, "us_fl")
            if not success:
                failed_cases.append(test_case_dir.name)

        # All test cases should pass
        assert len(failed_cases) == 0, f"Failed test cases: {failed_cases}"
