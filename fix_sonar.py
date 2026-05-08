from pathlib import Path
import re

# Fix update_models.py
path = Path('backend/scripts/update_models.py')
content = path.read_text()

# Manual replacement since string literals match perfectly might be tricky due to escapes.
# We'll just replace the lines.
lines = content.split('\n')
new_lines = []
skip = False
for line in lines:
    if line.startswith('CONSTANTS_MAP = {'):
        skip = True
        continue
    if skip and line == '}':
        skip = False
        continue
    if skip:
        continue

    if line.strip() == 'def get_val(m):':
        skip = True
        continue
    if skip and 'return CONSTANTS_MAP.get' in line:
        skip = False
        continue

    if "f'\\\\1{get_val(config" in line:
        new_lines.append(line.replace("f'\\\\1{get_val(config", "f'\\\\1\"{config").replace(")}'", "}\"'"))
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# One more cleanup to remove empty lines left by CONSTANTS_MAP removal
content = re.sub(r'\n{3,}', '\n\n', content)

path.write_text(content)
