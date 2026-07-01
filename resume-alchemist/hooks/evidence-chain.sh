#!/usr/bin/env bash
#
# resume-alchemist / evidence chain hook (v2 shim)
#
# Same architecture as truth-verification.sh: try the v2 Python validator
# on the ``evidence_chain`` principle, fall back to v1 grep if the v2 tools
# aren't installed.
#
# See truth-verification.sh for the full contract description.
set -uo pipefail

input="$(cat || true)"
[ -z "$input" ] && exit 0

_tool_name="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || echo "")"
_file_path="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")"

case "$_tool_name" in
  Write|Edit) : ;;
  *) exit 0 ;;
esac

case "$_file_path" in
  */resumes/*/resume*.html|*/resumes/*/resume*.yaml|*/profile/skills/data.yaml|*/profile/projects/*/data.yaml)
    : ;;  # match — proceed
  *)
    exit 0 ;;
esac

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

_locate_alchemist_root() {
  if [ -n "${RESUME_ALCHEMIST_ROOT:-}" ] && [ -d "$RESUME_ALCHEMIST_ROOT/tools/schemas" ]; then
    printf '%s' "$RESUME_ALCHEMIST_ROOT"
    return 0
  fi
  local candidate="$HOME/.claude/skills/resume-alchemist"
  if [ -d "$candidate/tools/schemas" ]; then
    printf '%s' "$candidate"
    return 0
  fi
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
      --principle evidence_chain 2>&1
    return $?
  fi
  ( cd "$root" && python -m tools.evidence_validator \
      --project-root "$PROJECT_DIR" \
      --principle evidence_chain 2>&1 )
  return $?
}

output=""
if output="$(_run_v2_validator)"; then
  exit 0
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    printf '%s\n' "$output" >&2
    cat >&2 <<'EOF'

BLOCKED by resume-alchemist evidence-chain hook.
Each skill claim must have: project reference + quantified result.
See shared-references/core-principles.md (Evidence Chain principle).
EOF
    exit 1
  fi
  # Fallback: v1 grep heuristic on resume Write payloads only
  if [ "$_tool_name" = "Write" ]; then
    content="$(printf '%s' "$input" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('content',''))" 2>/dev/null || echo "")"
    if [ -n "$content" ]; then
      has_quantification=false
      if printf '%s' "$content" | grep -qE "(提升|增长|节省|优化|降低|提高|减少)[0-9]+%"; then
        has_quantification=true
      fi
      has_project_reference=false
      if printf '%s' "$content" | grep -qE "(项目|proj-|Project)"; then
        has_project_reference=true
      fi
      if printf '%s' "$content" | grep -qE "(精通|熟练)" \
         && [ "$has_quantification" = false ] \
         && [ "$has_project_reference" = false ]; then
        cat >&2 <<'EOF'

BLOCKED (v1 fallback): Resume mentions skills but lacks quantified results or project references.

Upgrade to v2 for a richer explanation.
To proceed now:
  1. Add quantified results (e.g., "性能提升50%")
  2. Reference specific projects (e.g., "在XX项目中")
  3. Use STAR method: Situation, Task, Action, Result
EOF
        exit 1
      fi
    fi
  fi
  exit 0
fi
