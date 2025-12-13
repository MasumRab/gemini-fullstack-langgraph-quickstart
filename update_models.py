#!/usr/bin/env python3
"""
Script to update Gemini model configurations across the project.
Usage: python update_models.py [strategy]
Strategies:
  - optimized (default): Flash-Lite for queries, Flash for reflection, Pro for answer
  - stable: All Gemini 1.5 stable models
  - experimental: Latest Gemini 2.0/2.5 experimental models
  - cost_saver: All Flash-Lite/Flash models
"""

import sys
import re
from pathlib import Path

# Configuration Strategies
STRATEGIES = {
    "optimized": {
        "description": "Cost-optimized: Flash-Lite (query), Flash (reflection), Pro (answer)",
        "query": "gemini-2.5-flash-lite",
        "reflection": "gemini-2.5-flash",
        "answer": "gemini-2.5-pro",
        "tools": "gemini-2.5-flash",
        "frontend": "gemini-2.5-flash"
    },
    "stable": {
        "description": "Legacy Stable: Gemini 1.5 series",
        "query": "gemini-1.5-flash",
        "reflection": "gemini-1.5-flash",
        "answer": "gemini-1.5-pro",
        "tools": "gemini-1.5-pro",
        "frontend": "gemini-1.5-flash"
    },
    "experimental": {
        "description": "Experimental: Latest 2.0/2.5 features",
        "query": "gemini-2.0-flash-exp",
        "reflection": "gemini-2.5-flash",
        "answer": "gemini-2.0-pro-exp",
        "tools": "gemini-2.5-pro",
        "frontend": "gemini-2.5-flash"
    },
    "cost_saver": {
        "description": "Maximum Cost Savings: All Flash-Lite/Flash",
        "query": "gemini-2.5-flash-lite",
        "reflection": "gemini-2.5-flash-lite",
        "answer": "gemini-2.5-flash",
        "tools": "gemini-2.5-flash",
        "frontend": "gemini-2.5-flash-lite"
    }
}

# File Paths
BACKEND_DIR = Path("backend/src/agent")
FRONTEND_FILE = Path("frontend/src/hooks/useAgentState.ts")
ENV_FILE = Path(".env")
ENV_EXAMPLE = Path(".env.example")

def update_file(file_path: Path, pattern: str, replacement: str):
    """
    Apply a regular-expression substitution to a file and write the file only if changes occur.
    
    The function reads the file as UTF-8, applies `re.sub` with MULTILINE mode using `pattern` and `replacement`, and writes the updated content back to the same path if the substitution produces a different content. If the file does not exist, the function prints a warning and returns without modifying anything. When a file is updated, the function prints an update message.
    
    Parameters:
        file_path (Path): Path to the target file to read and potentially overwrite.
        pattern (str): Regular expression pattern to search for. Evaluated with MULTILINE mode.
        replacement (str): Replacement string passed to `re.sub`.
    
    Returns:
        bool: `True` if the file was modified and written, `False` otherwise.
    """
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content != new_content:
        file_path.write_text(new_content, encoding="utf-8")
        print(f"Updated {file_path}")
        return True
    return False

def main():
    """
    Apply a named model strategy across the repository by updating configuration, tool, frontend, and environment files.
    
    Validates the provided strategy name (defaults to "optimized") and exits with code 1 if unknown. For a valid strategy, updates backend configuration.py model defaults for query_generator_model, reflection_model, and answer_model; updates research_tools.py writer_model; updates the frontend hook's default reasoning_model; and updates QUERY_GENERATOR_MODEL, REFLECTION_MODEL, and ANSWER_MODEL in .env and .env.example when present. Prints progress and a completion message.
    """
    strategy_name = sys.argv[1] if len(sys.argv) > 1 else "optimized"

    if strategy_name not in STRATEGIES:
        print(f"Error: Unknown strategy '{strategy_name}'")
        print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
        sys.exit(1)

    config = STRATEGIES[strategy_name]
    print(f"Applying strategy: {strategy_name} ({config['description']})")

    # 1. Update backend configuration.py
    config_file = BACKEND_DIR / "configuration.py"

    # Queries
    update_file(
        config_file,
        r'(query_generator_model: str = Field\s*\n\s*default=")([^"]+)(")',
        f'\\1{config["query"]}\\3'
    )
    # Reflection
    update_file(
        config_file,
        r'(reflection_model: str = Field\s*\n\s*default=")([^"]+)(")',
        f'\\1{config["reflection"]}\\3'
    )
    # Answer
    update_file(
        config_file,
        r'(answer_model: str = Field\s*\n\s*default=")([^"]+)(")',
        f'\\1{config["answer"]}\\3'
    )

    # 2. Update research_tools.py (hardcoded model)
    tools_file = BACKEND_DIR / "research_tools.py"
    update_file(
        tools_file,
        r'(writer_model = init_chat_model\(model=")([^"]+)(")',
        f'\\1{config["tools"]}\\3'
    )

    # 3. Update Frontend Default
    update_file(
        FRONTEND_FILE,
        r'(reasoning_model: ")([^"]+)(")',
        f'\\1{config["frontend"]}\\3'
    )

    # 4. Update .env files (if they contain model defines)
    for env_path in [ENV_FILE, ENV_EXAMPLE]:
        if env_path.exists():
            update_file(env_path, r'(QUERY_GENERATOR_MODEL=)(.*)', f'\\1{config["query"]}')
            update_file(env_path, r'(REFLECTION_MODEL=)(.*)', f'\\1{config["reflection"]}')
            update_file(env_path, r'(ANSWER_MODEL=)(.*)', f'\\1{config["answer"]}')

    print("Model update complete!")

if __name__ == "__main__":
    main()