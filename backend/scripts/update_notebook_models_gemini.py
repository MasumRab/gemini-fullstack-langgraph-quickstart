
import glob
import json
import os

# Mapping from old/deprecated models to new standard models
PRO = "gemini-2.5-pro"
FLASH = "gemini-2.5-flash"

MODEL_REPLACEMENTS = {
    "gemini-1.5-flash": FLASH,
    "gemini-1.5-pro": PRO,
    "gemini-1.0-pro": "gemini-2.5-flash-lite", # Approximation
    "gemini-ultra": PRO,
    "gemini-pro": PRO,
    "gemini-2.0-flash-exp": FLASH,
}

def update_notebook(path):
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
