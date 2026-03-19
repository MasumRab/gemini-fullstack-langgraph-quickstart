#!/usr/bin/env python3
"""Script to ensure all notebooks have model configuration options enabled and correct Colab setup.
This script will:
1. Add/update the Colab setup cell (Clone + CD + Install)
2. Add/update the setup cell for backend environment (Local path setup)
3. Add/update the model configuration cell
4. Process all notebooks in the project
"""

import os
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell

# Constants
COLAB_SETUP_MARKER = "COLAB SETUP"
SETUP_MARKER = "Universal Setup for Backend Environment"
MODEL_CONFIG_MARKER = "MODEL CONFIGURATION"
MODEL_VERIFY_MARKER = "MODEL VERIFICATION"

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
    SELECTED_MODEL = "gemma-3-27b-it"
elif MODEL_STRATEGY == "Gemini 2.5 Flash-Lite (Fastest)":
    SELECTED_MODEL = "gemma-3-27b-it-lite"
elif MODEL_STRATEGY == "Gemini 2.5 Pro (Best Quality)":
    SELECTED_MODEL = "gemma-3-27b-it"
else:
    # Default fallback
    SELECTED_MODEL = "gemma-3-27b-it"

print(f"Selected Model: {SELECTED_MODEL}")
print(f"Strategy: {MODEL_STRATEGY}")

# Set Environment Variables to override defaults
os.environ["QUERY_GENERATOR_MODEL"] = SELECTED_MODEL
os.environ["REFLECTION_MODEL"] = SELECTED_MODEL
os.environ["ANSWER_MODEL"] = SELECTED_MODEL
os.environ["TOOLS_MODEL"] = SELECTED_MODEL

# Ensure GOOGLE_API_KEY is set if GEMINI_API_KEY is present (for LangChain compatibility)
if "GEMINI_API_KEY" in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    print("  [OK] Synced GEMINI_API_KEY to GOOGLE_API_KEY for LangChain")"""

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
        
    except OSError as e:
        print(f"  [X] Model verification failed: {e}")
        print(f"   This could mean:")
        print(f"   - Invalid API key")
        print(f"   - Model '{SELECTED_MODEL}' not available in your region")
        print(f"   - Quota/billing issues (for experimental models)")
        print(f"   - Network connectivity issues")"""

def get_colab_setup_cell(rel_path):
    """Generates a Colab setup cell that clones the repo and cds to the correct directory.
    rel_path: path of the notebook relative to repo root (e.g. 'notebooks', 'backend')
    """
    # Calculate path to cd into after cloning
    # If notebook is in 'notebooks/', we cd to 'gemini.../notebooks'
    # If notebook is in 'backend/', we cd to 'gemini.../backend'

    return f"""# --- COLAB SETUP START ---
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

if IN_COLAB:
    print("🔧 Running in Google Colab - Installing dependencies...")
    
    # 1. Clone the repository
    !rm -rf gemini-fullstack-langgraph-quickstart
    !git clone https://github.com/MasumRab/gemini-fullstack-langgraph-quickstart.git

    # 2. Navigate to the correct directory
    import os
    repo_name = "gemini-fullstack-langgraph-quickstart"
    target_dir = os.path.join(repo_name, "{rel_path}")

    if os.path.exists(target_dir):
        os.chdir(target_dir)
        print(f"  [OK] Changed directory to {{os.getcwd()}}")
    else:
        # Fallback to repo root if specific dir not found
        if os.path.exists(repo_name):
            os.chdir(repo_name)
            print(f"  [OK] Changed directory to {{os.getcwd()}} (Fallback)")

    # 3. Install Backend (Quietly)
    # We install from the backend directory which should be reachable
    # relative to current dir or absolute

    # Find backend relative to current position
    import sys
    if os.path.exists("backend"):
        !pip install -q -e backend
    elif os.path.exists("../backend"):
        !pip install -q -e ../backend
    elif os.path.exists("src"): # We might be IN backend
        !pip install -q -e .
    else:
        print("  [X] Error: Could not find backend directory to install.")
        sys.exit(1)

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


def process_notebook(notebook_path: Path, project_root: Path, dry_run: bool = False) -> bool:
    """Process a single notebook to ensure it has the required cells."""
    print(f"\n[..] Processing: {notebook_path.name}")
    
    try:
        with open(notebook_path, encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except OSError as e:
        print(f"  [X] Error reading notebook: {e}")
        return False
    
    modified = _update_notebook_cells(nb, notebook_path, project_root)
    
    # Save the notebook if modified
    if modified and not dry_run:
        try:
            with open(notebook_path, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f)
            print(f"  [OK] Saved changes to {notebook_path.name}")
            return True
        except OSError as e:
            print(f"  [X] Error saving notebook: {e}")
            return False
    elif modified and dry_run:
        print(f"  🔍 [DRY RUN] Would save changes to {notebook_path.name}")
        return True
    else:
        print("  [i] No changes needed")
        return False


def _update_notebook_cells(nb, notebook_path: Path, project_root: Path) -> bool:
    """Helper to update notebook cells. Returns True if modified."""
    modified = False
    
    # Calculate relative path for Colab setup
    try:
        rel_path = notebook_path.parent.relative_to(project_root)
    except ValueError:
        rel_path = Path(".")

    colab_setup_content = get_colab_setup_cell(str(rel_path))
    
    # Step 1: Ensure Colab setup cell
    if _ensure_cell(nb, COLAB_SETUP_MARKER, colab_setup_content, 0):
        modified = True
    
    # Step 2: Ensure setup cell exists (Backend setup)
    if _ensure_cell(nb, SETUP_MARKER, SETUP_CELL, 1):
        modified = True
    
    # Step 3: Ensure model configuration cell exists
    if _ensure_cell(nb, MODEL_CONFIG_MARKER, MODEL_CONFIG_CELL, _get_next_pos(nb, SETUP_MARKER, 2)):
        modified = True
    
    # Step 4: Ensure model verification cell exists
    if _ensure_cell(nb, MODEL_VERIFY_MARKER, MODEL_VERIFICATION_CELL, _get_next_pos(nb, MODEL_CONFIG_MARKER, 3)):
        modified = True
    
    return modified


def _ensure_cell(nb, marker: str, content: str, default_pos: int) -> bool:
    """Ensure a cell exists with the given marker and content."""
    has_marker = has_cell_with_marker(nb, marker)
    if has_marker:
        update_or_insert_cell(nb, marker, content, default_pos)
    else:
        update_or_insert_cell(nb, marker, content)
    return not has_marker  # Returns True if new cell was added


def _get_next_pos(nb, marker: str, default: int) -> int:
    """Get the next position after a marker."""
    idx = get_cell_index_with_marker(nb, marker)
    return idx + 1 if idx >= 0 else default


def main():
    """Main function to process all notebooks."""
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified\n")
    
    # Find all notebooks
    project_root = Path(__file__).parent.parent.resolve()
    
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
        if process_notebook(notebook_path, project_root, dry_run):
            success_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"\n[OK] Successfully processed {success_count}/{len(all_notebooks)} notebooks")
    
    if dry_run:
        print("\n💡 Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
