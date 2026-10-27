#!/usr/bin/env python3
"""生成每周一 A/B 重新分类建议，不盲目覆盖人工判断。"""
import json
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TIERS=ROOT/'monitoring-tiers.json'
OUTPUT=ROOT/'weekly-tier-review.json'

def build(data):
    groups=defaultdict(list)
    for project in data['projects']:groups[project['direction']].append(project)
    result=[]
    for direction,projects in sorted(groups.items()):
        ranked=sorted(projects,key=lambda x:(-(x.get('stars') or 0),x['repo']))
        top={x['repo'] for x in ranked[:10]}
        promoted=[x for x in projects if x.get('promoted_at') or x.get('manual_override')]
        suggested_a=top|{x['repo'] for x in sorted(promoted,key=lambda x:x.get('promoted_at') or '',reverse=True)[:3]}
        current={x['repo'] for x in projects if x['tier']=='A'}
        result.append({'direction':direction,'top10_by_stars':sorted(top),'currently_a':sorted(current),
            'suggested_a':sorted(suggested_a),'needs_human_review':sorted(current^suggested_a)})
    return {'rule':'每方向 10 个基础 A 级 + 最多 3 个近期触发升级的项目','directions':result}

if __name__=='__main__':
    result=build(json.loads(TIERS.read_text()))
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUTPUT),'directions':len(result['directions'])},ensure_ascii=False))
