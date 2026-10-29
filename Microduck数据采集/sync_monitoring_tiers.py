#!/usr/bin/env python3
"""从项目总表生成 A/B 监控名单。

A 级：已建档的重点项目，日常检查 README、Issue、评论和 Release。
B 级：其他已确认相关的 GitHub 项目，日常只做仓库信号和 README 变化检查。
"""
import datetime as dt
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'selection' / '项目选择清单.json'
OUTPUT = ROOT / 'monitoring-tiers.json'
PROJECT_ROOT = ROOT.parent
DATABASE = ROOT / 'data' / 'research.sqlite3'


def github_repo(row):
    stars = row.get('github_stars') or {}
    repo = stars.get('repository')
    return repo if repo and '/' in repo else None

def portable_record_path(value):
    if not value:return None
    path=Path(value)
    try:return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:return str(path) if not path.is_absolute() else None


def refresh_stars(data, database=DATABASE):
    """Reuse today's API snapshots, avoiding a second network scan or stale rankings."""
    if not Path(database).exists():return data
    db=sqlite3.connect('file:'+str(Path(database).resolve())+'?mode=ro',uri=True)
    try:
        latest={}
        for (payload,) in db.execute("SELECT payload FROM items WHERE platform='github' AND kind='repository_candidate'"):
            item=json.loads(payload);meta=item.get('meta') or {}
            if meta.get('stars') is not None and meta.get('stars_observed_at'):
                latest[item['title']]=meta
        for row in data['rows']:
            previous=row.get('github_stars') or {};repo=previous.get('repository');meta=latest.get(repo)
            if not meta:continue
            if 'fork' in meta:
                row['source_is_fork']=bool(meta['fork'])
                if row['source_is_fork'] and data.get('catalog_policy',{}).get('main_project_focus'):
                    row['monitoring_tier']='B'
                    row['tier_reason']='Fork按上游项目的附属资料观察，不单独重点监控'
            observed=meta['stars_observed_at'];old_date=previous.get('observed_at')
            if old_date and dt.datetime.fromisoformat(observed)<=dt.datetime.fromisoformat(old_date):continue
            current=dict(previous,stars=meta['stars'],observed_at=observed,
                         source='https://api.github.com/repos/'+repo,status='ok')
            current.update(delta=meta['stars']-previous['stars'] if previous.get('stars') is not None and old_date else None,
                           compared_with=old_date if previous.get('stars') is not None and old_date else None)
            row['github_stars']=current
        return data
    finally:db.close()


def build(source=SOURCE, previous=None, database=DATABASE, data=None):
    data = refresh_stars(data if data is not None else json.loads(Path(source).read_text()),database)
    old = {}
    if previous and Path(previous).exists():
        old = {x['repo']: x for x in json.loads(Path(previous).read_text()).get('projects', [])}
    projects = []
    for row in data['rows']:
        if row.get('monitoring_excluded'):continue
        repo = github_repo(row)
        if not repo:
            continue
        prior = old.get(repo, {})
        record=portable_record_path(row.get('record_path'))
        initialized=bool(row.get('already_initialized') and record and (PROJECT_ROOT/record).is_file())
        basic_mode = data.get('catalog_policy',{}).get('initialization')=='A_only'
        tier = (row.get('monitoring_tier') or prior.get('tier') or ('A' if initialized else 'B')) if basic_mode else ((row.get('monitoring_tier') or prior.get('tier') or 'A') if initialized else None)
        if data.get('catalog_policy',{}).get('main_project_focus') and row.get('source_is_fork'):
            tier='B'
        initialization_status='initialized' if initialized else ('not_required' if basic_mode and tier=='B' else 'pending')
        projects.append({
            'project_id': row.get('project_id'),
            'name': row.get('name'),
            'repo': repo,
            'direction': row.get('direction'),
            'tier': tier,
            'tier_reason': (row.get('tier_reason') or prior.get('tier_reason') or '基础入表，按研究价值分级') if initialized or basic_mode else '尚未完成初始化，暂不分级',
            'initialization_status': initialization_status,
            'basic_profile_status': row.get('basic_profile_status'),
            'record_path': record,
            'stars': (row.get('github_stars') or {}).get('stars'),
            'stars_observed_at': (row.get('github_stars') or {}).get('observed_at'),
            'promoted_at': prior.get('promoted_at'),
            'manual_override': prior.get('manual_override', False),
        })
    return {
        'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'catalog_policy': data.get('catalog_policy',{}),
        'policy': {
            'A': '每日检查全部变化，包括 README、Issue、评论和 Release',
            'B': '每日检查仓库更新、README 和 Star 重大变化，触发后再深读',
            'C': '暂不启用；连续 60 天没有更新且资料稀少时才可讨论降级',
            'weekly_review': '每周一重新分类；每个方向保留 10 个基础 A 级，可额外保留最多 3 个观察项目',
        },
        'promotion_triggers': [
            '出现实体鸭子验证', '出现真实使用者反馈', '出现新用途',
            '进入所在方向 Star 前 10', '7 天 Star 增长至少 5 且超过 20%', 'Star 绝对增长至少 50'
        ],
        'projects': projects,
    }


def main():
    data=refresh_stars(json.loads(SOURCE.read_text()))
    result = build(SOURCE, OUTPUT, data=data)
    SOURCE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    counts = {tier: sum(x['tier'] == tier for x in result['projects']) for tier in ('A', 'B', 'C')}
    counts['pending_initialization']=sum(x['tier'] is None for x in result['projects'])
    print(json.dumps({'output': str(OUTPUT), 'counts': counts}, ensure_ascii=False))


if __name__ == '__main__':
    main()
