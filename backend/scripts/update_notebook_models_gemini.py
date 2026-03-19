
import glob
import json
import os
from pathlib import Path

# Model name constants
GEMINI_FLASH = "gemini-2.5-flash"
GEMINI_FLASH_LITE = "gemini-2.5-flash-lite"
GEMINI_PRO = "gemini-2.5-pro"

# Mapping from old/deprecated models to new standard models
MODEL_REPLACEMENTS = {
    "gemini-1.5-flash": GEMINI_FLASH,
    "gemini-1.5-pro": GEMINI_PRO,
    "gemini-1.0-pro": GEMINI_FLASH_LITE,  # Approximation
    "gemini-ultra": GEMINI_PRO,
    "gemini-pro": GEMINI_PRO,
    "gemini-2.0-flash-exp": GEMINI_FLASH,
}

def update_notebook(path: str | Path) -> None:
    with open(path, encoding='utf-8') as f:
        content = f.read()

    original_content = content
    for old, new in MODEL_REPLACEMENTS.items():
        content = content.replace(old, new)
        # Also handle potential code strings if they use separate quotes
        # e.g. model="gemini-1.5-flash"
    
    if content != original_content:
        print(f"Updated {path}")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(f"No changes for {path}")

def main():
    notebooks = glob.glob("notebooks/*.ipynb") + glob.glob("backend/*.ipynb")
    for nb in notebooks:
        update_notebook(nb)

if __name__ == "__main__":
    main()
