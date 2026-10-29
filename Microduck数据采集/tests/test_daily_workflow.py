import base64
from contextlib import nullcontext
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))
import collector as C
import project_review as R
import sync_monitoring_tiers as T

spec=importlib.util.spec_from_file_location('ready_sender',SOURCE/'feishu/send_digest.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def repository(name='test/new', ident=1, fork=False):
    return dict(id=ident,full_name=name,html_url='https://github.com/'+name,owner={'login':'test'},
        description='Robot project',fork=fork,stargazers_count=10,forks_count=0,open_issues_count=0,
        updated_at='2026-10-27T00:00:00+00:00',pushed_at='2026-10-27T00:00:00+00:00',default_branch='main')


class Client:
    def __init__(self, repos):self.repos=repos;self.calls=[];self.tokens={'github':'offline-test'};self.warnings=[]
    def get(self,p,url,optional=False):
        self.calls.append(url)
        if url.endswith('/readme'):return {'encoding':'base64','content':base64.b64encode(b'Robot project explanation').decode()},{}
        return self.repos[url.split('/repos/')[1]],{}
    def pages(self,p,url,*a,**kw):
        self.calls.append(url)
        yield {'items':list(self.repos.values())} if '/search/' in url else []
    def warn(self,*args):self.warnings.append(args)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'Microduck数据采集';self.root.mkdir()
        self.store=C.Store(self.root/'data/research.sqlite3')
        (self.root/'selection').mkdir();(self.root/'selection/项目选择清单.json').write_text('{"rows":[]}')
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def collect(self, run, client, tiers=None):
        cfg={'github':{'queries':['microduck'],'search_pages':2,'repo_limit':1,'max_pages':5,'tracked_baseline_exists':True}}
        col=C.Collector(self.store,client,cfg,run);col.github_tiers=lambda:tiers or {};col.github();return col
    def test_new_project_gets_full_baseline_before_tiering(self):
        client=Client({'test/new':repository()});self.collect('one',client,{'test/new':'pending'})
        self.assertTrue(any(x.endswith('/readme') for x in client.calls))
        self.assertTrue(any('/issues?' in x for x in client.calls))
        self.assertTrue(self.store.pending_candidates()[0]['baseline_complete'])
        self.assertIsNotNone(self.store.state('gh:baseline:test/new'))
    def test_previous_signal_alone_cannot_skip_initialization(self):
        self.store.set('gh:signal:test/new',{k:repository().get(k) for k in ('pushed_at','updated_at','default_branch','archived','disabled')})
        client=Client({'test/new':repository()});self.collect('one',client,{'test/new':'pending'})
        self.assertTrue(any(x.endswith('/readme') for x in client.calls))
    def test_backlog_and_forks_survive_repeated_search(self):
        client=Client({'test/new':repository(),'test/fork':repository('test/fork',2,True)})
        one=self.collect('one',client);two=self.collect('two',client)
        self.assertEqual({x['repo'] for x in one.new_candidates},{'test/new','test/fork'})
        self.assertEqual({x['repo'] for x in two.new_candidates},{'test/new','test/fork'})
        self.assertEqual(two.coverage['github']['completed_repositories'],2)  # no silent repo_limit truncation
    def test_excluded_candidate_does_not_return_as_pending(self):
        client=Client({'test/new':repository()});self.collect('one',client)
        self.store.decide_candidate('test/new','excluded',{'reason':'not related'})
        self.assertEqual(self.collect('two',client).new_candidates,[])
    def test_old_cached_discovery_is_recovered(self):
        self.store.put('old',C.item('github','repo:1','repository_candidate','test/new','https://github.com/test/new'))
        client=Client({'test/new':repository()});col=self.collect('one',client)
        self.assertEqual(col.new_candidates[0]['repo'],'test/new')
    def test_failed_initialization_stays_pending(self):
        client=Client({'test/new':repository()})
        original=client.pages
        def pages(p,url,*a,**kw):
            if '/issues?' in url:raise RuntimeError('offline timeout')
            yield from original(p,url,*a,**kw)
        client.pages=pages;self.collect('one',client)
        self.assertFalse(self.store.pending_candidates()[0].get('baseline_complete',False))
        self.assertIsNone(self.store.state('gh:checked:test/new'))
    def test_seven_day_growth_ignores_older_history(self):
        today=dt.datetime.now(S.BEIJING).date()
        self.store.set('gh:stars:test/new',[{'date':(today-dt.timedelta(days=n)).isoformat(),'stars':v} for n,v in [(30,10),(7,100),(1,100)]])
        self.assertIsNone(C.Collector(self.store,None,{},'run').star_trigger('test/new',100))
    def test_missing_seven_day_observation_does_not_invent_growth(self):
        today=dt.datetime.now(S.BEIJING).date()
        self.store.set('gh:stars:test/new',[{'date':(today-dt.timedelta(days=30)).isoformat(),'stars':10}])
        self.assertIsNone(C.Collector(self.store,None,{},'run').star_trigger('test/new',16))
    def test_real_seven_day_growth_has_comparison_dates(self):
        today=dt.datetime.now(S.BEIJING).date();before=(today-dt.timedelta(days=7)).isoformat()
        self.store.set('gh:stars:test/new',[{'date':before,'stars':10}])
        alert=C.Collector(self.store,None,{},'run').star_trigger('test/new',16)
        self.assertEqual(alert['from_date'],before);self.assertEqual(alert['after'],16)
    def test_ranking_uses_latest_collected_stars(self):
        record=C.item('github','repo:1','repository_candidate','test/new','https://github.com/test/new',stars=29,stars_observed_at='2026-10-27T01:00:00+00:00')
        self.store.put('one',record)
        data={'rows':[{'github_stars':{'repository':'test/new','stars':10,'observed_at':'2026-10-26T01:00:00+00:00'}}]}
        result=T.refresh_stars(data,self.root/'data/research.sqlite3')['rows'][0]['github_stars']
        self.assertEqual(result['stars'],29);self.assertEqual(result['delta'],19)
        self.assertEqual(result['compared_with'],'2026-10-26T01:00:00+00:00')
    def decision(self):
        return dict(repo='test/new',status='accepted',reason='相关项目，完成初始化',sources=['https://github.com/test/new'],
            name='New robot',author='test',purpose='用于实验的机器人',current_state='仅在模拟环境验证',
            problems_and_resolutions='实体效果尚未验证',evaluation_and_limits='没有独立使用反馈',
            tier='B',tier_reason='早期项目，先轻量监控',direction='AI 应用与交互玩法',
            record_markdown='这是用于实验的机器人，目前只验证了模拟环境。实体效果尚未验证，没有独立使用反馈。\n\n[项目说明](https://github.com/test/new)')
    def test_cannot_accept_project_without_initialization_evidence(self):
        self.store.candidate('test/new',{})
        with self.assertRaises(ValueError):R.apply_decision(self.store,self.decision(),self.root)
        self.assertEqual(len(self.store.pending_candidates()),1)
    def test_initialization_creates_one_record_before_acceptance(self):
        self.collect('one',Client({'test/new':repository()}))
        decision=self.decision();R.apply_decision(self.store,decision,self.root);R.apply_decision(self.store,decision,self.root)
        self.assertEqual(len(list((self.root/'pilot/output/项目记录').glob('*.md'))),1)
        row=json.loads((self.root/'selection/项目选择清单.json').read_text())['rows'][0]
        self.assertTrue(row['already_initialized']);self.assertEqual(row['monitoring_tier'],'B')
        self.assertEqual(self.store.pending_candidates(),[])
    def test_uninitialized_project_is_not_given_a_tier(self):
        source=self.root/'selection/项目选择清单.json'
        source.write_text(json.dumps({'rows':[{'project_id':'P001','name':'test','direction':'AI 应用与交互玩法','github_stars':{'repository':'test/new','stars':10},'already_initialized':False}]}))
        row=T.build(source,database=self.root/'missing.sqlite')['projects'][0]
        self.assertIsNone(row['tier']);self.assertEqual(row['initialization_status'],'pending')


class DigestReadyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.today=dt.datetime.now(S.BEIJING).date();self.digest=self.root/'日报.md'
        self.markdown='🦆 调研日报｜'+self.today.isoformat()+'\n\n今天暂无重要新增。\n\n'+'\n\n'.join('**'+name+'：说明。**\n- 今天没有值得推送的新变化。' for name in S.SECTIONS)+'\n'
        self.run=self.root/'run-test';self.run.mkdir();self.db=self.root/'research.sqlite3'
        self.store=C.Store(self.db)
        t=(dt.datetime.now(S.BEIJING)-dt.timedelta(seconds=2)).isoformat()
        self.summary=dict(workflow_version=2,run=self.run.name,started=t,finished=t,errors=[],coverage={'github':{'planned_repositories':1,'completed_repositories':1}})
        (self.run/'summary.json').write_text(json.dumps(self.summary));self.digest.write_text(self.markdown)
        self.latest=self.root/'最新运行.json';self.latest.write_text(json.dumps({'directory':str(self.run)}))
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def approve(self):return S.approve_digest(self.digest,self.run,self.db,self.today,self.latest)
    def check(self):return S.validate_ready(self.digest,self.db,self.latest,self.today)
    def test_same_day_finished_report_can_be_approved_and_checked(self):
        self.approve();self.assertEqual(self.check()['status'],'ready')
    def test_missing_proof_cannot_be_sent(self):
        with self.assertRaises(ValueError):self.check()
    def test_legacy_collection_cannot_be_approved(self):
        self.summary.pop('workflow_version');(self.run/'summary.json').write_text(json.dumps(self.summary))
        with self.assertRaisesRegex(ValueError,'旧版采集'):self.approve()
    def test_pending_tier_list_cannot_be_approved_even_with_empty_database_queue(self):
        directory=self.db.parent.parent/'monitoring-tiers.json'
        # Put the list inside a separate collection directory matching production paths.
        collection=self.root/'collection';(collection/'data').mkdir(parents=True)
        other=C.Store(collection/'data/research.sqlite3')
        try:
            (collection/'monitoring-tiers.json').write_text(json.dumps({'projects':[{'repo':'test/pending','tier':None,'initialization_status':'pending'}]}))
            with self.assertRaisesRegex(ValueError,'未完成初始化'):S.candidate_progress(collection/'data/research.sqlite3')
        finally:other.db.close()
    def test_modified_report_invalidates_proof(self):
        self.approve();self.digest.write_text(self.markdown+'\n追加文字')
        with self.assertRaisesRegex(ValueError,'被修改'):self.check()
    def test_yesterday_report_is_rejected(self):
        yesterday=(self.today-dt.timedelta(days=1)).isoformat();self.digest.write_text(self.markdown.replace(self.today.isoformat(),yesterday))
        with self.assertRaises(ValueError):self.approve()
    def test_pending_candidate_prevents_completion(self):
        self.store.candidate('test/pending',{})
        with self.assertRaisesRegex(ValueError,'未处理'):self.approve()
    def test_new_pending_candidate_invalidates_approved_report(self):
        self.approve();self.store.candidate('test/pending',{})
        with self.assertRaises(ValueError):self.check()
    def test_incomplete_collection_cannot_be_approved(self):
        self.summary['coverage']['github']['completed_repositories']=0
        (self.run/'summary.json').write_text(json.dumps(self.summary))
        with self.assertRaises(ValueError):self.approve()
    def test_wrong_format_cannot_be_approved(self):
        self.digest.write_text(self.markdown.replace('**开发工具：说明。**','**其他：说明。**'))
        with self.assertRaises(ValueError):self.approve()
    def test_changed_run_summary_invalidates_proof(self):
        self.approve();self.summary['new_field']='changed';(self.run/'summary.json').write_text(json.dumps(self.summary))
        with self.assertRaises(ValueError):self.check()
    def test_live_send_refuses_before_reading_credentials(self):
        # This regression must never call a real credential helper or network request.
        with mock.patch.object(S,'ROOT',self.root),mock.patch.object(S,'research_lock',return_value=nullcontext()),mock.patch.object(S,'PREVIEW',self.root/'preview.json'),mock.patch.object(S,'append_log') as log,mock.patch.object(sys,'argv',['send_digest.py','--digest',str(self.digest)]),mock.patch.object(S,'credential') as credentials,mock.patch.object(S,'send') as send:
            with self.assertRaises(ValueError):S.main()
            credentials.assert_not_called();send.assert_not_called();log.assert_called_once()


if __name__=='__main__':unittest.main()
