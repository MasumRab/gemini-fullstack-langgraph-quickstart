# Project: Gemini Fullstack Langgraph Quickstart

## 🔍 Semantic Tooling & Intelligence

This project is integrated into the workspace's semantic search hierarchy. Use the following tools for discovery and analysis:

- **Semantic Search (`ck`)**: `ck --index .` (Use for intent-based search).
- **Structural Analysis (`ast-grep`)**: Uses tree-sitter for pattern matching.
- **Architecture Graph (`code-review-graph`)**: Registered as `langgraph`. Run `code-review-graph build --skip-flows` to initialize.
- **RAG / Documentation (`qmd`)**: Index any local docs with `qmd collection add ./docs`.

Refer to `~/github/local/workspace/SEARCH_SPEC.md` for the full technical specification and operational commands.
