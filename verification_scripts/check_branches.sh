#!/bin/bash
# verification_scripts/check_branches.sh
# Checks specific files across available remote branches

# Ensure output directory exists
mkdir -p reports

OUTPUT_FILE="reports/branch_audit.txt"
echo "Branch Audit Report" > "$OUTPUT_FILE"
echo "===================" >> "$OUTPUT_FILE"
date >> "$OUTPUT_FILE"

# List of branches to check (excluding HEAD/main as we already checked current)
BRANCHES=$(git branch -r | grep -v "\->" | grep -v "origin/main" | awk '{print $1}')

# Files to hunt for
FILES=(
    "backend/src/agent/kg.py"
    "backend/src/config/app_config.py"
    "backend/src/search/providers/brave.py"
    "backend/src/agent/_graph.py"
)

echo "Scanning remote branches for missing files..." >> "$OUTPUT_FILE"

for branch in $BRANCHES; do
    echo "Checking $branch..." >> "$OUTPUT_FILE"

    # Check for specific files
    for file in "${FILES[@]}"; do
        if git ls-tree -r "$branch" --name-only | grep -q "$file"; then
            echo "  [FOUND] $file in $branch" >> "$OUTPUT_FILE"
        fi
    done

    # Check for ChromaStore in rag.py specifically
    if git show "$branch:backend/src/agent/rag.py" 2>/dev/null | grep -q "ChromaStore"; then
        echo "  [FOUND] 'ChromaStore' content in backend/src/agent/rag.py in $branch" >> "$OUTPUT_FILE"
    fi

    # Check for Unified Search (SearchRouter)
    if git show "$branch:backend/src/agent/nodes.py" 2>/dev/null | grep -q "SearchRouter"; then
        echo "  [FOUND] 'SearchRouter' in backend/src/agent/nodes.py in $branch" >> "$OUTPUT_FILE"
    fi
done

echo "Branch scan complete." >> "$OUTPUT_FILE"
