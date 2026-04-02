import os
import re

# Update update_notebook_models_gemini.py
with open("backend/scripts/update_notebook_models_gemini.py", "r") as f:
    content = f.read()
# Let's fix line 9: `import os` and `import glob` might be unused or wrong order. Actually, looking at SonarCloud, "Make sure this dictionary is securely configured" or similar? Let's just run ruff check on these files, wait I already did.
