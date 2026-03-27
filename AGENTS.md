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

## Repository Hygiene and Workflows

### Dealing with Missing Configuration Files (Dependabot, Mergify)
When working on older Pull Requests, you may notice that important configuration files (like `.github/dependabot.yml` or `.mergify.yml`) appear to be "missing" or "deleted." This is almost never because an agent deleted them. It is because the branch you are on was created *before* those files were added to the `main` branch.

To avoid accidentally overwriting, deleting, or re-creating these files incorrectly, **agents MUST adhere to the following workflow when investigating missing configurations**:

1. **Check the `main` branch:** Run `git fetch origin main` and `git ls-tree origin/main .github/` to see if the file exists in the latest `main` branch.
2. **Review Open PRs:** Use `gh pr list --state all` and `gh pr view` to see if there are already merged or open Pull Requests that implemented the missing configuration (e.g., Dependabot or Mergify).
3. **Rebase or Merge (if instructed):** If the configuration exists in `main` but is missing in your current PR branch, you must sync your branch with `main` (`git merge origin/main` or `git rebase origin/main`) to acquire those files before attempting to "fix" them.
4. **Never blindly recreate:** Do not assume a file was maliciously deleted. Always verify the repository state and PR history to confirm if it was recently added to `main` and is simply absent from your outdated checkout.
