#!/bin/zsh
set -euo pipefail

GITHUB_READ_TOKEN=$(/usr/bin/osascript <<'APPLESCRIPT'
set dialogResult to display dialog "粘贴 GitHub 只读 Token。内容会隐藏并直接保存到 macOS 钥匙串。" default answer "" with hidden answer buttons {"取消", "保存"} default button "保存" with title "robotic harness GitHub 授权"
return text returned of dialogResult
APPLESCRIPT
)

if [[ -z "$GITHUB_READ_TOKEN" ]]; then
  /usr/bin/osascript -e 'display alert "没有输入 Token，未保存。"'
  exit 1
fi

/usr/bin/security add-generic-password \
  -a "robotic-harness" \
  -s "robotic-harness-github-token" \
  -w "$GITHUB_READ_TOKEN" \
  -U >/dev/null

unset GITHUB_READ_TOKEN
/usr/bin/osascript -e 'display notification "GitHub Token 已安全保存，可以开始验证。" with title "robotic harness"'
echo "GitHub Token 已保存到 macOS 钥匙串。"
