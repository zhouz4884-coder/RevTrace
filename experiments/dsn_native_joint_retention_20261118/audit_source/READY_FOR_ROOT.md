# Post-pilot opportunity audit: authored source, not results

This package is prepared during timed PILOT24 without reading any serving outcome.
Only frozen source/predicate/service-plan metadata were read. The v5 metric
contract preceded serving; this implementation is NOT claimed to have been
frozen before the first serving cell. Do not run tests, prepare raw-input hashes,
or analyze raw data until Root declares a post-pilot idle window.

External immutable roles: actual NN de0936/66files (ce99 manifest), pilot driver
f367/20files (c9c0 manifest), exact24 plan2ceea09f..., v5 contract32fcbdf... .
Own complete source commit/manifest/bundle is separate and must resolve at Root.
`job_accounting.py` is copied byte-for-byte from actual f367 (SHA c98a7777...),
and its origin is recorded in COPIED_DEPENDENCIES.json. Actual NN pure parsers
scan/fact_audit/reference_audit, FeedbackCut/Reconciler, original endpoints are
used from the verified full dependency; no model constructor is called.

22 focused CPU cases are authored in test_opportunities.py, unexecuted at freeze.
They exercise actual FullSpec/DependencyVersioned/UIR coordinator classes via
their frozen synthetic fixtures, not a mocked retention rule alone. Direct
handover agreement, pending ancestor-only disagreement, sticky convergence,
actual later legal install, same-F rejection, coverage/epoch, UIR suppression
with AU refusal, active/queued/unread/ready clocks, absent abort timers,
readiness sequence, durable/application split, gap censoring, legitimate zero,
and actual whole-view support/necessary withdrawal are included.

After the full pilot (or a preserved genuine technical stop), Root stages the
bundle on8TB and creates a separate immutable idle receipt:

```json
{
  "root_authorized_postpilot_idle_window": true,
  "timed_service_active": false,
  "pilot_driver_confirmed_exited": true,
  "pilot_plan_sha256": "2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6",
  "not_after_utc": "ROOT_CHOSEN_FUTURE_UTC_TIMESTAMP"
}
```

Fresh zero CUDA owners are required by the source in addition to this Root
coordination receipt. Source never signals processes or modifies CURRENT.

Prepare all24 raw hashes/config/environment only in that window:

```
python -B prepare_postpilot.py --manifest SOURCE.json --plan FIXED_SERVICE_PLAN.json --idle-receipt IDLE.json --out-dir /media/user/.../opportunity_prepared_v1 --raw-out /media/user/.../PILOT_OPPORTUNITY_AUDIT_V1
```

Missing/unexecuted cell paths remain explicit, never metric0. Freeze config and
ENVIRONMENT hashes before analysis. Root supplies default noarg NN and explicit
audit source preflight receipts, both actually PASS with their correct roles.
Prelaunch schema: experiment_id,code_commit,source_manifest_sha256,
frozen_config_sha256,environment_sha256,raw_result_location,
root_noarg_preflight/root_noarg_preflight_sha256,
audit_explicit_preflight/audit_explicit_preflight_sha256. All paths are actual
8TB staged paths, not machine-local Windows aliases.

```
CUDA_VISIBLE_DEVICES='' python -B run_audit.py --config CONFIG.json --manifest SOURCE.json --environment ENVIRONMENT.json --prelaunch PRELAUNCH.json --out /media/user/.../PILOT_OPPORTUNITY_AUDIT_V1
```

Root controls model scheduling; this source rechecks the idle receipt/expiry and
CUDA owner state before controls, every cell and final completion. Tests must
all pass without skip and without torch/transformers/whisper imports. Every
source/input/config/env hash is checked before and after. Raw facts use scan with
repair_tail=False. analyze_trial (which writes original metrics) is NOT called.

Outputs: full ALL24_CELL_TABLE.json and CSV, all actual same-source/repeat
strategy contrasts, presence-not-power assessment, detailed decision/job/paid
work/redispatch/Consumer ledgers on8TB. Full or zero opportunity is not a technical
gate; Ready0 and2percent resource drift do not filter rows. Main five arms are
not a factorial; shadow predicate has no alternative-schedule/audio-s estimand.
Only bounded tables/indices/negative examples are brought into Git.

One implementation boundary: reconstruction uses actual canonical-install
prefixes and stored first ancestor-only shadow fence. It does not pretend that
Fullcall emits dependency-versioned decisions, or that a job observed later
would still exist under that alternate schedule. Exact original C-entry time is
not logged, and abort infer timers stay missing. The full reports explicitly
carry these limits rather than manufacture data or require new NN callbacks.
