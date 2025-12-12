#!/usr/bin/env python3
"""
Script to update Gemini model configurations across the project.
Usage: python update_models.py [strategy]
Strategies:
  - free_tier (default): Gemini 1.5 Flash for EVERYTHING (Best for avoiding quotas)
  - optimized: Flash-Lite for queries, Flash for reflection, Pro for answer
  - stable: All Gemini 1.5 stable models
  - experimental: Latest Gemini 2.5 experimental models (Requires Billing/Quota)
"""

import sys
import re
from pathlib import Path

# Configuration Strategies
STRATEGIES = {
    "free_tier": {
        "description": "Free Tier Safe: Gemini 1.5 Flash for all components (High RPM limit)",
        "query": "gemini-1.5-flash",
        "reflection": "gemini-1.5-flash",
        "answer": "gemini-1.5-flash",
        "tools": "gemini-1.5-flash",
        "frontend": "gemini-1.5-flash"
    },
    "optimized": {
        "description": "Cost-optimized: 1.5 Flash-8b (query), 1.5 Flash (reflection), 1.5 Pro (answer)",
        "query": "gemini-1.5-flash-8b",
        "reflection": "gemini-1.5-flash",
        "answer": "gemini-1.5-pro",
        "tools": "gemini-1.5-flash",
        "frontend": "gemini-1.5-flash"
    },
    "stable": {
        "description": "Legacy Stable: Gemini 1.5 series",
        "query": "gemini-1.5-flash",
        "reflection": "gemini-1.5-flash",
        "answer": "gemini-1.5-pro",
        "tools": "gemini-1.5-pro",
        "frontend": "gemini-1.5-flash"
    },
    "flash_2_0": {
        "description": "Gemini 2.0 Flash Series: Flash-Lite (query) & Flash (answer)",
        "query": "gemini-2.0-flash-lite-preview-02-05",  # Using specific preview if stable not alias
        "reflection": "gemini-2.0-flash",
        "answer": "gemini-2.0-flash",
        "tools": "gemini-2.0-flash",
        "frontend": "gemini-2.0-flash"
    },
    "experimental": {
        "description": "Experimental: Gemini 2.5 models (Requires Quota/Billing)",
        "query": "gemini-2.5-flash",
        "reflection": "gemini-2.5-flash",
        "answer": "gemini-2.5-pro",
        "tools": "gemini-2.5-flash",
        "frontend": "gemini-2.5-flash"
    }
}

# File Paths
BACKEND_DIR = Path("backend/src/agent")
FRONTEND_FILE = Path("frontend/src/hooks/useAgentState.ts")
ENV_FILE = Path(".env")
ENV_EXAMPLE = Path(".env.example")
NOTEBOOKS_DIR = Path("notebooks")

def update_file(file_path: Path, pattern: str, replacement: str):
    """Update a file using regex pattern."""
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
    strategy_name = sys.argv[1] if len(sys.argv) > 1 else "free_tier"

    if strategy_name not in STRATEGIES:
        print(f"Error: Unknown strategy '{strategy_name}'")
        print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
        sys.exit(1)

    config = STRATEGIES[strategy_name]
    print(f"Applying strategy: {strategy_name} ({config['description']})")

    # 1. Update backend configuration.py
    config_file = BACKEND_DIR / "configuration.py"
    
    # Update fields in configuration.py
    # We use a more robust regex that handles multi-line fields
    update_file(
        config_file,
        r'(query_generator_model: str = Field\s*\(\s*default=")([^"]+)(")',
        f'\\1{config["query"]}\\3'
    )
    update_file(
        config_file,
        r'(reflection_model: str = Field\s*\(\s*default=")([^"]+)(")',
        f'\\1{config["reflection"]}\\3'
    )
    update_file(
        config_file,
        r'(answer_model: str = Field\s*\(\s*default=")([^"]+)(")',
        f'\\1{config["answer"]}\\3'
    )
    
    # Also catch the cleaner generic pattern just in case
    update_file(config_file, r'(query_generator_model: str = Field\n\s*default=")([^"]+)', f'\\1{config["query"]}')
    update_file(config_file, r'(reflection_model: str = Field\n\s*default=")([^"]+)', f'\\1{config["reflection"]}')
    update_file(config_file, r'(answer_model: str = Field\n\s*default=")([^"]+)', f'\\1{config["answer"]}')

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

    # 4. Update .env files
    for env_path in [ENV_FILE, ENV_EXAMPLE]:
        if env_path.exists():
            update_file(env_path, r'(QUERY_GENERATOR_MODEL=)(.*)', f'\\1{config["query"]}')
            update_file(env_path, r'(REFLECTION_MODEL=)(.*)', f'\\1{config["reflection"]}')
            update_file(env_path, r'(ANSWER_MODEL=)(.*)', f'\\1{config["answer"]}')
            
    # 5. Update Notebooks (Experimental)
    # Replaces common hardcoded patterns in ipynb files
    if NOTEBOOKS_DIR.exists():
        for nb in NOTEBOOKS_DIR.glob("*.ipynb"):
            update_file(nb, r'(model=\\")gemini-[^"]+(\\")', f'\\1{config["answer"]}\\2')

    print(f"Model update complete! Using {config['answer']} (and variants) for {strategy_name} strategy.")

if __name__ == "__main__":
    main()
