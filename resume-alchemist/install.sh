#!/usr/bin/env bash
#
# Resume Alchemist - Installation Script
#
# This script installs the Resume Alchemist skill into Claude Code.
#
# Usage:
#   bash install.sh                    # Install for Claude Code (default)
#   bash install.sh --copy             # Copy mode (instead of symlink)
#   bash install.sh --reinstall-hooks <project-dir>
#                                      # Reinstall hook scripts in an existing project
#
# After install, in your project directory: open Claude Code → say "初始化简历炼金术士"

set -euo pipefail

# Sub-skills to install
SUB_SKILLS=(
  resume-init
  resume-mine
  resume-import
  resume-verify
  resume-profile
  resume-jd
  resume-build
  resume-optimize
  resume-localize
  resume-interview
  resume-learn
  resume-export
  resume-status
  resume-blind
)

# Resolve the directory containing THIS script
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

MODE="symlink"

# --- --reinstall-hooks branch ---
if [[ "${1:-}" == "--reinstall-hooks" ]]; then
  PROJECT_DIR="${2:-}"
  if [[ -z "$PROJECT_DIR" ]]; then
    echo "❌ Usage: bash install.sh --reinstall-hooks <path-to-user-project>"
    exit 1
  fi
  if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "❌ Project dir not found: $PROJECT_DIR"
    exit 1
  fi
  if [[ ! -f "$PROJECT_DIR/.resume-state.json" ]]; then
    echo "❌ $PROJECT_DIR is not a resume-alchemist project (no .resume-state.json)."
    echo "   Run /resume-init in that directory first."
    exit 1
  fi

  HOOK_DST="$PROJECT_DIR/.resume-hooks"
  mkdir -p "$HOOK_DST"

  echo ""
  echo "Reinstalling hook scripts in: $PROJECT_DIR"
  echo "  source: $SCRIPT_DIR/hooks/"
  echo ""

  for hook_script in truth-verification.sh evidence-chain.sh; do
    if [[ -f "$SCRIPT_DIR/hooks/$hook_script" ]]; then
      cp "$SCRIPT_DIR/hooks/$hook_script" "$HOOK_DST/$hook_script"
      chmod +x "$HOOK_DST/$hook_script"
      echo "  ✅ updated: .resume-hooks/$hook_script"
    else
      echo "  ⚠️  missing in source: hooks/$hook_script (skipped)"
    fi
  done

  echo ""
  echo "✅ Hook scripts reinstalled."
  echo ""
  exit 0
fi

# --- Parse arguments ---
for arg in "$@"; do
  case "$arg" in
    --copy)
      MODE="copy"
      ;;
  esac
done

# --- Main installation ---
echo ""
echo "🧪 安装简历炼金术士 / Resume Alchemist"
echo ""

# Check dependencies
echo "检查依赖..."

# Python (fallback from python3 to python for Windows)
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
  PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
  PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
  echo "⚠️  Python 3 未安装。部分功能（PDF 导出、简历解析）将不可用。"
  echo "   安装 Python 3: https://www.python.org/downloads/"
else
  echo "  ✅ Python: $($PYTHON_CMD --version)"
fi

# pip (fallback from pip3 to pip for Windows)
PIP_CMD=""
if command -v pip3 &> /dev/null; then
  PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
  PIP_CMD="pip"
fi

if [ -z "$PIP_CMD" ]; then
  echo "⚠️  pip 未安装。Python 依赖将无法安装。"
else
  echo "  ✅ pip: 可用"
fi

echo ""

# Install Python dependencies
if [ -n "$PIP_CMD" ]; then
  echo "安装 Python 依赖..."
  $PIP_CMD install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>/dev/null || true
  echo "  ✅ Python 依赖已安装"
fi

echo ""

# Install to Claude Code skills directory
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"

echo "安装子 Skill 到: $SKILLS_DIR"
echo ""

for skill in "${SUB_SKILLS[@]}"; do
  skill_src="$SCRIPT_DIR/skills/$skill"
  skill_dst="$SKILLS_DIR/$skill"

  if [[ ! -d "$skill_src" ]]; then
    echo "  ⚠️  $skill: 源目录不存在，跳过"
    continue
  fi

  # Remove existing
  if [[ -e "$skill_dst" ]]; then
    rm -rf "$skill_dst"
  fi

  # Install
  if [[ "$MODE" == "copy" ]]; then
    cp -r "$skill_src" "$skill_dst"
  else
    ln -sf "$skill_src" "$skill_dst"
  fi

  echo "  ✅ $skill"
done

echo ""

# Install shared-references
SHARED_DIR="$SKILLS_DIR/resume-alchemist-shared"
if [[ -e "$SHARED_DIR" ]]; then
  rm -rf "$SHARED_DIR"
fi

if [[ "$MODE" == "copy" ]]; then
  cp -r "$SCRIPT_DIR/shared-references" "$SHARED_DIR"
else
  ln -sf "$SCRIPT_DIR/shared-references" "$SHARED_DIR"
fi

echo "  ✅ shared-references"

# Install templates
TEMPLATES_DIR="$SKILLS_DIR/resume-alchemist-templates"
if [[ -e "$TEMPLATES_DIR" ]]; then
  rm -rf "$TEMPLATES_DIR"
fi

if [[ "$MODE" == "copy" ]]; then
  cp -r "$SCRIPT_DIR/templates" "$TEMPLATES_DIR"
else
  ln -sf "$SCRIPT_DIR/templates" "$TEMPLATES_DIR"
fi

echo "  ✅ templates"

# Install tools
TOOLS_DIR="$SKILLS_DIR/resume-alchemist-tools"
if [[ -e "$TOOLS_DIR" ]]; then
  rm -rf "$TOOLS_DIR"
fi

if [[ "$MODE" == "copy" ]]; then
  cp -r "$SCRIPT_DIR/tools" "$TOOLS_DIR"
else
  ln -sf "$SCRIPT_DIR/tools" "$TOOLS_DIR"
fi

echo "  ✅ tools"

# Install slash commands to ~/.claude/commands/
# Claude Code loads /commands from .claude/commands/*.md
COMMANDS_DIR="$HOME/.claude/commands"
mkdir -p "$COMMANDS_DIR"

echo ""
echo "安装 slash 命令到: $COMMANDS_DIR"
echo ""

for skill in "${SUB_SKILLS[@]}"; do
  skill_md="$SCRIPT_DIR/skills/$skill/SKILL.md"
  cmd_dst="$COMMANDS_DIR/$skill.md"

  if [[ ! -f "$skill_md" ]]; then
    continue
  fi

  # Copy SKILL.md content as command file
  cp "$skill_md" "$cmd_dst"
  echo "  ✅ /$skill"
done

echo ""
echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 在你的求职项目目录中打开 Claude Code"
echo "2. 说 '初始化简历炼金术士'"
echo "3. 按照提示完成初始化"
echo ""
echo "其他命令："
echo "  - '聊聊我的经历' → 深挖经历"
echo "  - '导入简历' → 从现有简历导入"
echo "  - '分析这个 JD' → 分析岗位要求"
echo "  - '状态' → 查看当前进度"
echo ""
echo "文档："
echo "  - README.md: 用户文档"
echo "  - docs/USER-GUIDE.md: 详细使用指南"
echo ""
