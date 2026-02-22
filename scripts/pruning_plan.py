"""Script to analyze remote branches and suggest pruning actions."""

import subprocess
import re
import argparse

def get_remote_branches(base="main"):
    # Get all remote branches except HEAD and base
    cmd = ["git", "branch", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"git branch -r failed: {result.stderr.strip()}")

    branches = []
    for line in result.stdout.splitlines():
        branch = line.strip()
        if "->" in branch or f"origin/{base}" in branch or "upstream" in branch:
            continue
        branches.append(branch)
    return branches

def get_diff_stats(branch, base_branch="main"):
    # Check if merged first
    cmd_merged = ["git", "rev-list", "--count", f"{base_branch}..{branch}"]
    res_merged = subprocess.run(cmd_merged, capture_output=True, text=True)
    if res_merged.returncode == 0 and res_merged.stdout.strip() == "0":
        return "MERGED", 0
        
    # Get diff stats
    cmd = ["git", "diff", "--shortstat", f"{base_branch}...{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return "ERROR", 0

    output = result.stdout.strip()
    
    if not output:
        return "NO_DIFF", 0
        
    # Parse "X files changed, Y insertions(+), Z deletions(-)"
    insertions = 0
    deletions = 0
    
    m_ins = re.search(r'(\d+) insertion', output)
    if m_ins: insertions = int(m_ins.group(1))
    
    m_del = re.search(r'(\d+) deletion', output)
    if m_del: deletions = int(m_del.group(1))
    
    return output, insertions + deletions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main", help="Base branch to compare against")
    args = parser.parse_args()

    branches = get_remote_branches(base=args.base)
    plans = []
    
    print(f"Analyzing {len(branches)} remote branches against '{args.base}'...")
    
    for branch in branches:
        stats, total = get_diff_stats(branch, args.base)

        if stats == "MERGED":
            plans.append({"branch": branch, "action": "DELETE (Merged)", "size": 0})
        elif stats == "NO_DIFF":
            plans.append({"branch": branch, "action": "DELETE (No Diff)", "size": 0})
        elif stats == "ERROR":
            plans.append({"branch": branch, "action": "SKIP (Error)", "size": 0, "details": "Git command failed"})
        elif total < 50:
            plans.append({"branch": branch, "action": "DELETE (Small Change)", "size": total, "details": stats})
        else:
            plans.append({"branch": branch, "action": "KEEP (Large Change)", "size": total, "details": stats})
            
    # Sort by size
    plans.sort(key=lambda x: x['size'])
    
    with open("pruning_report.txt", "w", encoding="utf-8") as f:
        f.write("--- Pruning Plan ---\n")
        for p in plans:
            f.write(f"{p['branch']:<60} | {p['action']:<20} | Size: {p['size']}\n")
            
    print("Report saved to pruning_report.txt")

if __name__ == "__main__":
    main()
