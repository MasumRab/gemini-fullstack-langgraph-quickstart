# Fix SonarCloud issues
cd backend
sed -i 's/async def call_next(req): return Response("ok")/async def call_next(_req): return Response("ok")/' tests/agent/test_api_security.py
sed -i 's/async def mock_receive():/async def mock_receive():/' tests/test_proxy_security.py
sed -i 's/async def mock_send(message): pass/async def mock_send(_message): pass/' tests/test_proxy_security.py
