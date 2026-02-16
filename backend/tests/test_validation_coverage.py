import os
from unittest.mock import MagicMock, patch

import pytest

from config.validation import check_env_strict, validate_environment


class TestValidation:
    @pytest.fixture
    def mock_env(self):
        """Clean environment for each test."""
        with patch.dict(os.environ, {}, clear=True):
            yield

    def test_validate_environment_missing_keys(self, mock_env):
        """Test validation fails when API keys are missing."""
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            checks = validate_environment()
            assert checks["api_key"] is False

    def test_validate_environment_with_gemini_key(self, mock_env):
        """Test validation passes with GEMINI_API_KEY."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()):
            checks = validate_environment()
            assert checks["api_key"] is True

    def test_validate_environment_with_google_key(self, mock_env):
        """Test validation passes with GOOGLE_API_KEY."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()):
            checks = validate_environment()
            assert checks["api_key"] is True

    def test_validate_environment_missing_packages(self):
        """Test validation reports missing packages."""
        # Mock importlib.util.find_spec to return None for specific packages

        def mock_find_spec(name, package=None):
            if name == "langchain":
                return None
            return MagicMock()

        with patch("importlib.util.find_spec", side_effect=mock_find_spec):
            checks = validate_environment()
            assert checks["pkg_langchain"] is False
            # Others should be true (mock returns MagicMock which is truthy)
            assert checks["pkg_langgraph"] is True

    def test_validate_environment_optional_packages(self):
        """Test optional package checks."""
        with patch("importlib.util.find_spec") as mock_find:
            # Simulate sentence_transformers missing
            def side_effect(name, package=None):
                if name == "sentence_transformers":
                    return None
                return MagicMock()

            mock_find.side_effect = side_effect

            checks = validate_environment()
            assert checks["sentence_transformers"] is False

    def test_check_env_strict_failure(self, mock_env, caplog):
        """Test strict check fails and logs errors when env is invalid."""
        # Ensure validation returns failure
        with patch("config.validation.validate_environment", return_value={"api_key": False}):
            result = check_env_strict()
            assert result is False
            assert "Startup Validation Failed: Missing API Key" in caplog.text

    def test_check_env_strict_pkg_failure(self, mock_env, caplog):
        """Test strict check fails when package is missing."""
        # Ensure validation returns failure
        with patch("config.validation.validate_environment", return_value={"api_key": True, "pkg_langchain": False}):
            result = check_env_strict()
            assert result is False
            assert "Missing Package: pkg_langchain" in caplog.text

    def test_check_env_strict_success(self, mock_env):
        """Test strict check passes when everything is valid."""
        with patch("config.validation.validate_environment", return_value={"api_key": True, "pkg_langchain": True}):
            result = check_env_strict()
            assert result is True
