import os
from pydantic import BaseModel, Field
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


class Configuration(BaseModel):
    """The configuration for the agent."""

    query_generator_model: str = Field(
        default="gemini-1.5-flash",
        metadata={
            "description": "The name of the language model to use for the agent's query generation."
        },
    )

    reflection_model: str = Field(
        default="gemini-1.5-flash",
        metadata={
            "description": "The name of the language model to use for the agent's reflection."
        },
    )

    answer_model: str = Field(
        default="gemini-1.5-pro",
        metadata={
            "description": "The name of the language model to use for the agent's answer."
        },
    )

    number_of_initial_queries: int = Field(
        default=3,
        metadata={"description": "The number of initial search queries to generate."},
    )

    max_research_loops: int = Field(
        default=2,
        metadata={"description": "The maximum number of research loops to perform."},
    )

    require_planning_confirmation: bool = Field(
        default=True,
        metadata={
            "description": "If true, pause after planning until the user confirms the plan"
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        # Get raw values from environment or config
        raw_values: dict[str, Any] = {}
        for name, field_info in cls.model_fields.items():
            # Try to get from configurable first, then environment
            value = configurable.get(name, os.environ.get(name.upper()))
            
            if value is not None:
                # Handle type conversions
                field_type = field_info.annotation
                
                # Handle boolean fields
                if field_type == bool or (hasattr(field_type, '__origin__') and field_type.__origin__ == bool):
                    if isinstance(value, str):
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = bool(value)
                
                # Handle integer fields
                elif field_type == int or (hasattr(field_type, '__origin__') and field_type.__origin__ == int):
                    if isinstance(value, str):
                        value = int(value)
                
                raw_values[name] = value

        return cls(**raw_values)
