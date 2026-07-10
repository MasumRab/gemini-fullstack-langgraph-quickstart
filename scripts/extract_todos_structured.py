import os
import re
import json
from pathlib import Path

TODO_PATTERN = re.compile(r'TODO\(priority=([^,]+), complexity=([^,]+), owner=([^)]+)\):')
TODO_OLD_PATTERN = re.compile(r'TODO\(priority=([^,]+), complexity=([^)]+)\):')

def extract_todos(root_dir):
    todos = []
    # Exclude directories
    exclude_dirs = {'.git', 'node_modules', '.jules', '.Jules', 'dist', 'build', '.venv', '__pycache__'}
    this_file = Path(__file__).resolve()

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if not file.endswith(('.py', '.tsx', '.ts', '.js', '.jsx', '.md')):
                continue

            filepath = os.path.join(root, file)
            if Path(filepath).resolve() == this_file:
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        if 'TODO' not in line:
                            continue

                        # Simple parser
                        content = line.strip()
                        # Try to parse structured TODOs if they exist
                        # Format: TODO(priority=<Level>, complexity=<Level>, owner=<Owner>):
                        priority = "Unknown"
                        complexity = "Unknown"
                        owner = "Unknown"

                        match = TODO_PATTERN.search(content)
                        if match:
                            priority = match.group(1)
                            complexity = match.group(2)
                            owner = match.group(3)
                        else:
                            # Fallback for old format
                            match_old = TODO_OLD_PATTERN.search(content)
                            if match_old:
                                priority = match_old.group(1)
                                complexity = match_old.group(2)

                        todos.append({
                            'file': filepath,
                            'line': i + 1,
                            'content': content,
                            'priority': priority,
                            'complexity': complexity,
                            'owner': owner
                        })
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    return todos

if __name__ == "__main__":
    todos = extract_todos('.')
    print(json.dumps(todos, indent=2))
