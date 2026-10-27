#!/bin/zsh
set -euo pipefail

echo "请粘贴 GitHub 只读 Token。输入不会显示，按回车保存："
IFS= read -rs GITHUB_READ_TOKEN
echo

if [[ -z "$GITHUB_READ_TOKEN" ]]; then
  echo "没有输入 Token，未保存。"
  exit 1
fi

security add-generic-password \
  -a "robotic-harness" \
  -s "robotic-harness-github-token" \
  -w "$GITHUB_READ_TOKEN" \
  -U >/dev/null

unset GITHUB_READ_TOKEN
echo "已保存到 macOS 钥匙串。Token 不会写入项目文件。"
echo "保存后请回到 Codex 告诉我：完成。"
