"""CPU fixtures for actual Consumer retention, independent of model execution."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from feedback_contract import FeedbackCut, Reconciler
from resilience_consumer import ConsumerIntegrityError, SurvivorConsumer
from resilience_storage import FactStore, JournalIntegrityError
from resilience_trial import consumer_retention_setting, run_trial
from test_resilience_consumer import private
from test_resilience_storage import body, cut


class NativeRetentionControls(unittest.TestCase):
    def fixture(self, retain):
        folder = Path(tempfile.mkdtemp(prefix='native-retention-cpu-'))
        def cleanup():
            target=folder.resolve()
            if target.parent!=Path(tempfile.gettempdir()).resolve() or not target.name.startswith('native-retention-cpu-'):
                raise RuntimeError('CPU fixture cleanup escaped its temporary directory')
            shutil.rmtree(target)
        self.addCleanup(cleanup)
        root, first, second = cut(0), cut(8000, 'first'), cut(16000, 'second')
        store = FactStore(folder/'facts.wal', {'s':root.state},
                          {'scope':'synthetic CPU fixture; no neural execution'})
        self.addCleanup(store.close)
        consumer = SurvivorConsumer({'s':root.state}, folder/'consumer.jsonl',
                                    folder/'rejects.jsonl', folder/'facts.wal',
                                    consumer_retain_views=retain)
        self.addCleanup(consumer.close)
        consumer.begin_owner(0)
        return folder, store, consumer, root, first, second

    @staticmethod
    def commit(store, parent, end, serial=1, epoch=0):
        tx = body(parent, end, serial)
        tx['owner_epoch'] = epoch
        tx['job']['job_id'] = f'e{epoch}-j{serial:09d}'
        return store.commit(tx)

    @staticmethod
    def fact(receipt, end, publication_id=2):
        return {'kind':'canonical','source_id':'s','state':end.state,
                'durable_receipt':receipt,'publication_id':publication_id}

    def test_01_outer_config_defaults_to_legacy_retention(self):
        self.assertIs(consumer_retention_setting({}), True)
        for value in (False, True):
            self.assertIs(consumer_retention_setting({'consumer_retain_views':value}), value)

    def test_02_outer_config_rejects_non_boolean_values(self):
        for value in ('False','True',0,1,None,[],{}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                consumer_retention_setting({'consumer_retain_views':value})

    def test_03_invalid_config_stops_before_source_or_model_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json'
            config.write_text(json.dumps({'consumer_retain_views':'False'}), encoding='utf8')
            with patch('resilience_trial.verify_source') as verify:
                with self.assertRaises(ValueError):run_trial(config, 'missing-manifest', Path(tmp)/'out')
                verify.assert_not_called()
            self.assertFalse((Path(tmp)/'out').exists())

    def test_04_consumer_rejects_non_boolean_mode_before_opening_logs(self):
        for value in ('False',0,1,None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SurvivorConsumer({}, 'unused-log', 'unused-rejects', 'unused-facts',
                                 consumer_retain_views=value)

    def test_05_compatible_ahead_is_retained_only_by_s1(self):
        for retain in (False, True):
            _, store, c, root, first, second = self.fixture(retain)
            c.apply(private(root, first, second), 0)
            result=c.apply(self.fact(self.commit(store, root, first), first), 0)
            row=result['row'];w=row['view_reconciliation']
            self.assertEqual(row['visible_frontier'],16000 if retain else 8000)
            self.assertEqual(row['certified_frontier'],8000)
            self.assertEqual(row['consumer_retain_views'],retain)
            self.assertEqual(w['support_status'],'compatible_boundary')
            self.assertTrue(w['reconciliation']['compatible'])
            self.assertEqual(w['before']['visible_frontier'],16000)
            self.assertEqual(w['after']['visible_frontier'],row['visible_frontier'])
            self.assertEqual(w['before_tip_sha'],second.sha256)
            self.assertEqual(w['boundary_end_sha'],first.sha256)
            self.assertEqual(w['actual_new_canonical_sha'],first.sha256)

    def test_06_s0_still_accepts_private_first_publication_and_restoration(self):
        _, store, c, root, first, second=self.fixture(False)
        before=c.apply(private(root, first, second),0)['row']
        self.assertEqual(before['visible_frontier'],16000)
        self.assertEqual(before['certified_frontier'],0)
        dropped=c.apply(self.fact(self.commit(store,root,first),first),0)['row']
        restored=c.apply(private(first,second,publication_id=3),0)['row']
        self.assertEqual(dropped['visible_frontier'],8000)
        self.assertEqual(restored['visible_frontier'],16000)
        self.assertEqual(restored['certified_frontier'],8000)
        self.assertLessEqual(dropped['observed'],restored['observed'])

    def test_07_same_text_different_complete_boundary_is_refuted_in_both_modes(self):
        for retain in (False,True):
            _,store,c,root,first,second=self.fixture(retain)
            c.apply(private(root,first,second),0)
            state=first.state;state['last_attend_frame']+=1;actual=FeedbackCut(state)
            row=c.apply(self.fact(self.commit(store,root,actual),actual),0)['row']
            self.assertEqual(row['view_reconciliation']['support_status'],'refuted_boundary')
            self.assertFalse(row['view_reconciliation']['reconciliation']['compatible'])
            self.assertEqual(row['visible_frontier'],8000)
            self.assertIsNone(row['private_job'])

    def test_08_missing_boundary_is_not_mislabeled_refutation(self):
        for retain in (False,True):
            _,store,c,root,first,second=self.fixture(retain)
            c.apply(private(root,second),0)
            row=c.apply(self.fact(self.commit(store,root,first),first),0)['row']
            w=row['view_reconciliation']
            self.assertTrue(w['before_nonempty_visible_ahead'])
            self.assertEqual(w['support_status'],'missing_boundary')
            self.assertIsNone(w['boundary_index'])
            self.assertIsNone(w['boundary_end_sha'])
            self.assertEqual(row['visible_frontier'],8000)

    def test_09_without_ahead_both_modes_reach_same_view(self):
        snapshots=[]
        for retain in (False,True):
            _,store,c,root,first,_=self.fixture(retain)
            row=c.apply(self.fact(self.commit(store,root,first),first,1),0)['row']
            self.assertFalse(row['view_reconciliation']['before_nonempty_visible_ahead'])
            snapshots.append(c.snapshot('s'))
        self.assertEqual(*snapshots)

    def test_10_changed_published_state_is_rejected_before_install_in_both_modes(self):
        for retain in (False,True):
            _,store,c,root,first,_=self.fixture(retain)
            receipt=self.commit(store,root,first);event=self.fact(receipt,cut(8000,'forged'),1)
            before=c.snapshot('s')
            with self.assertRaises(ConsumerIntegrityError):c.apply(event,0)
            self.assertEqual(c.snapshot('s'),before)
            self.assertEqual(c.applied,0)

    def test_11_old_epoch_is_rejected_without_mutation_in_both_modes(self):
        for retain in (False,True):
            _,_,c,root,first,_=self.fixture(retain)
            c.apply(private(root,first),0);c.begin_owner(1);before=c.snapshot('s')
            result=c.apply({'publication_id':99,'source_id':'absent'},0)
            self.assertFalse(result['applied'])
            self.assertEqual(c.snapshot('s'),before)

    def test_12_duplicate_canonical_adds_no_new_observation_or_witness(self):
        for retain in (False,True):
            folder,store,c,root,first,_=self.fixture(retain)
            event=self.fact(self.commit(store,root,first),first,1)
            c.apply(event,0);result=c.apply(event,0)
            self.assertFalse(result['applied']);self.assertEqual(c.applied,1)
            self.assertEqual(len((folder/'consumer.jsonl').read_text(encoding='utf8').splitlines()),1)

    def test_13_receipt_checksum_guard_is_unchanged_in_both_modes(self):
        for retain in (False,True):
            _,store,c,root,first,_=self.fixture(retain)
            receipt=self.commit(store,root,first);receipt['record_sha256']='f'*64
            with self.assertRaises(JournalIntegrityError):c.apply(self.fact(receipt,first,1),0)
            self.assertEqual(c.snapshot('s')['certified_frontier'],0)

    def test_14_replay_has_same_mode_and_witness_but_no_duplicate_progress(self):
        for retain in (False,True):
            _,store,c,root,first,second=self.fixture(retain)
            c.apply(private(root,first,second),0)
            receipt=self.commit(store,root,first);c.begin_owner(1)
            row=c.replay_fact(receipt)['row']
            self.assertTrue(row['recovery_replay'])
            self.assertEqual(row['view_reconciliation']['support_status'],'compatible_boundary')
            self.assertEqual(row['visible_frontier'],16000 if retain else 8000)
            self.assertFalse(c.replay_fact(receipt)['applied'])

    def test_15_private_dependency_gap_is_rejected_in_both_modes(self):
        for retain in (False,True):
            _,_,c,root,first,second=self.fixture(retain)
            event=private(root,first,second)
            event['steps'][1]['start']=root.state
            before=c.snapshot('s')
            with self.assertRaises(ConsumerIntegrityError):c.apply(event,0)
            self.assertEqual(c.snapshot('s'),before)

    def test_16_wrong_source_receipt_cannot_mutate_either_source(self):
        for retain in (False,True):
            _,store,c,root,first,_=self.fixture(retain)
            state=root.state;state['contract']['source_sha']='other immutable audio'
            c.states['other']=Reconciler(FeedbackCut(state),retain);c.processed['other']=0
            event=self.fact(self.commit(store,root,first),first,1);event['source_id']='other'
            before={sid:c.snapshot(sid)for sid in c.states}
            with self.assertRaises(ConsumerIntegrityError):c.apply(event,0)
            self.assertEqual({sid:c.snapshot(sid)for sid in c.states},before)

    def test_17_publication_gap_is_rejected_before_install_in_both_modes(self):
        for retain in (False,True):
            _,store,c,root,first,_=self.fixture(retain)
            event=self.fact(self.commit(store,root,first),first,2)
            before=c.snapshot('s')
            with self.assertRaises(ConsumerIntegrityError):c.apply(event,0)
            self.assertEqual(c.snapshot('s'),before)
            self.assertEqual(c.applied,0)

    def test_18_stale_private_root_is_fenced_then_valid_publication_remains_allowed(self):
        for retain in (False,True):
            _,store,c,root,first,second=self.fixture(retain)
            c.apply(self.fact(self.commit(store,root,first),first,1),0)
            before=c.snapshot('s')
            dropped=c.apply(private(root,first,second,publication_id=2),0)
            self.assertFalse(dropped['applied']);self.assertEqual(dropped['reason'],'stale_private_root')
            self.assertEqual(c.snapshot('s'),before)
            row=c.apply(private(first,second,publication_id=3),0)['row']
            self.assertEqual(row['visible_frontier'],16000)


if __name__=='__main__':unittest.main()
