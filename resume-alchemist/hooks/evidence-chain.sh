#!/usr/bin/env bash
#
# resume-alchemist / evidence chain hook
#
# Ensures that skills mentioned in resume have supporting evidence in project files.
# Checks for evidence chain: skill → project → quantified result
#
# Uses python for JSON parsing (no jq dependency).
#
# Exit codes:
#   0 = allow tool call to proceed
#   1 = block tool call

set -uo pipefail

# Read tool call payload from stdin
input=$(cat)
if [[ -z "$input" ]]; then
  exit 0
fi

# Extract tool name and file path using python (no jq dependency)
tool_name=$(echo "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")
file_path=$(echo "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only intercept Write and Edit
if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
  exit 0
fi

# Only intercept resume HTML files
case "$file_path" in
  */resumes/*/resume*.html)
    : # match — continue checking
    ;;
  *)
    exit 0
    ;;
esac

# For Write — check if content has proper evidence chain
if [[ "$tool_name" == "Write" ]]; then
  content=$(echo "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")

  if [[ -z "$content" ]]; then
    exit 0
  fi

  # Check for quantified results
  # Look for patterns like "提升XX%", "增长XX%", "节省XX"
  has_quantification=false
  if echo "$content" | grep -qE "(提升|增长|节省|优化|降低|提高|减少)[0-9]+%"; then
    has_quantification=true
  fi

  # Check for project references
  has_project_reference=false
  if echo "$content" | grep -qE "(项目|proj-|Project)"; then
    has_project_reference=true
  fi

  # If resume has skills but no quantification or project references, block
  if echo "$content" | grep -qE "(精通|熟练)" && [[ "$has_quantification" == false ]] && [[ "$has_project_reference" == false ]]; then
    cat >&2 <<EOF

BLOCKED: Resume mentions skills but lacks quantified results or project references.

To proceed:
  1. Add quantified results (e.g., "性能提升50%")
  2. Reference specific projects (e.g., "在XX项目中")
  3. Use STAR method: Situation, Task, Action, Result
  4. Use /resume-mine or /resume-verify to build evidence chain

Every skill claim must have: project reference + quantified result.

See: shared-references/core-principles.md (Evidence Chain principle)
EOF
    exit 1
  fi
fi

exit 0
