import ast
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scipy.cluster.hierarchy as sch

# Set up paths
BACKEND_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = BACKEND_ROOT / "src"

# Known third-party packages to map imports to
# This is a simplified mapping; a production version might query pip
PACKAGE_MAPPING = {
    "langgraph": "langgraph",
    "langchain": "langchain",
    "langchain_core": "langchain-core",
    "langchain_google_genai": "langchain-google-genai",
    "google": "google-genai",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "dotenv": "python-dotenv",
    "sentence_transformers": "sentence-transformers",
    "faiss": "faiss-cpu",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "duckduckgo_search": "duckduckgo-search",
    "tenacity": "tenacity",
    "numpy": "numpy",
    "scipy": "scipy",
    "mcp": "mcp",
}

def get_third_party_imports(file_path):
    """Parses a python file and returns a set of third-party base modules imported."""
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split('.')[0]
                imports.add(base)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                base = node.module.split('.')[0]
                imports.add(base)

    # Filter for known third-party
    third_party = set()
    for imp in imports:
        # Simple heuristic: if it's in our map or standard library check (omitted for brevity)
        # We rely on the PACKAGE_MAPPING key match or partial match
        if imp in PACKAGE_MAPPING:
            third_party.add(PACKAGE_MAPPING[imp])
        elif imp in sys.stdlib_module_names:
            pass # Ignore stdlib
        else:
            # Check if it's a known top-level package
            pass
    return third_party

def scan_codebase(root_dir):
    """Scans all .py files in root_dir and maps files to their 3rd party deps."""
    file_deps = {}
    all_deps = set()

    for path in root_dir.rglob("*.py"):
        if "tests" in path.parts:
            continue

        rel_path = path.relative_to(root_dir)
        deps = get_third_party_imports(path)
        if deps:
            # Aggregate by module folder to reduce noise
            # e.g. agent/nodes.py -> agent
            module = str(rel_path.parent).replace("/", ".")
            if module == ".":
                module = "root"

            if module not in file_deps:
                file_deps[module] = set()
            file_deps[module].update(deps)
            all_deps.update(deps)

    return file_deps, sorted(list(all_deps))

def visualize_clusters(module_deps, all_deps):
    """Generates a hierarchical clustering dendrogram."""
    if not module_deps:
        print("No dependencies found to visualize.")
        return

    modules = sorted(list(module_deps.keys()))
    deps_list = all_deps

    # Create feature matrix (Modules x Dependencies)
    matrix = np.zeros((len(modules), len(deps_list)))

    for i, mod in enumerate(modules):
        for j, dep in enumerate(deps_list):
            if dep in module_deps[mod]:
                matrix[i, j] = 1

    # Compute linkage matrix
    # Using 'ward' linkage minimizes variance within clusters
    try:
        Z = sch.linkage(matrix, method='ward')
    except Exception as e:
        print(f"Clustering failed (likely too few samples): {e}")
        return

    # Plot
    plt.figure(figsize=(12, 8))
    plt.title('Codebase Feature Clustering by Dependency Usage')
    plt.xlabel('Distance')
    plt.ylabel('Modules (Features)')

    # Create dendrogram
    dendrogram = sch.dendrogram(
        Z,
        labels=modules,
        orientation='right',
        leaf_font_size=10
    )

    plt.tight_layout()
    output_path = BACKEND_ROOT.parent / "docs" / "dependency_structure.png"
    plt.savefig(output_path)
    print(f"Visualization saved to {output_path}")

def main():
    print(f"Scanning {SRC_ROOT}...")
    module_deps, all_deps = scan_codebase(SRC_ROOT)

    print(f"Found {len(module_deps)} modules and {len(all_deps)} unique dependencies.")
    print("Dependencies:", ", ".join(all_deps))

    visualize_clusters(module_deps, all_deps)

if __name__ == "__main__":
    main()
