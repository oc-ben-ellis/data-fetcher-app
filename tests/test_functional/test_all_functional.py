"""Comprehensive functional tests for all fetcher recipes.

This module contains functional tests that run all available fetcher recipes
against mock environments to verify end-to-end functionality across the entire system.
"""

from pathlib import Path

import pytest

from tests.test_functional.test_case_helper import TestCaseHelper


class TestAllFunctional:
    """Functional tests for all fetcher recipes."""

    @pytest.fixture
    def test_helper(self) -> TestCaseHelper:
        """Create a test case helper instance."""
        project_root = Path(__file__).parent.parent.parent
        return TestCaseHelper(project_root)

    def test_all_recipes_have_test_cases(self, test_helper: TestCaseHelper) -> None:
        """Test that all recipes have corresponding test cases.

        This test verifies that test cases exist for all available recipes
        to ensure comprehensive test coverage.
        """
        # Known recipes that should have test cases
        expected_recipes = ["fr", "us_fl"]

        for recipe in expected_recipes:
            test_cases = test_helper.discover_test_cases(recipe)
            assert len(test_cases) > 0, f"No test cases found for recipe: {recipe}"

    def test_fr_recipe_functional(self, test_helper: TestCaseHelper) -> None:
        """Test France API recipe functionality."""
        test_cases = test_helper.discover_test_cases("fr")
        assert len(test_cases) > 0, "No test cases found for fr recipe"

        # Run the first test case
        test_case_dir = test_cases[0]
        success = test_helper.run_test_case(test_case_dir, "fr")
        assert success, f"FR test case {test_case_dir.name} failed"

    def test_us_fl_recipe_functional(self, test_helper: TestCaseHelper) -> None:
        """Test US Florida SFTP recipe functionality."""
        test_cases = test_helper.discover_test_cases("us_fl")
        assert len(test_cases) > 0, "No test cases found for us_fl recipe"

        # Run the first test case
        test_case_dir = test_cases[0]
        success = test_helper.run_test_case(test_case_dir, "us_fl")
        assert success, f"US-FL test case {test_case_dir.name} failed"

    def test_all_available_test_cases(self, test_helper: TestCaseHelper) -> None:
        """Test all available test cases across all recipes.

        This comprehensive test runs all available test cases to ensure
        the entire system works correctly.
        """
        # Known recipes
        recipes = ["fr", "us_fl"]
        all_failed_cases = []

        for recipe in recipes:
            test_cases = test_helper.discover_test_cases(recipe)

            for test_case_dir in test_cases:
                success = test_helper.run_test_case(test_case_dir, recipe)
                if not success:
                    all_failed_cases.append(f"{recipe}/{test_case_dir.name}")

        # All test cases should pass
        assert len(all_failed_cases) == 0, f"Failed test cases: {all_failed_cases}"
