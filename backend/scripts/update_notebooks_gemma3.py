"""Update all notebooks to use gemma-3-27b-it as default model."""

import json
from pathlib import Path


def _apply_replacements(line: str) -> tuple[str, bool]:
    """Helper to apply model replacements."""
    original_line = line
    replacements = {
        'gemini-2.5-flash': 'gemma-3-27b-it',
        'gemini-2.5-pro': 'gemma-3-27b-it',
        'gemini-1.5-flash': 'gemma-3-27b-it',
        'gemini-1.5-pro': 'gemma-3-27b-it'
    }
    for old, new in replacements.items():
        line = line.replace(old, new)
    return line, line != original_line

def update_notebook(notebook_path: str | Path) -> bool:
    """Update a single notebook to use gemma-3-27b-it."""
    with open(notebook_path, encoding='utf-8') as f:
        nb = json.load(f)
    
    modified = False
    
    for cell in nb.get('cells', []):
        if cell.get('cell_type') == 'code':
            source = cell.get('source', [])
            if isinstance(source, list):
                new_source = []
                for line in source:
                    line, changed = _apply_replacements(line)
                    if changed:
                        modified = True
                    new_source.append(line)
                cell['source'] = new_source
    
    if modified:
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
        return True
    return False

if __name__ == "__main__":
    notebooks_dir = Path(__file__).parent.parent / 'notebooks'
    updated_count = 0
    
    for notebook in notebooks_dir.glob('*.ipynb'):
        if update_notebook(notebook):
            print(f"✓ Updated: {notebook.name}")
            updated_count += 1
        else:
            print(f"- No changes: {notebook.name}")
    
    print(f"\nTotal notebooks updated: {updated_count}")
