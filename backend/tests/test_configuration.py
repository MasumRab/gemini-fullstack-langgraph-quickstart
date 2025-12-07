"""Unit tests for the Configuration class.

Tests cover default values, environment variable overrides, and type conversions.
"""
import os
import pytest


class TestConfiguration:
    """Tests for the Configuration class."""

    def test_default_values(self):
        """Configuration should have sensible defaults."""
        from agent.configuration import Configuration
        
        config = Configuration()
        
        assert config.query_generator_model == "gemini-1.5-flash"
        assert config.reflection_model == "gemini-1.5-flash"
        assert config.answer_model == "gemini-1.5-pro"
        assert config.number_of_initial_queries == 3
        assert config.max_research_loops == 2
        assert config.require_planning_confirmation is True

    def test_from_runnable_config_with_none(self):
        """from_runnable_config with None should use defaults."""
        from agent.configuration import Configuration
        
        config = Configuration.from_runnable_config(None)
        
        assert config.query_generator_model == "gemini-1.5-flash"
        assert config.number_of_initial_queries == 3

    def test_from_runnable_config_with_empty_dict(self):
        """from_runnable_config with empty dict should use defaults."""
        from agent.configuration import Configuration
        
        config = Configuration.from_runnable_config({})
        
        assert config.max_research_loops == 2

    def test_from_runnable_config_overrides_from_configurable(self):
        """Values in configurable should override defaults."""
        from agent.configuration import Configuration
        
        runnable_config = {
            "configurable": {
                "query_generator_model": "custom-model",
                "number_of_initial_queries": 5,
                "max_research_loops": 10,
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        assert config.query_generator_model == "custom-model"
        assert config.number_of_initial_queries == 5
        assert config.max_research_loops == 10

    def test_boolean_field_from_string_true(self):
        """Boolean fields should handle string 'true' correctly."""
        from agent.configuration import Configuration
        
        runnable_config = {
            "configurable": {
                "require_planning_confirmation": "true",
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        assert config.require_planning_confirmation is True

    def test_boolean_field_from_string_false(self):
        """Boolean fields should handle string 'false' correctly."""
        from agent.configuration import Configuration
        
        runnable_config = {
            "configurable": {
                "require_planning_confirmation": "false",
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        assert config.require_planning_confirmation is False

    def test_integer_field_from_string(self):
        """Integer fields should handle string values correctly."""
        from agent.configuration import Configuration
        
        runnable_config = {
            "configurable": {
                "number_of_initial_queries": "7",
                "max_research_loops": "4",
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        assert config.number_of_initial_queries == 7
        assert config.max_research_loops == 4

    def test_from_runnable_config_with_env_vars(self, monkeypatch):
        """Environment variables should be used when configurable is empty."""
        from agent.configuration import Configuration
        
        monkeypatch.setenv("NUMBER_OF_INITIAL_QUERIES", "8")
        monkeypatch.setenv("MAX_RESEARCH_LOOPS", "5")
        
        config = Configuration.from_runnable_config({})
        
        assert config.number_of_initial_queries == 8
        assert config.max_research_loops == 5

    def test_configurable_takes_precedence_over_env(self, monkeypatch):
        """Configurable values should take precedence over env vars."""
        from agent.configuration import Configuration
        
        monkeypatch.setenv("NUMBER_OF_INITIAL_QUERIES", "100")
        
        runnable_config = {
            "configurable": {
                "number_of_initial_queries": 2,
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        assert config.number_of_initial_queries == 2

    def test_partial_override(self):
        """Partial overrides should leave other fields at defaults."""
        from agent.configuration import Configuration
        
        runnable_config = {
            "configurable": {
                "query_generator_model": "new-model",
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        assert config.query_generator_model == "new-model"
        # Other fields should have defaults
        assert config.reflection_model == "gemini-1.5-flash"
        assert config.number_of_initial_queries == 3
