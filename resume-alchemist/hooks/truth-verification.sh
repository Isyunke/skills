#!/usr/bin/env bash
#
# resume-alchemist / truth verification hook (v2 shim)
#
# In v2 the real validation logic lives in tools/evidence_validator.py.
# This hook is a thin bash shim that:
#   * exits 0 (allow) unless the tool call touches a resume file
#   * when it does, tries the v2 Python validator first
#   * falls back to the v1 grep heuristic if the validator isn't reachable
#
# Environment
#   CLAUDE_PROJECT_DIR    (set by Claude Code) — the user's resume project dir
#   RESUME_ALCHEMIST_ROOT (optional) — path to the resume-alchemist repo /
#                          installed skill dir (must contain `tools/` package).
#                          If unset, we try common install locations.
#
# Exit codes
#   0 = allow tool call
#   1 = block tool call
set -uo pipefail

# ---------------------------------------------------------------------------
# Read stdin (tool call payload)
# ---------------------------------------------------------------------------
input="$(cat || true)"
[ -z "$input" ] && exit 0

# ---------------------------------------------------------------------------
# Extract tool_name + file_path (using python, no jq dependency)
# ---------------------------------------------------------------------------
_tool_name="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")"
_file_path="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")"

case "$_tool_name" in
  Write|Edit) : ;;
  *) exit 0 ;;
esac

case "$_file_path" in
  */resumes/*/resume*.html|*/resumes/*/resume*.yaml)
    : ;;  # match — proceed
  *)
    exit 0 ;;
esac

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

# ---------------------------------------------------------------------------
# Locate the resume-alchemist tools package
# ---------------------------------------------------------------------------
_locate_alchemist_root() {
  # 1) explicit env override
  if [ -n "${RESUME_ALCHEMIST_ROOT:-}" ] && [ -d "$RESUME_ALCHEMIST_ROOT/tools/schemas" ]; then
    printf '%s' "$RESUME_ALCHEMIST_ROOT"
    return 0
  fi
  # 2) common install location: ~/.claude/skills/resume-alchemist
  local candidate="$HOME/.claude/skills/resume-alchemist"
  if [ -d "$candidate/tools/schemas" ]; then
    printf '%s' "$candidate"
    return 0
  fi
  # 3) pip-installed package
  if python -c "import resume_alchemist" 2>/dev/null; then
    printf '%s' "__pip__"
    return 0
  fi
  return 1
}

_run_v2_validator() {
  local root
  if ! root="$(_locate_alchemist_root)"; then
    return 127
  fi
  if [ "$root" = "__pip__" ]; then
    python -m resume_alchemist.tools.evidence_validator \
      --project-root "$PROJECT_DIR" \
      --principle truth_first 2>&1
    return $?
  fi
  ( cd "$root" && python -m tools.evidence_validator \
      --project-root "$PROJECT_DIR" \
      --principle truth_first 2>&1 )
  return $?
}

# ---------------------------------------------------------------------------
# Try v2 validator; fall back to v1 grep if it can't be located
# ---------------------------------------------------------------------------
output=""
if output="$(_run_v2_validator)"; then
  # exit 0 or 2 (warnings only) - treat both as allow
  exit 0
else
  rc=$?
  # rc == 127 means we could not locate the validator - degrade to v1
  # rc == 1 means real violation - block
  if [ "$rc" -eq 1 ]; then
    printf '%s\n' "$output" >&2
    cat >&2 <<EOF

BLOCKED by resume-alchemist truth-verification hook.
See docs/v2/07-ux-improvements.md section 4 for the What/Why/How template used above.
EOF
    exit 1
  fi
  # Fallback: v1 heuristic
  if [ "$_tool_name" = "Write" ]; then
    content="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")"
    if [ -n "$content" ] && printf '%s' "$content" | grep -q "精通"; then
      dir_path="$(dirname "$_file_path")"
      project_count="$(find "$dir_path/../../profile/projects" -name "*.md" 2>/dev/null | wc -l || echo 0)"
      if [ "$project_count" -eq 0 ]; then
        cat >&2 <<'EOF'

BLOCKED (v1 fallback): Resume claims "精通" (expert) skills but no project files found.

Upgrade to v2 for a richer explanation (docs/v2/07-ux-improvements.md).
To proceed now:
  1. Add project files in profile/projects/
  2. Or use /resume-mine to document your experiences
EOF
        exit 1
      fi
    fi
  fi
  exit 0
fi
