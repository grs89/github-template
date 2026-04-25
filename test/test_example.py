"""
Test suite example for github-template project.

This module provides example tests following pytest conventions.
Run with: pytest test/ -v
"""

import unittest
from unittest.mock import Mock, patch


class TestTemplateExample(unittest.TestCase):
    """Example test cases for the template project."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_data = {"name": "test", "value": 123}

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_sample_dict_creation(self):
        """Test that sample data is created correctly."""
        self.assertIsNotNone(self.sample_data)
        self.assertEqual(self.sample_data["name"], "test")
        self.assertEqual(self.sample_data["value"], 123)

    def test_sample_dict_has_required_keys(self):
        """Test that sample data has required keys."""
        required_keys = {"name", "value"}
        self.assertTrue(required_keys.issubset(self.sample_data.keys()))

    def test_sample_value_is_integer(self):
        """Test that value field is an integer."""
        self.assertIsInstance(self.sample_data["value"], int)

    def test_sample_name_is_string(self):
        """Test that name field is a string."""
        self.assertIsInstance(self.sample_data["name"], str)

    @patch("requests.get")
    def test_api_call_mocked(self, mock_get):
        """Test mocked API call."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "success"}

        # Simulate API call
        response = mock_get("http://api.example.com/data")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        mock_get.assert_called_once()


class TestEnvironmentConfig(unittest.TestCase):
    """Test environment configuration loading."""

    def test_env_file_exists(self):
        """Test that .env.example exists (template)."""
        import os
        env_example = ".env.example"
        self.assertTrue(os.path.exists(env_example), f"{env_example} not found")

    def test_requirements_file_exists(self):
        """Test that requirements.txt exists."""
        import os
        requirements = "utilidades/requirements.txt"
        self.assertTrue(os.path.exists(requirements), f"{requirements} not found")


if __name__ == "__main__":
    unittest.main()
