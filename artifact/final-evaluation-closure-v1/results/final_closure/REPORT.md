# RevTrace Final Evaluation Closure

Decision: **FINAL_EVALUATION_CLOSURE_PASS**

## F1 - Quality preservation

Decision: **F1_QUALITY_PRESERVATION_PASS**

| model | language | mode | utterances | wer | cer | partial_revision_edit_rate | verification_fraction |
|---|---|---|---|---|---|---|---|
| Qwen3-ASR-0.6B | Chinese | fp32_reproducible | 64 | None | 0.0271 | 0.3161 | 0.0000 |
| Qwen3-ASR-0.6B | Chinese | revtrace_risk_limited | 64 | None | 0.0271 | 0.3162 | 0.3851 |
| Qwen3-ASR-0.6B | Chinese | singleton_authoritative | 64 | None | 0.0271 | 0.3162 | 0.0000 |
| Qwen3-ASR-0.6B | Chinese | unprotected_batch | 64 | None | 0.0271 | 0.3161 | 0.0000 |
| Qwen3-ASR-0.6B | English | fp32_reproducible | 64 | 0.0207 | 0.0052 | 0.2541 | 0.0000 |
| Qwen3-ASR-0.6B | English | revtrace_risk_limited | 64 | 0.0215 | 0.0056 | 0.2541 | 0.2584 |
| Qwen3-ASR-0.6B | English | singleton_authoritative | 64 | 0.0215 | 0.0056 | 0.2541 | 0.0000 |
| Qwen3-ASR-0.6B | English | unprotected_batch | 64 | 0.0215 | 0.0056 | 0.2541 | 0.0000 |
| Qwen3-ASR-1.7B | Chinese | fp32_reproducible | 64 | None | 0.0216 | 0.3182 | 0.0000 |
| Qwen3-ASR-1.7B | Chinese | revtrace_risk_limited | 64 | None | 0.0216 | 0.3182 | 0.3736 |
| Qwen3-ASR-1.7B | Chinese | singleton_authoritative | 64 | None | 0.0216 | 0.3182 | 0.0000 |
| Qwen3-ASR-1.7B | Chinese | unprotected_batch | 64 | None | 0.0216 | 0.3182 | 0.0000 |
| Qwen3-ASR-1.7B | English | fp32_reproducible | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 |
| Qwen3-ASR-1.7B | English | revtrace_risk_limited | 64 | 0.0230 | 0.0076 | 0.2471 | 0.2884 |
| Qwen3-ASR-1.7B | English | singleton_authoritative | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 |
| Qwen3-ASR-1.7B | English | unprotected_batch | 64 | 0.0230 | 0.0076 | 0.2471 | 0.0000 |

### Paired quality versus singleton authoritative

| model | language | mode | terminal_exact_rate_vs_singleton | primary_error_delta | ci95_low | ci95_high | catastrophic_outliers |
|---|---|---|---|---|---|---|---|
| Qwen3-ASR-0.6B | Chinese | fp32_reproducible | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | Chinese | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | Chinese | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | fp32_reproducible | 0.9844 | -0.0008 | -0.0023 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-0.6B | English | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | fp32_reproducible | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | Chinese | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | fp32_reproducible | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | revtrace_risk_limited | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| Qwen3-ASR-1.7B | English | unprotected_batch | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |

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

| experiment | proposer_dtype | authoritative_draw | fixed_batch_shape | attention_backend | batch_invariant_requested | replay_guarantee |
|---|---|---|---|---|---|---|
| Phase 2 headline | float16 | float16 fixed-shape canonical | 16 | FLASH_ATTN | True | canonical-authoritative online commit; later replay not claimed bitwise deterministic |
| Phase 6 adaptation | float16 | float32 fixed-shape b16 | 16 | vllm-auto-unrecorded | False | 720/720 observed stable in the frozen probe; contract-scoped, not a universal deterministic proof |
| Phase 7 queue | float16 | float16 fixed-shape b16 | 16 | FLASH_ATTN | True | canonical-authoritative online commit; later replay not bitwise deterministic |
| Phase 7.1 c14 capacity | float16 | float16 fixed-shape b14 | 14 | FLASH_ATTN | True | canonical-authoritative online commit; replay audit is a separate draw |

## F4 - Joint risk/SLO Pareto table

### Joint feasible

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | risk_status | slo_status | joint_feasible | pareto_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase2 live Qwen3-ASR-0.6B c16 | Qwen3-ASR-0.6B | 16 | 2.9959 | 1.3359 | None | formal_anytime_contract_pass | pass | True | True | same-task end-to-end Pareto point |
| Phase2 live Qwen3-ASR-1.7B c16 | Qwen3-ASR-1.7B | 16 | 2.4151 | 1.7302 | None | formal_anytime_contract_pass | pass | True | True | same-task end-to-end Pareto point |

### Joint-feasible capacity points without a same-task normalized baseline

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | risk_status | slo_status | joint_feasible | pareto_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase7.1 c14 certified capacity | Qwen3-ASR-0.6B | 14 | None | 1.4126 | 12.5861 | split_sample_contract_pass | pass | True | False | risk-SLO capacity point; no same-task normalized baseline |
| Final closure c14 steady-state | Qwen3-ASR-0.6B | 14 | None | 1.7660 | 10.0037 | continued_split_sample_contract_pass | pass | True | False | risk-SLO capacity point; no same-task normalized baseline |

### Infeasible or not statistically certified

| source | model | concurrency | gpu_normalized_goodput_speedup | p99_seconds | energy_joules_per_audio_second | risk_status | slo_status | joint_feasible | pareto_eligible | comparison_scope |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase5C 0p6b-c16-d120-sync-mixed | Qwen3-ASR-0.6B | 16 | 2.3209 | 4.8581 | 15.5818 | pass | fail | False | True | same-task end-to-end Pareto point |
| Phase5C 0p6b-c16-d60-poisson-mixed | Qwen3-ASR-0.6B | 16 | 2.4727 | 2.8925 | 9.4731 | insufficient_statistical_evidence | fail | False | True | same-task end-to-end Pareto point |
| Phase5C 0p6b-c32-d120-burst-zh | Qwen3-ASR-0.6B | 32 | 3.3834 | 5.5912 | 13.7599 | observed_violation | fail | False | True | same-task end-to-end Pareto point |
| Phase5C 0p6b-c8-d30-sync-en | Qwen3-ASR-0.6B | 8 | 2.1665 | 1.4209 | 7.7431 | insufficient_statistical_evidence | pass | False | True | same-task end-to-end Pareto point |
| Phase5C 1p7b-c16-d120-poisson-mixed | Qwen3-ASR-1.7B | 16 | 1.6597 | 5.3167 | 22.6516 | pass | fail | False | True | same-task end-to-end Pareto point |
| Phase5C 1p7b-c16-d30-sync-mixed | Qwen3-ASR-1.7B | 16 | 2.6034 | 1.4464 | 8.1934 | insufficient_statistical_evidence | pass | False | True | same-task end-to-end Pareto point |
| Phase5C 1p7b-c32-d60-burst-zh | Qwen3-ASR-1.7B | 32 | 2.6767 | 2.9835 | 9.2942 | pass | fail | False | True | same-task end-to-end Pareto point |
| Phase5C 1p7b-c8-d60-poisson-en | Qwen3-ASR-1.7B | 8 | 1.4660 | 2.6718 | 18.2275 | insufficient_statistical_evidence | fail | False | True | same-task end-to-end Pareto point |
| Phase6 c32 Chinese burst repaired | Qwen3-ASR-0.6B | 32 | 2.9527 | 6.1070 | 15.2682 | observed_zero_after_repair | fail | False | True | same-task end-to-end Pareto point |

The table intentionally does not rank operator-only BIO/TBIK probes as
end-to-end serving systems.
