from typing import Dict, Any, List
import logging
from backend.src.agent.nodes import validate_web_results

logger = logging.getLogger(__name__)

def test_validation():
    """Verify validation logic with mock data."""
    print("Testing Validation Logic...")

    # Mock Config: require citations
    # In a real test, we'd mock the config object properly.
    # For this script, we assume the default config or environment variables are set.

    # Sample Data
    summaries = [
        "Python is great. [Python](http://python.org)",
        "Java is verbose.", # No citation
        "The sky is blue. [Nature](http://nature.com)",
        "Unrelated spam content." # No overlap with query "programming"
    ]

    # Mock State
    state = {
        "web_research_result": summaries,
        "search_query": ["programming languages"],
    }

    result = validate_web_results(state, {})

    print("Validation Notes:")
    for note in result["validation_notes"]:
        print(f"- {note}")

    print("\nValidated Results:")
    for res in result["validated_web_research_result"]:
        print(f"- {res}")

if __name__ == "__main__":
    test_validation()
