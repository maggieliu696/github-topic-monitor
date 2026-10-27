#!/bin/zsh
set -eu

service_webhook="robotic-harness-feishu-webhook"
service_secret="robotic-harness-feishu-secret"

printf "请输入飞书自定义机器人的 Webhook 地址："
IFS= read -r webhook
printf "请输入签名密钥（输入内容不会显示）："
IFS= read -rs secret
printf "\n"

case "$webhook" in
  https://open.feishu.cn/open-apis/bot/v2/hook/*) ;;
  *) printf "Webhook 地址格式不正确。\n" >&2; exit 1 ;;
esac

if [ -z "$secret" ]; then
  printf "签名密钥不能为空。\n" >&2
  exit 1
fi

keychain_account="$(id -un)"
security add-generic-password -U -a "$keychain_account" -s "$service_webhook" -w "$webhook" >/dev/null
security add-generic-password -U -a "$keychain_account" -s "$service_secret" -w "$secret" >/dev/null
printf "已保存到 macOS 钥匙串。下一步运行：\n"
printf "python3 Microduck数据采集/feishu/send_digest.py --dry-run\n"
