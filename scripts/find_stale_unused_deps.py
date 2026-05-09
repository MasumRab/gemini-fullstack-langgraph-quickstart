#!/usr/bin/env python3
import json
import subprocess
import os
import re
from datetime import datetime, timedelta, timezone

# --- CONFIG ---
AGE_THRESHOLD_DAYS = 90
REPORT_FILE = "unused_deps_report.txt"

# --- HELPERS ---
def get_file_blame_lines(filepath):
    """Returns a list of dicts with line number, commit date, and content."""
    try:
        output = subprocess.check_output(
            ["git", "blame", "--line-porcelain", filepath],
            universal_newlines=True, stderr=subprocess.DEVNULL
        )
        lines = []
        current_line = {}
        for line in output.splitlines():
            if line.startswith("author-time "):
                current_line['time'] = int(line.split(" ")[1])
            elif line.startswith("\t"):
                current_line['content'] = line[1:]
                lines.append(current_line)
                current_line = {}
        return lines
    except Exception as e:
        print(f"Error blaming {filepath}: {e}")
        return []

def get_age_days(timestamp):
    commit_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    return (now - commit_date).days

def is_used(dep_name, search_dirs, extensions):
    """Simple grep-based heuristic to check if a dependency is imported."""
    # This is a naive MVP check.
    # Convert hyphens to underscores for python (e.g. langchain-core -> langchain_core)
    py_dep = dep_name.replace('-', '_')

    # We will search for occurrences of dep_name or py_dep in source files.
    for d in search_dirs:
        for root, dirs, files in os.walk(d):
            if 'node_modules' in dirs:
                dirs.remove('node_modules')
            if '.venv' in dirs:
                dirs.remove('.venv')
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if dep_name in content or py_dep in content:
                                return True
                    except Exception:
                        pass
    return False

# --- FRONTEND (package.json) ---
def check_frontend():
    print("Checking frontend...")
    pkg_json = "frontend/package.json"
    if not os.path.exists(pkg_json):
        return []

    with open(pkg_json, 'r', encoding='utf-8') as f:
        pkg = json.load(f)

    deps = list(pkg.get("dependencies", {}).keys()) + list(pkg.get("devDependencies", {}).keys())

    blame = get_file_blame_lines(pkg_json)

    results = []
    for dep in deps:
        # Exclude internal or highly common toolings if desired, but for MVP check all
        if dep in ['react', 'react-dom', 'typescript', 'vite']: continue

        # Find oldest insertion of this dep in package.json
        age = 0
        for b_line in blame:
            if f'"{dep}"' in b_line['content']:
                age = max(age, get_age_days(b_line.get('time', 0)))

        if age > AGE_THRESHOLD_DAYS:
            # Check if used
            if not is_used(dep, ['frontend/src'], ['.ts', '.tsx', '.js', '.jsx', '.css']):
                results.append(f"[Frontend] {dep} (Age: {age} days)")
    return results

# --- BACKEND (pyproject.toml / requirements.txt) ---
def check_backend():
    print("Checking backend...")
    pyproj = "backend/pyproject.toml"
    results = []

    if os.path.exists(pyproj):
        with open(pyproj, 'r', encoding='utf-8') as f:
            content = f.read()

        deps = []
        in_deps = False
        for line in content.splitlines():
            line = line.strip()
            if line == 'dependencies = [':
                in_deps = True
                continue
            if in_deps and line == ']':
                in_deps = False
                continue
            if in_deps and line.startswith('"'):
                # parse dependency name
                dep = line.split('"')[1]
                # clean versions like "fastapi>=0.100" -> "fastapi"
                dep = re.split(r'[=><~]', dep)[0]
                deps.append(dep)

        blame = get_file_blame_lines(pyproj)

        for dep in deps:
            # Skip python runtime dep or core frameworks
            if dep in ['python', 'pytest']: continue
            age = 0
            for b_line in blame:
                if dep in b_line['content']:
                    age = max(age, get_age_days(b_line.get('time', 0)))

            if age > AGE_THRESHOLD_DAYS:
                if not is_used(dep, ['backend/src', 'backend/tests'], ['.py']):
                    results.append(f"[Backend] {dep} (Age: {age} days)")
    return results

# --- RUN ---
def main():
    report = []
    report.extend(check_frontend())
    report.extend(check_backend())

    with open(REPORT_FILE, 'w') as f:
        f.write("Unused Dependencies (>90 days old):\n")
        f.write("======================================\n")
        if not report:
            f.write("None found.\n")
        for item in report:
            f.write(f"- {item}\n")

    print(f"Done. Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    main()
