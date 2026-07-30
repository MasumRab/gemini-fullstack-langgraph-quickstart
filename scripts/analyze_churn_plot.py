import subprocess
import re
from datetime import datetime
import sys

def get_git_log(n=50):
    cmd = ['git', 'log', '--shortstat', '--date=iso', f'-n{n}', '--pretty=format:%h|%ad|%s']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.stdout

def parse_log(log_output):
    commits = []
    current_commit = {}
    
    lines = log_output.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if '|' in line and (line[0].isalnum() and len(line.split('|')[0]) >= 7): # Heuristic for header
            if current_commit:
                commits.append(current_commit)
            parts = line.split('|', 2)
            current_commit = {
                'hash': parts[0],
                'date': parts[1],
                'subject': parts[2] if len(parts) > 2 else '',
                'insertions': 0,
                'deletions': 0,
                'files_changed': 0
            }
        elif 'changed' in line:
            # Parse stats: " 2 files changed, 10 insertions(+), 5 deletions(-)"
            # Note: might be just "1 file changed, 1 deletion(-)"
            
            files_match = re.search(r'(\d+) file', line)
            if files_match:
                current_commit['files_changed'] = int(files_match.group(1))
                
            ins_match = re.search(r'(\d+) insertion', line)
            if ins_match:
                current_commit['insertions'] = int(ins_match.group(1))
                
            del_match = re.search(r'(\d+) deletion', line)
            if del_match:
                current_commit['deletions'] = int(del_match.group(1))
                
    if current_commit:
        commits.append(current_commit)
        
    return commits

def plot_churn(commits):
    if not commits:
        print("No commits found.")
        return

    # Ascending order for plot
    commits.reverse()
    
    max_change = 0
    for c in commits:
        total = c['insertions'] + c['deletions']
        if total > max_change:
            max_change = total
            
    if max_change == 0:
        max_change = 1
        
    scale = 50.0 / max_change
    
    print(f"\n{'Hash':<10} | {'Date':<20} | {'Churn':<50} | Subject")
    print("-" * 120)
    
    regression_keywords = ['fix', 'revert', 'resolve', 'bug']
    
    for c in commits:
        total = c['insertions'] + c['deletions']
        bar_len = int(total * scale)
        bar = '#' * bar_len
        if not bar and total > 0:
            bar = '.'
            
        # Highlight potential regressions/fixes
        subject = c['subject']
        prefix = "  "
        for kw in regression_keywords:
            if kw in subject.lower():
                prefix = "* "
                break
                
        print(f"{prefix}{c['hash']:<8} | {c['date'][:19]:<20} | {bar:<50} | {c['insertions']}+{c['deletions']}- : {subject[:40]}")

def analyze_regressions(commits):
    print("\n--- Regression Analysis ---")
    reverts = [c for c in commits if 'revert' in c['subject'].lower()]
    fixes = [c for c in commits if 'fix' in c['subject'].lower()]
    
    print(f"Total Commits Analyzed: {len(commits)}")
    print(f"Direct Reverts: {len(reverts)}")
    print(f"Fixes: {len(fixes)}")
    
    if reverts:
        print("\nPossible Regressions (Reverts):")
        for r in reverts:
            print(f"- {r['hash']}: {r['subject']}")
            
    if fixes:
        print("\nRecent Fixes (Potential instability spots):")
        for f in fixes[:5]: # Show last 5
            print(f"- {f['hash']}: {f['subject']}")

if __name__ == "__main__":
    log_data = get_git_log(50)
    parsed_commits = parse_log(log_data)
    plot_churn(parsed_commits)
    analyze_regressions(parsed_commits)
