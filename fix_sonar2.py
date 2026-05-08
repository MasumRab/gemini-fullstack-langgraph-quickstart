from pathlib import Path
import re

# test_proxy_security.py Line 134: async def mock_send(message): pass -> empty function
# Replace empty async defs with proper mock functions
path = Path('backend/tests/test_proxy_security.py')
content = path.read_text()
content = content.replace(
    'async def mock_send(message): pass',
    'async def mock_send(message):\n        """Mock send."""\n        pass'
)
content = content.replace(
    'async def mock_receive(): return {"type": "http.request"}',
    'async def mock_receive():\n        """Mock receive."""\n        return {"type": "http.request"}'
)
path.write_text(content)

# update_models.py Line 27: hardcoded IP or security issue?
# "query": "gemini-2.5-flash-lite", -> maybe Sonar thinks this is a hardcoded secret?
# Or is it complaining about Regex complexity?
# "f'\\\\1{config[\"frontend\"]}\\3'" -> Line 127/128?
# Let's fix test_api_security.py Line 218: empty function or hardcoded stuff
path = Path('backend/tests/agent/test_api_security.py')
content = path.read_text()
content = content.replace(
    'async def call_next(req):\n            return Response("ok")',
    'async def call_next(req):\n            """Mock next."""\n            return Response("ok")'
)
path.write_text(content)
