import logging
import os
from unittest.mock import patch

from config.validation import check_env_strict, validate_environment


class TestValidation:
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    def test_validate_environment_success(self):
        """Test validation passes when all requirements are met."""
        with patch("importlib.util.find_spec", return_value=True):
            checks = validate_environment()

        assert checks["api_key"] is True
        assert checks["pkg_langchain"] is True
        assert checks["pkg_langgraph"] is True
        assert checks["pkg_google_genai"] is True
        # sentence-transformers is optional but tested
        assert checks["sentence_transformers"] is True

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_missing_api_key(self):
        """Test validation flags missing API key."""
        with patch("importlib.util.find_spec", return_value=True):
            checks = validate_environment()

        assert checks["api_key"] is False

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    def test_validate_environment_missing_package(self):
        """Test validation flags missing critical package."""

        def mock_find_spec(name):
            if name == "google.genai":
                return None
            return True

        with patch("importlib.util.find_spec", side_effect=mock_find_spec):
            checks = validate_environment()

        assert checks["pkg_google_genai"] is False
        assert checks["pkg_langchain"] is True

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    def test_validate_environment_missing_optional_package(self):
        """Test validation handles missing optional package (sentence-transformers)."""

        def mock_find_spec(name):
            if name == "sentence_transformers":
                return None
            return True

        with patch("importlib.util.find_spec", side_effect=mock_find_spec):
            checks = validate_environment()

        assert checks["sentence_transformers"] is False
        assert checks["pkg_langchain"] is True

    def test_check_env_strict_success(self):
        """Test strict check returns True when valid."""
        with patch("config.validation.validate_environment") as mock_val:
            mock_val.return_value = {
                "api_key": True,
                "pkg_langchain": True,
                "pkg_langgraph": True,
                "pkg_google_genai": True,
            }
            assert check_env_strict() is True

    def test_check_env_strict_failure(self, caplog):
        """Test strict check returns False (and logs) when invalid."""
        with patch("config.validation.validate_environment") as mock_val:
            mock_val.return_value = {"api_key": False, "pkg_langchain": True}
            # Capture logs to verify the error path
            with caplog.at_level(logging.ERROR):
                result = check_env_strict()
                assert result is False
                assert "Startup Validation Failed" in caplog.text
                assert "Missing API Key" in caplog.text
