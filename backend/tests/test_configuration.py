"""Unit tests for the Configuration class.

Tests cover default values, environment variable overrides, type conversions,
and comprehensive validation.
"""
import pytest
from pydantic import ValidationError

from agent.configuration import Configuration
from agent.models import TEST_MODEL, GEMINI_PRO


class TestConfiguration:
    """Tests for the Configuration class."""

    def test_default_values(self):
        """Configuration should have sensible defaults."""
        config = Configuration()

        assert config.query_generator_model == TEST_MODEL
        assert config.reflection_model == TEST_MODEL
        assert config.answer_model == TEST_MODEL
        assert config.number_of_initial_queries == 3
        assert config.max_research_loops == 2
        assert config.require_planning_confirmation is True

    def test_from_runnable_config_with_none(self):
        """from_runnable_config with None should use defaults."""
        config = Configuration.from_runnable_config(None)

        assert config.query_generator_model == TEST_MODEL
        assert config.number_of_initial_queries == 3

    def test_from_runnable_config_with_empty_dict(self):
        """from_runnable_config with empty dict should use defaults."""
        config = Configuration.from_runnable_config({})

        assert config.max_research_loops == 2

    def test_from_runnable_config_overrides_from_configurable(self):
        """Values in configurable should override defaults."""
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
        runnable_config = {
            "configurable": {
                "require_planning_confirmation": "true",
            }
        }

        config = Configuration.from_runnable_config(runnable_config)
        assert config.require_planning_confirmation is True

    def test_boolean_field_from_string_false(self):
        """Boolean fields should handle string 'false' correctly."""
        runnable_config = {
            "configurable": {
                "require_planning_confirmation": "false",
            }
        }

        config = Configuration.from_runnable_config(runnable_config)
        assert config.require_planning_confirmation is False

    def test_integer_field_from_string(self):
        """Integer fields should handle string values correctly."""
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
        monkeypatch.setenv("NUMBER_OF_INITIAL_QUERIES", "8")
        monkeypatch.setenv("MAX_RESEARCH_LOOPS", "5")

        config = Configuration.from_runnable_config({})

        assert config.number_of_initial_queries == 8
        assert config.max_research_loops == 5

    def test_configurable_takes_precedence_over_env(self, monkeypatch):
        """Configurable values should take precedence over env vars."""
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
        runnable_config = {
            "configurable": {
                "query_generator_model": "new-model",
            }
        }

        config = Configuration.from_runnable_config(runnable_config)

        assert config.query_generator_model == "new-model"
        # Other fields should have defaults
        assert config.reflection_model == TEST_MODEL
        assert config.number_of_initial_queries == 3


class TestConfigurationValidation:
    """Test suite for Configuration field validation."""

    def test_model_field_accepts_string(self):
        """Test that model field accepts valid string."""
        config = Configuration(query_generator_model=GEMINI_PRO)
        assert config.query_generator_model == GEMINI_PRO

    def test_max_loops_accepts_positive_int(self):
        """Test that max_research_loops accepts positive integers."""
        config = Configuration(max_research_loops=10)
        assert config.max_research_loops == 10

    def test_require_planning_confirmation_boolean(self):
        """Test require_planning_confirmation accepts boolean."""
        config_true = Configuration(require_planning_confirmation=True)
        config_false = Configuration(require_planning_confirmation=False)

        assert config_true.require_planning_confirmation is True
        assert config_false.require_planning_confirmation is False


class TestConfigurationSerialization:
    """Test suite for Configuration serialization."""

    def test_to_dict(self):
        """Test Configuration can be converted to dict."""
        config = Configuration(
            query_generator_model="test-model",
            max_research_loops=5,
            number_of_initial_queries=2,
            require_planning_confirmation=True
        )

        config_dict = config.model_dump()

        assert config_dict["query_generator_model"] == "test-model"
        assert config_dict["max_research_loops"] == 5
        assert config_dict["number_of_initial_queries"] == 2
        assert config_dict["require_planning_confirmation"] is True


class TestConfigurationDefaults:
    """Test suite for Configuration default values consistency."""

    def test_default_max_loops_is_reasonable(self):
        """Test that default max_research_loops is a reasonable value."""
        config = Configuration()
        assert config.max_research_loops > 0
        assert config.max_research_loops < 100

    def test_default_num_queries_is_reasonable(self):
        """Test that default number_of_initial_queries is a reasonable value."""
        config = Configuration()
        assert config.number_of_initial_queries > 0
        assert config.number_of_initial_queries < 100

    def test_default_model_is_valid(self):
        """Test that default model is a non-empty string."""
        config = Configuration()
        assert isinstance(config.query_generator_model, str)
        assert len(config.query_generator_model) > 0

    def test_default_planning_confirmation_is_boolean(self):
        """Test that default require_planning_confirmation is boolean."""
        config = Configuration()
        assert isinstance(config.require_planning_confirmation, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
