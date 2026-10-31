"""RAM-only development/frozen controls; no model or temporary raw files."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
from content_reader import continuity, close, analyze_trial, FINAL
from content_endpoints import analyze_cell
from resilience_metrics import posterior_support
from resident_analysis import audit_request_clocks
from endpoints import recount
from refinement_trace import audit, digest, wire
from test_refinement_trace import bundle, state

class ContentControls(unittest.TestCase):
    def test_exact_G_uses_row_actual_ahead_frontier_not_target_F(self):
        rows=[dict(source_id='s',kind='private',observed=102.,text='whole G',visible_frontier=16000,certified_frontier=16000)]
        meta=dict(cell_id='x',stage='test',cohort='test',arm='fullcall',repeat=0)
        content,_,_,frontiers=analyze_cell(meta,rows,{'s':dict(frames=16000)},100.)
        facts=[dict(body=dict(source_id='s',next_state=dict(frontier=8000,transcript='different F'))),dict(body=dict(source_id='s',next_state=dict(frontier=16000,transcript='whole G')))]
        result=posterior_support(rows,frontiers,facts)['raw']
        self.assertEqual(result['original_credit_supported_seconds'],1.)
        self.assertEqual(result['original_credit_mismatching_seconds'],0.)

    def test_missing_actual_G_canonical_is_unknown_not_zero_or_final_text(self):
        rows=[dict(source_id='s',kind='private',observed=102.,text='G',visible_frontier=16000,certified_frontier=16000)]
        _,_,_,frontiers=analyze_cell(dict(cell_id='x'),rows,{'s':dict(frames=16000)},100.)
        facts=[dict(body=dict(source_id='s',next_state=dict(frontier=8000,transcript='G')))]
        r=posterior_support(rows,frontiers,facts)['raw']
        self.assertEqual(r['original_credit_unknown_seconds'],1.)
        self.assertEqual(r['all_offered_frontier_counts']['unknown'],2)

    def test_mismatch_is_preserved_as_a_separate_credit_bucket(self):
        rows=[dict(source_id='s',kind='private',observed=102.,text='X',visible_frontier=16000,certified_frontier=16000)]
        _,_,_,frontiers=analyze_cell(dict(cell_id='x'),rows,{'s':dict(frames=16000)},100.)
        r=posterior_support(rows,frontiers,[dict(body=dict(source_id='s',next_state=dict(frontier=16000,transcript='Y'))) ])['raw']
        self.assertEqual(r['original_credit_mismatching_seconds'],1.)

    def test_actual_codepoint_introduction_and_retraction_are_occurrences(self):
        rows=[dict(source_id='s',kind='private',observed=101.+i*.1,text=t,visible_frontier=8000,certified_frontier=8000) for i,t in enumerate(['甲乙','甲丙','甲乙'])]
        r,_,spans,_=analyze_cell(dict(cell_id='x'),rows,{'s':dict(frames=8000)},100.)
        self.assertEqual(r['raw']['introduced_code_point_occurrences'],4)
        self.assertEqual(r['raw']['retracted_occurrence_code_points'],2)
        self.assertEqual(r['raw']['still_visible_occurrence_code_points'],2)
        self.assertEqual(sum(s['code_points'] for s in spans if s['retracted'] and s['mode']=='raw'),2)

    def test_compatible_update_preserves_full_actual_tip_and_censors_last(self):
        b,_=bundle();checked=audit(**b);r,events,intervals,segments=continuity(b['frames'],b['publication_rows'],b['consumer_rows'])
        self.assertEqual(r['compatible_ahead_preserved'],checked['counts']['compatible_ahead_preserved'])
        self.assertEqual(r['compatible_ahead_preserved'],1)
        self.assertEqual(events[0]['before_tip_sha256'],events[0]['after_tip_sha256'])
        self.assertEqual(len([x for x in segments if x['compatible_updates_crossed']]),1)
        self.assertTrue(segments[-1]['right_censored'])
        self.assertEqual(max(i['end_perf'] for i in intervals),b['consumer_rows'][-1]['observed'])

    def test_false_preservation_in_actual_snapshot_is_rejected(self):
        b,_=bundle();b['consumer_rows'][2]['visible_frontier']=8000
        with self.assertRaises(Exception):audit(**b)
        with self.assertRaisesRegex(ValueError,'actual snapshot mismatch'):continuity(b['frames'],b['publication_rows'],b['consumer_rows'])

    def test_same_text_different_complete_boundary_requires_withdrawal(self):
        # A compact interval-reader fixture follows the complete structural
        # checker boundary: predicted cut and true cut render the same text,
        # but tokens/context differ. Text equality must not establish support.
        initial=state(0);pred=state(8000,0);actual=state(8000,9);tip=state(16000,0)
        self.assertEqual(pred['transcript'],actual['transcript'])
        frames=[(dict(kind='genesis',body=dict(initials={'s':initial})),dict(sequence=1)),(dict(kind='canonical',body=dict(source_id='s',parent_state=initial,next_state=actual,record=dict(native_model_evaluated=True))),dict(sequence=2))]
        pub=dict(owner_epoch=0,event=dict(kind='private',source_id='s',publication_id=1,canonical_sha=digest(initial),steps=[dict(start=initial,end=pred,job_id='a'),dict(start=pred,end=tip,job_id='b')]))
        rows=[dict(kind='private',source_id='s',observed=1.,owner_epoch=0,publication_id=1,canonical_sha=digest(initial),certified_frontier=0,visible_frontier=16000,text=tip['transcript'],private_job='b'),dict(kind='canonical',source_id='s',observed=2.,owner_epoch=0,journal_sequence=2,canonical_sha=digest(actual),certified_frontier=8000,visible_frontier=8000,text=actual['transcript'],private_job=None)]
        r,events,_,_=continuity(frames,[pub],rows)
        self.assertEqual(r['compatible_ahead_applications'],0)
        self.assertEqual(r['necessary_incompatible_withdrawals'],1)
        self.assertFalse(events[0]['full_boundary_compatible'])

    def test_missing_private_dependency_path_is_rejected(self):
        b,_=bundle();b['publication_rows'][1]['event']['steps'][1]['start']['tokens']=[[999]]
        with self.assertRaises(Exception):audit(**b)

    def test_empty_internal_ahead_tip_is_separate_from_actual_nonempty_view(self):
        initial=state(0);boundary=state(8000);tip=state(16000);tip['transcript']=''
        frames=[(dict(kind='genesis',body=dict(initials={'s':initial})),dict(sequence=1)),(dict(kind='canonical',body=dict(source_id='s',parent_state=initial,next_state=boundary,record=dict(native_model_evaluated=True))),dict(sequence=2))]
        pub=dict(owner_epoch=0,event=dict(kind='private',source_id='s',publication_id=1,canonical_sha=digest(initial),steps=[dict(start=initial,end=boundary,job_id='a'),dict(start=boundary,end=tip,job_id='b')]))
        rows=[dict(kind='private',source_id='s',observed=1.,owner_epoch=0,publication_id=1,canonical_sha=digest(initial),certified_frontier=0,visible_frontier=0,text='',private_job='b'),dict(kind='canonical',source_id='s',observed=2.,owner_epoch=0,journal_sequence=2,canonical_sha=digest(boundary),certified_frontier=8000,visible_frontier=0,text='',private_job='b')]
        r,events,_,_=continuity(frames,[pub],rows)
        self.assertEqual(r['compatible_ahead_preserved'],1)
        self.assertEqual(r['compatible_ahead_empty_tips'],1)
        self.assertEqual(r['compatible_ahead_nonempty_views'],0)
        self.assertEqual(r['observed_nonempty_seconds_of_tip_segments_crossing_compatible_updates'],0)
        self.assertEqual(events[0]['actual_visible_before_frontier'],0)

    def test_per_request_origin_adapter_prevents_borrowing_first_clock(self):
        sources={'a':dict(source_id='a',frames=8000,audio_sha256='a'*64),'b':dict(source_id='b',frames=8000,audio_sha256='b'*64)}
        origins={'a':100.,'b':110.};rows=[dict(source_id=s,observed=origins[s]+.7,visible_frontier=8000,certified_frontier=8000) for s in sources]
        ledger=[];ingress=[]
        for i,s in enumerate(sources):
            previous=None if i==0 else 'a'
            ledger.append(dict(kind='request_admitted',source_id=s,request_index=i,request_origin_perf=origins[s],observed=origins[s],previous_source_id=previous,previous_complete_perf=None if i==0 else 100.7))
            ledger.append(dict(kind='request_complete',source_id=s,observed=origins[s]+.7,EOS_frontier=8000,certified_frontier=8000,consumer_observed_perf=origins[s]+.7))
            ingress.append(dict(source_id=s,frontier=8000,original_offer=origins[s]+.5,observed=origins[s]+.5,audio_sha256=s*64))
        config=dict(settings=dict(sources=list(sources.values())),request_order=['a','b'])
        self.assertTrue(audit_request_clocks(config,origins,ledger,ingress,rows)['EOS_included'])
        r=recount(rows,sources,origins);self.assertAlmostEqual(r['primary_linear_all_offered_D99'],.2)
        wrong=recount(rows,sources,{'a':100.,'b':100.});self.assertGreater(wrong['primary_linear_all_offered_D99'],2.)
        bad=copy.deepcopy(origins);bad['b']=100.
        with self.assertRaises(Exception):audit_request_clocks(config,bad,ledger,ingress,rows)

    def test_missing_EOS_is_retained_in_all_offered_denominator(self):
        r=recount([dict(source_id='s',observed=101.,visible_frontier=8000,certified_frontier=8000)],{'s':dict(frames=9000)},{'s':100.})
        self.assertEqual(r['offered_frontiers'],2)
        self.assertEqual(r['missing_D_frontiers'],1)
        self.assertFalse(r['complete_coverage_and_original_quantile_pass'])

    def test_vendored_modules_are_exact_original_bytes(self):
        root=Path(__file__).resolve().parent;deps=json.loads((root/'DEPENDENCIES.json').read_bytes())
        self.assertEqual(len(deps['files']),12)
        for r in deps['files']:
            b=(root/r['vendored_path']).read_bytes();self.assertEqual(len(b),r['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),r['sha256'])

    def test_numeric_conservation_does_not_treat_unknown_as_zero(self):
        with self.assertRaises(ValueError):close(None,0.)
        with self.assertRaises(ValueError):close(dict(unknown=1),dict(unknown=0))

    def test_control_file_drift_fails_instead_of_successful_relabel(self):
        from evidence_io import verify_controls_unchanged
        before={'frozen_config':dict(bytes=1,sha256='a'*64)}
        with patch('evidence_io.control_hashes',return_value=copy.deepcopy(before)):
            self.assertEqual(verify_controls_unchanged([],before),before)
        changed=copy.deepcopy(before);changed['frozen_config']['sha256']='b'*64
        with patch('evidence_io.control_hashes',return_value=changed):
            with self.assertRaisesRegex(ValueError,'changed during analysis'):verify_controls_unchanged([],before)

    def test_full_trial_adapter_in_RAM_conserves_existing_content(self):
        b,_=bundle();sid='s';root=Path('/memory_only/cell')
        sources={sid:dict(source_id=sid,frames=16000,audio_sha256='a'*64)}
        config=dict(cell_id='x',arm='fullcall',repeat=0,settings=dict(source_commit=FINAL,sources=list(sources.values())))
        b['frames'][0][0]['body']['metadata'].update(actual_source_commit=FINAL,config_sha256=hashlib.sha256(wire(config)).hexdigest())
        for d in b['dispatch_rows']:d['job']['dispatched_perf']=100.+d['job']['end']/16000+.01
        meta=dict(cell_id='x',stage='original',cohort='original',arm='fullcall',repeat=0)
        content,_,_,ff=analyze_cell(meta,b['consumer_rows'],sources,100.)
        facts=[dict(body=obj['body']) for obj,_ in b['frames'][1:]]
        old=dict(primary=recount(b['consumer_rows'],sources,{'s':100.}),content=content,posterior_whole_text_support=posterior_support(b['consumer_rows'],ff,facts))
        values={'CONFIG.json':config,'ORIGIN.json':dict(origin_perf=100.,original_D=2.,original_C=8.),'SUMMARY.json':old,
            'consumer.jsonl':b['consumer_rows'],'publications.jsonl':b['publication_rows'],
            'owner_e0/dispatch.jsonl':b['dispatch_rows'],'owner_e0/worker_results.jsonl':b['completion_rows'],
            'ingress.jsonl':[dict(kind='accepted_input',source_id='s',frontier=F,audio_sha256='a'*64,original_offer=100.+F/16000,observed=100.+F/16000) for F in (8000,16000)]}
        class MemoryInputs:
            def json(self,p):return values[p.relative_to(root).as_posix()]
            lines=json
            def path(self,p):return p
        cell=dict(raw_root=str(root),cell_id='x',arm='fullcall',repeat=0,cohort='paired',owner_directories=['owner_e0'],source_ids=['s'],expected_sources=list(sources.values()))
        owner=SimpleNamespace(name='owner_e0',is_dir=lambda:True)
        with patch('content_reader.read_frames',return_value=(b['frames'],dict(valid_bytes=1))),patch.object(Path,'iterdir',return_value=iter([owner])):
            result,requests,*_=analyze_trial(cell,MemoryInputs())
        self.assertEqual(result['continuity']['compatible_ahead_preserved'],1)
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0]['content']['raw']['introduced_code_point_occurrences'],content['raw']['introduced_code_point_occurrences'])
        # The same in-memory complete path also traverses the distinct resident
        # ledger adapter; no old c4 single-origin request-clock assumption leaks.
        config.update(request_contract='closed_loop_single_outstanding_independent_EOS_v1',request_order=['s'])
        b['frames'][0][0]['body']['metadata']['config_sha256']=hashlib.sha256(wire(config)).hexdigest()
        eos=next(r for r in b['consumer_rows'] if r['certified_frontier']==16000)
        values.update({'REQUEST_ORIGINS.json':{'s':100.},'request_ledger.jsonl':[
            dict(kind='request_admitted',source_id='s',request_index=0,request_origin_perf=100.,observed=100.,previous_source_id=None),
            dict(kind='request_complete',source_id='s',observed=eos['observed'],EOS_frontier=16000,certified_frontier=16000,consumer_observed_perf=eos['observed'])]})
        values['SUMMARY.json']=dict(primary=old['primary'],per_request=[dict(source_id='s',primary=old['primary'])])
        cell['cohort']='resident'
        with patch('content_reader.read_frames',return_value=(b['frames'],dict(valid_bytes=1))),patch.object(Path,'iterdir',return_value=iter([owner])):
            resident_result,resident_requests,*_=analyze_trial(cell,MemoryInputs())
        self.assertEqual(resident_result['request_clock']['requests'],1)
        self.assertEqual(resident_requests[0]['request_origin_perf'],100.)

if __name__=='__main__':unittest.main(verbosity=2)
