import os
import sys
import json
import requests
import subprocess
from datetime import datetime, timezone

def get_repo_info():
    """Attempt to get repository 'owner/repo' string."""
    # 1. From Environment
    repo = os.getenv("GITHUB_REPOSITORY")
    if repo:
        return repo

    # 2. From git config using subprocess
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True
        )
        remote_url = result.stdout.strip()

        if remote_url:
            # Handle ssh: git@github.com:Owner/Repo.git
            if "git@github.com:" in remote_url:
                repo = remote_url.split("git@github.com:")[1]
            # Handle https: https://github.com/Owner/Repo.git
            elif "github.com/" in remote_url:
                repo = remote_url.split("github.com/")[1]

            if repo and repo.endswith(".git"):
                repo = repo[:-4]
            return repo
    except Exception as e:
        print(f"Error getting repo info: {e}")
        pass
    return None

def fetch_open_prs(repo, token):
    """Fetch open PRs and their changed files with pagination."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    api_url = "https://api.github.com"

    # Get list of open PRs with pagination
    prs = []
    # Add per_page=100 to get more results per request
    next_url = f"{api_url}/repos/{repo}/pulls?state=open&per_page=100"

    while next_url:
        try:
            resp = requests.get(next_url, headers=headers, timeout=10)
            resp.raise_for_status()

            page_prs = resp.json()
            if not page_prs:
                break

            prs.extend(page_prs)

            # Check for next page in Link header
            if 'Link' in resp.headers:
                links = resp.headers['Link'].split(', ')
                next_url = None
                for link in links:
                    if 'rel="next"' in link:
                        next_url = link[link.find("<")+1:link.find(">")]
                        break
            else:
                next_url = None

        except requests.exceptions.RequestException as e:
            print(f"Request failed while fetching PRs: {e}")
            break

    results = []
    print(f"Found {len(prs)} open PRs.")

    for pr in prs:
        pr_number = pr["number"]
        # Get files for this PR
        files_url = f"{api_url}/repos/{repo}/pulls/{pr_number}/files"
        files = []
        try:
            f_resp = requests.get(files_url, headers=headers, timeout=10)
            f_resp.raise_for_status()
            files = [f["filename"] for f in f_resp.json()]
        except requests.exceptions.RequestException as e:
            print(f"Request failed while fetching files for PR #{pr_number}: {e}")
            # Continue with empty files list for this PR rather than failing completely

        results.append({
            "number": pr_number,
            "title": pr["title"],
            "user": pr["user"]["login"],
            "url": pr["html_url"],
            "files": files
        })

    return results

def generate_markdown(prs):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
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
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set. Creating placeholder context.")
        os.makedirs("docs", exist_ok=True)
        with open("docs/ACTIVE_CONTEXT.md", "w") as f:
            f.write("# 🧠 Active Development Context\n\n*Github Token missing - Context unavailable*")
        return

    repo = get_repo_info()
    if not repo:
        print("Could not determine repository. Creating placeholder context and exiting.")
        os.makedirs("docs", exist_ok=True)
        with open("docs/ACTIVE_CONTEXT.md", "w") as f:
            f.write("# 🧠 Active Development Context\n\n*Repository detection failed - Context unavailable*")
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
