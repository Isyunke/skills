#!/usr/bin/env bash
#
# resume-alchemist / truth verification hook
#
# Verifies that resume content is based on real experiences.
# Checks that skills mentioned in resume have supporting evidence in project files.
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

# For Write — check if content has unsupported claims
if [[ "$tool_name" == "Write" ]]; then
  content=$(echo "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")

  if [[ -z "$content" ]]; then
    exit 0
  fi

  # Check if "精通" appears without supporting projects
  if echo "$content" | grep -q "精通"; then
    # Check if there are project files in the same directory
    dir_path=$(dirname "$file_path")
    project_count=$(find "$dir_path/../../profile/projects" -name "*.md" 2>/dev/null | wc -l)

    if [[ "$project_count" -eq 0 ]]; then
      cat >&2 <<EOF

BLOCKED: Resume claims "精通" (expert) skills but no project files found.

To proceed:
  1. Add project files in profile/projects/
  2. Use /resume-mine to document your experiences
  3. Or use /resume-verify to verify existing projects via code tracing

Each "精通" skill must have supporting evidence in project files.

See: shared-references/core-principles.md (Truth First principle)
EOF
      exit 1
    fi
  fi
fi

exit 0
