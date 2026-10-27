#!/usr/bin/env python3
"""Read-only official API collector. Standard library only; no model API calls."""
import argparse
import base64
import concurrent.futures
import datetime as dt
import difflib
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # macOS/Linux
    msvcrt = None

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc
def now(): return dt.datetime.now(UTC).isoformat(timespec='seconds')
def dump(v): return json.dumps(v, ensure_ascii=False, sort_keys=True)
def plain(s): return html.unescape(re.sub('<[^>]+>', ' ', s or '')).strip()
def qs(p): return urllib.parse.urlencode(p)
def safe_title(s): return re.sub(r'[\n\r\[\]]', ' ', s or '')[:160]

def github_token():
    token=os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    if token:return token
    try:
        result=subprocess.run([
            'security','find-generic-password','-a','robotic-harness',
            '-s','robotic-harness-github-token','-w'
        ],capture_output=True,text=True,timeout=5,check=False)
        return result.stdout.strip() if result.returncode==0 else None
    except (FileNotFoundError,subprocess.TimeoutExpired):
        return None

# These fields are cheap for a program to compare and do not need model review.
METRIC_FIELDS = ('stars', 'forks', 'open_issues', 'watchers')

def record_fingerprint(item):
    """Stable fingerprint for human-authored substance only."""
    substance={k:item.get(k) for k in ('title','body','status','author','url','kind')}
    return hashlib.sha256(dump(substance).encode()).hexdigest()

def metric_snapshot(item):
    meta=item.get('meta') or {}
    return {k:meta.get(k) for k in METRIC_FIELDS if meta.get(k) is not None}

class StopPlatform(Exception): pass

def acquire_run_lock(handle):
    """Acquire a non-blocking single-process lock on macOS, Linux, or Windows."""
    try:
        if fcntl is not None:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        elif msvcrt is not None:
            handle.write('0');handle.flush();handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            raise RuntimeError('当前系统没有可用的文件锁实现')
    except (BlockingIOError,OSError):
        raise SystemExit('已有采集运行，本次退出以避免重复执行。')

class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,platform TEXT,kind TEXT,
          payload TEXT,hash TEXT,first_seen TEXT,last_seen TEXT);
        CREATE TABLE IF NOT EXISTS changes(run TEXT,id TEXT,kind TEXT,payload TEXT,previous TEXT,
          PRIMARY KEY(run,id));
        CREATE TABLE IF NOT EXISTS cache(url TEXT PRIMARY KEY,etag TEXT,modified TEXT,body BLOB,headers TEXT);
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,started TEXT,finished TEXT,summary TEXT);
        ''')
        self.db.commit()
    def state(self, k, default=None):
        with self.lock:
            r=self.db.execute('SELECT value FROM state WHERE key=?',(k,)).fetchone()
            return json.loads(r[0]) if r else default
    def set(self,k,v):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(k,dump(v)))
            self.db.commit()
    def put(self, run, item):
        # Counts and timestamps change without changing the author's substance.
        h=record_fingerprint(item)
        payload=dump(item)
        with self.lock:
            old=self.db.execute('SELECT * FROM items WHERE id=?',(item['id'],)).fetchone()
            previous=json.loads(old['payload']) if old else None
            if not old:
                change='first_observed'
            elif old['hash']!=h:
                change='changed'
            elif metric_snapshot(previous)!=metric_snapshot(item):
                change='metric_changed'
            else:
                change=None
            self.db.execute('INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?,?)',
                (item['id'],item['platform'],item['kind'],payload,h,old['first_seen'] if old else now(),now()))
            if change:
                self.db.execute('INSERT OR REPLACE INTO changes VALUES(?,?,?,?,?)',
                    (run,item['id'],change,payload,old['payload'] if old else None))
            self.db.commit()
        return change
    def rows(self,sql,args=()):
        with self.lock: return self.db.execute(sql,args).fetchall()

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old_host=urllib.parse.urlparse(req.full_url).hostname
        host=urllib.parse.urlparse(newurl).hostname
        if host not in {'api.github.com','huggingface.co','hacker-news.firebaseio.com'}:
            raise urllib.error.URLError('Blocked redirect outside official API/content hosts')
        result=super().redirect_request(req,fp,code,msg,headers,newurl)
        if result is not None and host!=old_host: result.remove_header('Authorization')
        return result

class Client:
    def __init__(self, store, run_dir, limits):
        self.store,self.run_dir,self.limits=store,run_dir,limits
        self.counts={k:0 for k in limits};self.errors=[];self.warnings=[]
        self.lock=threading.RLock();self.next_search=0
        self.opener=urllib.request.build_opener(Redirect())
        self.tokens={'github':github_token(),
                     'huggingface':os.getenv('HF_TOKEN')}
    def warn(self,platform,message):
        with self.lock:
            entry={'platform':platform,'message':message}
            if entry not in self.warnings:self.warnings.append(entry)
    def get(self, platform, url, optional=False):
        expected={'github':'api.github.com','huggingface':'huggingface.co','hackernews':'hacker-news.firebaseio.com'}
        if urllib.parse.urlparse(url).hostname!=expected[platform]: raise ValueError('Unexpected host')
        with self.lock:
            if self.counts[platform]>=self.limits[platform]: raise StopPlatform('已达本次请求预算')
            self.counts[platform]+=1
        if platform=='github' and '/search/' in url:
            delay=max(0,self.next_search-time.monotonic())
            if delay:time.sleep(delay)
            self.next_search=time.monotonic()+6.2
        cached=self.store.rows('SELECT * FROM cache WHERE url=?',(url,))
        cached=cached[0] if cached else None
        headers={'User-Agent':'MicroduckResearch/0.1 (public-read-only)', 'Accept':'application/json'}
        if self.tokens.get(platform): headers['Authorization']='Bearer '+self.tokens[platform]
        if cached and cached['etag']: headers['If-None-Match']=cached['etag']
        if cached and cached['modified']: headers['If-Modified-Since']=cached['modified']
        status=0; body=None; response_headers={}
        try:
            with self.opener.open(urllib.request.Request(url,headers=headers),timeout=25) as response:
                status=response.status;response_headers=dict(response.headers)
                body=response.read(8_000_001)
                if len(body)>8_000_000:raise ValueError('Response exceeds 8MB limit')
                with self.store.lock:
                    self.store.db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?,?,?)',
                      (url,response.headers.get('ETag'),response.headers.get('Last-Modified'),zlib.compress(body),dump(response_headers)))
                    self.store.db.commit()
                if platform=='github' and int(response.headers.get('X-RateLimit-Remaining','100'))<=2:
                    # Permit processing this successful response, then stop the next request.
                    self.limits[platform]=self.counts[platform]
                    self.warn(platform,'GitHub剩余额度低，已停止后续请求；需只读Token提高免费额度。')
        except urllib.error.HTTPError as exc:
            status=exc.code
            if exc.code==304 and cached:
                body=zlib.decompress(cached['body']);response_headers=json.loads(cached['headers'])
            elif optional and exc.code in (404,410):
                self.warn(platform,f'资源暂不可读取（HTTP {exc.code}）：{url}')
            else:
                entry={'platform':platform,'url':url,'status':exc.code,'error':exc.reason}
                with self.lock:self.errors.append(entry)
                if exc.code in (403,429):raise StopPlatform(f'HTTP {exc.code}，停止本平台请求，不绕过访问限制')
                raise
        except Exception as exc:
            with self.lock:self.errors.append({'platform':platform,'url':url,'error':str(exc)})
            raise
        finally:
            with self.lock:
                with (self.run_dir/'requests.jsonl').open('a') as f:
                    f.write(dump({'at':now(),'platform':platform,'url':url,'status':status,'bytes':len(body) if body else 0})+'\n')
        if body is None:return None,{}
        text=body.decode('utf-8',errors='replace')
        try:return json.loads(text),response_headers
        except json.JSONDecodeError:return text,response_headers
    def pages(self,p,url,max_pages=5,optional=False,strict=True):
        for _ in range(max_pages):
            data,headers=self.get(p,url,optional)
            if data is None:return
            yield data
            link=next((v for k,v in headers.items() if k.lower()=='link'),'')
            nxt=re.search(r'<([^>]+)>;\s*rel="next"',link)
            if not nxt:return
            url=nxt.group(1)
        self.warn(p,'分页达到上限，未宣称全量覆盖：'+url)
        if strict:raise RuntimeError('分页未完成，不推进该来源的成功检查时间')

def item(platform,key,kind,title,url,body='',author='',updated=None,status='',**meta):
    return dict(id=f'{platform}:{key}',platform=platform,kind=kind,title=title or '',url=url,
                body=body or '',author=author or '',source_updated_at=updated,status=status,meta=meta)

class Collector:
    def __init__(self,store,client,config,run):
        self.s,self.c,self.cfg,self.run=store,client,config,run
        self.coverage={};self.seen=set();self.new_candidates=[];self.tier_review=[]
    def put(self,record):
        change=self.s.put(self.run,record);self.seen.add(record['id']);return change
    def github_tiers(self):
        path=ROOT/self.cfg['github'].get('tier_file','monitoring-tiers.json')
        data=json.loads(path.read_text()) if path.exists() else {'projects':[]}
        tiers={x['repo']:x.get('tier','B') for x in data.get('projects',[])}
        for repo in self.cfg['github'].get('background_repos',[]):tiers.setdefault(repo,'A')
        if not tiers:tiers.update({r:'A' for r in self.cfg['github'].get('repos',[])})
        return tiers
    def star_trigger(self,repo,stars):
        if stars is None:return None
        key='gh:stars:'+repo;history=self.s.state(key,[])
        today=dt.datetime.now(UTC).date().isoformat()
        history=[x for x in history if x.get('date')!=today]
        prior=history[-1]['stars'] if history else stars
        history.append({'date':today,'stars':stars});history=history[-35:]
        self.s.set(key,history)
        if stars-prior>=50:return {'reason':'star_absolute_growth','before':prior,'after':stars}
        cutoff=dt.datetime.now(UTC).date()-dt.timedelta(days=7)
        old=next((x for x in history if dt.date.fromisoformat(x['date'])<=cutoff),None)
        if old and stars-old['stars']>=5 and stars>old['stars']*1.2:
            return {'reason':'star_7d_growth','before':old['stars'],'after':stars}
        return None
    def github(self):
        p='github';tiers=self.github_tiers();seeds=list(tiers);discovered={}
        for query in self.cfg['github']['queries']:
            url='https://api.github.com/search/repositories?'+qs({'q':query,'sort':'updated','per_page':100})
            for page in self.c.pages(p,url,self.cfg['github']['search_pages'],strict=False):
                if page.get('incomplete_results'):self.c.warn(p,'GitHub搜索返回incomplete_results，候选发现不完整。')
                for r in page['items']:
                    discovered[r['full_name']]=r
                    change=self.put(item(p,'repo:'+str(r['id']),'repository_candidate',r['full_name'],r['html_url'],
                        r.get('description'),r['owner']['login'],r.get('updated_at'),
                        fork=r.get('fork'),created_at=r.get('created_at'),stars=r.get('stargazers_count'),stars_observed_at=now(),
                        interpretation='关键词候选，不自动纳入独立项目或买家统计'))
                    if change=='first_observed' and r['full_name'] not in tiers and not r.get('fork'):
                        self.new_candidates.append({'repo':r['full_name'],'url':r['html_url'],'description':r.get('description'),
                            'author':r['owner']['login'],'stars':r.get('stargazers_count'),'reason':'首次搜索到，待去重和相关性判断'})
        names=sorted(seeds,key=lambda r:(0 if tiers[r]=='A' else 1,self.s.state('gh:checked:'+r,''),r))
        self.coverage[p]={'planned_repositories':len(names),'seed_repositories':len(seeds),'completed_repositories':0,
                          'a_repositories':sum(x=='A' for x in tiers.values()),'b_repositories':sum(x=='B' for x in tiers.values()),
                          'discovered_candidates':len(discovered),'new_candidates_to_classify':len(self.new_candidates),
                          'authenticated':bool(self.c.tokens.get(p))}
        for repo in names[:self.cfg['github']['repo_limit']]:
            start=now();last=self.s.state('gh:checked:'+repo)
            try:
                url='https://api.github.com/repos/'+repo
                r=discovered.get(repo)
                if r is None:r,_=self.c.get(p,url,optional=True)
                if not r:continue
                repo_change=self.put(item(p,'repo:'+str(r['id']),'repository_candidate',r['full_name'],r['html_url'],
                    r.get('description'),r['owner']['login'],r.get('updated_at'),fork=r.get('fork'),created_at=r.get('created_at'),
                    stars=r.get('stargazers_count'),forks=r.get('forks_count'),open_issues=r.get('open_issues_count'),
                    watchers=r.get('subscribers_count'),stars_observed_at=now()))
                star_alert=self.star_trigger(repo,r.get('stargazers_count'))
                if star_alert:self.tier_review.append({'repo':repo,'tier':tiers[repo],**star_alert})

                # First compare the inexpensive repository signal. If neither code nor repository
                # metadata changed, the expensive README/issues/comments/releases scan is skipped.
                signal={k:r.get(k) for k in ('pushed_at','updated_at','default_branch','archived','disabled')}
                signal_key='gh:signal:'+repo
                previous_signal=self.s.state(signal_key)
                # The tracked repositories already have readable baseline dossiers. On the first
                # incremental run, establish their machine baseline without asking the model to
                # reread all historical content.
                if previous_signal is None and repo in seeds and self.cfg['github'].get('tracked_baseline_exists',False):
                    self.s.set(signal_key,signal)
                    self.s.set('gh:checked:'+repo,start)
                    self.coverage[p]['completed_repositories']+=1
                    self.coverage[p]['baselines_initialized']=self.coverage[p].get('baselines_initialized',0)+1
                    continue
                if previous_signal==signal:
                    self.s.set('gh:checked:'+repo,start)
                    self.coverage[p]['completed_repositories']+=1
                    self.coverage[p]['skipped_unchanged_repositories']=self.coverage[p].get('skipped_unchanged_repositories',0)+1
                    continue
                readme,_=self.c.get(p,url+'/readme',optional=True)
                if readme and readme.get('encoding')=='base64':
                    body=base64.b64decode(readme['content']).decode('utf-8',errors='replace')
                    readme_change=self.put(item(p,'readme:'+str(r['id']),'project_readme',repo,readme.get('html_url',r['html_url']),
                        body,r['owner']['login'],None,sha=readme.get('sha'),seed=repo in seeds))
                    if tiers[repo]=='B' and readme_change in ('first_observed','changed'):
                        self.tier_review.append({'repo':repo,'tier':'B','reason':'readme_changed','url':readme.get('html_url',r['html_url'])})
                # B 级不日常扫描 Issue、评论和 Release。触发后才进入升级审查。
                if tiers[repo]=='B':
                    if repo_change=='changed':self.tier_review.append({'repo':repo,'tier':'B','reason':'repository_changed','url':r['html_url']})
                    self.s.set('gh:checked:'+repo,start);self.s.set(signal_key,signal)
                    self.coverage[p]['completed_repositories']+=1
                    self.coverage[p]['b_light_checks']=self.coverage[p].get('b_light_checks',0)+1
                    continue
                params={'state':'all','sort':'updated','direction':'desc','per_page':100}
                if last:params['since']=(dt.datetime.fromisoformat(last)-dt.timedelta(days=1)).isoformat()
                for page in self.c.pages(p,url+'/issues?'+qs(params),self.cfg['github']['max_pages']):
                    for x in page:
                        kind='pull_request' if 'pull_request' in x else 'issue'
                        self.put(item(p,'issue:'+str(x['id']),kind,x['title'],x['html_url'],x.get('body'),
                            x['user']['login'],x.get('updated_at'),x['state'],repo=repo,created_at=x.get('created_at')))
                comments={k:v for k,v in params.items() if k!='state'}
                for page in self.c.pages(p,url+'/issues/comments?'+qs(comments),self.cfg['github']['max_pages']):
                    for x in page:self.put(item(p,'comment:'+str(x['id']),'issue_comment',repo+' 的回复',x['html_url'],
                        x.get('body'),x['user']['login'],x.get('updated_at'),repo=repo,parent=x.get('issue_url')))
                for page in self.c.pages(p,url+'/releases?per_page=100',1):
                    for x in page:self.put(item(p,'release:'+str(x['id']),'release',x.get('name') or x['tag_name'],
                        x['html_url'],x.get('body'),x.get('author',{}).get('login'),x.get('updated_at'),
                        repo=repo,published_at=x.get('published_at'),created_at=x.get('created_at')))
                self.s.set('gh:checked:'+repo,start)
                self.s.set(signal_key,signal)
                self.coverage[p]['completed_repositories']+=1
            except StopPlatform:raise
            except Exception:continue
        pending=len(names)-self.coverage[p]['completed_repositories']
        if pending:self.c.warn(p,f'本轮仍有{pending}个候选/种子仓库未完成全部端点检查；下轮优先续采。')

    def hf(self):
        p='huggingface';repos={}
        for typ in self.cfg['huggingface']['repo_types']:
            for term in self.cfg['huggingface']['queries']:
                for page in self.c.pages(p,'https://huggingface.co/api/'+typ+'?'+qs({'search':term,'limit':100,'sort':'lastModified','direction':-1}),3,strict=False):
                    for r in page:
                        name=r.get('id') or r.get('modelId');repos[(typ,name)]=r
        for typ,name in self.cfg['huggingface']['repos']:repos.setdefault((typ,name),{})
        keys=sorted(repos,key=lambda k:(self.s.state('hf:checked:'+':'.join(k),''),0 if k[1].startswith('pollen-robotics/') else 1,k))
        self.coverage[p]={'discovered_repositories':len(keys),'completed_repositories':0}
        for typ,name in keys[:self.cfg['huggingface']['repo_limit']]:
            start=now();api='https://huggingface.co/api/'+typ+'/'+name
            public='https://huggingface.co/'+(typ+'/' if typ!='models' else '')+name
            try:
                r,_=self.c.get(p,api,optional=True)
                if not r:continue
                self.put(item(p,typ+':'+name,'repository_candidate',name,public,'',name.split('/')[0],
                    r.get('lastModified'),repo_type=typ,sha=r.get('sha'),created_at=r.get('createdAt'),
                    interpretation='可能是配套模型/数据集，不独立计为开发项目'))
                body,_=self.c.get(p,public+'/resolve/main/README.md',optional=True)
                if isinstance(body,str):self.put(item(p,typ+':'+name+':readme','project_readme',name,public+'/blob/main/README.md',body,
                    name.split('/')[0],None,sha=r.get('sha'),repo_type=typ))
                complete=True
                for n in range(self.cfg['huggingface']['discussion_pages']):
                    listing,_=self.c.get(p,api+'/discussions?'+qs({'p':n}),optional=True)
                    if not listing:break
                    for discussion in listing.get('discussions',[]):
                        num=discussion['num'];detail,_=self.c.get(p,api+'/discussions/'+str(num),optional=True)
                        if not detail:
                            complete=False
                            self.c.warn(p,'讨论详情未取得：'+name+' #'+str(num))
                            continue
                        u=public+'/discussions/'+str(num)
                        self.put(item(p,typ+':'+name+':discussion:'+str(num),'discussion',detail['title'],u,'',
                            detail.get('author',{}).get('name'),detail.get('createdAt'),detail.get('status','')))
                        for event in detail.get('events',[]):
                            if event.get('type')!='comment':continue
                            data=event.get('data',{});latest=data.get('latest') or {}
                            hidden=data.get('hidden',False)
                            self.put(item(p,typ+':'+name+':event:'+event['id'],'discussion_comment',detail['title'],u,
                                '' if hidden else latest.get('raw',''),event.get('author',{}).get('name'),
                                latest.get('updatedAt') or event.get('createdAt'),'hidden' if hidden else 'visible',parent=u,thread_status=detail.get('status',''),created_at=event.get('createdAt')))
                    if listing.get('start',0)+len(listing.get('discussions',[]))>=listing.get('count',0):break
                else:
                    complete=False;self.c.warn(p,'讨论分页达到上限：'+name)
                if complete:
                    self.s.set('hf:checked:'+typ+':'+name,start)
                    self.coverage[p]['completed_repositories']+=1
            except StopPlatform:raise
            except Exception:continue
        if len(keys)>self.coverage[p]['completed_repositories']:self.c.warn(p,'部分Hugging Face仓库待续采，见覆盖统计。')

    def hn(self):
        p='hackernews';base='https://hacker-news.firebaseio.com/v0/'
        new,_=self.c.get(p,base+'newstories.json')
        selected=new[:self.cfg['hackernews']['new_story_limit']]
        tracked=set(self.s.state('hn:tracked',self.cfg['hackernews']['stories']))
        checked=set();root_map={}
        def fetch(n):
            try:return n,self.c.get(p,base+f'item/{n}.json')[0]
            except StopPlatform as e:return n,{'_error':str(e)}
            except Exception as e:return n,{'_error':str(e)}
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for n,data in pool.map(fetch,selected):
                if data and '_error' not in data and any(term.casefold() in (str(data.get('title',''))+' '+str(data.get('text',''))+' '+str(data.get('url',''))).casefold() for term in self.cfg['hackernews']['keywords']):
                    tracked.add(n);root_map[n]=data
        self.s.set('hn:tracked',sorted(tracked))
        self.coverage[p]={'discovery_window_returned':len(new),'new_story_ids_checked':len(selected),
            'tracked_stories':len(tracked),'thread_items_read':0,'discovery_complete':False}
        self.c.warn(p,f'HN新帖发现仅检查官方最新窗口中的{len(selected)}条，不是全站关键词穷尽；已知主题另回查评论树。')
        frontier=list(tracked);failures=0
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            while frontier:
                batch=[n for n in frontier if n not in checked];frontier=[]
                if not batch:break
                # Process cached discovered roots as well; all discussion descendants remain separate evidence.
                for n,data in pool.map(fetch,batch):
                    checked.add(n)
                    if not data or '_error' in data:failures+=1;continue
                    self.coverage[p]['thread_items_read']+=1
                    state='deleted' if data.get('deleted') else ('dead' if data.get('dead') else 'visible')
                    title=data.get('title') or f'Hacker News 评论 {n}'
                    self.put(item(p,str(n),data.get('type','comment'),title,f'https://news.ycombinator.com/item?id={n}',
                        plain(data.get('text')) if state=='visible' else '',data.get('by'),
                        dt.datetime.fromtimestamp(data['time'],UTC).isoformat() if data.get('time') else None,state,
                        parent=data.get('parent'),external_url=data.get('url'),score=data.get('score'),
                        timestamp_meaning='发表时间，不是编辑时间'))
                    frontier.extend(data.get('kids',[]))
                if self.c.counts[p]>=self.c.limits[p]:
                    if frontier:self.c.warn(p,'HN请求预算用尽，评论树尚未读取完整；下轮回查。')
                    break
        self.coverage[p]['failed_items']=failures

def write_outputs(store,client,collector,run_dir,run,start):
    changes=[dict(r) for r in store.rows('SELECT * FROM changes WHERE run=?',(run,))]
    queue=[]
    for row in changes:
        current=json.loads(row['payload']);prev=json.loads(row['previous']) if row['previous'] else None
        entry={'change':row['kind'],'record':current,
               'needs_agent_review':row['kind'] in ('first_observed','changed') and current.get('kind')!='repository_candidate'}
        if prev:
            entry['previous_status']=prev.get('status')
            entry['body_diff']='\n'.join(difflib.unified_diff(prev.get('body','').splitlines(),current.get('body','').splitlines(),n=3))[:8000]
            before,after=metric_snapshot(prev),metric_snapshot(current)
            if before!=after:entry['metric_changes']={k:{'before':before.get(k),'after':after.get(k)} for k in set(before)|set(after) if before.get(k)!=after.get(k)}
        queue.append(entry)
    (run_dir/'changes.json').write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n')
    agent_queue=[x for x in queue if x['needs_agent_review']]
    (run_dir/'agent-review-queue.json').write_text(json.dumps(agent_queue,ensure_ascii=False,indent=2)+'\n')
    (run_dir/'new-project-candidates.json').write_text(json.dumps(collector.new_candidates,ensure_ascii=False,indent=2)+'\n')
    (run_dir/'tier-review-queue.json').write_text(json.dumps(collector.tier_review,ensure_ascii=False,indent=2)+'\n')
    totals={p:len([x for x in queue if x['record']['platform']==p]) for p in client.counts}
    stats={'run':run,'started':start,'finished':now(),'requests':client.counts,'changes_by_platform':totals,
           'first_observed':sum(x['change']=='first_observed' for x in queue),'changed':sum(x['change']=='changed' for x in queue),
           'metric_changed':sum(x['change']=='metric_changed' for x in queue),'agent_review_items':len(agent_queue),
           'records_seen':len(collector.seen),'new_candidates_to_classify':len(collector.new_candidates),
           'tier_review_items':len(collector.tier_review),'coverage':collector.coverage,'warnings':client.warnings,'errors':client.errors,
           'interpretation':'首次入库不等于当天新发布；关键词候选不等于独立项目、买家或真实用户；未执行作者项目。'}
    (run_dir/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    with store.lock:
        store.db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?)',(run,start,stats['finished'],dump(stats)))
        store.db.commit()
    lines=['# Microduck 采集运行记录','',f'采集时间：{start} 至 {stats["finished"]}（UTC）','',
        f'本轮检查并入库 {stats["records_seen"]} 条内容，首次入库 {stats["first_observed"]} 条，正文或状态变化 {stats["changed"]} 条，需 Agent 阅读 {stats["agent_review_items"]} 条。',
        '首次入库包括历史资料；以下数量不是项目数或买家数。','',
        '| 平台 | 请求数 | 首次入库及变化记录 |','|---|---:|---:|']
    lines += [f'| {p} | {client.counts[p]} | {totals[p]} |' for p in client.counts]
    lines += ['','## 覆盖情况','', '```json',json.dumps(collector.coverage,ensure_ascii=False,indent=2),'```','', '## 待处理情况','']
    lines += [f'- {x["platform"]}：{x["message"]}' for x in client.warnings] or ['- 没有记录到覆盖警告。']
    lines += [f'- 访问失败：{x["platform"]} {x.get("status","")} {x.get("url","")}' for x in client.errors]
    lines += ['','## 优先阅读的原文','']
    substantive=[x for x in queue if x['record']['body'] and x['record']['kind']!='repository_candidate']
    substantive.sort(key=lambda x:(0 if x['change']=='changed' else 1,0 if 'comment' in x['record']['kind'] or x['record']['kind']=='issue' else 1))
    for x in substantive[:30]:
        r=x['record'];lines += [f'- [{safe_title(r["title"])}]({r["url"]}) · {r["platform"]} · '+('内容变化' if x['change']=='changed' else '首次入库')]
    lines += ['','全部机械差异见 changes.json；只交给 Agent 的增量见 agent-review-queue.json。研究结论须阅读原文后形成，程序未自动推断满意度或购买状态。','']
    (run_dir/'采集记录.md').write_text('\n'.join(lines))
    (ROOT/'最新运行.json').write_text(json.dumps({'run':run,'directory':str(run_dir),'summary':str(run_dir/'summary.json')},ensure_ascii=False,indent=2)+'\n')
    return stats

def active_platforms(value):
    platforms = [p.strip() for p in value.split(',') if p.strip()]
    if platforms != ['github']:
        raise ValueError('当前项目仅监控 GitHub；其他平台由后续独立工具接入。')
    return platforms


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--platforms',default='github')
    parser.add_argument('--config',type=Path,default=ROOT/'config.json');parser.add_argument('--data-dir',type=Path,default=ROOT/'data')
    args=parser.parse_args();cfg=json.loads(args.config.read_text())
    try: platforms=active_platforms(args.platforms)
    except ValueError as exc: raise SystemExit(str(exc))
    if not cfg.get('execution',{}).get('enabled',False):
        raise SystemExit('研究范围与推送格式已确认；当前配置未启用采集，自动流程仍待接通。')
    args.data_dir.mkdir(parents=True,exist_ok=True)
    lock=(args.data_dir/'collector.lock').open('w')
    acquire_run_lock(lock)
    run=dt.datetime.now(UTC).strftime('%Y%m%dT%H%M%S')+'-'+os.urandom(3).hex();start=now()
    run_dir=ROOT/'runs'/run;run_dir.mkdir(parents=True)
    s=Store(args.data_dir/'research.sqlite3')
    limits={'github':cfg['github']['max_requests'] if github_token() else min(60,cfg['github']['max_requests']),
        'huggingface':cfg['huggingface']['max_requests'],'hackernews':cfg['hackernews']['max_requests']}
    c=Client(s,run_dir,limits);collector=Collector(s,c,cfg,run)
    for p in platforms:
        if p not in limits:raise SystemExit('Unsupported platform: '+p)
        print('开始 '+p,flush=True)
        try:getattr(collector,{'github':'github','huggingface':'hf','hackernews':'hn'}[p])()
        except StopPlatform as exc:c.warn(p,str(exc))
        except Exception as exc:c.warn(p,'本平台未完整结束：'+str(exc))
        print('结束 '+p+' '+dump(collector.coverage.get(p,{})),flush=True)
    stats=write_outputs(s,c,collector,run_dir,run,start)
    print(dump({'run_directory':str(run_dir),'records_seen':stats['records_seen'],'warnings':len(c.warnings),'errors':len(c.errors)}),flush=True)
    return 2 if c.errors or c.warnings else 0

if __name__=='__main__':raise SystemExit(main())
