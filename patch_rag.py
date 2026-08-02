import re

with open("backend/src/agent/rag.py", "r") as f:
    content = f.read()

content = content.replace('''<<<<<<< HEAD
        self,
        query: str,
        max_tokens: int = 4000,
        subgoal_ids: List[str] | None = None,
=======
        self, query: str, max_tokens: int = 4000, subgoal_ids: List[str] | None = None
>>>>>>> origin/main''', '        self, query: str, max_tokens: int = 4000, subgoal_ids: List[str] | None = None,')

with open("backend/src/agent/rag.py", "w") as f:
    f.write(content)
