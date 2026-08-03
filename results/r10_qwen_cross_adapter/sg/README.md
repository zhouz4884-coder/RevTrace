# R10 same-workload SG cells

These two raw JSON files close the SG/Coarse-DGFT/Hybrid-DGFT ablation under
the R10 workload: 16 bilingual 30-second sessions, synchronized arrival, two
RTX 3090 GPUs, FP16 batched proposal, and FP16 2-second singleton authority.
The frozen empirical scheduling thresholds are 0.05 for 0.6B and 0.10 for
1.7B. They are not deterministic margin certificates.

The unchanged serving runner is
`scripts/remote/run_revtrace_dual_gpu.py` (Git blob
`3413bdeb7b588bfe51fc97327e187b78e8ce09d8`). Both accepted cells record
deployment commit `9a33d7f7ffeebcd2942d961854e5a4fee18f2b00` in their environment block.
The post-service fresh singleton audit is excluded from service wall time and
energy and is used only to compare every selected output and state projection.

The first 1.7B attempt omitted `REVTRACE_CODE_COMMIT` after a launch-path
repair. Its outputs were not hand-edited or promoted. The raw file is retained
as `../diagnostics/qwen17-sg-r10-unrecorded.json`; the paper-facing 1.7B cell is
a complete rerun with recorded provenance. Earlier launch failures from a
missing `PYTHONPATH` and a residual vLLM child process produced no result JSON
and are not included in any metric.

The excluded and accepted 1.7B runs nevertheless provide a repeat control:
all 240 selected outputs, all 240 state projections, and all 240 verification
decisions agree exactly across runs. Wall speedup changes from 4.629x to
4.682x and P99 state-entry latency from 2.799 s to 2.964 s, while the miss rate
remains 4.17%. This confirms that the SG tail failure is not caused by a text
trajectory change, while also exposing ordinary system-tail variance.

Run the fail-closed aggregation with:

```powershell
python scripts/finalize_r10_dgft_ablation.py `
  --input-dir results/r10_qwen_cross_adapter `
  --output-json results/r10_qwen_cross_adapter/ablation_summary.json `
  --output-md docs/reports/r10_same_workload_dgft_ablation.md
```

The aggregate decision is intentionally
`COMPLETE_R10_ABLATION_WITH_SG_TAIL_BOUNDARY`: all output, state, and version
checks pass, but both SG cells fail the 2-second state-entry tail gate under a
synchronized terminal burst.
