"""CPU protocol controls, never neural, scheduling-performance or GPU evidence."""
import copy
import unittest
from resilience_inbound import IntegrityError, WritesFrozenError
from resilience_policy import CommitHookError
from versioned_policy import SafeVersionedCoordinator, ReadyOnlyCoordinator, DependencyVersionedCoordinator, is_policy_fence
import test_resilience_policy as fixtures
from test_resilience_policy import cut


class VersionedControls(unittest.TestCase):
    # Reuse exact full-state fixtures and owned delivery helpers, not a second
    # approximation of the protocol under test.
    register = fixtures.ResiliencePolicyControls.register
    early_event = fixtures.ResiliencePolicyControls.early_event
    completion_event = fixtures.ResiliencePolicyControls.completion_event
    deliver = fixtures.ResiliencePolicyControls.deliver
    early = fixtures.ResiliencePolicyControls.early
    finish = fixtures.ResiliencePolicyControls.finish
    two_pending = fixtures.ResiliencePolicyControls.two_pending

    def setUp(self):
        self.sid, self.root, self.serial = "s", cut(0), 0
        self.commits, self.audit = [], []
        self.c = self.make()

    def make(self, kind=SafeVersionedCoordinator, hook=None):
        import numpy as np
        def durable(tx):
            self.assertTrue(self.c.canonical(self.sid).same(cut(0)) if not self.commits
                            else self.c.canonical(self.sid).state == self.commits[-1]["next_state"])
            self.commits.append(copy.deepcopy(tx))
            return dict(transition_id="commit-"+str(len(self.commits)),
                        journal_seq=len(self.commits), record_sha="a"*64)
        return kind(initials={self.sid:self.root.state},
                    audio={self.sid:np.zeros(2000000,dtype=np.float32)},
                    runtime_identity={"source":"fixed"},
                    source_frames={self.sid:2000000}, authority_workers=("f0","f1"),
                    owner_epoch=7, worker_incarnations={"f0":0,"f1":0},
                    before_commit=hook or durable, history_limit=4,
                    audit_sink=lambda k,r:self.audit.append((k,r)))

    def test_current_parent_original_commits_then_advances_policy_token(self):
        j=self.register(); out=self.finish(j,cut(8000,"selected"))["outcome"]
        self.assertEqual(out["kind"],"canonical")
        self.assertEqual(self.c.install_generations[self.sid],1)
        self.assertEqual(self.commits[0]["job"]["birth_install_generation"],0)
        self.assertEqual(self.c.epochs[self.sid],0)
        self.assertEqual(self.c.inbound.worker_incarnations,{"f0":0,"f1":0})

    def test_birth_root_fence_is_not_complete_input_refutation(self):
        parent,child,p1,p2=self.two_pending(); frozen=copy.deepcopy(self.c.jobs[child])
        self.finish(parent,p1); proof=self.c.invalidations()[child]
        self.assertTrue(is_policy_fence(proof)); self.assertTrue(proof["policy_only_fence"])
        self.assertIsNone(proof["complete_input_refutation"])
        self.assertTrue(proof["complete_input_equals_current_parent"])
        self.assertFalse(proof["fence_uses_input_refutation"])
        for key in ("job_id","worker","dispatch_epoch","birth_canonical_sha","start","frozen_dependencies"):
            self.assertEqual(self.c.jobs[child][key],frozen[key])
        self.assertNotIn(self.sid,self.c.active_authority)
        self.assertEqual(len(self.c.promotions),0)

    def test_birth_root_late_complete_discards_without_new_fact(self):
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        self.assertEqual(self.finish(child,p2)["outcome"]["kind"],"discarded")
        self.assertEqual(len(self.commits),1); self.assertEqual(self.c.pop_ready_commits(),[])

    def test_birth_root_already_complete_result_is_fenced(self):
        parent,child,p1,p2=self.two_pending()
        self.assertEqual(self.finish(child,p2)["outcome"]["kind"],"buffered_full")
        self.finish(parent,p1); self.assertEqual(self.c.pop_ready_commits(),[])
        self.assertEqual(self.c.discarded_full[-1]["job"]["job_id"],child)
        self.assertEqual(len(self.commits),1)

    def test_stale_live_job_does_not_block_current_parent_recompute(self):
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        self.assertTrue(self.c.next_full_start(self.sid,16000).same(p1))
        replacement=self.register("f0",p1)
        self.assertEqual(self.c.active_authority[self.sid],replacement)
        self.assertEqual(self.finish(replacement,p2)["outcome"]["kind"],"canonical")
        self.assertIn(child,self.c.jobs)

    def test_fence_or_abandon_never_erases_supported_whole_view(self):
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        before=self.c.view_event(self.sid); proof=self.c.invalidations()[child]
        self.c.abandon("f1",child,proof)
        self.assertEqual(self.c.view_event(self.sid),before)
        self.assertEqual(before["steps"][-1]["end"],p2.state)

    def test_policy_proof_cannot_be_forged_or_used_by_other_worker(self):
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        proof=self.c.invalidations()[child]
        with self.assertRaises(ValueError):self.c.abandon("f0",child,proof)
        with self.assertRaises(ValueError):self.c.abandon("f1",child,dict(proof,current_install_generation=99))

    def test_durable_hook_failure_does_not_advance_policy_token(self):
        def fail(_):raise OSError("synthetic durable failure")
        self.c=self.make(hook=fail); j=self.register()
        with self.assertRaises(CommitHookError):self.finish(j,cut(8000,"new"))
        self.assertEqual(self.c.install_generations[self.sid],0)
        self.assertTrue(self.c.canonical(self.sid).same(self.root))
        with self.assertRaises(WritesFrozenError):self.register("f1")

    def test_session_epoch_is_not_repurposed_for_policy_version(self):
        j=self.register(); self.c.reset_epoch(self.sid,self.root)
        self.assertEqual(self.c.invalidations()[j]["kind"],"session_epoch_changed")
        self.assertEqual(self.c.install_generations[self.sid],0)

    def test_duplicate_terminal_cannot_advance_generation_or_lease(self):
        j=self.register(); event=self.completion_event(j,cut(8000,"x")); self.deliver(event)
        result=self.deliver(event)
        self.assertFalse(result["physical_terminal"])
        self.assertEqual(self.c.install_generations[self.sid],1)

    def test_ready_only_preserves_completed_matching_originals(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(child,p2); self.finish(parent,p1)
        ready=self.c.pop_ready_commits()
        self.assertEqual([r["job"]["job_id"] for r in ready],[child])
        self.assertEqual(len(self.commits),2)
        self.assertTrue(self.c.canonical(self.sid).same(p2))

    def test_ready_only_late_completion_cannot_enter_memoization_bank(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        proof=self.c.invalidations()[child]
        self.assertEqual(proof["kind"],"inflight_at_install_policy_fence")
        self.assertTrue(proof["complete_input_equals_current_parent"])
        self.assertEqual(self.finish(child,p2)["outcome"]["kind"],"discarded")
        self.assertEqual(self.c.pop_ready_commits(),[])

    def test_ready_only_retains_supported_view_after_live_call_fence(self):
        self.c=self.make(ReadyOnlyCoordinator)
        self.test_fence_or_abandon_never_erases_supported_whole_view()

    def test_ready_only_actual_parent_mismatch_still_rejects_ready_full(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(child,p2)
        self.finish(parent,cut(8000,"different")); self.assertEqual(self.c.pop_ready_commits(),[])
        self.assertEqual(self.c.discarded_full[-1]["proof"]["kind"],"actual_canonical_disagrees_with_complete_start")

    def test_ready_only_fence_retirement_is_bounded(self):
        self.c=self.make(ReadyOnlyCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        self.assertIn(child,self.c.inflight_install_fences)
        self.finish(child,p2); self.c.collect_history()
        self.assertEqual(self.c.inflight_install_fences,{})

    def test_dependency_versioned_accepts_complete_matching_parent_handover(self):
        self.c=self.make(DependencyVersionedCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(parent,p1)
        self.assertNotIn(child,self.c.invalidations())
        self.assertEqual(self.c.active_authority[self.sid],child)
        self.assertEqual(self.finish(child,p2)["outcome"]["kind"],"canonical")

    def test_dependency_versioned_accepts_ready_matching_parent_handover(self):
        self.c=self.make(DependencyVersionedCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(child,p2); self.finish(parent,p1)
        self.assertEqual([r["job"]["job_id"] for r in self.c.pop_ready_commits()],[child])

    def test_dependency_versioned_fence_survives_later_complete_input_convergence(self):
        self.c=self.make(DependencyVersionedCoordinator)
        parent,child,p1,p2=self.two_pending(); self.finish(child,p2)
        future=self.register("f1",p2)
        actual1=cut(8000,"different ancestor"); self.finish(parent,actual1)
        proof=self.c.invalidations()[future]
        self.assertEqual(proof["kind"],"dependency_version_policy_fence")
        self.assertEqual(proof["witness_frontier"],8000)
        self.assertIsNone(proof["complete_input_refutation"])
        # Discard the now-wrong ready child, recompute its original real parent.
        self.c.pop_ready_commits(); replacement=self.register("f0",actual1)
        self.finish(replacement,p2)
        self.assertTrue(self.c.jobs[future]["start"].same(self.c.canonical(self.sid)))
        self.assertEqual(self.c.invalidations()[future],proof)
        self.assertEqual(self.finish(future,cut(24000,"late converged result"))["outcome"]["kind"],"discarded")


if __name__ == "__main__":unittest.main()
