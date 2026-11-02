"""Prepare immutable analysis inputs/reference extracts; never reads serving raw."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extracted(text: str, names: list[str]) -> str:
    lines = text.splitlines()
    tree = ast.parse(text)
    out = []
    for name in names:
        node = next(n for n in tree.body if getattr(n, 'name', None) == name)
        start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
        out.append('\n'.join(lines[start - 1:node.end_lineno]))
    return '\n\n'.join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source_out = Path(__file__).resolve().parent
    if (source_out / '.git').exists():
        raise RuntimeError('Preparation must run before this source is frozen; refusing to mutate a Git execution checkout')
    source_out.mkdir(parents=True, exist_ok=True)
    historical = args.repo / 'experiments/legal_progress_20261026'
    src = historical / 'final_source_v2/runtime/src/revtrace'
    provenance = []
    parts = []
    for name, definitions in [
        ('dgft.py', ['digest_tokens']),
        ('certified_display.py', ['text_sha', 'ContinuityView']),
        ('envelope_display.py', ['EnvelopeView']),
    ]:
        path = src / name
        text = path.read_text(encoding='utf-8')
        parts.append(extracted(text, definitions))
        provenance.append(dict(source=str(path.relative_to(args.repo)), sha256=sha(path),
                               extracted_definitions=definitions))
    header = ('"""Verbatim CPU reference definitions; see REFERENCE_PROVENANCE.json.\n'
              'No model, tokenizer, neural or filesystem service code is imported.\n"""\n'
              'from __future__ import annotations\n'
              'import hashlib, json, time, queue, threading, re, heapq\n'
              'from hashlib import sha256\nfrom typing import Sequence\n')
    (source_out / 'reference_view.py').write_text(header + '\n\n'.join(parts) + '\n', encoding='utf-8')
    core = src / 'composed_kernel.py'
    (source_out / 'reference_kernel.py').write_bytes(core.read_bytes())
    provenance.append(dict(source=str(core.relative_to(args.repo)), sha256=sha(core),
                           copied_verbatim='reference_kernel.py'))
    (source_out / 'REFERENCE_PROVENANCE.json').write_text(json.dumps(dict(
        origin='Existing frozen final_source_v2; analysis oracle only, not execution source relabeling',
        entries=provenance), indent=2) + '\n', encoding='utf-8')
    attempts = []
    bank_inputs = []
    for bank in ['n5', 'ck5']:
        path = historical / ('S0_' + bank.upper() + '_SCAN_v2.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        bank_inputs.append(dict(bank=bank, source=str(path.relative_to(args.repo)),
                                bytes=path.stat().st_size, sha256=sha(path),
                                original_counts=data['counts']))
        for ordinal, item in enumerate(data['attempts']):
            attempts.append(dict(bank=bank, ordinal=ordinal, attempt=item['attempt'],
                stage=item.get('stage'), controlled=item.get('controlled'),
                cell=item.get('cell'), original_status=item['status'],
                original_actual_rows=item.get('actual_rows_checked'),
                original_canonical_updates=item.get('canonical_updates'),
                original_point_opportunities=item.get('opportunities', 0),
                trace_identity=item.get('trace_identity', [])))
    manifest = dict(schema=1, input_banks=bank_inputs, attempts=attempts,
        denominator='All 151 N5 and 136 CK5 original attempts, including censored/failed attempts; not independent speakers',
        raw_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025',
        original_positive_cuts=json.loads((historical / 'S0_N5_SCAN_v2.json').read_text())['opportunities'])
    (args.out / 'BANK_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    config = dict(schema=1, experiment_id='REVTRACE-H1-CONTINUITY-20261102-V1',
        evidence_tier='Offline fixed-producer-history original-Consumer-clock counterfactual opportunity analysis; no deployed gain claim',
        expected_attempts=dict(n5=151, ck5=136), expected_original_point_cuts=dict(n5=14, ck5=0),
        policies=['native_latest', 'registered_native_scan', 'registered_joint_scan', 'registered_joint_index'],
        selection_rank=['audio_end_sample', 'original_display_revision', 'original_job_id'],
        query_triggers=['canonical-display', 'display', 'view-mode'],
        candidate_universe='Only already original-Consumer-registered publications; host-only and unpublished results never become candidate tips',
        support='Native published-path compatibility plus unchanged generic core all-parent uniqueness predicate; core source frozen separately',
        revocation='Original mode/epoch/FIFO fences, explicit revoked_job_ids, and recorded owner generation retirement by original wall clock',
        clocks='Original Consumer observed_perf only; never new CPU replay time or candidate age',
        interval_window='Report both within-session last-application window and global observed FIFO-prefix held-state extension; latter is right-censored',
        include_partial_EOS=True, display_deadline_seconds=2.0, certified_deadline_seconds=8.0,
        service_cost='Report opportunity durations and offline analysis CPU separately; zero additional application delay is an opportunity ceiling',
        assertions=['reproduce all original Consumer roots/frontiers/text exactly', 'input bytes and SHA before/after',
                    'no candidate before actual registration/host receipt', 'no retired/epoch-fenced reauthorization',
                    'scan/index identical selected original IDs', 'generic core apply-request/view-applied approves every positive joint selection'],
        primary='Within-session-observation original-clock audio-seconds x wall-seconds coverage deficit relative to actual native view, jointly admissible candidates only; global-prefix extension separate',
        secondary=['distinct deficient audio', 'duration and right-censoring per gap', 'old-node restoration vs newly-legal old publication',
                   'first D2 and certified C8 including EOS', 'trigger strata', 'equal-frontier different-text ties and character revision cost'],
        no_claims=['new neural execution', 'changed online ACK/dispatch counterfactual', 'population incidence', 'independent indexing algorithm',
                   'deployed end-to-end Goodput', 'partial word accuracy without alignment'])
    (args.out / 'CONFIG.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(status='PREPARED_NOT_FORMAL_EXECUTION', attempts=len(attempts),
                          config='CONFIG.json', manifest='BANK_MANIFEST.json')))


if __name__ == '__main__':
    main()
