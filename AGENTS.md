# Repository Agents

This repository is equipped with specialized AI agents for different development phases:

- **[Sentinel](.Jules/sentinel.md)**: Security auditor. Focuses on vulnerability detection and multi-step reasoning for safety.
- **[Bolt](.Jules/bolt.md)**: Performance optimizer. Specializes in latency reduction and efficient data structures.
- **[Antigravity](.Jules/antigravity.md)**: Lead coding assistant. Expert in LangGraph orchestration, React frontend, and Gemma model integration.

## Cloud Execution Compatibility
These agents are configured for cloud execution in environments with the following tools pre-installed:
- `npm` (v10+): Frontend builds and testing.
- `python` (v3.12+): Backend agent execution and tests.
- `make`: Task orchestration.
- `jules`: Remote agent session management.
- `tavily`: Web research integration (requires API key).
- `google-search`: Primary research tool.
