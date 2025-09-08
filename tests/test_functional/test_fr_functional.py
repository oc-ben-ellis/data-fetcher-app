"""Functional tests for France (FR) API fetcher.

This module contains functional tests that run the France API fetcher
against mock environments to verify end-to-end functionality.
"""

from pathlib import Path

import pytest

from tests.test_functional.test_case_helper import TestCaseHelper


class TestFrFunctional:
    """Functional tests for France API fetcher."""

    @pytest.fixture
    def test_helper(self) -> TestCaseHelper:
        """Create a test case helper instance."""
        project_root = Path(__file__).parent.parent.parent
        return TestCaseHelper(project_root)

    def test_fr_basic_functional(self, test_helper: TestCaseHelper) -> None:
        """Test basic France API fetcher functionality.

        This test runs the France API fetcher against a mock environment
        and validates that it produces the expected output structure.
        """
        # Discover test cases for fr recipe
        test_cases = test_helper.discover_test_cases("fr")

        # Should have at least one test case
        assert len(test_cases) > 0, "No test cases found for fr recipe"

        # Run the first test case
        test_case_dir = test_cases[0]
        success = test_helper.run_test_case(test_case_dir, "fr")

        assert success, f"Test case {test_case_dir.name} failed"

    def test_fr_all_test_cases(self, test_helper: TestCaseHelper) -> None:
        """Test all available France API test cases.

        This test runs all available test cases for the France API fetcher
        to ensure comprehensive coverage.
        """
        # Discover all test cases for fr recipe
        test_cases = test_helper.discover_test_cases("fr")

        # Should have at least one test case
        assert len(test_cases) > 0, "No test cases found for fr recipe"

        # Run all test cases
        failed_cases = []
        for test_case_dir in test_cases:
            success = test_helper.run_test_case(test_case_dir, "fr")
            if not success:
                failed_cases.append(test_case_dir.name)

        # All test cases should pass
        assert len(failed_cases) == 0, f"Failed test cases: {failed_cases}"
