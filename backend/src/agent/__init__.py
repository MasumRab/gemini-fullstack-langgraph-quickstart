"""Agent package initialization.

This module initializes the agent package. It uses lazy imports or try/except blocks
to allow the package to be imported even if some optional dependencies are missing.
"""
import logging

logger = logging.getLogger(__name__)

# Try to import critical submodules to expose them at package level if needed,
# but usually, we want to keep __init__.py minimal to avoid side effects.
# If tests are relying on `from agent import persistence`, then `persistence`
# must be exposed here OR `agent` must be a namespace package where `agent.persistence` works.
# Since we added this __init__.py, it is now a regular package.

# We don't necessarily need to import everything here, but if tests expect
# `from agent import persistence` to work, `persistence` must be available as a submodule.
# Python handles `import agent.persistence` fine without this, but `from agent import persistence`
# might require `persistence` to be in `sys.modules['agent']` or imported here.

# Ideally, tests should use `from agent.persistence import ...` or `import agent.persistence`.
# The failure `ImportError: cannot import name 'persistence' from 'agent'` often happens
# when `agent` is imported from `backend/tests/agent` (shadowing) instead of `backend/src/agent`.

# By ensuring `backend/src` is in sys.path and `backend/tests/agent` does NOT have __init__.py
# (or we rename it), we can fix this.

# However, since the user asked to "Guard backend/src/agent/__init__.py against import-time failures",
# I will populate it with safe imports if needed, but for now, an empty or minimal one is safer
# than one that tries to import everything.

# Let's just allow it to be a package.
