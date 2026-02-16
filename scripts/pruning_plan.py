import subprocess
import re

def get_remote_branches():
    # Get all remote branches excluding HEAD and main
    cmd = ["git", "branch", "-r"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    branches = []
    for line in result.stdout.splitlines():
        branch = line.strip()
        if "->" in branch or "origin/main" in branch or "upstream" in branch:
            continue
        branches.append(branch)
    return branches

def get_diff_stats(branch):
    # Check if merged first
    cmd_merged = ["git", "rev-list", "--count", f"main..{branch}"]
    res_merged = subprocess.run(cmd_merged, capture_output=True, text=True)
    if res_merged.returncode == 0 and res_merged.stdout.strip() == "0":
        return "MERGED", 0
        
    # Get diff stats
    cmd = ["git", "diff", "--shortstat", f"main...{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
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
    branches = get_remote_branches()
    plans = []
    
    print(f"Analyzing {len(branches)} remote branches...")
    
    for branch in branches:
        stats, total = get_diff_stats(branch)
        if stats == "MERGED":
            plans.append({"branch": branch, "action": "DELETE (Merged)", "size": 0})
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
