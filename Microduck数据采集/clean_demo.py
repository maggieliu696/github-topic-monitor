#!/usr/bin/env python3
"""Lossless-source export plus conservative cleaning; no inferred opinions."""
import argparse, collections, hashlib, html, json, re, sqlite3, zlib
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DIRECTIONS={'动作训练与算法实验':'D01','开发工具与运行环境':'D02','AI 应用与交互玩法':'D03','硬件复刻与适配':'D04'}
class TextWithLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('p','br','div','li','pre'):self.parts.append('\n')
        if tag=='a':self.links.append(a.get('href',''))
    def handle_endtag(self,tag):
        if tag in ('p','div','li','pre'):self.parts.append('\n')
        if tag=='a' and self.links:
            href=self.links.pop()
            if href:self.parts.append(' ('+href+')')
    def handle_data(self,text):self.parts.append(text)
def text_html(raw):
    p=TextWithLinks();p.feed(raw);return ''.join(p.parts)
def tidy(raw):
    return re.sub(r'\n{3,}','\n\n','\n'.join(line.rstrip() for line in raw.replace('\r\n','\n').replace('\r','\n').split('\n'))).strip()
def project_key(url):
    url=url.split('#')[0].rstrip('/')
    m=re.match(r'https://github.com/([^/]+/[^/]+)',url)
    if m:return 'https://github.com/'+m[1].lower()
    m=re.match(r'https://huggingface.co/(spaces/[^/]+/[^/]+)',url)
    if m:return 'https://huggingface.co/'+m[1].lower()
    return None

def clean(db_path,out):
    out.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(db_path);db.row_factory=sqlite3.Row
    rows=list(db.execute('SELECT * FROM items ORDER BY platform,id'))
    cache={r['url']:r for r in db.execute('SELECT * FROM cache')}
    old=json.loads((ROOT.parent/'.cognitive-research/microduck-user-research/developers100/coded-projects.json').read_text())
    projects={project_key(p['url']):p for p in old if project_key(p['url'])}
    normalized={r['id']:json.loads(r['payload']) for r in rows}
    exported=[];audit=[];seen=set();raw_records=[]
    api_sources=[];parent_contexts={};hf_events={};github_releases={}
    for u,cached in cache.items():
        body=zlib.decompress(cached['body']).decode('utf-8')
        try:payload=json.loads(body)
        except ValueError:payload=body
        api_sources.append({'api_url':u,'payload':payload})
        if re.match(r'^https://api\.github\.com/repos/[^/]+/[^/]+/releases(?:\?|$)',u) and isinstance(payload,list):
            for x in payload:
                if isinstance(x,dict) and x.get('id') is not None:
                    github_releases['github:release:'+str(x['id'])]=x
        if u.startswith('https://api.github.com/repos/') and '/issues?' in u and isinstance(payload,list):
            for x in payload:
                parent_contexts[x['html_url']]={'title':x['title'],'text':x.get('body') or '', 'kind':'pull_request' if 'pull_request' in x else 'issue','url':x['html_url'],'author':x.get('user',{}).get('login')}
                if x.get('url'):parent_contexts[x['url'].replace('https://api.github.com/repos/','https://github.com/')]=parent_contexts[x['html_url']]
        if u.startswith('https://huggingface.co/api/') and re.search(r'/discussions/\d+$',u) and isinstance(payload,dict):
            comments=[e for e in payload.get('events',[]) if e.get('type')=='comment']
            public=u.replace('https://huggingface.co/api/','https://huggingface.co/')
            first=comments[0] if comments else {}
            data=first.get('data',{})
            parent_contexts[public]={'title':payload.get('title'),'text':'' if data.get('hidden') else (data.get('latest') or {}).get('raw',''),'kind':'discussion','url':public,'author':payload.get('author',{}).get('name')}
            for e in comments:hf_events[e['id']]=e
    (out/'API原始响应.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in api_sources))
    def thread_for(r):
        if r['platform']=='hackernews':
            cur=r;visited=set()
            while cur['meta'].get('parent') and cur['id'] not in visited:
                visited.add(cur['id']);parent=normalized.get('hackernews:'+str(cur['meta']['parent']))
                if not parent:break
                cur=parent
            return cur['url']
        parent=r['meta'].get('parent')
        if parent and parent.startswith('https://api.github.com/repos/'):
            return parent.replace('https://api.github.com/repos/','https://github.com/')
        return parent or (r['url'] if r['kind'] in ('issue','discussion') else None)
    for row in rows:
        r=normalized[row['id']];raw=r['body'];meta=r['meta'];raw_source='normalized_collector_body'
        published=meta.get('created_at');updated=r.get('source_updated_at')
        if r['platform']=='github' and r['kind']=='release':
            original=github_releases.get(r['id'])
            if original is not None:
                # The raw response is authoritative, including explicit/missing nulls.
                published=original.get('published_at');updated=original.get('updated_at')
            else:
                published=meta.get('published_at')
                # Legacy releases stored published_at in source_updated_at. Only the
                # new mapping writes this meta key, even when publication is unknown.
                updated=r.get('source_updated_at') if 'published_at' in meta else None
        if r['platform']=='huggingface' and ':event:' in r['id']:
            event=hf_events.get(r['id'].split(':event:')[-1],{})
            published=event.get('createdAt')
        if r['platform']=='github' and r['kind']=='issue_comment':
            for api in api_sources:
                if '/issues/comments?' in api['api_url'] and isinstance(api['payload'],list):
                    for original in api['payload']:
                        if str(original.get('id'))==r['id'].split(':')[-1]:published=original.get('created_at')
        if r['platform']=='hackernews':
            u='https://hacker-news.firebaseio.com/v0/item/'+r['id'].split(':')[-1]+'.json'
            if u in cache:
                obj=json.loads(zlib.decompress(cache[u]['body']));raw=obj.get('text','');raw_source='official_api_text_html'
            published=r.get('source_updated_at');updated=None
        raw_records.append({'record':r,'raw_text':raw,'raw_format':'html' if r['platform']=='hackernews' else 'markdown','raw_source':raw_source,'first_captured_at':row['first_seen'],'last_checked_at':row['last_seen']})
        body=tidy(text_html(raw) if r['platform']=='hackernews' else raw)
        reason=None
        if r['kind']=='repository_candidate':reason='项目元数据，用作索引，不单算研究正文'
        elif r['kind']=='discussion':reason='讨论标题和状态作为上下文，正文见具体评论'
        elif r['status'] in ('hidden','deleted','dead'):reason='不可见或删除内容，不作为有效正文'
        elif not body:reason='无正文，保留元数据和处理记录'
        dedup_key=(r['platform'],r['id'])
        if dedup_key in seen:reason='相同平台与记录编号重复'
        seen.add(dedup_key)
        if reason:
            audit.append({'id':r['id'],'action':'context_only','reason':reason,'source_url':r['url']});continue
        key=project_key(r['url']);p=projects.get(key)
        url=r['url']
        if r['platform']=='huggingface' and ':event:' in r['id']:url=url+'#'+r['id'].split(':event:')[-1]
        thread=thread_for(r)
        context=parent_contexts.get(thread)
        if context:thread=context['url']
        if r['platform']=='hackernews' and meta.get('parent'):
            parent=normalized.get('hackernews:'+str(meta['parent']))
            if parent:context={k:parent.get(k) for k in ('title','body','kind','url','author')}
        if r['kind']=='issue_comment' and context and context['kind']=='pull_request':record_type='pull_request_comment'
        else:record_type=r['kind']
        record={'record_id':r['id'],'platform':r['platform'],'record_type':record_type,'title':r['title'],'source_url':url,
            'author_handle':r['author'],'published_at':published,'updated_at':updated,
            'timestamp_note':('HN只提供发表时间，编辑时间未知' if r['platform']=='hackernews' else
                'Release发表与更新时间分别取published_at和updated_at；缺失保持null，created_at和采集时间不替代发表时间' if r['platform']=='github' and r['kind']=='release' else
                '缺失时间保持null；项目说明不把仓库更新时间当正文更新时间'),
            'first_captured_at':row['first_seen'],'last_checked_at':row['last_seen'],'source_status':('hidden' if r['status']=='hidden' else 'visible') if r['platform']=='huggingface' and r['kind']=='discussion_comment' else r['status'],'thread_status':meta.get('thread_status',r['status']) if r['platform']=='huggingface' and r['kind']=='discussion_comment' else None,
            'project_id':p['id'] if p else None,'direction_id':DIRECTIONS.get(p['primary_category']) if p else None,
            'classification_basis':'沿用前轮项目主分类' if p else '待人工归类；官方参考仓库和独立讨论不强行计作第三方项目',
            'project_url':key,'thread_url':thread,'parent_reference':meta.get('parent'),'parent_context':context,'context_complete':bool(context) if meta.get('parent') else True,
            'text':body,'text_sha256':hashlib.sha256(body.encode()).hexdigest(),
            'cleaning':['保留原文并另存清洗副本','统一换行与多余空行','HTML转文本保留链接' if r['platform']=='hackernews' else '保留Markdown代码、表格、链接'],
            'research_decision':'待阅读上下文后判断；正文有效不等于需要日报或改变结论'}
        exported.append(record);audit.append({'id':r['id'],'action':'cleaned_text','reason':'可读取正文；保留事实，不自动生成结论','source_url':url})
    for name,data in [('原始记录.json',raw_records),('清洗审计.json',audit)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (out/'清洗后信息.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in exported))
    summaries=[]
    for platform in ['github','huggingface','hackernews']:
        rs=[r for r in rows if r['platform']==platform];xs=[x for x in exported if x['platform']==platform]
        summaries.append({'platform':platform,'records_received':len(rs),'readable_text_records':len(xs),'context_only_records':len(rs)-len(xs),'types':dict(collections.Counter(x['record_type'] for x in xs))})
    summary={'scope':'选定来源的一次快照；数量是资料记录，不是项目数、用户数或当天新增量','platforms':summaries,'source_records':len(rows),'cleaned_text_records':len(exported),'context_only_records':len(rows)-len(exported),'new_research_conclusions':0,'automatic_sentiment_or_buyer_inference':False,'records_with_missing_parent_context':sum(bool(x['parent_reference']) and not x['context_complete'] for x in exported)}
    (out/'清洗统计.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    db.close();return summary
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=ROOT/'data-demo/research.sqlite3');p.add_argument('--out',type=Path,default=ROOT/'demo');a=p.parse_args();print(json.dumps(clean(a.db,a.out),ensure_ascii=False))
