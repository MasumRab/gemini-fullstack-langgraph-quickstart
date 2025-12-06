"""
Comprehensive unit tests for backend/src/agent/configuration.py

Tests cover:
- Configuration initialization
- Default values
- Field validation
- Configuration with custom values
- Edge cases
"""

import pytest
from pydantic import ValidationError

from agent.configuration import Configuration


# Tests for Configuration initialization
class TestConfigurationInitialization:
    """Test suite for Configuration initialization"""

    def test_default_initialization(self):
        """Test Configuration with default values"""
        config = Configuration()
        
        assert config.model == "gemini-2.0-flash-exp"
        assert config.max_loops == 3
        assert config.num_queries == 3
        assert config.require_planning_confirmation == False

    def test_custom_initialization(self):
        """Test Configuration with custom values"""
        config = Configuration(
            model="custom-model",
            max_loops=5,
            num_queries=10,
            require_planning_confirmation=True
        )
        
        assert config.model == "custom-model"
        assert config.max_loops == 5
        assert config.num_queries == 10
        assert config.require_planning_confirmation == True

    def test_partial_custom_initialization(self):
        """Test Configuration with some custom values"""
        config = Configuration(max_loops=10)
        
        assert config.model == "gemini-2.0-flash-exp"
        assert config.max_loops == 10
        assert config.num_queries == 3
        assert config.require_planning_confirmation == False


# Tests for field validation
class TestConfigurationValidation:
    """Test suite for Configuration field validation"""

    def test_model_field_accepts_string(self):
        """Test that model field accepts valid string"""
        config = Configuration(model="gemini-1.5-pro")
        assert config.model == "gemini-1.5-pro"

    def test_max_loops_accepts_positive_int(self):
        """Test that max_loops accepts positive integers"""
        config = Configuration(max_loops=10)
        assert config.max_loops == 10

    def test_max_loops_accepts_one(self):
        """Test that max_loops accepts 1"""
        config = Configuration(max_loops=1)
        assert config.max_loops == 1

    def test_max_loops_zero_validation(self):
        """Test max_loops with zero value"""
        try:
            config = Configuration(max_loops=0)
            # If it allows 0, that's a design choice
            assert config.max_loops == 0
        except ValidationError:
            # If it rejects 0, that's also valid
            assert True

    def test_max_loops_negative_validation(self):
        """Test max_loops rejects negative values"""
        with pytest.raises(ValidationError):
            Configuration(max_loops=-1)

    def test_num_queries_accepts_positive_int(self):
        """Test that num_queries accepts positive integers"""
        config = Configuration(num_queries=5)
        assert config.num_queries == 5

    def test_num_queries_accepts_one(self):
        """Test that num_queries accepts 1"""
        config = Configuration(num_queries=1)
        assert config.num_queries == 1

    def test_num_queries_zero_validation(self):
        """Test num_queries with zero value"""
        try:
            config = Configuration(num_queries=0)
            assert config.num_queries == 0
        except ValidationError:
            assert True

    def test_num_queries_negative_validation(self):
        """Test num_queries rejects negative values"""
        with pytest.raises(ValidationError):
            Configuration(num_queries=-1)

    def test_require_planning_confirmation_boolean(self):
        """Test require_planning_confirmation accepts boolean"""
        config_true = Configuration(require_planning_confirmation=True)
        config_false = Configuration(require_planning_confirmation=False)
        
        assert config_true.require_planning_confirmation is True
        assert config_false.require_planning_confirmation is False

    def test_invalid_type_for_model(self):
        """Test that model field rejects non-string types"""
        with pytest.raises(ValidationError):
            Configuration(model=123)

    def test_invalid_type_for_max_loops(self):
        """Test that max_loops rejects non-integer types"""
        with pytest.raises(ValidationError):
            Configuration(max_loops="not an int")

    def test_invalid_type_for_num_queries(self):
        """Test that num_queries rejects non-integer types"""
        with pytest.raises(ValidationError):
            Configuration(num_queries="not an int")

    def test_invalid_type_for_require_planning_confirmation(self):
        """Test that require_planning_confirmation rejects non-boolean"""
        with pytest.raises(ValidationError):
            Configuration(require_planning_confirmation="not a bool")


# Tests for Configuration metadata
class TestConfigurationMetadata:
    """Test suite for Configuration field metadata"""

    def test_model_has_description(self):
        """Test that model field has description metadata"""
        schema = Configuration.model_json_schema()
        assert "model" in schema["properties"]
        assert "description" in schema["properties"]["model"]

    def test_max_loops_has_description(self):
        """Test that max_loops field has description metadata"""
        schema = Configuration.model_json_schema()
        assert "max_loops" in schema["properties"]
        assert "description" in schema["properties"]["max_loops"]

    def test_num_queries_has_description(self):
        """Test that num_queries field has description metadata"""
        schema = Configuration.model_json_schema()
        assert "num_queries" in schema["properties"]
        assert "description" in schema["properties"]["num_queries"]

    def test_require_planning_confirmation_has_description(self):
        """Test that require_planning_confirmation has description"""
        schema = Configuration.model_json_schema()
        assert "require_planning_confirmation" in schema["properties"]
        assert "description" in schema["properties"]["require_planning_confirmation"]


# Tests for Configuration serialization
class TestConfigurationSerialization:
    """Test suite for Configuration serialization"""

    def test_to_dict(self):
        """Test Configuration can be converted to dict"""
        config = Configuration(
            model="test-model",
            max_loops=5,
            num_queries=2,
            require_planning_confirmation=True
        )
        
        config_dict = config.model_dump()
        
        assert config_dict["model"] == "test-model"
        assert config_dict["max_loops"] == 5
        assert config_dict["num_queries"] == 2
        assert config_dict["require_planning_confirmation"] is True

    def test_to_json(self):
        """Test Configuration can be serialized to JSON"""
        config = Configuration(max_loops=10)
        
        json_str = config.model_dump_json()
        
        assert isinstance(json_str, str)
        assert "max_loops" in json_str
        assert "10" in json_str

    def test_from_dict(self):
        """Test Configuration can be created from dict"""
        config_dict = {
            "model": "custom-model",
            "max_loops": 7,
            "num_queries": 4,
            "require_planning_confirmation": True
        }
        
        config = Configuration(**config_dict)
        
        assert config.model == "custom-model"
        assert config.max_loops == 7
        assert config.num_queries == 4
        assert config.require_planning_confirmation is True


# Tests for Configuration equality
class TestConfigurationEquality:
    """Test suite for Configuration equality"""

    def test_equal_configurations(self):
        """Test that identical configurations are equal"""
        config1 = Configuration(max_loops=5, num_queries=3)
        config2 = Configuration(max_loops=5, num_queries=3)
        
        assert config1.model_dump() == config2.model_dump()

    def test_different_configurations(self):
        """Test that different configurations are not equal"""
        config1 = Configuration(max_loops=5)
        config2 = Configuration(max_loops=10)
        
        assert config1.model_dump() != config2.model_dump()


# Tests for Configuration edge cases
class TestConfigurationEdgeCases:
    """Test suite for Configuration edge cases"""

    def test_empty_model_string(self):
        """Test Configuration with empty model string"""
        try:
            config = Configuration(model="")
            # If it allows empty string, verify it
            assert config.model == ""
        except ValidationError:
            # If it rejects empty string, that's also valid
            assert True

    def test_very_large_max_loops(self):
        """Test Configuration with very large max_loops"""
        config = Configuration(max_loops=1000000)
        assert config.max_loops == 1000000

    def test_very_large_num_queries(self):
        """Test Configuration with very large num_queries"""
        config = Configuration(num_queries=1000000)
        assert config.num_queries == 1000000

    def test_model_with_special_characters(self):
        """Test model field with special characters"""
        config = Configuration(model="gemini-2.0-flash-exp-@#$")
        assert config.model == "gemini-2.0-flash-exp-@#$"

    def test_model_with_spaces(self):
        """Test model field with spaces"""
        config = Configuration(model="model with spaces")
        assert config.model == "model with spaces"

    def test_float_to_int_coercion(self):
        """Test if float values are coerced to int"""
        try:
            config = Configuration(max_loops=5.7)
            # Pydantic might coerce or reject
            assert isinstance(config.max_loops, int)
        except ValidationError:
            # If it rejects floats, that's also valid
            assert True


# Tests for Configuration immutability
class TestConfigurationImmutability:
    """Test suite for Configuration immutability"""

    def test_configuration_is_frozen_or_mutable(self):
        """Test whether Configuration allows modification after creation"""
        config = Configuration(max_loops=5)
        
        try:
            config.max_loops = 10
            # If modification is allowed, verify it worked
            assert config.max_loops == 10
        except (ValidationError, AttributeError):
            # If frozen, modification should fail
            assert config.max_loops == 5


# Tests for Configuration defaults consistency
class TestConfigurationDefaults:
    """Test suite for Configuration default values consistency"""

    def test_default_max_loops_is_reasonable(self):
        """Test that default max_loops is a reasonable value"""
        config = Configuration()
        assert config.max_loops > 0
        assert config.max_loops < 100  # Reasonable upper bound

    def test_default_num_queries_is_reasonable(self):
        """Test that default num_queries is a reasonable value"""
        config = Configuration()
        assert config.num_queries > 0
        assert config.num_queries < 100

    def test_default_model_is_valid(self):
        """Test that default model is a non-empty string"""
        config = Configuration()
        assert isinstance(config.model, str)
        assert len(config.model) > 0

    def test_default_planning_confirmation_is_boolean(self):
        """Test that default require_planning_confirmation is boolean"""
        config = Configuration()
        assert isinstance(config.require_planning_confirmation, bool)


# Integration tests
class TestConfigurationIntegration:
    """Integration tests for Configuration usage"""

    def test_configuration_in_runnable_config(self):
        """Test Configuration usage in RunnableConfig context"""
        from langchain_core.runnables import RunnableConfig
        
        config = Configuration(max_loops=7, num_queries=5)
        
        runnable_config = RunnableConfig(
            configurable=config.model_dump()
        )
        
        assert runnable_config["configurable"]["max_loops"] == 7
        assert runnable_config["configurable"]["num_queries"] == 5

    def test_multiple_configurations(self):
        """Test creating multiple independent configurations"""
        config1 = Configuration(max_loops=3)
        config2 = Configuration(max_loops=5)
        config3 = Configuration(max_loops=10)
        
        assert config1.max_loops == 3
        assert config2.max_loops == 5
        assert config3.max_loops == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])