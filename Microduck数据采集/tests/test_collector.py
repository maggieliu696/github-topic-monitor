import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
import zlib

spec=importlib.util.spec_from_file_location('collector',Path(__file__).resolve().parents[1]/'collector.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=m.Store(self.root/'db.sqlite')
    def tearDown(self):
        self.store.db.close();self.tmp.cleanup()
    def record(self,body='original',status='open',**meta):
        return m.item('github','issue:1','issue','A question','https://github.com/a/b/issues/1',body,'author',status=status,**meta)
    def test_metric_changes_are_separate_from_substantive_changes(self):
        self.assertEqual(self.store.put('run1',self.record(stars=3)),'first_observed')
        self.assertEqual(self.store.put('run2',self.record(stars=5)),'metric_changed')
        self.assertEqual(len(self.store.rows('SELECT * FROM changes')),2)
        self.assertIsNone(self.store.put('run3',self.record(stars=5)))
    def test_fix_and_body_change_keep_previous_evidence(self):
        self.store.put('run1',self.record())
        self.assertEqual(self.store.put('run2',self.record('fixed',status='closed')),'changed')
        r=self.store.rows('SELECT * FROM changes WHERE run=?',('run2',))[0]
        self.assertEqual(json.loads(r['previous'])['body'],'original')
        self.assertEqual(json.loads(r['payload'])['status'],'closed')
    def test_cached_304_preserves_pagination(self):
        u='https://api.github.com/repos/a/b/issues'
        headers={'Link':'<https://api.github.com/repos/a/b/issues?page=2>; rel="next"'}
        self.store.db.execute('INSERT INTO cache VALUES(?,?,?,?,?)',(u,'abc',None,zlib.compress(b'[]'),json.dumps(headers)))
        self.store.db.commit()
        c=m.Client(self.store,self.root,{'github':10})
        class Opener:
            def open(self,*args,**kwargs):raise urllib.error.HTTPError(u,304,'not modified',{},None)
        c.opener=Opener()
        body,result=c.get('github',u)
        self.assertEqual(body,[]);self.assertEqual(result['Link'],headers['Link'])
    def test_pagination_cap_is_not_success(self):
        c=m.Client(self.store,self.root,{'github':10})
        c.get=lambda *a,**k:([{'id':1}],{'Link':'<https://api.github.com/next>; rel="next"'})
        with self.assertRaises(RuntimeError):list(c.pages('github','https://api.github.com/first',1))
        self.assertTrue(c.warnings)
    def test_failed_repo_does_not_advance_checkpoint(self):
        c=m.Client(self.store,self.root,{'github':10})
        def get(p,url,optional=False):
            if url.endswith('/readme'):return None,{}
            return {'id':1,'full_name':'a/b','html_url':'https://github.com/a/b','owner':{'login':'a'}},{}
        c.get=get
        def pages(*a,**k):
            yield []
            raise RuntimeError('incomplete pagination')
        c.pages=pages
        cfg={'github':{'repos':['a/b'],'queries':[],'repo_limit':2,'max_pages':1}}
        collector=m.Collector(self.store,c,cfg,'run');collector.github()
        self.assertIsNone(self.store.state('gh:checked:a/b'))
        self.assertEqual(collector.coverage['github']['completed_repositories'],0)
    def test_tier_file_controls_a_and_b_lists(self):
        tier_file=self.root/'tiers.json'
        tier_file.write_text(json.dumps({'projects':[{'repo':'a/deep','tier':'A'},{'repo':'b/light','tier':'B'}]}))
        cfg={'github':{'tier_file':str(tier_file),'background_repos':['official/base']}}
        # Absolute paths are supported in tests because pathlib joins preserve them.
        tiers=m.Collector(self.store,None,cfg,'run').github_tiers()
        self.assertEqual(tiers,{'a/deep':'A','b/light':'B','official/base':'A'})
    def test_star_growth_trigger_is_programmatic(self):
        cfg={'github':{}}
        col=m.Collector(self.store,None,cfg,'run')
        self.assertIsNone(col.star_trigger('a/b',10))
        self.store.set('gh:stars:a/b',[{'date':'2026-01-01','stars':10}])
        self.assertEqual(col.star_trigger('a/b',65)['reason'],'star_absolute_growth')
    def test_unexpected_host_blocked_before_request(self):
        c=m.Client(self.store,self.root,{'github':10})
        with self.assertRaises(ValueError):c.get('github','https://example.com/steal')
        self.assertEqual(c.counts['github'],0)
    def test_hf_hidden_comment_is_not_retained_as_visible(self):
        c=m.Client(self.store,self.root,{'huggingface':20})
        c.pages=lambda *a,**k:iter([[]])
        def get(p,u,optional=False):
            if '/resolve/' in u:return 'Readme',{}
            if '/discussions?' in u:return {'discussions':[{'num':1}],'count':1},{}
            if u.endswith('/discussions/1'):
                return {'title':'Help','status':'closed','events':[{'id':'e1','type':'comment','author':{'name':'a'},'data':{'hidden':True,'latest':{'raw':'hidden body'}}}]},{}
            return {'sha':'abc'},{}
        c.get=get
        cfg={'huggingface':{'repo_types':[],'queries':[],'repos':[['spaces','a/b']],'repo_limit':1,'discussion_pages':1}}
        m.Collector(self.store,c,cfg,'run').hf()
        record=json.loads(self.store.rows('SELECT payload FROM items WHERE kind=?',('discussion_comment',))[0][0])
        self.assertEqual(record['body'],'');self.assertEqual(record['status'],'hidden')

    def test_hf_page_limit_not_counted_complete(self):
        c=m.Client(self.store,self.root,{'huggingface':20})
        c.pages=lambda *a,**k:iter([[]])
        def get(p,u,optional=False):
            if '/resolve/' in u:return 'Readme',{}
            if '/discussions?' in u:return {'discussions':[],'count':3,'start':0},{}
            return {'sha':'abc'},{}
        c.get=get
        cfg={'huggingface':{'repo_types':[],'queries':[],'repos':[['spaces','a/b']],'repo_limit':1,'discussion_pages':1}}
        col=m.Collector(self.store,c,cfg,'run');col.hf()
        self.assertEqual(col.coverage['huggingface']['completed_repositories'],0)
        self.assertIsNone(self.store.state('hf:checked:spaces:a/b'))

if __name__=='__main__':unittest.main()
