#!/usr/bin/env python3
"""从项目总表生成 A/B 监控名单。

A 级：已建档的重点项目，日常检查 README、Issue、评论和 Release。
B 级：其他已确认相关的 GitHub 项目，日常只做仓库信号和 README 变化检查。
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'selection' / '项目选择清单.json'
OUTPUT = ROOT / 'monitoring-tiers.json'
PROJECT_ROOT = ROOT.parent


def github_repo(row):
    stars = row.get('github_stars') or {}
    repo = stars.get('repository')
    return repo if repo and '/' in repo else None

def portable_record_path(value):
    if not value:return None
    path=Path(value)
    try:return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:return str(path) if not path.is_absolute() else None


def build(source=SOURCE, previous=None):
    data = json.loads(Path(source).read_text())
    old = {}
    if previous and Path(previous).exists():
        old = {x['repo']: x for x in json.loads(Path(previous).read_text()).get('projects', [])}
    projects = []
    for row in data['rows']:
        repo = github_repo(row)
        if not repo:
            continue
        prior = old.get(repo, {})
        tier = prior.get('tier') or ('A' if row.get('already_initialized') else 'B')
        projects.append({
            'project_id': row.get('project_id'),
            'name': row.get('name'),
            'repo': repo,
            'direction': row.get('direction'),
            'tier': tier,
            'tier_reason': prior.get('tier_reason') or ('已完成初始化，纳入重点监控' if tier == 'A' else '已确认相关，先做轻量监控'),
            'record_path': portable_record_path(row.get('record_path')),
            'stars': (row.get('github_stars') or {}).get('stars'),
            'promoted_at': prior.get('promoted_at'),
            'manual_override': prior.get('manual_override', False),
        })
    return {
        'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
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
    result = build(SOURCE, OUTPUT)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    counts = {tier: sum(x['tier'] == tier for x in result['projects']) for tier in ('A', 'B', 'C')}
    print(json.dumps({'output': str(OUTPUT), 'counts': counts}, ensure_ascii=False))


if __name__ == '__main__':
    main()
