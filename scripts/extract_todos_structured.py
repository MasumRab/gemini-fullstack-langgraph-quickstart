import os
import re
import json

def extract_todos(root_dir):
    todos = []
    # Grep for TODOs
    try:
        # Using grep to find TODOs recursively, excluding node_modules, .git, .jules
        # -r: recursive, -n: line number, -I: ignore binary
        stream = os.popen(f"grep -rIn 'TODO' {root_dir} --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.jules --exclude-dir=dist --exclude-dir=.venv")
        lines = stream.readlines()

        for line in lines:
            parts = line.strip().split(':', 2)
            if len(parts) < 3:
                continue
            filepath = parts[0]
            lineno = parts[1]
            content = parts[2]

            # Simple parsing
            match = re.search(r'TODO\((.*?)\):(.*)', content)
            if match:
                metadata = match.group(1)
                text = match.group(2).strip()
                todos.append({
                    'file': filepath,
                    'line': lineno,
                    'raw': content.strip(),
                    'text': text,
                    'metadata': metadata
                })
            else:
                todos.append({
                    'file': filepath,
                    'line': lineno,
                    'raw': content.strip(),
                    'text': content.replace('//', '').replace('#', '').replace('TODO', '').strip(),
                    'metadata': 'legacy'
                })
    except Exception as e:
        print(f"Error extracting TODOs: {e}")

    return todos

if __name__ == "__main__":
    todos = extract_todos(".")
    print(json.dumps(todos, indent=2))
