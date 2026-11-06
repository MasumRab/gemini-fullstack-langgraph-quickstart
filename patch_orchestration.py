import re

with open('backend/src/agent/orchestration.py', 'r') as f:
    content = f.read()

# Fix the bug in _load_default_tools where rag_tool.invoke is called but rag_tool doesn't have invoke
fix = """        # RAG retrieval
        try:
            from agent.rag import create_rag_tool, is_rag_enabled
            if is_rag_enabled():
                rag_tool = create_rag_tool([])
                if rag_tool:
                    self.register(
                        "rag_search",
                        lambda query: rag_tool.retrieve(query), # Fixed missing invoke method
                        description="Search internal knowledge base",
                        category="search",
                    )
        except ImportError:
            pass"""

content = re.sub(r'        # RAG retrieval.*?pass', fix, content, flags=re.DOTALL)

with open('backend/src/agent/orchestration.py', 'w') as f:
    f.write(content)
