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

## Agent Workflows
To avoid duplicate work on automated repository tasks:
- **Check Open Pull Requests**: Before initiating a repository-wide refactor, dependency update, or mass formatting, agents MUST check for open Pull Requests addressing the same issue. Use `curl -s "https://api.github.com/repos/MasumRab/gemini-fullstack-langgraph-quickstart/pulls?state=open"` or the GitHub CLI (`gh pr list`). If an existing unmerged PR is addressing the target intent, agents should verify whether the intended local changes are already covered there before duplicating effort locally.
