from pathlib import Path
import re

path = Path('backend/scripts/update_models.py')
content = path.read_text()
# Replace the rest of the regexes with simple strings
content = content.replace(r"r'(QUERY_GENERATOR_MODEL=)(.*)'", "r'QUERY_GENERATOR_MODEL=.*'")
content = content.replace(r"f'\\1{config[\"query\"]}'", "f'QUERY_GENERATOR_MODEL={config[\"query\"]}'")

content = content.replace(r"r'(REFLECTION_MODEL=)(.*)'", "r'REFLECTION_MODEL=.*'")
content = content.replace(r"f'\\1{config[\"reflection\"]}'", "f'REFLECTION_MODEL={config[\"reflection\"]}'")

content = content.replace(r"r'(ANSWER_MODEL=)(.*)'", "r'ANSWER_MODEL=.*'")
content = content.replace(r"f'\\1{config[\"answer\"]}'", "f'ANSWER_MODEL={config[\"answer\"]}'")

content = content.replace(
    r"r'(reasoning_model: \")([^\"]+)(\")'",
    r'r"reasoning_model: \\"[^\"]+\\""'
)
content = content.replace(
    r"f'\1{config[\"frontend\"]}\3'",
    r'f"reasoning_model: \"{config[\"frontend\"]}\""'
)
path.write_text(content)

path = Path('backend/scripts/dev.py')
content = path.read_text()
# Line 9 was flagged, meaning probably the command line list `shlex.split`
content = content.replace('is_windows = sys.platform.startswith("win")', 'is_windows = sys.platform.startswith("win")')

path = Path('backend/scripts/test_model_availability.py')
content = path.read_text()
# Ensure subprocess call has explicit timeout and exception handling (sometimes SonarCloud flags missing timeouts)
content = content.replace('subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False)', 'subprocess.run(cmd, capture_output=True, text=True, check=True, shell=False, timeout=30)')
path.write_text(content)

path = Path('backend/scripts/test_available_models.py')
content = path.read_text()
content = content.replace('subprocess.run(["make", "dev-backend"], shell=False, cwd=str(backend_dir))', 'subprocess.run(["make", "dev-backend"], shell=False, cwd=str(backend_dir), timeout=60)')
path.write_text(content)
