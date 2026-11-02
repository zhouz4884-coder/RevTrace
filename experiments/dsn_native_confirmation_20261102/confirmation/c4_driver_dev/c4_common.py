"""Standard-library identity and fixed confirmation32-to-original-C4 mapping."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess

CHECKER = 'c4dde9ea9c7abf80fae084bc2293e193262c71e6'
NN4F = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
SUPPORT = 'a13fa0a335529dc188f7e738877a3acd027ce4a7'
B = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')


class GateError(RuntimeError):
    pass


def need(value, message):
    if not value:
        raise GateError(message)


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def put(path, data, replace=False):
    with Path(path).open('w' if replace else 'x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def verify_source(source, manifest_path, expected=None):
    source, manifest_path = Path(source).resolve(strict=True), Path(manifest_path).resolve(strict=True)
    manifest = read(manifest_path)
    commit = manifest.get('source_commit',manifest.get('code_commit'))
    need(isinstance(commit,str) and len(commit)==40, 'complete actual source commit missing')
    need(expected is None or commit==expected, 'actual dependency source differs')
    need(Path(git(source,'rev-parse','--show-toplevel')).resolve()==source, 'dependency is not an independent checkout')
    need(git(source,'rev-parse','HEAD')==commit and git(source,'cat-file','-t',commit)=='commit', 'unresolvable/wrong actual HEAD')
    need(not git(source,'status','--porcelain','--untracked-files=all'), 'dirty execution/checker source')
    need(git(source,'config','--get','core.autocrlf')=='false', 'source requires autocrlf=false')
    files=manifest['files']
    tracked=set(git(source,'ls-files','-z').split('\0'))-{''}
    need(len(files)==len({row['path'] for row in files}) and tracked=={row['path'] for row in files}, 'incomplete complete-source manifest')
    for row in files:
        path=source/row['path']
        need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(source), 'source path escaped/symlinked')
        need(path.stat().st_size==row['bytes'] and sha(path)==row['sha256'], 'source bytes/hash changed: '+row['path'])
    return dict(source_commit=commit,source_root=str(source),source_manifest=str(manifest_path),
                manifest_sha256=sha(manifest_path),complete_files=len(files),clean=True)


def disk(path, base=B):
    path, base = Path(path), Path(base)
    need(path.is_absolute() and path.resolve().is_relative_to(base.resolve()), 'path escaped designated experiment disk')
    return path


def confirmation32(plan):
    need(plan['actual_NN']['source_commit']==NN4F and plan['production_support']['source_commit']==SUPPORT,
         'original NN4f/a13 roles changed')
    sources=plan['sources']
    need(plan['expected_source_count']==len(sources)==8 and plan['expected_trials']==32,'fixed actual8speaker/32cell scope changed')
    ids={source['source_id'] for source in sources}
    need(len(ids)==len({source['speaker_id'] for source in sources})==8,'source/speaker duplicates in frozen confirmation')
    cells=plan['cells']
    expected={(source,strategy,repeat) for source in ids for strategy in ('conservative','fullcall') for repeat in (0,1)}
    need(len(cells)==32 and len({row['cell_id'] for row in cells})==32,'confirmation32 IDs missing or duplicated')
    need({(row['source_id'],row['strategy'],row['repeat']) for row in cells}==expected,'confirmation fixed matrix changed')
    source_speakers={source['source_id']:source['speaker_id'] for source in sources}
    need(all(row['speaker_id']==source_speakers[row['source_id']] and row['primary_gpu']==row['repeat'] for row in cells),
         'speaker binding or original per-repeat GPU role changed')
    for source in ids:
        r0=sorted((row for row in cells if row['source_id']==source and row['repeat']==0),key=lambda row:row['position'])
        r1=sorted((row for row in cells if row['source_id']==source and row['repeat']==1),key=lambda row:row['position'])
        need([row['strategy'] for row in r1]==[row['strategy'] for row in r0][::-1],'per-speaker original ABBA reversal changed')
    return cells


def prerequisites(plan, summary, gate):
    cells=confirmation32(plan)
    expected_status='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS'
    need(summary['status']==expected_status and summary['completed_trials']==summary['planned_trials']==32
         and summary['independent_speakers']==8 and summary['actual_NN_source_commit']==NN4F,
         'actual confirmation32 terminal summary incomplete')
    need(gate['status']==expected_status and gate['completed_trials']==32,'actual confirmation32 terminal gate incomplete')
    rows=summary['cells']
    need(len(rows)==32 and {row['cell_id'] for row in rows}=={cell['cell_id'] for cell in cells}, 'confirmation32 terminal record set differs from plan')
    by_id={row['cell_id']:row for row in rows}
    for cell in cells:
        row=by_id[cell['cell_id']]
        need(row['raw_result_location']==cell['out'],'actual NN raw differs from frozen plan output')
        need(row['source_id']==cell['source_id'] and row['strategy']==cell['strategy'] and row['repeat']==cell['repeat'],
             'source/strategy/repeat relabeled')
        need(row['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE'
             and row['semantic']['actual_NN_source_commit']==NN4F, 'original complete-task/selected-reference gate failed')
    return by_id


def input_roles(case_root):
    root=Path(case_root).resolve(strict=True)
    owners=sorted(root.glob('owner_e*'),key=lambda path:int(path.name.removeprefix('owner_e')))
    need(bool(owners) and all(path.is_dir() and not path.is_symlink() for path in owners), 'no valid actual Owner attempt set')
    roles=dict(runtime_config=root/'CONFIG.json',fact_journal=root/'facts.wal',
               publication_journal=root/'publications.jsonl',consumer_journal=root/'consumer.jsonl',
               origin_record=root/'ORIGIN.json',ingress_journal=root/'ingress.jsonl')
    required=list(roles.values())
    for owner in owners:
        required.extend(owner/name for name in ['dispatch.jsonl','worker_results.jsonl','owner_events.jsonl','policy_audit.jsonl'])
    need(all(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root) for path in required),
         'required full original actual-trace input missing or escaped')
    return roles, owners, required


def inventory(paths):
    return {str(path.resolve()):dict(bytes=path.stat().st_size,sha256=sha(path)) for path in paths}


def checker_config(cell, checker_identity, inputs, roles, owners, out):
    return dict(experiment_id='REVTRACE_CONFIRM32_ORIGINAL_C4_'+cell['cell_id'],mode='actual_complete_trace',
        checker_source_commit=CHECKER,checker_manifest_sha256=checker_identity['manifest_sha256'],
        actual_runtime_source_commit=NN4F,case_root=str(Path(cell['out']).resolve()),
        original_raw_result_location=cell['out'],owner_directories=[str(path.resolve()) for path in owners],
        inputs=inputs,**{key:str(path.resolve()) for key,path in roles.items()},
        allow_incomplete_uncommitted_tail=False,
        fixed_data_rule='Every original Owner attempt/full dispatch/result/fact/publication/Consumer/ingress; no outcome filtering',
        scope='Unchanged original C4 structural actual-trace checker. No model calls, new method, GPU equality or natural-failure claim.')


def checker_command(checker_root, config, manifest, output):
    import sys
    return [sys.executable,'-B',str(Path(checker_root)/'run_trace.py'),'--config',str(config),
            '--manifest',str(manifest),'--out',str(output)]
