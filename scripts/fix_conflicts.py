import sys, re, os

def resolve_markdown_list(content):
    # More robust pattern to match git conflicts
    pattern = re.compile(r'<<<<<<< .*?\n(.*?)\n?=======\n?(.*?)\n?>>>>>>>.*?(\n|$)', re.DOTALL)
    
    def replacement(match):
        lines1 = match.group(1).split('\n') if match.group(1) else []
        lines2 = match.group(2).split('\n') if match.group(2) else []
        
        combined = []
        seen = set()
        for line in lines1 + lines2:
            l = line.strip()
            if l and line not in seen:
                combined.append(line)
                seen.add(line)
        return '\n'.join(combined) + '\n'
        
    return pattern.sub(replacement, content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    path = sys.argv[1]
    if os.path.isdir(path):
        sys.exit(0)
    if not os.path.exists(path):
        sys.exit(0)
    with open(path, 'r') as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            sys.exit(0)
    resolved = resolve_markdown_list(content)
    with open(path, 'w') as f:
        f.write(resolved)
