#!/usr/bin/env bash
#
# Resume Alchemist - Uninstallation Script
#
# This script uninstalls the Resume Alchemist skill from Claude Code.
# Your project data (resumes, profiles, etc.) is NOT touched.
#
# Usage:
#   bash uninstall.sh

set -euo pipefail

# Sub-skills to uninstall
SUB_SKILLS=(
  resume-init
  resume-mine
  resume-import
  resume-profile
  resume-jd
  resume-build
  resume-optimize
  resume-interview
  resume-learn
  resume-export
  resume-status
  resume-blind
)

SKILLS_DIR="$HOME/.claude/skills"

echo ""
echo "🧪 卸载简历炼金术士 / Resume Alchemist"
echo ""

# Check if installed
if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "❌ Claude Code skills 目录不存在: $SKILLS_DIR"
  echo "   简历炼金术士可能未安装。"
  exit 1
fi

# Remove sub-skills
echo "移除子 Skill..."
echo ""

for skill in "${SUB_SKILLS[@]}"; do
  skill_dst="$SKILLS_DIR/$skill"

  if [[ -e "$skill_dst" ]]; then
    rm -rf "$skill_dst"
    echo "  ✅ 已移除: $skill"
  else
    echo "  ⚠️  未找到: $skill (跳过)"
  fi
done

echo ""

# Remove shared-references
SHARED_DIR="$SKILLS_DIR/resume-alchemist-shared"
if [[ -e "$SHARED_DIR" ]]; then
  rm -rf "$SHARED_DIR"
  echo "  ✅ 已移除: shared-references"
fi

# Remove templates
TEMPLATES_DIR="$SKILLS_DIR/resume-alchemist-templates"
if [[ -e "$TEMPLATES_DIR" ]]; then
  rm -rf "$TEMPLATES_DIR"
  echo "  ✅ 已移除: templates"
fi

# Remove tools
TOOLS_DIR="$SKILLS_DIR/resume-alchemist-tools"
if [[ -e "$TOOLS_DIR" ]]; then
  rm -rf "$TOOLS_DIR"
  echo "  ✅ 已移除: tools"
fi

echo ""
echo "=========================================="
echo "✅ 卸载完成！"
echo "=========================================="
echo ""
echo "注意："
echo "  - 你的项目数据（简历、技能树等）未被删除"
echo "  - 你的配置文件（.resume-state.json）未被删除"
echo "  - 如需完全清理，请手动删除项目目录"
echo ""
echo "重新安装："
echo "  bash install.sh"
echo ""
