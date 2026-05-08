from pathlib import Path
import re

path = Path('backend/tests/test_proxy_security.py')
content = path.read_text()
# Add docstrings or `pass` appropriately to empty functions in test_proxy_security.py
content = content.replace(
    '    async def mock_send(message):\n        pass',
    '    async def mock_send(message):\n        """Mock send."""\n        pass'
)
content = content.replace(
    '    async def mock_receive():\n        return {"type": "http.request"}',
    '    async def mock_receive():\n        """Mock receive."""\n        return {"type": "http.request"}'
)
path.write_text(content)

path = Path('backend/scripts/dev.py')
content = path.read_text()
# Fix security hotspot about `shell=is_windows` and `shell=False` inside dev.py
# SonarQube complains about variable `shell` being assigned a boolean and passed to `shell=` argument or unused.
# Let's remove the `shell` variable entirely from `dev.py`
content = content.replace("    shell = is_windows  # specialized shell handling for windows\n", "")
path.write_text(content)

path = Path('backend/scripts/update_models.py')
content = path.read_text()
# SonarQube complains about regex complexity or similar in update_models.py
# Let's simplify the regex replacements
content = content.replace(
    r"""    update_file(
        models_file,
        r'(DEFAULT_QUERY_MODEL\s*=\s*)(.+)',
        f'\1"{config["query"]}"'
    )
    update_file(
        models_file,
        r'(DEFAULT_REFLECTION_MODEL\s*=\s*)(.+)',
        f'\1"{config["reflection"]}"'
    )
    update_file(
        models_file,
        r'(DEFAULT_ANSWER_MODEL\s*=\s*)(.+)',
        f'\1"{config["answer"]}"'
    )""",
    r"""    update_file(models_file, r'DEFAULT_QUERY_MODEL = .+', f'DEFAULT_QUERY_MODEL = "{config["query"]}"')
    update_file(models_file, r'DEFAULT_REFLECTION_MODEL = .+', f'DEFAULT_REFLECTION_MODEL = "{config["reflection"]}"')
    update_file(models_file, r'DEFAULT_ANSWER_MODEL = .+', f'DEFAULT_ANSWER_MODEL = "{config["answer"]}"')"""
)

path.write_text(content)
