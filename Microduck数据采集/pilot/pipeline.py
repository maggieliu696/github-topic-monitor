#!/usr/bin/env python3
"""Offline, evidence-linked local pilot. No network, scheduling or external publishing."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECTS = ('P141', 'P160', 'P177')
PROJECT_RECORDS = {'P141': 'Microduck Academy', 'P160': 'Duck on Desk', 'P177': 'microduck-replica'}
DIRECTIONS = {'D01': '动作训练与算法实验', 'D02': '开发工具与运行环境', 'D03': 'AI应用与交互玩法', 'D04': '硬件复刻与适配'}
KINDS = {'author_claim': '作者陈述', 'user_report': '用户反馈', 'research_inference': '研究判断', 'unknown': '未知'}
SOURCE_KEYS = ('record_id', 'platform', 'record_type', 'title', 'source_url', 'author_handle', 'published_at', 'updated_at', 'source_status', 'thread_status', 'project_id', 'direction_id', 'project_url', 'thread_url', 'parent_reference', 'parent_context', 'context_complete', 'text')


def packed(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(v):
    return hashlib.sha256(v if isinstance(v, bytes) else packed(v)).hexdigest()


def load(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text)
        tmp = f.name
    os.replace(tmp, path)


def immutable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'归档校验失败，拒绝覆盖：{path}')
        return
    with path.open('xb') as f:
        f.write(data)
    path.chmod(0o444)


def source_hash(r):
    return digest({k: r.get(k) for k in SOURCE_KEYS})


def snapshot_digest(records):
    return digest({r['record_id']: source_hash(r) for r in sorted(records, key=lambda x: x['record_id'])})


def validate(a, records, pid):
    errors = []
    if a.get('project_id') != pid:
        errors.append('项目编号不匹配')
    for key in ('project_name', 'author_name', 'direction_id', 'direction_name', 'purpose', 'current_conclusion', 'discovered_problems', 'reviewed_on', 'sections', 'conclusions', 'daily_candidates', 'coverage'):
        if key not in a:
            errors.append(f'缺少字段：{key}')
    if a.get('direction_id') not in DIRECTIONS:
        errors.append('未知研究方向')
    owned = {r['record_id'] for r in records if r.get('project_id') == pid}
    directions = {r.get('direction_id') for r in records if r.get('project_id') == pid and r.get('direction_id')}
    if directions and directions != {a.get('direction_id')}:
        errors.append('审阅方向与现有项目编码不一致，需先明确分类调整依据')
    items = [i for s in a.get('sections', []) for i in s.get('items', [])]
    cs, ds = a.get('conclusions', []), a.get('daily_candidates', [])
    for group in (items, cs, ds):
        ids = [i.get('id') for i in group]
        if None in ids or len(ids) != len(set(ids)):
            errors.append('条目编号缺失或重复')
        for i in group:
            refs = i.get('evidence_ids', [])
            if not refs and i.get('evidence_kind') != 'unknown' and i.get('status') != 'unknown':
                errors.append(f"{i.get('id')} 缺少证据；未知项必须显式标注 unknown")
            if any(rid not in owned for rid in refs):
                errors.append(f"{i.get('id')} 引用了不存在或不属于本项目的证据")
    for i in items:
        if i.get('evidence_kind') not in KINDS:
            errors.append(f"{i.get('id')} evidence_kind 不合法")
    cids = {c.get('id') for c in cs}
    for i in ds:
        if not isinstance(i.get('human_review'), bool):
            errors.append(f"{i.get('id')} human_review 必须为布尔值")
        if any(c not in cids for c in i.get('conclusion_ids', [])):
            errors.append(f"{i.get('id')} 引用了不存在的结论")
    reviewed = set(a.get('coverage', {}).get('reviewed_record_ids', []))
    if not reviewed <= owned:
        errors.append('已阅读清单含不存在或跨项目的记录')
    used = {rid for i in items + cs + ds for rid in i.get('evidence_ids', [])}
    if not used <= reviewed:
        errors.append('部分引用证据未登记为已阅读')
    return errors


def time_flags(records, now):
    flags = []
    for r in records:
        for field in ('published_at', 'updated_at'):
            raw = r.get(field)
            if not raw:
                continue
            try:
                t = datetime.fromisoformat(raw.replace('Z', '+00:00'))
                if t.tzinfo is None:
                    raise ValueError('无时区')
                if t > now:
                    flags.append({'record_id': r['record_id'], 'field': field, 'value': raw, 'reason': '来源时间晚于处理时间，不据此判断市场新增'})
            except (ValueError, TypeError):
                flags.append({'record_id': r['record_id'], 'field': field, 'value': raw, 'reason': '来源时间无法可靠解析，保留原值待核验'})
    return flags


def display_time(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return value + '（时区未知）'
        return dt.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S 北京时间')
    except (ValueError, TypeError):
        return value


def source_times(records):
    ts = [r.get('last_checked_at') or r.get('first_captured_at') for r in records.values()]
    ts = sorted(x for x in ts if x)
    return f'{display_time(ts[0])} 至 {display_time(ts[-1])}' if ts else '未知'


def conclusion_diff(accepted, annotation, new_manifest):
    old = {c['id']: c for c in accepted['annotation']['conclusions']} if accepted else {}
    new = {c['id']: c for c in annotation['conclusions']}
    old_manifest = accepted['evidence_manifest'] if accepted else {}
    result = []
    for cid in sorted(set(old) | set(new)):
        before, after = old.get(cid), new.get(cid)
        refs_used = set((before or {}).get('evidence_ids', [])) | set((after or {}).get('evidence_ids', []))
        evidence_changed = any(old_manifest.get(rid, {}).get('source_hash') != new_manifest.get(rid, {}).get('source_hash') for rid in refs_used)
        if before != after or evidence_changed:
            kind = 'added' if before is None else 'removed' if after is None else 'updated' if before != after else 'evidence_rechecked'
            result.append({'conclusion_id': cid, 'type': kind, 'old': before, 'new': after, 'evidence_changed': evidence_changed})
    return result


def team_context(output, selected):
    """Read the exact accepted versions used by this run, never current annotations."""
    versions, candidates = {}, {}
    for item in selected:
        pid, cid = item['project_id'], item['id']
        path = (output / item['basis_version']).resolve()
        if not path.is_relative_to(output.resolve()):
            raise ValueError('团队稿引用的研究版本超出归档目录')
        version = load(path)
        if not version or version['annotation']['project_id'] != pid:
            raise ValueError('团队稿引用的研究版本不存在或项目不匹配')
        candidate = next((c for c in version['annotation']['daily_candidates'] if c['id'] == cid), None)
        if not candidate or any(item.get(k) != v for k, v in candidate.items()):
            raise ValueError('日报候选与采用的历史版本不匹配')
        if cid in candidates or (pid in versions and versions[pid] != version):
            raise ValueError('团队稿候选重复或同项目采用了不同版本')
        versions[pid], candidates[cid] = version, candidate
    return versions, candidates


def render_team_text(editorial, output, selected):
    """Validate evidence bindings before rendering human-written team prose."""
    versions, candidates = team_context(output, selected)
    if not selected or not isinstance(editorial, dict) or editorial.get('schema_version') != 1:
        raise ValueError('缺少适用于本轮资料的团队版编辑稿')
    cids = editorial.get('candidate_ids', [])
    if len(cids) != len(set(cids)) or set(cids) != set(candidates):
        raise ValueError('团队稿候选范围与本轮不一致')
    if editorial.get('reviewed_source_digests') != {pid: v['source_digest'] for pid, v in versions.items()}:
        raise ValueError('资料已变化，团队稿需重新审阅')
    if editorial.get('reviewed_candidate_hashes') != {cid: digest(c) for cid, c in candidates.items()}:
        raise ValueError('研究判断已变化，团队稿需重新审阅')
    visible = []
    def prose(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('团队稿缺少可读正文')
        visible.append(value)
        return value.strip()
    title, date, edition = (prose(editorial.get(k)) for k in ('title', 'date', 'edition'))
    if not isinstance(editorial.get('lead'), list) or not editorial['lead']:
        raise ValueError('团队稿缺少导读')
    lines = [f'# {title}', f'{date} · {edition}', *[prose(x) for x in editorial['lead']]]
    sections = editorial.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('团队稿缺少正文板块')
    seen_projects = set()
    for section in sections:
        pid = section.get('project_id')
        if pid not in versions:
            raise ValueError('团队稿板块没有对应的已审阅项目')
        seen_projects.add(pid)
        lines.append('## ' + prose(section.get('heading')))
        paragraphs = section.get('paragraphs')
        if not isinstance(paragraphs, list) or not paragraphs:
            raise ValueError('团队稿板块缺少正文')
        lines.extend(prose(x) for x in paragraphs)
        sources = section.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError('团队稿板块缺少原文链接')
        links = []
        for source in sources:
            manifest = versions[pid]['evidence_manifest'].get(source.get('record_id'))
            if not manifest:
                raise ValueError('团队稿来源不存在或不属于该项目的研究版本')
            record = load(output / manifest['archive_path'])
            if not record or record.get('project_id') != pid or source_hash(record) != manifest['source_hash']:
                raise ValueError('团队稿来源归属或归档校验失败')
            url = record.get('source_url', '')
            if not url.startswith(('https://', 'http://')):
                raise ValueError('团队稿来源缺少可访问的原文地址')
            links.append(f"[{prose(source.get('label'))}]({url})")
        lines.append('来源：' + ' · '.join(links))
    if seen_projects != set(versions):
        raise ValueError('团队稿遗漏了本轮项目')
    followups = editorial.get('followups')
    if not isinstance(followups, list):
        raise ValueError('团队稿缺少后续关注说明')
    if followups:
        lines.extend(['## 接下来值得关注', '\n'.join('- ' + prose(x) for x in followups)])
    lines.append(prose(editorial.get('scope_note')))
    if re.search(r'(?<![A-Za-z0-9])(?:P\d{3}(?:-[A-Z]\d+)?|D0[1-4]|C\d+)(?![A-Za-z0-9])|(?:github|huggingface|hackernews):|record_id|source_digest|basis_version|SHA-256|审核队列|离线模式|运行日志|来源版本JSON', '\n'.join(visible)):
        raise ValueError('团队正文含内部编号或运行术语，请重写给项目组阅读')
    return '\n\n'.join(lines) + '\n'


def team_status(output, has_candidates=False, link_prefix=''):
    if has_candidates:
        body = '已有值得关注的资料，但需补写团队版摘要，完成编辑审阅后再提供给项目组。'
    else:
        body = '本次没有可发布的新动态。此前待核实的问题仍需跟进；这不代表市场没有变化。'
    links = [f'[查看项目记录]({link_prefix}索引.md#项目记录)']
    if (output / '团队日报样例.md').exists():
        links.insert(0, f'[最近一期团队简报]({link_prefix}团队日报样例.md)')
    return '# robotic harness 调研简报\n\n' + body + '\n\n' + ' · '.join(links) + '\n'


def require_pilot_output(output):
    metadata = load(output / '团队日报元数据.json', {})
    if metadata.get('batch') or metadata.get('user_accepted_40_project_digest'):
        raise ValueError('此目录已有正式批次日报；三个项目试点不能覆盖，请指定独立的 --output 目录。')


def save_team_edition(output, rdir, text, editorial):
    require_pilot_output(output)
    write(rdir / '团队编辑稿.json', editorial)
    write(output / '团队日报样例.md', text)
    write(output / '日报.md', text)
    write(output / '团队日报元数据.json', {'run_id': rdir.name, 'text_sha256': digest(text.encode()), 'date': editorial['date'], 'edition': editorial['edition']})


def latest_team_text(output):
    metadata = load(output / '团队日报元数据.json', {})
    path = output / '团队日报样例.md'
    if path.exists() and digest(path.read_bytes()) == (metadata.get('text_sha256') or metadata.get('sha256')):
        return path.read_text()
    return None


def render_team_run(output, run_id, editorial_path):
    """Re-edit one saved briefing without running research or touching its state."""
    require_pilot_output(output)
    rdir = (output / 'runs' / run_id).resolve()
    if rdir.parent != (output / 'runs').resolve() or not (rdir / '日报条目.json').exists():
        raise ValueError('找不到指定的历史运行')
    selected = load(rdir / '日报条目.json')
    editorial = load(editorial_path)
    text = render_team_text(editorial, output, selected)
    report = rdir / '日报.md'
    if report.exists():
        original = report.read_bytes()
        backup = rdir / '日报.原版存档.md'
        if not backup.exists():
            immutable(backup, original)
    write(report, text)
    save_team_edition(output, rdir, text, editorial)
    return {'status': 'rendered', 'run_id': run_id, 'report': str(report), 'research_state_changed': False}


def run(records_path, raw_path, annotations_dir, output, project_ids=PROJECTS, now=None, team_digest_path=None):
    require_pilot_output(output)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('处理时间必须带时区')
    stamp = now.isoformat()
    records_bytes, raw_bytes = records_path.read_bytes(), raw_path.read_bytes()
    records = [json.loads(x) for x in records_bytes.decode().splitlines() if x.strip()]
    for line in raw_bytes.decode().splitlines():
        if line.strip():
            json.loads(line)
    ids = [r['record_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('重复 record_id，停止以避免覆盖不同证据')
    if not raw_bytes.strip() or not records:
        raise ValueError('原始 API 或清洗输入为空，不能报告没有变化')
    output.mkdir(parents=True, exist_ok=True)
    state = load(output / 'state.json', {'schema_version': 1, 'projects': {}, 'runs': 0})
    run_id = f"{now.strftime('%Y%m%dT%H%M%S')}-{state['runs'] + 1:04d}"
    raw_rel, clean_rel = f'archive/api/{digest(raw_bytes)}.jsonl', f'archive/cleaned/{digest(records_bytes)}.jsonl'
    immutable(output / raw_rel, raw_bytes)
    immutable(output / clean_rel, records_bytes)
    inputs = {'mode': 'offline_snapshot', 'network_refreshed': False, 'records_path': str(records_path.resolve()), 'raw_api_path': str(raw_path.resolve()), 'raw_archive': raw_rel, 'raw_sha256': digest(raw_bytes), 'cleaned_archive': clean_rel, 'cleaned_sha256': digest(records_bytes), 'processed_at': stamp, 'input_record_count': len(records), 'source_capture_range': source_times({r['record_id']: r for r in records})}
    queue, selected, summaries = [], [], []
    total_changes = 0
    for pid in project_ids:
        pdir = output / 'projects' / pid
        prior = state['projects'].get(pid, {'records': {}, 'events': [], 'accepted': None, 'published_candidates': {}, 'versions': []})
        current = [r for r in records if r.get('project_id') == pid]
        supplied = {r['record_id'] for r in current}
        missing = sorted(set(prior['records']) - supplied)
        added, changed = [], []
        for r in current:
            rid, sem, blob = r['record_id'], source_hash(r), packed(r) + b'\n'
            rel = f'archive/records/{digest(blob)}.json'
            immutable(output / rel, blob)
            old = prior['records'].get(rid)
            if old is None:
                added.append(rid)
            elif old['source_hash'] != sem:
                changed.append(rid)
            prior['records'][rid] = {'source_hash': sem, 'archive_path': rel}
        merged = {rid: load(output / s['archive_path']) for rid, s in prior['records'].items()}
        sd = snapshot_digest(list(merged.values()))
        flags, events_before = time_flags(current, now), len(prior['events'])
        def event(kind, description, **kw):
            prior['events'].append({'id': f"{pid}-E{len(prior['events']) + 1:04d}", 'type': kind, 'processed_at': stamp, 'description': description, 'input_manifest': f'runs/{run_id}/inputs.json', **kw})
        if added or changed:
            event('首次建档' if events_before == 0 else '来源变化待判断', f'本地首次纳入 {len(added)} 条，已有内容变化 {len(changed)} 条；不声称市场新发布。', record_ids=sorted(added + changed), source_digest=sd)
            total_changes += len(added) + len(changed)
        if missing:
            queue.append({'project_id': pid, 'type': 'source_missing', 'record_ids': missing, 'reason': '本次未返回曾见记录，保留旧资料；待核验采集范围/失败原因，不判断删除'})
        if not current:
            queue.append({'project_id': pid, 'type': 'project_missing', 'reason': '本次没有该项目输入，不能判断没有变化'})
        queue += [{'project_id': pid, 'type': 'timestamp_review', **f} for f in flags]
        a = load(annotations_dir / f'{pid}.json')
        errors = validate(a, list(merged.values()), pid) if a else ['缺少经过阅读的 annotations 文件']
        ad, accepted = digest(a) if a else None, prior['accepted']
        changed_since_review = bool(accepted and accepted['source_digest'] != sd)
        stale = bool(changed_since_review and (not a or a.get('reviewed_source_digest') != sd))
        needs_revision = bool(accepted and (accepted['annotation_digest'] != ad or accepted['source_digest'] != sd))
        if needs_revision and not stale and not (a or {}).get('revision_reason', '').strip():
            errors.append('修订已接受版本必须填写 revision_reason，说明为什么改变或保持原判断')
        if errors:
            queue.append({'project_id': pid, 'type': 'annotation_invalid', 'reason': errors})
            status = '待补齐有效审阅'
        elif missing or not current:
            status = '输入覆盖不完整，保留上次结论'
        elif stale:
            queue.append({'project_id': pid, 'type': 'evidence_changed_review_required', 'reason': '证据已变化，旧审阅不能自动覆盖新来源；复核后在 annotations 填入该 digest', 'reviewed_source_digest': sd, 'record_ids': sorted(added + changed)})
            status = '新证据待复核，以下保留上次结论'
        elif flags:
            status = '来源时间异常待核验，暂不采用新结论'
        else:
            if not accepted or accepted['annotation_digest'] != ad or accepted['source_digest'] != sd:
                version = {'version': len(prior['versions']) + 1, 'processed_at': stamp, 'source_digest': sd, 'annotation_digest': ad, 'annotation': a, 'evidence_manifest': dict(prior['records']), 'previous_version': prior['versions'][-1] if prior['versions'] else None, 'change_reason': '首次建立历史基线' if not accepted else a['revision_reason'].strip(), 'conclusion_changes': conclusion_diff(accepted, a, prior['records']), 'inputs': inputs}
                vrel = f'projects/{pid}/versions/v{version["version"]:04d}-{digest(version)[:12]}.json'
                immutable(output / vrel, packed(version) + b'\n')
                prior['versions'].append(vrel)
                prior['accepted'] = accepted = version
                event('建立结论基线' if len(prior['versions']) == 1 else '结论版本更新', version['change_reason'] + '；旧版本保留，可按证据回查。', version_path=vrel, conclusion_changes=version['conclusion_changes'])
            status = '已审阅的历史基线' if len(prior['versions']) == 1 else '已审阅更新'
            for c in a['daily_candidates']:
                identity = digest({'candidate': c, 'evidence': {rid: prior['records'][rid]['source_hash'] for rid in c['evidence_ids']}})
                if identity not in prior['published_candidates']:
                    selected.append(dict(c, project_id=pid, direction_id=a['direction_id'], project_name=a['project_name'], basis_version=prior['versions'][-1], novelty='首次基线阅读' if len(prior['versions']) == 1 else '已复核档案变化', source_links=[{'record_id': rid, 'url': merged[rid].get('source_url')} for rid in c['evidence_ids']]))
                    prior['published_candidates'][identity] = run_id
        write(pdir / '变化日志.json', prior['events'])
        write(pdir / '当前输入快照.json', {'observed_record_ids': sorted(supplied), 'retained_missing_record_ids': missing, 'source_digest': sd, 'input_manifest': inputs})
        summaries.append({'project_id': pid, 'status': status, 'input_records': len(current), 'retained_records': len(merged), 'reviewed_records': len(accepted['annotation']['coverage']['reviewed_record_ids']) if accepted else 0, 'added_to_local_archive': len(added), 'changed_records': len(changed), 'missing_records': len(missing), 'new_history_events': len(prior['events']) - events_before, 'conclusion_versions': len(prior['versions']), 'source_digest': sd})
        state['projects'][pid] = prior
    research_questions = []
    for pid in project_ids:
        accepted = state['projects'][pid]['accepted']
        if accepted:
            research_questions += [dict(c, project_id=pid, direction_id=accepted['annotation']['direction_id'], basis_version=state['projects'][pid]['versions'][-1]) for c in accepted['annotation']['daily_candidates'] if c['human_review']]
    summary = {'run_id': run_id, 'processed_at': stamp, 'mode': 'offline_snapshot', 'network_refreshed': False, 'scheduled': False, 'external_delivery': False, 'projects': summaries, 'new_source_records_or_changes': total_changes, 'daily_item_count': len(selected), 'review_queue_count': len(queue), 'research_question_count': len(research_questions), 'inputs': inputs}
    rdir = output / 'runs' / run_id
    for name, value in (('inputs.json', inputs), ('summary.json', summary), ('审核队列.json', queue), ('日报条目.json', selected), ('研究待核实事项.json', research_questions)):
        write(rdir / name, value)
    write(output / 'summary.json', summary)
    write(output / '审核队列.json', queue)
    write(output / '研究待核实事项.json', research_questions)
    team_text = None
    if selected and team_digest_path:
        try:
            editorial = load(team_digest_path)
            team_text = render_team_text(editorial, output, selected)
            write(rdir / '团队编辑稿.json', editorial)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            write(rdir / '团队稿校验.json', {'status': 'needs_editorial_review', 'reason': str(exc)})
    if team_text:
        save_team_edition(output, rdir, team_text, editorial)
    write(rdir / '日报.md', team_text or team_status(output, bool(selected), '../../'))
    write(output / '日报.md', team_text or latest_team_text(output) or team_status(output, bool(selected)))
    state['runs'] += 1
    write(output / 'state.json', state)
    index = ['# robotic harness 调研资料\n', '[团队日报](日报.md)\n', '## 项目记录\n']
    for pid in project_ids:
        name = PROJECT_RECORDS.get(pid)
        if name:
            index.append(f'- [{name}](<项目记录/{name}.md>)')
    write(output / '索引.md', '\n'.join(index) + '\n')
    return summary


def main():
    home = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records', '--input', type=Path, default=home / 'input' / '清洗记录补全.jsonl')
    p.add_argument('--raw-api', type=Path, default=home.parent / 'demo' / 'API原始响应.jsonl')
    p.add_argument('--annotations', type=Path, default=home / 'annotations')
    p.add_argument('--output', type=Path, default=home / 'replay-output')
    p.add_argument('--team-digest', type=Path, default=home / 'team_digest.json')
    p.add_argument('--render-team-run', help='只重排指定历史简报，不运行研究或修改已展示状态')
    args = p.parse_args()
    if args.render_team_run:
        try:
            result = render_team_run(args.output, args.render_team_run, args.team_digest)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(str(exc))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    try:
        result = run(args.records, args.raw_api, args.annotations, args.output, team_digest_path=args.team_digest)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failure = {'status': 'failed', 'reason': str(exc), 'market_change': 'unknown', 'message': '处理失败，不代表没有变化；原有结论未获新审核。', 'processed_at': datetime.now(timezone.utc).isoformat()}
        write(args.output / '最近失败.json', failure)
        raise SystemExit(json.dumps(failure, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
