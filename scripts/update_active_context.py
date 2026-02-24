import os
import sys
import json
import requests
from datetime import datetime

def get_repo_info():
    """
    Determine the repository identifier in the form "owner/repo".
    
    Checks the GITHUB_REPOSITORY environment variable first, then falls back to parsing the configured git remote origin URL (supports common SSH and HTTPS GitHub URL formats). Returns None if no repository can be determined or an error occurs.
    
    Returns:
        repo (str or None): Repository identifier in 'owner/repo' format if found, otherwise None.
    """
    # 1. From Environment
    repo = os.getenv("GITHUB_REPOSITORY")
    if repo:
        return repo

    # 2. From git config
    try:
        remote_url = os.popen("git config --get remote.origin.url").read().strip()
        if remote_url:
            # Handle ssh: git@github.com:Owner/Repo.git
            if "git@github.com:" in remote_url:
                repo = remote_url.split("git@github.com:")[1]
            # Handle https: https://github.com/Owner/Repo.git
            elif "github.com/" in remote_url:
                repo = remote_url.split("github.com/")[1]

            if repo.endswith(".git"):
                repo = repo[:-4]
            return repo
    except Exception:
        pass
    return None

def fetch_open_prs(repo, token):
    """
    Retrieve open pull requests for a repository and collect the filenames changed in each PR.
    
    Parameters:
        repo (str): Repository identifier in the form "owner/repo".
        token (str): GitHub personal access token used for API authentication.
    
    Returns:
        list[dict]: A list of dictionaries describing each open PR. Each dictionary contains:
            - "number" (int): PR number.
            - "title" (str): PR title.
            - "user" (str): Author's login.
            - "url" (str): PR HTML URL.
            - "files" (list[str]): Filenames changed in the PR (may be empty).
    
    Notes:
        - If the request for the list of PRs fails or returns a non-200 status, an empty list is returned.
        - Failures when fetching per-PR file lists are ignored for that PR; those PRs will have an empty "files" list.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    api_url = "https://api.github.com"

    # Get list of open PRs
    prs_url = f"{api_url}/repos/{repo}/pulls?state=open"
    try:
        resp = requests.get(prs_url, headers=headers)
        if resp.status_code != 200:
            print(f"Error fetching PRs: {resp.status_code} {resp.text}")
            return []
        prs = resp.json()
    except Exception as e:
        print(f"Request failed: {e}")
        return []

    results = []
    print(f"Found {len(prs)} open PRs.")

    for pr in prs:
        pr_number = pr["number"]
        # Get files for this PR
        files_url = f"{api_url}/repos/{repo}/pulls/{pr_number}/files"
        files = []
        try:
            f_resp = requests.get(files_url, headers=headers)
            if f_resp.status_code == 200:
                files = [f["filename"] for f in f_resp.json()]
        except Exception:
            pass

        results.append({
            "number": pr_number,
            "title": pr["title"],
            "user": pr["user"]["login"],
            "url": pr["html_url"],
            "files": files
        })

    return results

def generate_markdown(prs):
    """
    Builds a Markdown document summarizing open pull requests and their modified files.
    
    Parameters:
        prs (list): Sequence of pull request mappings. Each mapping is expected to contain the keys:
            - `number` (int): PR number.
            - `title` (str): PR title.
            - `user` (str): Author login.
            - `url` (str): HTML URL to the PR.
            - `files` (list): List of modified file paths (may be empty).
    
    Returns:
        str: A Markdown-formatted string containing a header with a UTC timestamp and, for each PR,
             the PR number and title, author, GitHub link, and a bulleted list of modified files.
             If `prs` is empty, the document notes that no open pull requests were found.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🧠 Active Development Context",
        f"Last Updated: {timestamp}\n",
        "## 🚧 Open Pull Requests & Locked Files",
        "> **CONFLICT WARNING:** Do not modify files listed below if they are currently being changed in an open PR.\n"
    ]

    if not prs:
        lines.append("*No open pull requests found.*")
    else:
        for pr in prs:
            lines.append(f"### PR #{pr['number']}: {pr['title']}")
            lines.append(f"- **Author:** @{pr['user']}")
            lines.append(f"- **Link:** [View on GitHub]({pr['url']})")
            lines.append("- **Files Modified:**")
            if pr['files']:
                for f in pr['files']:
                    lines.append(f"  - `{f}`")
            else:
                lines.append("  - *(No file changes detected)*")
            lines.append("")

    return "\n".join(lines)

def main():
    """
    Orchestrates retrieval of repository pull-request context and writes an Active Development Context Markdown file.
    
    Writes a summary of open pull requests and their changed files to docs/ACTIVE_CONTEXT.md. If the GITHUB_TOKEN environment variable is missing, writes a placeholder indicating the context is unavailable. Ensures the docs directory exists, overwrites the target file, and emits simple status messages to stdout.
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set. Creating placeholder context.")
        with open("docs/ACTIVE_CONTEXT.md", "w") as f:
            f.write("# 🧠 Active Development Context\n\n*Github Token missing - Context unavailable*")
        return

    repo = get_repo_info()
    if not repo:
        print("Could not determine repository. Exiting.")
        return

    print(f"Fetching context for {repo}...")
    prs = fetch_open_prs(repo, token)
    md_content = generate_markdown(prs)

    os.makedirs("docs", exist_ok=True)
    with open("docs/ACTIVE_CONTEXT.md", "w") as f:
        f.write(md_content)
    print("Updated docs/ACTIVE_CONTEXT.md")

if __name__ == "__main__":
    main()
