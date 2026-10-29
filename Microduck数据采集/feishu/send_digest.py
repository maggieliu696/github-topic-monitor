#!/usr/bin/env python3
"""Render an approved Markdown digest as a signed Feishu bot card and send it once."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import datetime as dt
import hashlib
import hmac
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sqlite3
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
CARD_LAYOUT = Path(__file__).resolve().parent / "card_layout.json"
BEIJING = dt.timezone(dt.timedelta(hours=8))
SECTIONS = ('自己组装', '开发工具', '教鸭子做动作', '应用玩法')


@contextmanager
def research_lock(database: Path):
    """Do not approve or send while collection/project decisions are being written."""
    if not database.parent.exists():raise ValueError('尚无采集数据库目录')
    with (database.parent/'collector.lock').open('a') as handle:
        try:
            import fcntl
        except ImportError:
            import msvcrt
            handle.write('0');handle.flush();handle.seek(0)
            try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:raise ValueError('研究任务仍在运行，暂不确认或发送日报') from exc
            try:yield
            finally:
                handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:raise ValueError('研究任务仍在运行，暂不确认或发送日报') from exc
            try:yield
            finally:fcntl.flock(handle,fcntl.LOCK_UN)


def readiness_path(digest: Path) -> Path:
    return digest.with_suffix('.ready.json')


def validate_digest_format(markdown: str, today: dt.date) -> None:
    lines = compact_feishu_spacing(markdown).strip().splitlines()
    title = lines[0] if lines else ''
    match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日|(\d{4})-(\d{2})-(\d{2})', title)
    if not match:
        raise ValueError('日报标题没有日期')
    values = match.groups()[:3] if match.group(1) else match.groups()[3:]
    if dt.date(*map(int, values)) != today:
        raise ValueError('日报标题不是北京时间当天，拒绝发送')
    headings = []
    for i, line in enumerate(lines):
        for section in SECTIONS:
            if re.match(r'^(?:#{1,3}\s+|\*\*)'+re.escape(section)+r'[：:]', line):
                headings.append((i, section))
    if [name for _, name in headings] != list(SECTIONS):
        raise ValueError('日报必须按顺序保留四个板块')
    if not any(line.strip() for line in lines[1:headings[0][0]]):
        raise ValueError('日报缺少开头主线')
    for n, (begin, name) in enumerate(headings):
        end = headings[n+1][0] if n+1 < len(headings) else len(lines)
        bullets = sum(bool(re.match(r'^[-*] ', line)) for line in lines[begin+1:end])
        if not 1 <= bullets <= 3:
            raise ValueError(name+'板块应有 1–3 条；无重要变化时写一条说明')


def candidate_progress(database: Path) -> dict:
    if not database.exists():
        raise ValueError('没有采集数据库，不能确认初始化已完成')
    db = sqlite3.connect('file:'+str(database.resolve())+'?mode=ro', uri=True)
    try:
        pending = db.execute("SELECT count(*) FROM project_reviews WHERE status='pending'").fetchone()[0]
        revision = db.execute('SELECT coalesce(max(id),0) FROM project_review_log').fetchone()[0]
        if pending:
            raise ValueError(f'还有 {pending} 个候选未处理，不能将本轮标记为完成')
        tiers=database.parent.parent/'monitoring-tiers.json'
        tier_hash=None
        if tiers.exists():
            projects=json.loads(tiers.read_text()).get('projects',[])
            uninitialized=sum(x.get('initialization_status')=='pending' or x.get('tier') not in {'A','B'} for x in projects)
            if uninitialized:raise ValueError(f'还有 {uninitialized} 个已知项目未完成初始化或分级')
            tier_hash=hashlib.sha256(tiers.read_bytes()).hexdigest()
        return {'pending':pending, 'review_revision':revision, 'tier_sha256':tier_hash}
    except sqlite3.OperationalError as exc:
        raise ValueError('候选处理台账尚未建立，请先运行新版采集器') from exc
    finally:
        db.close()


def run_evidence(run_dir: Path, digest: Path, today: dt.date) -> dict:
    summary_path = run_dir/'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    if summary.get('workflow_version') != 2:
        raise ValueError('旧版采集批次没有初始化完成校验，必须先运行新版采集器')
    start = dt.datetime.fromisoformat(summary['started'])
    finish = dt.datetime.fromisoformat(summary['finished'])
    if start.astimezone(BEIJING).date() != today or finish.astimezone(BEIJING).date() != today:
        raise ValueError('采集批次不是今天')
    if digest.stat().st_mtime < finish.timestamp():
        raise ValueError('日报早于采集完成时间，可能是旧稿')
    coverage = summary.get('coverage', {}).get('github', {})
    if summary.get('errors') or not coverage.get('planned_repositories') or coverage.get('completed_repositories') != coverage.get('planned_repositories'):
        raise ValueError('本轮存在采集失败或未完成检查，不能标记成稿')
    if summary.get('run') != run_dir.name:
        raise ValueError('采集批次与目录不一致')
    return {'run':summary['run'], 'summary_sha256':hashlib.sha256(summary_path.read_bytes()).hexdigest()}


def approve_digest(digest: Path, run_dir: Path, database: Path, today=None, latest_path=None) -> dict:
    today = today or dt.datetime.now(BEIJING).date()
    markdown = digest.read_text(encoding='utf-8')
    validate_digest_format(markdown, today)
    if latest_path:
        latest = json.loads(latest_path.read_text())
        if Path(latest['directory']).resolve() != run_dir.resolve():
            raise ValueError('只允许批准最新采集批次的日报')
    evidence = run_evidence(run_dir, digest, today)
    progress = candidate_progress(database)
    proof = dict(evidence, **progress, date=today.isoformat(),status='ready',
                 digest_sha256=digest_id(markdown),approved_at=dt.datetime.now(BEIJING).isoformat())
    atomic_write(readiness_path(digest),json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    return proof


def validate_ready(digest: Path, database: Path, latest_path: Path, today=None) -> dict:
    today = today or dt.datetime.now(BEIJING).date()
    proof_path = readiness_path(digest)
    if not proof_path.exists():
        raise ValueError('没有当日成稿凭证，请完成研究并执行 --approve --run 后再发送')
    proof = json.loads(proof_path.read_text(encoding='utf-8'))
    if proof.get('status') != 'ready' or proof.get('date') != today.isoformat():
        raise ValueError('成稿凭证不是今天的有效凭证')
    markdown = digest.read_text(encoding='utf-8')
    validate_digest_format(markdown,today)
    if proof.get('digest_sha256') != digest_id(markdown):
        raise ValueError('日报在检查后被修改，必须重新确认成稿')
    latest = json.loads(latest_path.read_text())
    run_dir = Path(latest['directory'])
    evidence = run_evidence(run_dir,digest,today)
    if any(proof.get(k) != v for k,v in evidence.items()):
        raise ValueError('采集结果已经改变，旧成稿凭证失效')
    if candidate_progress(database) != {k:proof.get(k) for k in ('pending','review_revision','tier_sha256')}:
        raise ValueError('项目处理记录已经改变，必须重新确认成稿')
    return proof


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
    layout = json.loads(CARD_LAYOUT.read_text(encoding="utf-8")) if CARD_LAYOUT.exists() else {}
    elements = [{"tag": "markdown", "content": body}]
    if layout.get("collapse_body", True):
        # Keep the introduction visible; preserve all four sections and their links inside.
        heading = re.search(r"(?m)^(?:#{1,3}\s+|\*\*)自己组装[：:]", body)
        intro = body[:heading.start()].strip() if heading else ""
        details = body[heading.start():].strip() if heading else body
        elements = []
        if intro:
            elements.append({"tag": "markdown", "content": intro})
        elements.append({
            "tag": "collapsible_panel",
            "expanded": False,
            "header": {
                "title": {"tag": "plain_text", "content": layout.get("panel_title", "展开阅读完整日报")},
                "icon": {"tag": "standard_icon", "token": "down-small-ccm_outlined", "size": "16px 16px"},
                "icon_position": "right",
                "icon_expanded_angle": -180,
            },
            "elements": [{"tag": "markdown", "content": details}],
        })
    elements.extend([
        {"tag": "hr"},
        {"tag": "note", "elements": [{"tag": "plain_text", "content": "robotic harness 调研项目 · GitHub / Hugging Face 公开资料"}]},
    ])
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": layout.get("card_title", title)}},
            "elements": elements,
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
    parser.add_argument('--approve',action='store_true',help='检查已完成的研究并生成成稿凭证，不发送')
    parser.add_argument('--run',type=Path,help='--approve 对应的最新采集运行目录')
    parser.add_argument('--check',action='store_true',help='只检查成稿凭证，不发送')
    args = parser.parse_args()

    database=ROOT/'Microduck数据采集/data/research.sqlite3'
    latest=ROOT/'Microduck数据采集/最新运行.json'
    if args.dry_run:return execute(args,database,latest)
    with research_lock(database):
        return execute(args,database,latest)


def execute(args, database, latest):
    if args.approve:
        if not args.run:raise ValueError('--approve 必须同时指定 --run')
        print(json.dumps(approve_digest(args.digest,args.run,database,latest_path=latest),ensure_ascii=False))
        return 0
    if args.check:
        print(json.dumps(validate_ready(args.digest,database,latest),ensure_ascii=False))
        return 0

    markdown = args.digest.read_text(encoding="utf-8")
    content_id = digest_id(markdown)
    payload = card_payload(markdown)
    if args.dry_run:
        atomic_write(PREVIEW, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": "previewed", "digest_sha256": content_id, "preview": str(PREVIEW)}, ensure_ascii=False))
        return 0

    try:
        validate_ready(args.digest,database,latest)
    except Exception as exc:
        append_log({'status':'blocked','phase':'readiness','attempted_at':dt.datetime.now(BEIJING).isoformat(timespec='seconds'),'error':str(exc)})
        raise

    if LAST_SENT.exists() and not args.force:
        prior = json.loads(LAST_SENT.read_text(encoding="utf-8"))
        if prior.get("digest_sha256") == content_id:
            print(json.dumps({"status": "skipped_duplicate", "digest_sha256": content_id}, ensure_ascii=False))
            return 0
        if prior.get('sent_at','')[:10] == dt.datetime.now(BEIJING).date().isoformat():
            print(json.dumps({'status':'skipped_already_sent_today'},ensure_ascii=False))
            return 0

    delivery_file = STATE_DIR / "delivery.json"
    if delivery_file.exists():
        if delivery_file.stat().st_mode & 0o077:
            raise PermissionError("推送目标配置权限应为600")
        delivery = json.loads(delivery_file.read_text(encoding="utf-8"))
        webhook = delivery["webhook"]
        if delivery.get("auth_mode") != "none":
            raise ValueError("推送目标认证配置不受支持，停止发送")
        secret = None  # 正式群已验证无需签名，不沿用旧测试机器人密钥。
    else:
        webhook = credential("FEISHU_BOT_WEBHOOK", KEYCHAIN_WEBHOOK, "webhook")
        secret = credential("FEISHU_BOT_SECRET", KEYCHAIN_SECRET, "secret")
        if not webhook or not secret:
            raise SystemExit("尚未配置飞书机器人凭证。请先运行 configure_macos_keychain.sh。")
    validate_webhook(webhook)
    if secret:
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
