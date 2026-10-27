#!/usr/bin/env python3
"""Render an approved Markdown digest as a signed Feishu bot card and send it once."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIGEST = ROOT / "Microduck数据采集/pilot/output/日报.md"
STATE_DIR = Path(__file__).resolve().parent / "state"
LAST_SENT = STATE_DIR / "最后发送.json"
SEND_LOG = STATE_DIR / "发送记录.jsonl"
PREVIEW = STATE_DIR / "卡片预览.json"
CREDENTIAL_FILE = STATE_DIR / "credentials.json"
KEYCHAIN_WEBHOOK = "robotic-harness-feishu-webhook"
KEYCHAIN_SECRET = "robotic-harness-feishu-secret"
KEYCHAIN_HELPER = Path(__file__).resolve().parent / "feishu_keychain_helper"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(text)
        temp = f.name
    os.replace(temp, path)


def keychain_value(service: str) -> str | None:
    command = [str(KEYCHAIN_HELPER), "get", service] if KEYCHAIN_HELPER.exists() else [
        "security", "find-generic-password", "-a", getpass.getuser(), "-s", service, "-w"
    ]
    try:
        return subprocess.run(
            command,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def credential_file_value(key: str) -> str | None:
    if not CREDENTIAL_FILE.exists():
        return None
    if CREDENTIAL_FILE.stat().st_mode & 0o077:
        raise PermissionError(f"凭证文件权限过宽：{CREDENTIAL_FILE}，应为 600")
    values = json.loads(CREDENTIAL_FILE.read_text(encoding="utf-8"))
    return values.get(key)


def credential(env_name: str, service: str, file_key: str) -> str | None:
    return os.environ.get(env_name) or credential_file_value(file_key) or keychain_value(service)


def split_title(markdown: str) -> tuple[str, str]:
    lines = markdown.strip().splitlines()
    if lines and lines[0].startswith("# "):
        return lines[0][2:].strip(), "\n".join(lines[1:]).strip()
    return "robotic harness 调研日报", markdown.strip()


def public_markdown(markdown: str) -> str:
    """Remove local-only Markdown links while preserving their labels."""
    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2).strip("<>")
        parsed = urllib.parse.urlparse(target)
        return match.group(0) if parsed.scheme in {"http", "https"} else label
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, markdown)


def compact_feishu_spacing(markdown: str) -> str:
    """Remove blank rows immediately before list items; Feishu renders them too tall."""
    compacted = re.sub(r"\n[ \t]*\n+(?=[*-] )", "\n", markdown)
    return re.sub(r"(?m)^\* (?=\*\*)", "- ", compacted)


def card_payload(markdown: str) -> dict:
    title, body = split_title(compact_feishu_spacing(public_markdown(markdown)))
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": title}},
            "elements": [
                {"tag": "markdown", "content": body},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": "robotic harness 调研项目 · GitHub 公开资料"}]},
            ],
        },
    }


def signature(timestamp: str, secret: str) -> str:
    key = f"{timestamp}\n{secret}".encode()
    return base64.b64encode(hmac.new(key, b"", hashlib.sha256).digest()).decode()


def digest_id(markdown: str) -> str:
    return hashlib.sha256(markdown.encode()).hexdigest()


def validate_webhook(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "open.feishu.cn":
        raise ValueError("Webhook 必须使用 https://open.feishu.cn")
    if not parsed.path.startswith("/open-apis/bot/v2/hook/"):
        raise ValueError("Webhook 路径不是飞书自定义机器人地址")


def append_log(record: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with SEND_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def send(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "robotic-harness-research/1.0"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"飞书返回 HTTP {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest", type=Path, default=DEFAULT_DIGEST)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    markdown = args.digest.read_text(encoding="utf-8")
    content_id = digest_id(markdown)
    payload = card_payload(markdown)
    atomic_write(PREVIEW, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if args.dry_run:
        print(json.dumps({"status": "previewed", "digest_sha256": content_id, "preview": str(PREVIEW)}, ensure_ascii=False))
        return 0

    if LAST_SENT.exists() and not args.force:
        prior = json.loads(LAST_SENT.read_text(encoding="utf-8"))
        if prior.get("digest_sha256") == content_id:
            print(json.dumps({"status": "skipped_duplicate", "digest_sha256": content_id}, ensure_ascii=False))
            return 0

    webhook = credential("FEISHU_BOT_WEBHOOK", KEYCHAIN_WEBHOOK, "webhook")
    secret = credential("FEISHU_BOT_SECRET", KEYCHAIN_SECRET, "secret")
    if not webhook or not secret:
        raise SystemExit("尚未配置飞书机器人凭证。请先运行 configure_macos_keychain.sh。")
    validate_webhook(webhook)
    timestamp = str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
    payload["timestamp"] = timestamp
    payload["sign"] = signature(timestamp, secret)
    sent_at = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")
    try:
        response = send(webhook, payload)
        if response.get("code", response.get("StatusCode", 0)) != 0:
            raise RuntimeError("飞书拒绝消息：" + json.dumps(response, ensure_ascii=False))
        record = {"status": "sent", "sent_at": sent_at, "digest_sha256": content_id, "response": response}
        append_log(record)
        atomic_write(LAST_SENT, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(record, ensure_ascii=False))
        return 0
    except Exception as exc:
        append_log({"status": "failed", "attempted_at": sent_at, "digest_sha256": content_id, "error": str(exc)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
