#!/usr/bin/env python3
"""Apply evidence-backed Agent decisions; initialize one document before tiering."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import tempfile
import os

from collector import ROOT, Store, acquire_run_lock, now

DIRECTIONS = {'动作训练与算法实验', '开发工具与运行环境', 'AI 应用与交互玩法', '硬件复刻与适配'}


def atomic_json(path, data):
    atomic_text(path, json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(text)
        temporary = f.name
    os.replace(temporary, path)


def apply_decision(store, decision, root=ROOT):
    root = Path(root)
    repo = decision['repo']
    rows = store.rows('SELECT * FROM project_reviews WHERE repo=?', (repo,))
    if not rows:
        raise ValueError('不是待处理候选：'+repo)
    if rows[0]['status'] != 'pending':
        # A retry after an interrupted batch must not duplicate accepted projects.
        if json.loads(rows[0]['payload']).get('decision') == decision:
            return
        raise ValueError('项目已处理；修改决定需要单独复核：'+repo)
    status = decision.get('status')
    if status not in {'accepted', 'excluded', 'merged'} or not decision.get('reason'):
        raise ValueError('必须明确收录、排除或合并，并说明理由')
    sources = decision.get('sources', [])
    if not sources or any(not isinstance(s, str) or not s.startswith('https://') for s in sources):
        raise ValueError('处理决定必须附公开来源链接')
    source_path = root/'selection/项目选择清单.json'
    data = json.loads(source_path.read_text())
    basic_mode=data.get('catalog_policy',{}).get('initialization')=='A_only'
    matched = [x for x in data['rows'] if (x.get('github_stars') or {}).get('repository') == repo or repo in x.get('github_repositories',[]) or x.get('url','').rstrip('/') == 'https://github.com/'+repo]
    if status == 'merged':
        target = decision.get('merged_into')
        target_row = next((x for x in data['rows'] if target in {x.get('project_id'), (x.get('github_stars') or {}).get('repository')}), None)
        if target == repo or not target_row or not (target_row.get('already_initialized') or basic_mode and target_row.get('basic_profile_status')):
            raise ValueError('合并目标必须是已基础识别的其他项目')
        # 配套来源必须留在目标项目，不能只标记merged后丢失链接。
        target_row['sources']=list(dict.fromkeys(target_row.get('sources',[])+sources))
        target_row['github_repositories']=list(dict.fromkeys(target_row.get('github_repositories',[])+[repo]))
        target_row['platforms']=list(dict.fromkeys(target_row.get('platforms',[])+['GitHub']))
        target_row.setdefault('huggingface_sources',[])
        if not (target_row.get('github_stars') or {}).get('repository'):
            ev=json.loads(rows[0]['payload'])
            target_row['github_stars']={'repository':repo,'stars':ev.get('stars'),'observed_at':ev.get('stars_observed_at'),'status':'ok'}
    if status != 'accepted':
        if any(x.get('already_initialized') for x in matched):
            raise ValueError('已建档项目不能通过候选处理接口删除')
        for row in matched:
            row.update(initialization_status='已排除' if status == 'excluded' else '已合并',
                       monitoring_excluded=True, exclusion_reason=decision['reason'],
                       merged_into=decision.get('merged_into'))
        atomic_json(source_path, data)
        store.decide_candidate(repo, status, decision)
        return
    evidence = json.loads(rows[0]['payload'])
    if decision.get('tier')=='A' and data.get('catalog_policy',{}).get('main_project_focus') and evidence.get('fork'):
        raise ValueError('主项目优先：Fork只作附属观察，不单独升A')
    if basic_mode and decision.get('tier')=='B':
        if not evidence.get('readme_checked') or not evidence.get('basic_profile_complete'):
            raise ValueError('B类须先完成说明检查和基础采集，不能凭空入表')
        for field in ('name','author','purpose','tier_reason'):
            if not isinstance(decision.get(field),str) or not decision[field].strip():raise ValueError('基础识别缺少：'+field)
        if decision.get('direction') not in DIRECTIONS|{'待归类'}:raise ValueError('必须记录研究方向或待归类')
        if matched:row=matched[0]
        else:
            numbers=[int(x['project_id'][1:])for x in data['rows']if re.fullmatch(r'P\d+',x.get('project_id',''))]
            row={'number':max((x.get('number',0)for x in data['rows']),default=0)+1,'project_id':'P%03d'%(max(numbers,default=0)+1)}
            data['rows'].append(row)
        row.update(name=decision['name'],author=decision['author'],plain_purpose=decision['purpose'],
            url='https://github.com/'+repo,direction=decision['direction'],sources=list(dict.fromkeys(row.get('sources',[])+sources)),
            monitoring_tier='B',tier_reason=decision['tier_reason'],basic_profile_status=decision.get('basic_profile_status','已基础识别'),
            basic_profile_updated_at=now(),monitoring_excluded=False,
            already_initialized=bool(row.get('already_initialized')),initialization_status='已建档'if row.get('already_initialized')else'仅总表',
            archive_status='已建档'if row.get('already_initialized')else'B类不要求建档',
            github_stars=dict(row.get('github_stars')or{},repository=repo,stars=evidence.get('stars'),
                observed_at=evidence.get('stars_observed_at'),source='https://api.github.com/repos/'+repo,status='ok'))
        row['source_is_fork']=bool(evidence.get('fork'))
        row['platforms']=list(dict.fromkeys(row.get('platforms',[])+['GitHub']))
        row['github_repositories']=list(dict.fromkeys(row.get('github_repositories',[])+[repo]))
        row.setdefault('huggingface_sources',[])
        row.setdefault('catalog_added_at',now())
        atomic_json(source_path,data)
        store.decide_candidate(repo,status,decision)
        return
    if not evidence.get('baseline_complete') or not evidence.get('readme_checked'):
        raise ValueError('必须先完成说明、问题、评论和版本的基础采集：'+repo)
    for field in ('name','author','purpose','current_state','problems_and_resolutions','evaluation_and_limits','tier_reason','record_markdown'):
        if not isinstance(decision.get(field), str) or not decision[field].strip():
            raise ValueError('初始化缺少：'+field)
    if decision.get('direction') not in DIRECTIONS or decision.get('tier') not in {'A','B'}:
        raise ValueError('完成初始化后必须选择一个研究方向和 A/B 级别')
    if not any(url in decision['record_markdown'] for url in sources):
        raise ValueError('唯一项目记录中必须保留来源链接')
    if matched:
        row = matched[0]
        project_id = row['project_id']
        path = Path(row['record_path']) if row.get('record_path') else None
    else:
        numbers = [int(x['project_id'][1:]) for x in data['rows'] if re.fullmatch(r'P\d+', x.get('project_id',''))]
        project_id = 'P%03d' % (max(numbers,default=0)+1)
        row = {'number':max((x.get('number',0) for x in data['rows']),default=0)+1,'project_id':project_id}
        data['rows'].append(row)
        path = None
    if path is None:
        slug = re.sub(r'[^A-Za-z0-9_.-]', '-', repo)
        path = root/'pilot/output/项目记录'/(project_id+'-'+slug+'.md')
    elif not path.is_absolute():
        path = root.parent/path
    path = path.resolve()
    if not path.is_relative_to((root/'pilot/output/项目记录').resolve()):
        raise ValueError('项目记录只能写入现有项目记录目录')
    stars = evidence.get('stars')
    repo_meta = store.rows("SELECT payload FROM items WHERE id=?",('github:repo:'+str(evidence.get('repo_id')),))
    meta = json.loads(repo_meta[0]['payload']).get('meta',{}) if repo_meta else {}
    text = '# '+decision['name']+'\n\n'+project_id+' · '+decision['direction']+' · 作者：'+decision['author']+'\n\n'+decision['record_markdown'].strip()+'\n'
    # Commit the readable record before promoting it into the monitoring list.
    atomic_text(path, text)
    row.update(name=decision['name'], author=decision['author'], url='https://github.com/'+repo,
               direction=decision['direction'], plain_purpose=decision['purpose'],
               current_assessment=decision['current_state'],
               problems_and_resolutions=decision['problems_and_resolutions'],
               evaluation_and_limits=decision['evaluation_and_limits'], sources=sources,
               reason=decision['tier_reason'], already_initialized=True,
               initialization_status='已建档',monitoring_excluded=False,
               monitoring_tier=decision['tier'],tier_reason=decision['tier_reason'],
               record_path=str(path.relative_to(root.parent.resolve())),initialized_at=now(),
               record_sha256=hashlib.sha256(text.encode()).hexdigest(),
               github_stars=dict(row.get('github_stars') or {},repository=repo,
                   stars=meta.get('stars',stars),observed_at=meta.get('stars_observed_at'),
                   source='https://api.github.com/repos/'+repo,repository_url='https://github.com/'+repo,status='ok'))
    atomic_json(source_path, data)
    # Mark complete last. If writing any file failed, the candidate stays pending.
    store.decide_candidate(repo, status, decision)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--example',action='store_true',help='输出 Agent 处理决定的格式，不修改数据')
    args=parser.parse_args()
    if args.example:
        print(json.dumps([{'repo':'owner/repository','status':'accepted','reason':'确认相关并完成初始化',
            'name':'项目名称','author':'作者公开署名','purpose':'项目是做什么的','direction':'AI 应用与交互玩法',
            'current_state':'目前做到哪一步、版本与验证范围','problems_and_resolutions':'遇到的问题及如何处理',
            'evaluation_and_limits':'作者或用户评价；未验证内容明确写未知','sources':['https://github.com/owner/repository'],
            'record_markdown':'可以直接阅读的完整项目记录，保留具体信息并在相应段落附来源链接。',
            'tier':'B','tier_reason':'完成初始化后的分级理由'},
            {'repo':'owner/noise','status':'excluded','reason':'无相关开发内容的榜单','sources':['https://github.com/owner/noise']},
            {'repo':'owner/duplicate','status':'merged','merged_into':'owner/repository','reason':'同一个项目的配套仓库','sources':['https://github.com/owner/duplicate']}],ensure_ascii=False,indent=2))
        return
    lock=(ROOT/'data/collector.lock').open('a')
    acquire_run_lock(lock)
    store=Store(ROOT/'data/research.sqlite3')
    if args.decisions:
        decisions=json.loads(args.decisions.read_text())
        if not isinstance(decisions,list):raise ValueError('处理结果必须是 JSON 数组')
        for decision in decisions:apply_decision(store,decision)
    pending=store.pending_candidates()
    print(json.dumps({'pending':len(pending),'projects':[x['repo'] for x in pending]},ensure_ascii=False))
    store.db.close()


if __name__=='__main__':main()
