
import json
import os
import glob

# Mapping from old/deprecated models to new standard models
MODEL_REPLACEMENTS = {
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-1.0-pro": "gemini-2.5-flash-lite", # Approximation
    "gemini-ultra": "gemini-2.5-pro",
    "gemini-pro": "gemini-2.5-pro",
    "gemini-2.0-flash-exp": "gemini-2.5-flash",
}

def update_notebook(path):
    with open(path, 'r', encoding='utf-8') as f:
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
