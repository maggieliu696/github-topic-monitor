import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

SPEC = importlib.util.spec_from_file_location('pipeline', Path(__file__).resolve().parents[1] / 'pipeline.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)
NOW = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.records_path, self.raw = self.root / 'records.jsonl', self.root / 'raw.jsonl'
        self.anns, self.out = self.root / 'annotations', self.root / 'output'
        self.anns.mkdir()
        self.rows = [dict(record_id='github:readme:1', project_id='P160', platform='github', record_type='project_readme', title='Description', source_url='https://example.org/project', author_handle='maker', published_at=None, updated_at=None, first_captured_at='2026-10-26T06:00:00Z', last_checked_at='2026-10-26T06:00:00Z', text='Author says GPU tested; video and setup docs linked.', parent_context=None),
                     dict(record_id='github:comment:2', project_id='P160', platform='github', record_type='issue_comment', title='GPU report', source_url='https://example.org/issue/1', author_handle='user', published_at='2026-09-01T00:00:00Z', updated_at=None, first_captured_at='2026-10-26T06:00:01Z', last_checked_at='2026-10-26T06:00:01Z', text='Still no GPU load on my setup.', parent_context={'title': 'GPU not used', 'text': 'The original problem in full.'})]
        self.a = dict(project_id='P160', project_name='duck-on-desk', author_name='maker', direction_id='D03', direction_name='AI应用与交互玩法', branch_label='桌面应用', purpose='Respond to coding state', current_conclusion='Two source statements cannot be reconciled yet.', discovered_problems='GPU reports differ and test conditions unknown.', reviewed_on='2026-10-26', sections=[{'title':'结果与问题', 'items':[{'id':'F01','text':'Author says tested', 'evidence_ids':['github:readme:1'],'evidence_kind':'author_claim'}, {'id':'F02','text':'User says failed', 'evidence_ids':['github:comment:2'],'evidence_kind':'user_report'}, {'id':'F03','text':'Whether user retested is unknown','evidence_ids':[],'evidence_kind':'unknown'}]}], conclusions=[{'id':'C1','text':'Evidence conflicts; conditions unknown','evidence_ids':['github:readme:1','github:comment:2'],'scope':'Only this project','status':'待验证'}], daily_candidates=[{'id':'D1','title':'GPU needs verification','summary':'Author and user reports differ.','reason':'Need conditions to resolve.','human_review':True,'evidence_ids':['github:readme:1','github:comment:2'],'conclusion_ids':['C1']}], coverage={'reviewed_record_ids':['github:readme:1','github:comment:2'],'unread_links':[{'url':'https://example.org/video','reason':'not inspected'}],'limitations':['No reproduction.']})
        self.raw.write_text('{"api_url":"https://example.org","payload":{"body":"full original"}}\n')
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        self.records_path.write_text(''.join(json.dumps(r) + '\n' for r in self.rows))
        (self.anns / 'P160.json').write_text(json.dumps(self.a))

    def run_pilot(self):
        return P.run(self.records_path,self.raw,self.anns,self.out,('P160',),NOW)

    def state(self):
        return P.load(self.out / 'state.json')['projects']['P160']

    def test_baseline_preserves_original_unknown_and_counterevidence(self):
        r = self.run_pilot()
        self.assertEqual(r['daily_item_count'], 1)
        self.assertEqual(r['review_queue_count'], 0)
        self.assertEqual((self.out / r['inputs']['raw_archive']).read_bytes(),self.raw.read_bytes())
        accepted = self.state()['accepted']
        self.assertEqual(len(accepted['annotation']['sections'][0]['items']), 3)
        for rid, ref in accepted['evidence_manifest'].items():
            original=P.load(self.out / ref['archive_path'])
            self.assertEqual(original, next(x for x in self.rows if x['record_id']==rid))
        original = P.load(self.out / accepted['evidence_manifest']['github:comment:2']['archive_path'])
        self.assertIn('original problem in full', original['parent_context']['text'])
        self.assertIsNone(P.load(self.out / accepted['evidence_manifest']['github:readme:1']['archive_path'])['published_at'])
        self.assertEqual(r['mode'], 'offline_snapshot')
        self.assertFalse(r['network_refreshed'])
        self.assertEqual(list((self.out/'projects').glob('**/*.md')), [])
        self.assertFalse((self.out/'运行记录.md').exists())
        self.assertIn('需补写团队版摘要', (self.out/'日报.md').read_text())

    def test_identical_second_run_has_no_duplicate_versions_events_or_digest_items(self):
        self.run_pilot(); first=copy.deepcopy(self.state())
        r=self.run_pilot(); second=self.state()
        self.assertEqual(r['daily_item_count'],0)
        self.assertEqual(r['research_question_count'],1)
        self.assertEqual(len(P.load(self.out/'研究待核实事项.json')),1)
        self.assertIn('[团队日报](日报.md)',(self.out/'索引.md').read_text())
        self.assertIn('[Duck on Desk](<项目记录/Duck on Desk.md>)',(self.out/'索引.md').read_text())
        self.assertNotIn('资料维护',(self.out/'索引.md').read_text())
        self.assertNotIn('projects/',(self.out/'索引.md').read_text())
        self.assertEqual(r['new_source_records_or_changes'],0)
        self.assertEqual(first['versions'],second['versions'])
        self.assertEqual(first['events'],second['events'])
        self.assertEqual(len(list((self.out/'runs').glob('*/日报.md'))),2)

    def test_check_timestamp_only_is_not_substantive_change(self):
        self.run_pilot()
        self.rows[0]['last_checked_at']='2026-10-26T07:00:00Z';self.save()
        r=self.run_pilot()
        self.assertEqual(r['new_source_records_or_changes'],0)
        self.assertEqual(r['daily_item_count'],0)
        self.assertEqual(r['review_queue_count'],0)

    def test_changed_evidence_requires_explicit_re_review_digest(self):
        self.run_pilot(); original=self.state()['accepted']
        self.rows[0]['text']='CUDA supported on tested hardware now.';self.save()
        r=self.run_pilot()
        self.assertEqual(r['daily_item_count'],0)
        self.assertEqual(self.state()['accepted'],original)
        q=P.load(self.out/'审核队列.json')
        self.assertEqual(q[0]['type'],'evidence_changed_review_required')
        # Editing prose alone cannot claim the fresh source was reviewed.
        self.a['current_conclusion']='Changed interpretation';self.save()
        self.assertEqual(self.run_pilot()['daily_item_count'],0)
        self.a['reviewed_source_digest']=q[0]['reviewed_source_digest']
        self.a['revision_reason']='Author added hardware-specific test conditions, but user retest is not confirmed.'
        self.a['conclusions'][0]['text']='CUDA author-claimed, user retest unknown'
        self.a['daily_candidates'][0]['summary']='Author now provides a hardware-specific claim.';self.save()
        self.assertEqual(self.run_pilot()['daily_item_count'],1)
        self.assertEqual(len(self.state()['versions']),2)
        self.assertTrue((self.out/self.state()['versions'][0]).exists())
        v=self.state()['accepted']
        self.assertEqual(v['change_reason'],self.a['revision_reason'])
        self.assertEqual(v['conclusion_changes'][0]['old']['text'],'Evidence conflicts; conditions unknown')
        self.assertEqual(v['conclusion_changes'][0]['new']['text'],self.a['conclusions'][0]['text'])

    def test_revision_needs_reason_even_if_same_source(self):
        self.run_pilot()
        self.a['current_conclusion']='Changed interpretation without explanation';self.save()
        r=self.run_pilot()
        self.assertEqual(len(self.state()['versions']),1)
        self.assertEqual(r['daily_item_count'],0)
        self.assertIn('revision_reason',json.dumps(P.load(self.out/'审核队列.json')))

    def test_missing_source_retained_never_reported_deleted(self):
        self.run_pilot()
        self.rows=self.rows[:1];self.save()
        r=self.run_pilot()
        self.assertEqual(r['projects'][0]['missing_records'],1)
        self.assertEqual(r['projects'][0]['retained_records'],2)
        self.assertEqual(r['daily_item_count'],0)
        self.assertEqual(len(self.state()['versions']),1)
        self.assertIn('source_missing',{q['type'] for q in P.load(self.out/'审核队列.json')})

    def test_cross_project_or_nonexistent_evidence_blocked(self):
        self.a['sections'][0]['items'][0]['evidence_ids']=['github:readme:999']
        self.rows.append(dict(self.rows[0],record_id='github:readme:999',project_id='P141'))
        self.save();r=self.run_pilot()
        self.assertEqual(r['daily_item_count'],0)
        self.assertIsNone(self.state()['accepted'])
        self.assertIn('annotation_invalid',{q['type'] for q in P.load(self.out/'审核队列.json')})

    def test_future_source_timestamp_not_treated_as_new_market_event(self):
        self.rows[0]['published_at']='2030-01-01T00:00:00Z';self.save()
        r=self.run_pilot()
        self.assertEqual(r['daily_item_count'],0)
        self.assertIsNone(self.state()['accepted'])
        self.assertIn('timestamp_review',{q['type'] for q in P.load(self.out/'审核队列.json')})

    def test_corrupt_input_fails_instead_of_no_change(self):
        self.run_pilot(); before=(self.out/'state.json').read_bytes()
        self.records_path.write_text('broken-json\n')
        with self.assertRaises(ValueError):self.run_pilot()
        self.assertEqual((self.out/'state.json').read_bytes(),before)

    def editorial(self, summary):
        selected = P.load(self.out / 'runs' / summary['run_id'] / '日报条目.json')
        versions, candidates = P.team_context(self.out, selected)
        return dict(schema_version=1, title='桌面机器人调研简报', date='2026-10-26', edition='首次观察',
                    lead=['桌面鸭子除了陪伴，还可以成为训练实验入口。'],
                    sections=[dict(heading='桌面互动：先确认训练环境是否可用', project_id='P160',
                                   paragraphs=['Duck on Desk 可以回应编程工具状态。作者与用户对苹果电脑训练支持的描述仍需对齐版本。'],
                                   sources=[dict(record_id='github:readme:1', label='项目说明'), dict(record_id='github:comment:2', label='用户讨论')])],
                    followups=['核对用户的软件版本与测试条件。'], scope_note='这是首次整理已有资料，不能代表今天新发生的市场趋势。',
                    candidate_ids=list(candidates), reviewed_source_digests={pid:v['source_digest'] for pid,v in versions.items()},
                    reviewed_candidate_hashes={cid:P.digest(c) for cid,c in candidates.items()})

    def test_team_render_is_readable_evidence_linked_and_does_not_change_research(self):
        summary = self.run_pilot()
        original_report = (self.out / 'runs' / summary['run_id'] / '日报.md').read_bytes()
        draft = self.root / 'team_digest.json'
        P.write(draft, self.editorial(summary))
        state_before = (self.out / 'state.json').read_bytes()
        versions_before = {str(p):p.read_bytes() for p in (self.out/'projects').glob('*/versions/*.json')}
        result = P.render_team_run(self.out, summary['run_id'], draft)
        self.assertFalse(result['research_state_changed'])
        text = (self.out / '日报.md').read_text()
        for forbidden in ('P160', 'D03', 'C1', 'record_id', 'source_digest', '来源版本JSON', '审核队列', '离线模式', '运行日志'):
            self.assertNotIn(forbidden, text)
        self.assertIn('[用户讨论](https://example.org/issue/1)', text)
        self.assertIn('[项目说明](https://example.org/project)', text)
        self.assertEqual((self.out / 'state.json').read_bytes(), state_before)
        self.assertEqual({str(p):p.read_bytes() for p in (self.out/'projects').glob('*/versions/*.json')}, versions_before)
        self.assertEqual((self.out / 'runs' / summary['run_id'] / '日报.原版存档.md').read_bytes(), original_report)
        self.assertEqual((self.out / '团队日报样例.md').read_text(), text)
        # A repeated input run retains the full, dated team edition instead of replacing it with an empty log.
        second = self.run_pilot()
        self.assertEqual((self.out / '日报.md').read_text(), text)
        self.assertIn('本次没有可发布的新动态', (self.out / 'runs' / second['run_id'] / '日报.md').read_text())
        self.assertFalse((self.out / '团队待核实事项.md').exists())
        self.assertIn('查看项目记录', (self.out / 'runs' / second['run_id'] / '日报.md').read_text())

    def test_project_record_is_not_overwritten_or_relabelled_when_sources_change(self):
        record = self.out / '项目记录' / 'Duck on Desk.md'
        record.parent.mkdir(parents=True)
        content = '# Duck on Desk\n\n资料截至：2026年10月26日。\n\n作者报告支持苹果电脑；用户验证仍有疑问。\n'
        record.write_text(content)
        self.run_pilot()
        self.run_pilot()
        self.rows[0]['text'] = 'New source content still requires review.'
        self.save()
        self.run_pilot()
        self.assertEqual(record.read_text(), content)
        self.assertEqual(list((self.out / 'projects').glob('**/*.md')), [])
        self.assertFalse((self.out / '研究待核实事项.md').exists())
        self.assertFalse((self.out / '团队待核实事项.md').exists())
        self.assertTrue((self.out / 'projects/P160/变化日志.json').exists())
        self.assertTrue((self.out / 'projects/P160/当前输入快照.json').exists())
        self.assertEqual(len(self.state()['versions']), 1)
        self.assertIn('evidence_changed_review_required', {q['type'] for q in P.load(self.out / '审核队列.json')})
        index = (self.out / '索引.md').read_text()
        self.assertEqual(index.count(']('), 2)
        self.assertIn('项目记录/Duck on Desk.md', index)

    def test_team_draft_rejected_when_source_or_candidate_has_changed(self):
        first = self.run_pilot()
        editorial = self.editorial(first)
        draft = self.root / 'team_digest.json'
        P.write(draft, editorial)
        P.render_team_run(self.out, first['run_id'], draft)
        published = (self.out / '日报.md').read_bytes()
        self.rows[0]['text'] = 'New evidence: CUDA tested on specified hardware.'
        self.a['reviewed_source_digest'] = P.snapshot_digest(self.rows)
        self.a['revision_reason'] = 'New hardware test has been reviewed.'
        self.a['daily_candidates'][0]['summary'] = 'The author now provides a hardware-specific test.'
        self.save()
        second = P.run(self.records_path,self.raw,self.anns,self.out,('P160',),NOW,team_digest_path=draft)
        self.assertEqual(second['daily_item_count'], 1)
        self.assertIn('需补写团队版摘要', (self.out / 'runs' / second['run_id'] / '日报.md').read_text())
        self.assertEqual((self.out / '日报.md').read_bytes(), published)
        with self.assertRaisesRegex(ValueError, '资料已变化'):
            P.render_team_run(self.out, second['run_id'], draft)
        # Rebinding only the source version cannot bypass a changed research candidate.
        current = self.editorial(second)
        editorial['reviewed_source_digests'] = current['reviewed_source_digests']
        P.write(draft, editorial)
        with self.assertRaisesRegex(ValueError, '研究判断已变化'):
            P.render_team_run(self.out, second['run_id'], draft)

    def test_team_editorial_rejects_internal_codes_and_unowned_sources(self):
        summary = self.run_pilot()
        selected = P.load(self.out / 'runs' / summary['run_id'] / '日报条目.json')
        editorial = self.editorial(summary)
        editorial['sections'][0]['paragraphs'][0] += ' 内部项目 P160。'
        with self.assertRaisesRegex(ValueError, '内部编号'):
            P.render_team_text(editorial, self.out, selected)
        editorial = self.editorial(summary)
        editorial['sections'][0]['sources'][0]['record_id'] = 'github:readme:999'
        with self.assertRaisesRegex(ValueError, '来源不存在或不属于'):
            P.render_team_text(editorial, self.out, selected)
        editorial = self.editorial(summary)
        editorial['candidate_ids'].append('not-in-run')
        with self.assertRaisesRegex(ValueError, '候选范围'):
            P.render_team_text(editorial, self.out, selected)

    def test_current_batch_is_never_overwritten_by_old_pilot(self):
        self.out.mkdir()
        original = '# 已确认的40项目日报\n'
        P.write(self.out / '日报.md', original)
        P.write(self.out / '索引.md', '正式入口')
        P.write(self.out / '团队日报元数据.json', {'batch': '20261026-top10'})
        before = {p.name:p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaisesRegex(ValueError, '不能覆盖'):
            self.run_pilot()
        with self.assertRaisesRegex(ValueError, '不能覆盖'):
            P.render_team_run(self.out, 'old-run', self.root / 'unused.json')
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.out.iterdir()})

    def test_current_hash_field_retains_latest_digest(self):
        self.out.mkdir()
        text = '# 正式稿\n'
        P.write(self.out / '团队日报样例.md', text)
        P.write(self.out / '团队日报元数据.json', {'sha256': P.digest(text.encode())})
        self.assertEqual(P.latest_team_text(self.out), text)
        P.write(self.out / '团队日报样例.md', text + 'changed')
        self.assertIsNone(P.latest_team_text(self.out))

    def test_archive_collision_never_overwrites_existing_bytes(self):
        path=self.root/'archive'
        P.immutable(path,b'original')
        with self.assertRaises(ValueError):P.immutable(path,b'replacement')
        self.assertEqual(path.read_bytes(),b'original')


if __name__=='__main__':unittest.main()
