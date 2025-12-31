import os
import re
import json
from pathlib import Path

def extract_todos(root_dir):
    todos = []
    # Exclude directories
    exclude_dirs = {'.git', 'node_modules', '.jules', 'dist', 'build', '.venv', '__pycache__'}

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(('.py', '.tsx', '.ts', '.js', '.jsx', '.md')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if 'TODO' in line:
                                # Simple parser
                                content = line.strip()
                                # Try to parse structured TODOs if they exist
                                # Format: TODO(priority=<Level>, complexity=<Level>):
                                priority = "Unknown"
                                complexity = "Unknown"

                                match = re.search(r'TODO\(priority=(.*?), complexity=(.*?)\):', content)
                                if match:
                                    priority = match.group(1)
                                    complexity = match.group(2)

                                todos.append({
                                    'file': filepath,
                                    'line': i + 1,
                                    'content': content,
                                    'priority': priority,
                                    'complexity': complexity
                                })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    return todos

if __name__ == "__main__":
    todos = extract_todos('.')
    print(json.dumps(todos, indent=2))
