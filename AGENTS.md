# Repository Agents

This repository is equipped with specialized AI agents for different development phases:

- **[Sentinel](.Jules/sentinel.md)**: Security auditor. Focuses on vulnerability detection and multi-step reasoning for safety.
- **[Bolt](.Jules/bolt.md)**: Performance optimizer. Specializes in latency reduction and efficient data structures.
- **[Antigravity](.Jules/antigravity.md)**: Lead coding assistant. Expert in LangGraph orchestration, React frontend, and Gemma model integration.

## Jules Integration Tools

Available for managing Jules sessions and PR triage:

### Commands (`.kilo/commands/`)
- `jules-manager.py` - CLI for Jules API: list sessions, send messages, approve plans

### Scripts (`scripts/jules_tools/`)
- `fast_pr_analysis.py` - Generate individual PR markdown files with repair prompts
- `jules_pr_triage.py` - Build file overlap conflict map for merge ordering
- `jules_pr_context.py` - Extract PR context (CI, comments, conflicts)

### Documentation (`docs/pr_analysis/`)
- `PR_CONFLICT_MAP.md` - Current PR conflict summary and merge order
- `individual/PR_*.md` - Per-PR analysis files with repair prompts

### Jules Session-PR Correlation
Use `JULES_API_KEY` environment variable to access:
- `jm_list_sessions` - List recent sessions
- `jm_get_session` - Get session details (includes PR URLs in outputs)
- `jm_send_message` - Unblock agents or request PR creation
- `jm_approve_plan` - Approve session plans

## Cloud Execution Compatibility
These agents are configured for cloud execution in environments with the following tools pre-installed:
- `npm` (v10+): Frontend builds and testing.
- `python` (v3.12+): Backend agent execution and tests.
- `make`: Task orchestration.
- `jules`: Remote agent session management.
- `tavily`: Web research integration (requires API key).
- `google-search`: Primary research tool.
