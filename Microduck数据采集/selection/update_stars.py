#!/usr/bin/env python3
"""Read public GitHub metadata; preserve snapshots and refresh the existing selection table."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
RUN = sys.argv[2] if len(sys.argv)>2 and sys.argv[1]=='--resume' else dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'star-snapshots' / RUN

def repo_of(url):
    p = urllib.parse.urlparse(url)
    return '/'.join(p.path.strip('/').split('/')[:2]) if p.hostname == 'github.com' else None

def main():
    data = json.loads((ROOT / '项目选择清单.json').read_text())
    wanted = {repo_of(r['url']).lower(): repo_of(r['url']) for r in data['rows'] if repo_of(r['url'])}
    OUT.mkdir(parents=True, exist_ok=True)
    found, errors = {}, []
    headers = {'User-Agent':'robotic-harness-research/1.0', 'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28'}
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    if token: headers['Authorization'] = 'Bearer ' + token
    stopped = False
    calls = 0
    resume = '--resume' in sys.argv
    if resume and (OUT/'observations.json').exists():
        found.update(json.loads((OUT/'observations.json').read_text()))
        prior=json.loads((OUT/'summary.json').read_text())
        calls=prior['api_calls']
        errors.extend(e for e in prior['errors'] if 'url' in e)
    def get(url):
        nonlocal calls, stopped
        calls += 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                body = json.load(response)
                stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
                (OUT / ('api-%03d.json' % calls)).write_text(json.dumps({'url':url,'observed_at':stamp,'http_status':response.status,'payload':body},ensure_ascii=False))
                return body, stamp
        except urllib.error.HTTPError as e:
            errors.append({'url':url,'status':e.code})
            if e.code in (403,429): stopped = True
        except Exception as e:
            errors.append({'url':url,'error':str(e)})
        return None, None
    def accept(r, stamp, source, requested=None):
        key = (requested or r.get('full_name','')).lower()
        if key not in wanted or not isinstance(r.get('stargazers_count'),int):return
        found[key] = {'repo_id':r['id'],'repository':r['full_name'],'stars':r['stargazers_count'],'observed_at':stamp,'source':source,'repository_url':r['html_url'],'fork':r.get('fork',False),'archived':r.get('archived',False)}
    # Search yields up to 100 repositories per call, avoiding one request per known repository.
    for page in ([] if resume else range(1,3)):
        url = 'https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q':'microduck fork:true','per_page':100,'page':page,'sort':'stars','order':'desc'})
        body,stamp = get(url)
        if body is None:break
        for r in body.get('items',[]):accept(r,stamp,url)
        print('search page',page,'matched',len(found),'of',len(wanted),flush=True)
        if len(found)==len(wanted) or len(body.get('items',[]))<100:break
        time.sleep(7)
    # Multiple user qualifiers are ORed by GitHub; limit groups to reduce unrelated results.
    owners=list(dict.fromkeys(repo.split('/')[0] for key,repo in wanted.items() if key not in found))
    for offset in range(0,min(len(owners),24),4):
        if stopped:break
        query='fork:true ' + ' '.join('user:'+owner for owner in owners[offset:offset+4])
        url='https://api.github.com/search/repositories?'+urllib.parse.urlencode({'q':query,'per_page':100,'sort':'updated'})
        time.sleep(7)
        body,stamp=get(url)
        if body:
            for r in body.get('items',[]):accept(r,stamp,url)
        print('owner search matched',len(found),'of',len(wanted),flush=True)
    # Exact repository lookup covers differently named projects and search omissions.
    for key,repo in wanted.items():
        if key in found or stopped:continue
        if any(e.get('status')==404 and e.get('url','').lower()=='https://api.github.com/repos/'+key for e in errors):continue
        if calls >= 45:
            errors.append({'reason':'conservative unauthenticated request budget reached'});break
        url='https://api.github.com/repos/'+repo
        body,stamp=get(url)
        if body:accept(body,stamp,url,repo)
    previous = {}
    for path in sorted((ROOT/'star-snapshots').glob('*/observations.json')):
        if path.parent==OUT:continue
        for key,record in json.loads(path.read_text()).items():previous[key]=record
    for row in data['rows']:
        repo=repo_of(row['url'])
        if not repo:
            row['github_stars']={'status':'not_applicable'};continue
        key=repo.lower()
        if key not in found:
            old=row.get('github_stars',{})
            row['github_stars']={**old,'status':'not_refreshed','last_attempt_at':RUN}
            if any(e.get('status')==404 and e.get('url','').lower()=='https://api.github.com/repos/'+key for e in errors):
                row['github_stars']['http_status']=404
            continue
        metric=found[key].copy();old=previous.get(key)
        metric['status']='ok'
        metric['scope']='branch_in_repository' if len(urllib.parse.urlparse(row['url']).path.strip('/').split('/'))>2 else 'repository'
        metric['delta']=metric['stars']-old['stars'] if old and old['repo_id']==metric['repo_id'] else None
        metric['compared_with']=old['observed_at'] if metric['delta'] is not None else None
        row['github_stars']=metric
    data['star_collection']={'run':RUN,'matched_repositories':len(found),'requested_repositories':len(wanted),'api_calls':calls,'errors':errors}
    (OUT/'observations.json').write_text(json.dumps(found,ensure_ascii=False,indent=2)+'\n')
    (OUT/'summary.json').write_text(json.dumps(data['star_collection'],ensure_ascii=False,indent=2)+'\n')
    (ROOT/'项目选择清单.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    table_path=ROOT.parent.parent/'Microduck项目候选清单.md'
    text=table_path.read_text()
    text=re.sub(r'<!-- github-stars:start -->.*?<!-- github-stars:end -->\n*','',text,flags=re.S)
    note=('<!-- github-stars:start -->\n**Star 已补充：**本轮从 GitHub 官方 API 取得 %s/%s 个 GitHub 仓库的数据。每个数字后标注北京时间采集日期；同一天有多次采集时，具体时刻保存在后台。Star 表示收藏关注，不等于购买、使用或认可。分支项目显示的是整个仓库的 Star。其他平台写“不适用”，取不到的数据不当作 0。首次采集不计算增长；后续有两次可比记录才显示增减及比较日期。\n<!-- github-stars:end -->\n\n' % (len(found),len(wanted)))
    first=text.index('\n\n')+2
    text=text[:first]+note+text[first:]
    by_number={r['number']:r for r in data['rows']}
    lines=[]
    for line in text.splitlines():
        if line.startswith('| 选择号 |'):
            line='| 选择号 | 项目／作者 | GitHub Star（采集日期） | 用普通话说，做什么 | 建议与原因 | 具体证据和限制 |'
        elif line.startswith('|---:|'):
            line='|---:|---|---|---|---|---|'
        elif re.match(r'^\| \d+ \|',line):
            cells=[c.strip() for c in line.strip('|').split('|')]
            row=by_number[int(cells[0])];m=row['github_stars']
            if len(cells)==6:cells.pop(2)
            if m['status']=='not_applicable':value='不适用'
            elif 'stars' not in m:value='暂无法读取（API 返回 404）' if m.get('http_status')==404 else '待补采'
            else:
                day=dt.datetime.fromisoformat(m['observed_at']).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d')
                value='**{:,}**<br>{}'.format(m['stars'],day)
                if m['status']!='ok':value+='<br>旧值，本轮未更新'
                if m.get('scope')=='branch_in_repository':value+='<br>整个仓库，非该分支单独数量'
                if m.get('delta') is not None:
                    before=dt.datetime.fromisoformat(m['compared_with']).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%m-%d %H:%M')
                    after=dt.datetime.fromisoformat(m['observed_at']).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime('%m-%d %H:%M')
                    value+='<br>{:+,}（{} → {}）'.format(m['delta'],before,after)
            cells.insert(2,value);line='| '+' | '.join(cells)+' |'
        lines.append(line)
    table_path.write_text('\n'.join(lines)+'\n')
    print(json.dumps(data['star_collection'],ensure_ascii=False),flush=True)

if __name__=='__main__':main()
