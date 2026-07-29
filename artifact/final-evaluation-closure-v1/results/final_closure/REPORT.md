# RevTrace Final Evaluation Closure

Decision: **F5_F8_PROTOCOL_CLOSURE_PASS_WITH_F7_TAIL_VARIANCE**

## F1 - Quality preservation

Decision: **F1_QUALITY_PRESERVATION_PASS**

| model | language | mode | utterances | wer | cer | partial_revision_edit_rate | terminal_verification_fraction | nonterminal_verification_fraction | online_selection_authority_violations |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-ASR-0.6B | Chinese | deployed_revtrace_fixed_shape_authority | 64 | None | 0.0271 | 0.3162 | 1.0000 | 0.0273 | 0 |
| Qwen3-ASR-0.6B | Chinese | fp32_fixed_contract | 64 | None | 0.0271 | 0.3161 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | Chinese | revtrace_risk_limited | 64 | None | 0.0271 | 0.3162 | 1.0000 | 0.0273 | 0 |
| Qwen3-ASR-0.6B | Chinese | singleton_authoritative | 64 | None | 0.0271 | 0.3162 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | Chinese | unprotected_batch | 64 | None | 0.0271 | 0.3161 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | deployed_revtrace_fixed_shape_authority | 64 | 0.0215 | 0.0056 | 0.2541 | 1.0000 | 0.0246 | 0 |
| Qwen3-ASR-0.6B | English | fp32_fixed_contract | 64 | 0.0207 | 0.0052 | 0.2541 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | revtrace_risk_limited | 64 | 0.0215 | 0.0056 | 0.2541 | 1.0000 | 0.0246 | 0 |
| Qwen3-ASR-0.6B | English | singleton_authoritative | 64 | 0.0215 | 0.0056 | 0.2541 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | unprotected_batch | 64 | 0.0215 | 0.0056 | 0.2541 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | deployed_revtrace_fixed_shape_authority | 64 | None | 0.0216 | 0.3182 | 1.0000 | 0.0182 | 0 |
| Qwen3-ASR-1.7B | Chinese | fp32_fixed_contract | 64 | None | 0.0216 | 0.3182 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | revtrace_risk_limited | 64 | None | 0.0216 | 0.3182 | 1.0000 | 0.0091 | 0 |
| Qwen3-ASR-1.7B | Chinese | singleton_authoritative | 64 | None | 0.0216 | 0.3182 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | unprotected_batch | 64 | None | 0.0216 | 0.3182 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | deployed_revtrace_fixed_shape_authority | 64 | 0.0230 | 0.0076 | 0.2471 | 1.0000 | 0.0640 | 0 |
| Qwen3-ASR-1.7B | English | fp32_fixed_contract | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | revtrace_risk_limited | 64 | 0.0230 | 0.0076 | 0.2471 | 1.0000 | 0.0640 | 0 |
| Qwen3-ASR-1.7B | English | singleton_authoritative | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | unprotected_batch | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 | 0.0000 | 0 |

### Paired quality versus singleton authoritative

| model | language | mode | terminal_exact_rate_vs_singleton | primary_error_delta | ci95_low | ci95_high | catastrophic_outliers | terminal_mismatch_rate_upper_95 |
|---|---|---|---|---|---|---|---|---|
| Qwen3-ASR-0.6B | Chinese | deployed_revtrace_fixed_shape_authority | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | Chinese | fp32_fixed_contract | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | Chinese | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | Chinese | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | English | deployed_revtrace_fixed_shape_authority | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | English | fp32_fixed_contract | 0.9844 | -0.0008 | -0.0023 | 0.0000 | 0 | None |
| Qwen3-ASR-0.6B | English | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-0.6B | English | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | Chinese | deployed_revtrace_fixed_shape_authority | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | Chinese | fp32_fixed_contract | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | Chinese | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | Chinese | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | English | deployed_revtrace_fixed_shape_authority | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | English | fp32_fixed_contract | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | English | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |
| Qwen3-ASR-1.7B | English | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0.0457 |

## F2 - Cold start versus steady state

Decision: **F2_STEADY_STATE_DECOMPOSITION_PASS**

- Time to certify (interpolated): 102.635 s
- Cold verification fraction: 0.9333
- Adaptation roots promoted: 2
- Dynamic threshold after adaptation: 0.062501
- Steady verification fraction: 0.0905
- Cold/steady goodput: 13.322 / 14.993 events/s
- Cold/steady P99: 1.468 / 1.766 s
- Cold/steady energy: 12.381 / 10.004 J/audio-s

The initial two-stage run is retained as a failed mechanism version. It recorded replay-audit counterexamples but did not feed their roots back into the dynamic failure floor.
The repaired protocol uses the middle stage only for adaptation and reports the independently seeded third stage as steady validation.

## F3 - Canonical contract matrix

| experiment | proposer_dtype | authoritative_draw | fixed_batch_shape | attention_backend | batch_invariant_requested | end_to_end_invariance_verified | replay_guarantee |
|---|---|---|---|---|---|---|---|
| Phase 2 headline | float16 | float16 fixed-shape canonical | 16 | FLASH_ATTN | True | False | canonical-authoritative online commit; later replay not claimed bitwise deterministic |
| Phase 6 adaptation | float16 | float32 fixed-shape b16 | 16 | vllm-auto-unrecorded | False | False | 720/720 observed stable in the frozen probe; contract-scoped, not a universal deterministic proof |
| Phase 7 queue | float16 | float16 fixed-shape b16 | 16 | FLASH_ATTN | True | False | canonical-authoritative online commit; later replay not bitwise deterministic |
| Phase 7.1 c14 capacity | float16 | float16 fixed-shape b14 | 14 | FLASH_ATTN | True | False | canonical-authoritative online commit; replay audit is a separate draw |

## F4 - Joint risk/SLO Pareto table

### Joint feasible

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | all_canonical_energy_joules_per_audio_second | energy_ratio_vs_all_canonical | risk_status | slo_status | joint_feasible | comparison_eligible | safe_frontier_eligible | energy_frontier_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F6 matched energy Phase2 live Qwen3-ASR-0.6B c16 | Qwen3-ASR-0.6B | 16 | 2.9451 | 1.3705 | 5.3978 | 27.4497 | 0.1966 | formal_anytime_contract_pass | pass | True | True | True | True | same-task end-to-end comparison point |
| F6 matched energy Phase2 live Qwen3-ASR-1.7B c16 | Qwen3-ASR-1.7B | 16 | 2.3780 | 1.5048 | 8.1655 | 31.3125 | 0.2608 | formal_anytime_contract_pass | pass | True | True | True | True | same-task end-to-end comparison point |

### Joint-feasible capacity points without a same-task normalized baseline

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | all_canonical_energy_joules_per_audio_second | energy_ratio_vs_all_canonical | risk_status | slo_status | joint_feasible | comparison_eligible | safe_frontier_eligible | energy_frontier_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase7.1 c14 certified capacity | Qwen3-ASR-0.6B | 14 | None | 1.4126 | 12.5861 | None | None | split_sample_contract_pass | pass | True | False | False | False | risk-SLO capacity point; no same-task normalized baseline |
| Final closure c14 steady-state | Qwen3-ASR-0.6B | 14 | None | 1.7660 | 10.0037 | None | None | continued_split_sample_contract_pass | pass | True | False | False | False | risk-SLO capacity point; no same-task normalized baseline |

### Infeasible or not statistically certified

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | all_canonical_energy_joules_per_audio_second | energy_ratio_vs_all_canonical | risk_status | slo_status | joint_feasible | comparison_eligible | safe_frontier_eligible | energy_frontier_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phase5C 0p6b-c16-d120-sync-mixed | Qwen3-ASR-0.6B | 16 | 2.3209 | 4.8581 | 15.5818 | None | None | pass | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 0p6b-c16-d60-poisson-mixed | Qwen3-ASR-0.6B | 16 | 2.4727 | 2.8925 | 9.4731 | None | None | insufficient_statistical_evidence | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 0p6b-c32-d120-burst-zh | Qwen3-ASR-0.6B | 32 | 3.3834 | 5.5912 | 13.7599 | None | None | observed_violation | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 0p6b-c8-d30-sync-en | Qwen3-ASR-0.6B | 8 | 2.1665 | 1.4209 | 7.7431 | None | None | insufficient_statistical_evidence | pass | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 1p7b-c16-d120-poisson-mixed | Qwen3-ASR-1.7B | 16 | 1.6597 | 5.3167 | 22.6516 | None | None | pass | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 1p7b-c16-d30-sync-mixed | Qwen3-ASR-1.7B | 16 | 2.6034 | 1.4464 | 8.1934 | None | None | insufficient_statistical_evidence | pass | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 1p7b-c32-d60-burst-zh | Qwen3-ASR-1.7B | 32 | 2.6767 | 2.9835 | 9.2942 | None | None | pass | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase5C 1p7b-c8-d60-poisson-en | Qwen3-ASR-1.7B | 8 | 1.4660 | 2.6718 | 18.2275 | None | None | insufficient_statistical_evidence | fail | False | True | False | False | same-task end-to-end comparison point |
| Phase6 c32 Chinese burst repaired | Qwen3-ASR-0.6B | 32 | 2.9527 | 6.1070 | 15.2682 | None | None | observed_zero_after_repair | fail | False | True | False | False | same-task end-to-end comparison point |

The table intentionally does not rank operator-only BIO/TBIK probes as
end-to-end serving systems.

## F5 - Deployed-path quality attachment

The deployed quality rows use the real Phase-2 authority split: FP16 batched
proposer, FP16 singleton authority for low-margin intermediate revisions, and
GPU-1 FP16 fixed-shape b16 authority for terminal revisions.

## F6 - Matched headline energy

Decision: **F6_MATCHED_ENERGY_MEASUREMENT_PASS**

| model | replicates | margin_thresholds | headline_threshold_match | revtrace_joules_per_audio_second | all_canonical_joules_per_audio_second | energy_ratio_revtrace_over_all_canonical | terminal_verification_fraction | nonterminal_verification_fraction | canonical_replay_state_disagreements | online_stale_or_replayed_result_events |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-ASR-0.6B | 3 | [0.05] | True | 5.3978 +/- 0.0960 | 27.4497 +/- 0.0415 | 0.1966 +/- 0.0032 | 1.0000 +/- 0.0000 | 0.0134 +/- 0.0000 | 0 | 0 |
| Qwen3-ASR-1.7B | 3 | [0.1] | True | 8.1655 +/- 0.1306 | 31.3125 +/- 0.1907 | 0.2608 +/- 0.0028 | 1.0000 +/- 0.0000 | 0.0312 +/- 0.0000 | 0 | 0 |

## F7 - Independent steady-state replications

Decision: **F7_STEADY_REPLICATION_COMPLETE_WITH_TAIL_VARIANCE**

| seed_label | events | goodput_events_per_second | p99_seconds | deadline_miss_events | deadline_miss_rounds | joules_per_audio_second | verification_fraction | unverified_fast_path_replay_roots | verified_canonical_replay_roots | post_stage_replay_output_disagreements | post_stage_replay_state_disagreements |
|---|---|---|---|---|---|---|---|---|---|---|---|
| steady_seed_1 | 1260 | 15.2004 | 2.0277 | 28 | 2 | 9.6221 | 0.0905 | 0 | 2 | 7 | 13 |
| steady_seed_2 | 1260 | 16.2882 | 1.8590 | 0 | 0 | 9.2192 | 0.0825 | 0 | 1 | 2 | 12 |
| steady_seed_3 | 1260 | 16.1335 | 1.8611 | 0 | 0 | 9.5084 | 0.0833 | 0 | 3 | 5 | 9 |

The replication is complete, but not all seeds satisfy the 2-second tail target: 2/3 seeds have zero deadline misses. Replay disagreements are later independent draws and are not online selection-authority violations.

## F8 - Reporting repair

FP32 is named `fp32_fixed_contract`; bootstrap intervals describe empirical
holdout deltas; terminal and nonterminal verification are separated; and the
comparison, safe-frontier, and matched-energy eligibility fields are distinct.
