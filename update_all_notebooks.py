#!/usr/bin/env python3
"""
Script to ensure all notebooks have model configuration options enabled.
This script will:
1. Add/update the setup cell for backend environment
2. Add/update the model configuration cell with all available Gemini models
3. Process all notebooks in the project
"""

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell
from pathlib import Path
import sys

# Define the setup cell content
SETUP_CELL = """# Universal Setup for Backend Environment
import sys
import os
import subprocess
from pathlib import Path

def setup_environment():
    \"\"\"Setup the environment by installing necessary dependencies and setting paths.\"\"\"
    # Get the backend directory. If we are in 'backend', it is cwd.
    backend_dir = Path.cwd()
    if backend_dir.name != 'backend':
        # Search for backend
        if (backend_dir / 'backend').exists():
             backend_dir = backend_dir / 'backend'
        elif (backend_dir.parent / 'backend').exists():
             backend_dir = backend_dir.parent / 'backend'
    
    # Add src to path if it exists (for 'from agent import ...' style)
    src_dir = backend_dir / 'src'
    if src_dir.exists():
        if str(src_dir) not in sys.path:
            sys.path.append(str(src_dir))
            print(f"  [OK] Added {src_dir} to sys.path")
    
    if str(backend_dir) not in sys.path:
        sys.path.append(str(backend_dir))
        
    # Verify backend/agent can be imported
    try:
        import agent
        print("  [OK] Agent module found and imported.")
    except ImportError:
        print("  [!] Agent module not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(backend_dir)])
        print("  [OK] Backend installed in editable mode.")

setup_environment()"""

# Define the model configuration cell content
MODEL_CONFIG_CELL = """# --- MODEL CONFIGURATION ---
# @title Select Gemini Model
# @markdown Choose the Gemini model to use. Only Gemini 2.5 models are currently accessible via the API.

MODEL_STRATEGY = "Gemini 2.5 Flash (Recommended)" # @param ["Gemini 2.5 Flash (Recommended)", "Gemini 2.5 Flash-Lite (Fastest)", "Gemini 2.5 Pro (Best Quality)"]

import os

# Map selection to model ID
# Note: Gemini 1.5 and 2.0 models are deprecated/not accessible via this API
if MODEL_STRATEGY == "Gemini 2.5 Flash (Recommended)":
    SELECTED_MODEL = "gemini-2.5-flash"
elif MODEL_STRATEGY == "Gemini 2.5 Flash-Lite (Fastest)":
    SELECTED_MODEL = "gemini-2.5-flash-lite"
elif MODEL_STRATEGY == "Gemini 2.5 Pro (Best Quality)":
    SELECTED_MODEL = "gemini-2.5-pro"
else:
    # Default fallback
    SELECTED_MODEL = "gemini-2.5-flash"

print(f"Selected Model: {SELECTED_MODEL}")
print(f"Strategy: {MODEL_STRATEGY}")

# Set Environment Variables to override defaults
os.environ["QUERY_GENERATOR_MODEL"] = SELECTED_MODEL
os.environ["REFLECTION_MODEL"] = SELECTED_MODEL
os.environ["ANSWER_MODEL"] = SELECTED_MODEL
os.environ["TOOLS_MODEL"] = SELECTED_MODEL"""

# Define the model verification cell content
MODEL_VERIFICATION_CELL = """# --- MODEL VERIFICATION (Optional) ---
# @title Verify Model Configuration
# @markdown Run this cell to verify that your API key is configured correctly and the selected model is available.

import os

# Check if API key is set
if "GEMINI_API_KEY" not in os.environ:
    print("⚠️  GEMINI_API_KEY not found in environment variables!")
    print("   Please set it before proceeding:")
    print("   export GEMINI_API_KEY='your-api-key-here'")
else:
    try:
        from google import genai
        
        # Initialize the client
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        
        # Test the selected model
        print(f"🧪 Testing model: {SELECTED_MODEL}")
        response = client.models.generate_content(
            model=SELECTED_MODEL,
            contents="Explain how AI works in a few words"
        )
        
        print(f"  [OK] Model verification successful!")
        print(f"   Model: {SELECTED_MODEL}")
        print(f"   Response: {response.text[:100]}...")
        
    except ImportError:
        print("  [!] google-genai package not installed!")
        print("   Installing now...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "google-genai"])
        print("  [OK] Installed! Please re-run this cell.")
        
    except Exception as e:
        print(f"  [X] Model verification failed: {e}")
        print(f"   This could mean:")
        print(f"   - Invalid API key")
        print(f"   - Model '{SELECTED_MODEL}' not available in your region")
        print(f"   - Quota/billing issues (for experimental models)")
        print(f"   - Network connectivity issues")"""

# Define Colab-specific setup cell
COLAB_SETUP_CELL = """# --- COLAB SETUP START ---
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    print("🔧 Running in Google Colab - Installing dependencies...")
    
    # Install backend package
    !rm -rf gemini-fullstack-langgraph-quickstart
    !pip install -q git+https://github.com/MasumRab/gemini-fullstack-langgraph-quickstart.git#subdirectory=backend
    
    # Or if running from a local copy
    # !pip install -q -e ./backend
    
    print("  [OK] Dependencies installed!")
else:
    print("  [OK] Running locally")
# --- COLAB SETUP END ---"""


def has_cell_with_marker(nb, marker):
    """Check if notebook has a cell containing the marker text."""
    for cell in nb.cells:
        if marker in cell.source:
            return True
    return False


def get_cell_index_with_marker(nb, marker):
    """Get the index of the cell containing the marker text."""
    for i, cell in enumerate(nb.cells):
        if marker in cell.source:
            return i
    return -1


def update_or_insert_cell(nb, marker, new_content, position=0):
    """Update existing cell or insert new one."""
    idx = get_cell_index_with_marker(nb, marker)
    
    if idx >= 0:
        # Update existing cell
        nb.cells[idx].source = new_content
        print(f"  [OK] Updated existing cell at position {idx}")
        return idx
    else:
        # Insert new cell
        nb.cells.insert(position, new_code_cell(new_content))
        print(f"  [OK] Inserted new cell at position {position}")
        return position


def process_notebook(notebook_path: Path, dry_run=False):
    """Process a single notebook to ensure it has the required cells."""
    print(f"\n[..] Processing: {notebook_path.name}")
    
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"  [X] Error reading notebook: {e}")
        return False
    
    modified = False
    
    # Determine if this is a Colab-focused notebook
    is_colab_notebook = "colab" in notebook_path.name.lower()
    
    # Step 1: Ensure Colab setup cell (if applicable)
    if is_colab_notebook:
        if not has_cell_with_marker(nb, "COLAB SETUP"):
            update_or_insert_cell(nb, "COLAB SETUP", COLAB_SETUP_CELL, 0)
            modified = True
    
    # Step 2: Ensure setup cell exists
    setup_marker = "Universal Setup for Backend Environment"
    if not has_cell_with_marker(nb, setup_marker):
        # Insert after Colab setup if it exists, otherwise at position 0
        pos = 1 if is_colab_notebook else 0
        update_or_insert_cell(nb, setup_marker, SETUP_CELL, pos)
        modified = True
    else:
        # Update existing setup cell to latest version
        idx = update_or_insert_cell(nb, setup_marker, SETUP_CELL)
        modified = True
    
    # Step 3: Ensure model configuration cell exists
    model_marker = "MODEL CONFIGURATION"
    if not has_cell_with_marker(nb, model_marker):
        # Insert after setup cell
        setup_idx = get_cell_index_with_marker(nb, setup_marker)
        pos = setup_idx + 1 if setup_idx >= 0 else 1
        update_or_insert_cell(nb, model_marker, MODEL_CONFIG_CELL, pos)
        modified = True
    else:
        # Update existing model config cell to latest version
        idx = update_or_insert_cell(nb, model_marker, MODEL_CONFIG_CELL)
        modified = True
    
    # Step 4: Ensure model verification cell exists
    verify_marker = "MODEL VERIFICATION"
    if not has_cell_with_marker(nb, verify_marker):
        # Insert after model config cell
        model_idx = get_cell_index_with_marker(nb, model_marker)
        pos = model_idx + 1 if model_idx >= 0 else 2
        update_or_insert_cell(nb, verify_marker, MODEL_VERIFICATION_CELL, pos)
        modified = True
    else:
        # Update existing verification cell to latest version
        idx = update_or_insert_cell(nb, verify_marker, MODEL_VERIFICATION_CELL)
        modified = True
    
    # Save the notebook if modified
    if modified and not dry_run:
        try:
            with open(notebook_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f)
            print(f"  [OK] Saved changes to {notebook_path.name}")
            return True
        except Exception as e:
            print(f"  [X] Error saving notebook: {e}")
            return False
    elif modified and dry_run:
        print(f"  🔍 [DRY RUN] Would save changes to {notebook_path.name}")
        return True
    else:
        print(f"  [i] No changes needed")
        return False


def main():
    """Main function to process all notebooks."""
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    
    # Find all notebooks
    project_root = Path(__file__).parent
    
    # Define notebook directories to process
    notebook_dirs = [
        project_root / "notebooks",
        project_root / "backend",
        project_root / "examples" / "thinkdepthai_deep_research_example",
        project_root / "examples" / "open_deep_research_example" / "src" / "legacy"
    ]
    
    all_notebooks = []
    for nb_dir in notebook_dirs:
        if nb_dir.exists():
            all_notebooks.extend(nb_dir.glob("*.ipynb"))
    
    if not all_notebooks:
        print("❌ No notebooks found!")
        return
    
    print(f"[..] Found {len(all_notebooks)} notebooks to process\n")
    print("=" * 60)
    
    # Process each notebook
    success_count = 0
    for notebook_path in all_notebooks:
        if process_notebook(notebook_path, dry_run):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"\n[OK] Successfully processed {success_count}/{len(all_notebooks)} notebooks")
    
    if dry_run:
        print("\n💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
