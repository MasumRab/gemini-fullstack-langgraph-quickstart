import logging
import re
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_remote_branches():
    """Get all remote branches excluding HEAD and main."""
    cmd = ["git", "branch", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"git branch -r failed: {result.stderr}")

    branches = []
    for line in result.stdout.splitlines():
        branch = line.strip()
        if (
            "->" in branch
            or branch == "origin/main"
            or branch == "upstream"
            or branch.startswith("upstream/")
        ):
            continue
        branches.append(branch)
    return branches


def get_diff_stats(branch, default_branch: str = "main"):
    """
    Get diff statistics for a branch compared to the default branch.

    Args:
        branch: The branch to analyze
        default_branch: The default branch to compare against (default: "main")

    Returns:
        Dict with keys: status, summary, changes
    """
    # Check if merged first
    cmd_merged = ["git", "rev-list", "--count", f"{default_branch}..{branch}"]
    res_merged = subprocess.run(cmd_merged, capture_output=True, text=True)

    if res_merged.returncode != 0:
        logger.error(
            f"Failed to check merge status for {branch}: command {cmd_merged} failed with stderr: {res_merged.stderr}"
        )
        exit(1)

    if res_merged.stdout.strip() == "0":
        return {"status": "MERGED", "summary": "", "changes": 0}

    # Get diff stats
    cmd = ["git", "diff", "--shortstat", f"{default_branch}..{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(
            f"Failed to get diff stats for {branch}: command {cmd} failed with stderr: {result.stderr}"
        )
        exit(1)

    output = result.stdout.strip()

    if not output:
        return {"status": "NO_DIFF", "summary": "", "changes": 0}

    # Parse "X files changed, Y insertions(+), Z deletions(-)"
    insertions = 0
    deletions = 0

    m_ins = re.search(r"(\d+)\s+insertions?", output)
    if m_ins:
        insertions = int(m_ins.group(1))

    m_del = re.search(r"(\d+)\s+deletions?", output)
    if m_del:
        deletions = int(m_del.group(1))

    return {"status": "DIFF", "summary": output, "changes": insertions + deletions}


def main():
    branches = get_remote_branches()
    plans = []

    print(f"Analyzing {len(branches)} remote branches...")

    for branch in branches:
        info = get_diff_stats(branch)
        stats = info.get("summary", "")
        total = info.get("changes", 0)
        status = info.get("status", "")

        if status == "MERGED":
            plans.append({"branch": branch, "action": "DELETE (Merged)", "size": 0})
        elif total < 50:
            plans.append(
                {
                    "branch": branch,
                    "action": "DELETE (Small Change)",
                    "size": total,
                    "details": stats,
                }
            )
        else:
            plans.append(
                {
                    "branch": branch,
                    "action": "KEEP (Large Change)",
                    "size": total,
                    "details": stats,
                }
            )

    # Sort by size
    plans.sort(key=lambda x: x["size"])

    with open("pruning_report.txt", "w", encoding="utf-8") as f:
        f.write("--- Pruning Plan ---\n")
        for p in plans:
            f.write(f"{p['branch']:<60} | {p['action']:<20} | Size: {p['size']}\n")

    print("Report saved to pruning_report.txt")


if __name__ == "__main__":
    main()
