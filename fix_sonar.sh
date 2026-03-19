# Fix SonarCloud issues
cd backend

sed -i 's/def process_notebook(notebook_path: Path, project_root: Path, dry_run=False):/def process_notebook(notebook_path, project_root, dry_run=False):/' scripts/update_all_notebooks.py
