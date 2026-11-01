"""Validate bounded review artifacts and record provenance; no research runs."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import platform
import re
import subprocess
import sys

E=Path(__file__).resolve().parent
R=E.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a],text=True).strip()
old_head='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
assert git('rev-parse','HEAD')==old_head
pdfs=json.loads((E/'PDF_INDEX.json').read_text(encoding='utf-8'))
for p in pdfs:
    assert sha((R/p['path']).read_bytes())==p['sha256'], p['path']
stats=json.loads((E/'CATALOG_STATS.json').read_text(encoding='utf-8'))
inventory=json.load(gzip.open(E/'FILE_INVENTORY.json.gz','rt',encoding='utf-8'))
assert len(inventory['files'])==inventory['file_count']==154154
with (E/'EVIDENCE_LEDGER.csv').open(encoding='utf-8-sig',newline='') as f:
    ledger=list(csv.DictReader(f))
assert len(ledger)==len(set(x['evidence_id'] for x in ledger))==28
with (E/'COVERAGE.csv').open(encoding='utf-8-sig',newline='') as f:
    coverage=list(csv.DictReader(f))
assert len(coverage)==41
bad_patterns=[rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
              rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{50,}',
              rb'hf_[A-Za-z0-9]{30,}']
for p in E.iterdir():
    if p.is_file() and p.suffix in {'.md','.txt','.json','.csv'}:
        b=p.read_bytes()
        assert not any(re.search(pat,b) for pat in bad_patterns), 'Credential-shaped content: '+p.name
record={
    'audit_id':'REVTRACE-DSN-EVIDENCE-INVENTORY-20261101',
    'kind':'read_only_evidence_selection_and_opportunity_review',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'legacy_checkout_head':old_head,
    'initial_delivery_base_commit':'848b360150d54cf5823223752c23bcc242e3d373',
    'execution_source_commit':None,
    'execution_source_note':'No experiment source was executed or relabelled; per-experiment identities remain in the referenced evidence.',
    'review_helper_runtime':{'python':sys.version.split()[0],'platform':platform.system(),'release':platform.release()},
    'scope':{'filename_inventory':154154,'existing_experiment_families':36,
             'markdown_candidates_scanned':stats['catalogued_files'],
             'unique_markdown_contents':stats['unique_byte_contents'],
             'evidence_cards':28,'coverage_rows':41},
    'pdf_identities_unchanged':pdfs,
    'source_pointer_sha256_at_review_close':sha((R/'experiments/repository_identity_20261027/CURRENT.json').read_bytes()),
    'paper_modified':False,'source_pointer_modified':False,
    'new_gpu_or_model_calls':0,'new_serving_or_fault_trials':0,
    'new_formal_tool_runs':0,'new_result_recounts':0,
    'remote_raw_fetched':False,'conference_submission_performed':False,
    'gate':'PASS_BOUNDED_REVIEW_INDEX_AND_MANUSCRIPT_IDENTITY',
    'gate_scope':'Index/links/ledger consistency and original PDF byte identities only; not new validation of every historical experiment.',
    'known_remaining_research':'S14 original-clock sustained-coverage analysis and current full-protocol cost attribution are proposals, not completed results.',
}
(E/'AUDIT_RECORD.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
excluded={'PUBLICATION_MANIFEST.json','DELIVERY_RECEIPT.json','FINAL_REMOTE_VERIFICATION.json'}
items=[]
for p in sorted(E.iterdir()):
    if p.is_file() and p.name not in excluded:
        b=p.read_bytes()
        assert len(b)<2_000_000, p.name
        items.append({'path':p.relative_to(R).as_posix(),'bytes':len(b),'sha256':sha(b)})
manifest={'scope':'Only this bounded review directory; no paper, runtime, old evidence, or CURRENT mutation.',
          'files':len(items),'bytes':sum(x['bytes'] for x in items),'items':items}
(E/'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'gate':record['gate'],'files':manifest['files'],'bytes':manifest['bytes'],
                  'new_model_calls':0,'original_pdf_hashes_match':True}))
