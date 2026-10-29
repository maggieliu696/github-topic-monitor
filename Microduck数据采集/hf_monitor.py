#!/usr/bin/env python3
"""HF轻量扫描：全量关键词发现、已知来源补查、差异入队；不自动拆分项目或调用模型。"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = 'https://huggingface.co'

def read(p, default):
    return json.loads(p.read_text()) if p.exists() else default

def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_name(p.name + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    temp.replace(p)

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'robotic-harness-research/1.0'})
    with urllib.request.urlopen(req, timeout=30) as res:
        raw = res.read().decode('utf-8')
        return raw, res.headers.get('Link', '')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', action='store_true', help='以已收集的公开数据建立首次基线，不联网')
    args = parser.parse_args()
    config = read(ROOT / 'config.json', {}).get('huggingface', {})
    queries = config.get('queries', ['microduck'])
    kinds = config.get('repo_types', ['models', 'datasets', 'spaces'])
    catalog_path = ROOT / 'selection/项目选择清单.json'
    index_path = ROOT / 'selection/平台来源索引.json'
    catalog = read(catalog_path, {})
    index = read(index_path, {})
    known = {s['source_key']: s for s in index.get('sources', []) if s['platform'] == 'huggingface'}
    state = ROOT / 'data/huggingface-state.json'
    previous = read(state, {})
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    stamp = now.isoformat(timespec='seconds')
    if args.seed:
        if state.exists():
            raise SystemExit('基线已存在，不覆盖历史。')
        save(state, {'observed_at': stamp, 'sources': known, 'readme_hashes': {}, 'discussion_hashes': {}})
        print(json.dumps({'seeded_sources': len(known)}, ensure_ascii=False))
        return
    run = ROOT / 'huggingface-runs' / now.strftime('%Y%m%d-%H%M%S')
    run.mkdir(parents=True)
    lock = ROOT / 'data/huggingface-scan.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    current, errors, queue, metrics = {}, [], [], []
    hashes = dict(previous.get('readme_hashes', {}))
    discussions = dict(previous.get('discussion_hashes', {}))
    old_sources = previous.get('sources', {})
    a_ids = {r['project_id'] for r in catalog.get('rows', []) if r.get('monitoring_tier') == 'A'}

    def request(url):
        raw, links = get(url)
        name = hashlib.sha256(url.encode()).hexdigest()[:20]
        save(run / 'raw' / (name + '.json'), {'url': url, 'at': stamp, 'body': raw})
        return json.loads(raw), links

    try:
        searches = [(kind, term) for kind in kinds for term in queries]
        for kind, term in searches:
            url = API + '/api/' + kind + '?' + urllib.parse.urlencode({'search': term, 'limit': 100, 'full': 'true'})
            try:
                while url:
                    items, links = request(url)
                    if not isinstance(items, list):
                        raise ValueError('HF列表响应格式异常')
                    for item in items:
                        repo = item.get('id') or item.get('modelId')
                        if repo:
                            current['hf:' + kind + ':' + repo] = item
                    match = re.search(r'<([^>]+)>;\s*rel="next"', links)
                    url = match.group(1) if match else None
            except Exception as exc:
                errors.append({'scope': kind, 'error': str(exc)})
        # 已归并来源即便改名或不再命中关键词，也继续跟踪；失败不当成被删除。
        for key, source in known.items():
            if key not in current:
                try:
                    item, _ = request(API + '/api/' + source['repo_type'] + '/' + source['repository'])
                    current[key] = item
                except Exception as exc:
                    errors.append({'source_key': key, 'error': str(exc)})
                    continue
            item = current[key]
            old = old_sources.get(key, {})
            new = dict(source, likes=item.get('likes'), downloads_30d=item.get('downloads'),
                       sha=item.get('sha'), last_modified=item.get('lastModified'), metrics_observed_at=stamp,
                       daily_scan_state='已接入每日扫描')
            current[key] = new
            pid = source.get('project_id')
            change = any(old.get(k) is not None and old.get(k) != new.get(k) for k in ('sha', 'last_modified'))
            if any(old.get(k) != new.get(k) for k in ('likes', 'downloads_30d')):
                metrics.append({'source_key': key, 'project_id': pid, 'before': old, 'after': new})
            if change and pid not in a_ids:
                queue.append({'type': 'B_source_changed', 'project_id': pid, 'source_key': key, 'source': new['url']})
            if pid in a_ids:
                # A类每天读说明指纹及讨论列表，正文仅变化时交给Agent。
                if change or key not in hashes:
                    try:
                        raw, _ = get(source['readme_evidence_url'])
                        digest = hashlib.sha256(raw.encode()).hexdigest()
                        path = run / 'readmes' / (hashlib.sha256(key.encode()).hexdigest()[:20] + '.md')
                        path.parent.mkdir(exist_ok=True)
                        path.write_text(raw)
                        if hashes.get(key) != digest:
                            queue.append({'type': 'A_readme_changed' if key in hashes else 'A_readme_first_snapshot',
                                          'project_id': pid, 'source': source['url'], 'local_file': str(path)})
                        hashes[key] = digest
                    except Exception as exc:
                        errors.append({'source_key': key, 'scope': 'A_readme', 'error': str(exc)})
                try:
                    body, _ = request(API + '/api/' + source['repo_type'] + '/' + source['repository'] + '/discussions')
                    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
                    if discussions.get(key) != digest:
                        queue.append({'type': 'A_discussion_list_changed' if key in discussions else 'A_discussion_first_snapshot',
                                      'project_id': pid, 'source': source['url'] + '/discussions', 'listing': body})
                    discussions[key] = digest
                except Exception as exc:
                    errors.append({'source_key': key, 'scope': 'A_discussions', 'error': str(exc)})
        # 新来源先进入持久待归并队列，不把单个模型版本当成新项目。
        pending_path = ROOT / 'data/huggingface-pending-sources.json'
        pending = read(pending_path, {})
        for key, item in current.items():
            if key not in known:
                pending[key] = {'source_key': key, 'metadata': item, 'last_seen_at': stamp,
                                'first_seen_at': pending.get(key, {}).get('first_seen_at', stamp)}
        pending = {k: v for k, v in pending.items() if k not in known}
        save(pending_path, pending)
        for source in index.get('sources', []):
            if source['source_key'] in known and source['source_key'] in current:
                source.update(current[source['source_key']])
        index['updated_at'] = stamp
        lookup = {s['source_key']: s for s in index.get('sources', [])}
        for row in catalog.get('rows', []):
            row['huggingface_sources'] = [lookup.get(s['source_key'], s) for s in row.get('huggingface_sources', [])]
            sources = row['huggingface_sources']
            if sources:
                likes = [s['likes'] for s in sources if s.get('likes') is not None]
                downloads = [s['downloads_30d'] for s in sources if s.get('repo_type') == 'models' and s.get('downloads_30d') is not None]
                row['hf_metrics'].update(max_likes=max(likes) if likes else None,
                                         max_model_downloads_30d=max(downloads) if downloads else None)
        save(index_path, index)
        save(catalog_path, catalog)
        # 请求失败保留旧状态；下次仍能对照到未完成的变化。
        if not errors:
            save(state, {'observed_at': stamp, 'sources': {k: current[k] for k in known},
                         'readme_hashes': hashes, 'discussion_hashes': discussions})
        save(run / 'agent-review-queue.json', queue)
        save(run / 'metric-changes.json', metrics)
        save(run / 'new-source-candidates.json', list(pending.values()))
        summary = {'at': stamp, 'run_dir': str(run), 'complete': not errors, 'known_sources': len(known),
                   'review_items': len(queue), 'new_sources_pending_merge': len(pending), 'errors': errors}
        save(run / 'summary.json', summary)
        save(ROOT / 'huggingface-最新运行.json', summary)
        print(json.dumps(summary, ensure_ascii=False))
        if errors:
            raise SystemExit(1)
    finally:
        lock.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
