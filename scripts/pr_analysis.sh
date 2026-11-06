#!/bin/bash
set -euo pipefail

# =============================================================================
# PR Analysis Script - gemini-fullstack-langgraph-quickstart
# =============================================================================
# Automates fetching GitHub PR data via gh CLI and generating analysis markdown
# files with repair prompts for conflicting PRs.
#
# Dependencies: gh (GitHub CLI), jq (JSON processor)
#
# Usage:
#   ./scripts/pr_analysis.sh --repo MasumRab/gemini-fullstack-langgraph-quickstart --pr-set "275 283 287 289 ..."
# =============================================================================

REPO="MasumRab/gemini-fullstack-langgraph-quickstart"
PR_SET=""
OUTPUT_DIR="docs/pr_analysis/individual"

# Check dependencies
command -v gh >/dev/null 2>&1 || { echo "Error: gh CLI not found. Install: https://cli.github.com/"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "Error: jq not found. Install: https://jqlang.github.io/jq/download/"; exit 1; }

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)
            REPO="$2"
            shift 2
            ;;
        --pr-set)
            PR_SET="$2"
            shift 2
            ;;
        --all)
            shift
            # Fetch all open PR numbers
            PR_SET=$(gh pr list --repo "$REPO" --state open --json number | jq -r '.[].number' | tr '\n' ' ')
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 --repo <owner/repo> --pr-set 'PR1 PR2 ...' OR --all"
            exit 1
            ;;
    esac
done

if [[ -z "$PR_SET" ]]; then
    echo "Usage: $0 --repo <owner/repo> --pr-set 'PR1 PR2 ...' OR --all"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# -----------------------------------------------------------------------------
# Helper: fetch PR overview
# -----------------------------------------------------------------------------
fetch_pr_overview() {
    local pr_num="$1"
    gh pr view "$pr_num" --repo "$REPO" --json number,title,author,headRefName,baseRefName,mergeable,additions,deletions,changedFiles,url,body 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Helper: fetch PR file changes
# -----------------------------------------------------------------------------
fetch_pr_files() {
    local pr_num="$1"
    gh pr diff "$pr_num" --repo "$REPO" --stat 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Helper: fetch PR checks
# -----------------------------------------------------------------------------
fetch_pr_checks() {
    local pr_num="$1"
    gh pr checks "$pr_num" --repo "$REPO" --json bucket,name,state,description 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Helper: extract Jules session links from PR body and comments
# -----------------------------------------------------------------------------
extract_jules_links() {
    local pr_num="$1"
    local body_json
    body_json=$(gh pr view "$pr_num" --repo "$REPO" --json body,comments 2>/dev/null || true)
    # Use jq to robustly extract text content before grepping for URLs
    echo "$body_json" | jq -r '.body, (.comments[]?.body // empty)' 2>/dev/null | grep -oE 'https://jules\.google\.com/task/[a-zA-Z0-9]+' | sort -u || true
}

# -----------------------------------------------------------------------------
# Helper: extract Linear issue links
# -----------------------------------------------------------------------------
extract_linear_links() {
    local pr_num="$1"
    local body_json
    body_json=$(gh pr view "$pr_num" --repo "$REPO" --json body,comments 2>/dev/null || true)
    # Use jq to robustly extract text content before grepping for URLs
    echo "$body_json" | jq -r '.body, (.comments[]?.body // empty)' 2>/dev/null | grep -oE 'https://linear\.app/[^[:space:]]+' | sort -u || true
}

# -----------------------------------------------------------------------------
# Helper: generate repair prompt
# -----------------------------------------------------------------------------
generate_repair_prompt() {
    local pr_num="$1"
    local mergeable="$2"
    local has_jules="$3"
    local changed_files="$4"

    local prompt=""
    prompt="
## Repair Prompt

**Priority:** CRITICAL
**Issue:** Merge conflicts with base branch \`main\`
**Files Changed:** ${changed_files}

### Recovery Actions
\`\`\`bash
# 1. Fetch and rebase
git fetch origin && git rebase origin/main

# 2. Resolve merge conflict markers in affected files
# 3. Run lint and tests
cd backend && make lint && cd ../frontend && npm run lint

# 4. Push and verify CI passes
git push -f
\`\`\`"

    if [[ "$has_jules" == "yes" ]]; then
        prompt="${prompt}
### Jules Session
- Check associated Jules session for context."
    fi

    echo "$prompt"
}

# -----------------------------------------------------------------------------
# Helper: determine priority based on branch name
# -----------------------------------------------------------------------------
get_priority() {
    local branch="$1"
    if [[ "$branch" == sentinel/* ]] || [[ "$branch" == *security* ]]; then
        echo "🔴 CRITICAL"
    elif [[ "$branch" == bolt/* ]]; then
        echo "🟠 HIGH (Performance)"
    elif [[ "$branch" == antigravity/* ]] || [[ "$branch" == fix/* ]]; then
        echo "🟠 HIGH (Bugfix)"
    elif [[ "$branch" == *test* ]]; then
        echo "🟡 MEDIUM"
    else
        echo "🔵 LOW (Feature/Chore)"
    fi
}

# -----------------------------------------------------------------------------
# Helper: render PR markdown (used in main loop)
# -----------------------------------------------------------------------------
render_pr_markdown() {
    local pr="$1"
    local title="$2"
    local author="$3"
    local url="$4"
    local head_ref="$5"
    local base_ref="$6"
    local mergeable="$7"
    local additions="$8"
    local deletions="$9"
    local changed_files="${10}"
    local jules_escaped="${11}"
    local linear_escaped="${12}"
    local repair_prompt="${13}"

    cat > "$OUTPUT_DIR/PR_${pr}.md" <<EOF
# PR #${pr}: ${title}

## Overview
- **Repository**: ${REPO}
- **PR Number**: ${pr}
- **Title**: ${title}
- **Author**: ${author}
- **URL**: ${url}
- **Head Ref**: ${head_ref}
- **Base Ref**: ${base_ref}
- **Mergeable**: ${mergeable}
- **Additions**: ${additions}
- **Deletions**: ${deletions}
- **Changed Files**: ${changed_files}

## Jules Session Links
${jules_escaped}
## Linear Issues
${linear_escaped}
${repair_prompt}
EOF
    echo "  Wrote: $OUTPUT_DIR/PR_${pr}.md"
}

# -----------------------------------------------------------------------------
# Main processing loop
# -----------------------------------------------------------------------------
echo "Repo: $REPO"
echo "PR set: $PR_SET"
echo "Output directory: $OUTPUT_DIR"
echo ""

for pr in $PR_SET; do
    echo "Processing PR #$pr..."
    overview=$(fetch_pr_overview "$pr")
    if [[ -z "$overview" ]]; then
        echo "  Warning: Could not fetch PR #$pr overview" >&2
        continue
    fi

    # Use jq for robust JSON parsing with error logging
    title=$(echo "$overview" | jq -r '.title // empty' 2>/dev/null) || {
        echo "  Warning: failed to parse title for PR #$pr" >&2
        title=""
    }
    author=$(echo "$overview" | jq -r '.author.login // empty' 2>/dev/null) || {
        echo "  Warning: failed to parse author for PR #$pr" >&2
        author=""
    }
    head_ref=$(echo "$overview" | jq -r '.headRefName // empty' 2>/dev/null) || {
        echo "  Warning: failed to parse headRefName for PR #$pr" >&2
        head_ref=""
    }
    base_ref=$(echo "$overview" | jq -r '.baseRefName // empty' 2>/dev/null) || {
        echo "  Warning: failed to parse baseRefName for PR #$pr" >&2
        base_ref=""
    }
    mergeable=$(echo "$overview" | jq -r '.mergeable // empty' 2>/dev/null) || {
        echo "  Warning: failed to parse mergeable for PR #$pr" >&2
        mergeable=""
    }
    additions=$(echo "$overview" | jq -r '.additions // 0' 2>/dev/null) || {
        echo "  Warning: failed to parse additions for PR #$pr" >&2
        additions="0"
    }
    deletions=$(echo "$overview" | jq -r '.deletions // 0' 2>/dev/null) || {
        echo "  Warning: failed to parse deletions for PR #$pr" >&2
        deletions="0"
    }
    changed_files=$(echo "$overview" | jq -r '.changedFiles // 0' 2>/dev/null) || {
        echo "  Warning: failed to parse changedFiles for PR #$pr" >&2
        changed_files="0"
    }

    url="https://github.com/${REPO}/pull/${pr}"

    jules_links=$(extract_jules_links "$pr")
    linear_links=$(extract_linear_links "$pr")
    has_jules="no"
    [[ -n "$jules_links" ]] && has_jules="yes"

    repair_prompt=""
    if [[ "$mergeable" == "CONFLICTING" ]]; then
        repair_prompt=$(generate_repair_prompt "$pr" "$mergeable" "$has_jules" "$changed_files")
    fi

    # Format jules and linear links for markdown
    jules_md=""
    if [[ -n "$jules_links" ]]; then
        jules_md="Found Jules session links:\\n"
        while IFS= read -r link; do
            [[ -n "$link" ]] && jules_md="${jules_md}- ${link}\\n"
        done <<< "$jules_links"
    fi

    linear_md=""
    if [[ -n "$linear_links" ]]; then
        linear_md="Found Linear issue links:\\n"
        while IFS= read -r link; do
            [[ -n "$link" ]] && linear_md="${linear_md}- ${link}\\n"
        done <<< "$linear_links"
    fi

    # Escape for cat heredoc
    jules_escaped=$(echo -e "${jules_md:-No Jules session links found in PR body or comments.}" | sed 's/`/\\`/g')
    linear_escaped=$(echo -e "${linear_md:-No Linear issue links found.}" | sed 's/`/\\`/g')

    # Use the render_pr_markdown function instead of inline generation
    render_pr_markdown "$pr" "$title" "$author" "$url" "$head_ref" "$base_ref" "$mergeable" "$additions" "$deletions" "$changed_files" "$jules_escaped" "$linear_escaped" "$repair_prompt"
    echo ""
done

echo "All PRs processed."
