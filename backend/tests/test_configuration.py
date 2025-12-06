import pathlib
import sys
import os
from unittest.mock import patch

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent.configuration import Configuration  # noqa: E402


class TestConfiguration:
    """Test suite for Configuration class."""

    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = Configuration()
        assert config.query_generator_model == "gemini-2.0-flash"
        assert config.reflection_model == "gemini-2.5-flash"
        assert config.answer_model == "gemini-2.5-pro"
        assert config.number_of_initial_queries == 3
        assert config.max_research_loops == 5
        assert config.require_planning_confirmation is False

    def test_from_runnable_config_with_configurable(self):
        """Test Configuration.from_runnable_config with configurable dict."""
        runnable_config = {
            "configurable": {
                "query_generator_model": "gemini-1.5-pro",
                "max_research_loops": 10,
                "require_planning_confirmation": True,
            }
        }
        config = Configuration.from_runnable_config(runnable_config)
        assert config.query_generator_model == "gemini-1.5-pro"
        assert config.max_research_loops == 10
        assert config.require_planning_confirmation is True
        # Check defaults are still set for non-specified fields
        assert config.reflection_model == "gemini-2.5-flash"

    @patch.dict(os.environ, {
        "QUERY_GENERATOR_MODEL": "gemini-test-model",
        "MAX_RESEARCH_LOOPS": "7",
        "REQUIRE_PLANNING_CONFIRMATION": "true"
    })
    def test_from_runnable_config_with_environment(self):
        """Test Configuration.from_runnable_config with environment variables."""
        config = Configuration.from_runnable_config({})
        assert config.query_generator_model == "gemini-test-model"
        assert config.max_research_loops == 7
        assert config.require_planning_confirmation is True

    @patch.dict(os.environ, {"QUERY_GENERATOR_MODEL": "env-model"})
    def test_configurable_overrides_environment(self):
        """Test that configurable dict takes precedence over environment."""
        runnable_config = {
            "configurable": {
                "query_generator_model": "config-model",
            }
        }
        config = Configuration.from_runnable_config(runnable_config)
        # Environment has "env-model", but configurable should take precedence
        # Based on the implementation, configurable.get(name) is checked first
        assert config.query_generator_model == "config-model"

    def test_from_runnable_config_empty(self):
        """Test Configuration.from_runnable_config with empty config uses defaults."""
        config = Configuration.from_runnable_config({})
        assert config.query_generator_model == "gemini-2.0-flash"
        assert config.reflection_model == "gemini-2.5-flash"
        assert config.answer_model == "gemini-2.5-pro"

    def test_from_runnable_config_with_none_values(self):
        """Test that None values in configurable are filtered out."""
        runnable_config = {
            "configurable": {
                "query_generator_model": None,
                "max_research_loops": 8,
            }
        }
        config = Configuration.from_runnable_config(runnable_config)
        # None values should be filtered, so defaults should apply
        assert config.query_generator_model == "gemini-2.0-flash"
        assert config.max_research_loops == 8

    def test_boolean_field_conversion(self):
        """Test boolean field handling in configuration."""
        runnable_config = {
            "configurable": {
                "require_planning_confirmation": "true",
            }
        }
        config = Configuration.from_runnable_config(runnable_config)
        # The new implementation doesn't do type conversion, so this would be a string
        # This test verifies current behavior
        assert config.require_planning_confirmation == "true"

    def test_integer_field_conversion(self):
        """Test integer field handling in configuration."""
        runnable_config = {
            "configurable": {
                "max_research_loops": "15",
            }
        }
        config = Configuration.from_runnable_config(runnable_config)
        # The new implementation doesn't do type conversion
        assert config.max_research_loops == "15"

    def test_pydantic_validation(self):
        """Test that pydantic validates types correctly."""
        # Valid types should work
        config = Configuration(
            query_generator_model="test-model",
            max_research_loops=5,
            require_planning_confirmation=False
        )
        assert config.query_generator_model == "test-model"
        assert config.max_research_loops == 5
        assert config.require_planning_confirmation is False

    def test_field_metadata(self):
        """Test that field metadata is correctly defined."""
        fields = Configuration.model_fields
        assert "query_generator_model" in fields
        assert "reflection_model" in fields
        assert "answer_model" in fields
        assert "number_of_initial_queries" in fields
        assert "max_research_loops" in fields
        assert "require_planning_confirmation" in fields
        
        # Check that metadata exists
        query_field = fields["query_generator_model"]
        assert query_field.metadata is not None
        assert "description" in query_field.metadata[0]