"""Independent, local-only frozen confirmation config review; no execution."""
import datetime, hashlib, json, pathlib

H = pathlib.Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
p = H / 'SERVICE_CONFIRMATION_v1_FROZEN.json'
plan = json.loads(p.read_text(encoding='utf-8'))
assert sha(p) == '84f7a755bdf81713f083bbb54d6d7b0504bb683f583adfc09988fd015b8d8070'
assert plan['expected_cells'] == len(plan['cells']) == 16
assert plan['source_commit'] == 'bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
assert plan['original_D2_seconds'] == 2 and plan['original_C8_seconds'] == 8
assert plan['all_offered_including_EOS'] is True
rows, blocks, invariant = [], {}, None
for i, cell in enumerate(plan['cells']):
    cp = H / 'service_confirmation_v1_configs' / pathlib.PurePosixPath(cell['config']).name
    assert sha(cp) == cell['config_sha256']
    c = json.loads(cp.read_text(encoding='utf-8'))
    s = c['settings']; sid = s['sources'][0]['source_id']; rep = c['repeat']
    assert len(s['sources']) == 1 and c['arm'] == cell['arm']
    assert c['maximum_service_seconds'] == 180
    assert s['source_commit'] == plan['source_commit']
    assert s['primary_gpu'] == rep and rep in (0,1)
    assert s['max_ahead_frames'] == 32000 and s['corrector_dtype'] == 'float32'
    assert len(s['model_sources']) == 4
    assert s['warmup']['fixed_start'] == 24000 and s['warmup']['fixed_end'] == 32000
    assert s['warmup']['discard_output'] and s['warmup']['reset_service_genesis']
    source = next(x for x in s['model_sources'] if x['source_id'] == sid)
    assert s['sources'][0] == source
    comparable = {k:v for k,v in s.items() if k not in ('sources','primary_gpu')}
    if invariant is None: invariant = comparable
    assert comparable == invariant
    key = (sid,rep); blocks.setdefault(key,[]).append(c['arm'])
    assert c['paired_block'] == i//2 and c['position'] == i%2
    rows.append(dict(position=i,cell_id=c['cell_id'],source_id=sid,repeat=rep,
                     arm=c['arm'],primary_gpu=s['primary_gpu'],config_sha256=sha(cp)))
assert len(blocks) == 8
for sid in {r['source_id'] for r in rows}:
    assert set(blocks[sid,0]) == {'two_full_early','two_full_spec_early'}
    assert blocks[sid,1] == list(reversed(blocks[sid,0]))
assert len({r['source_id'] for r in rows}) == 4
for i,b in enumerate(plan['block_order']):
    assert rows[i*2]['source_id'] == b['source_id']
    assert rows[i*2]['repeat'] == b['repeat'] == b['primary_gpu']
out = dict(experiment_id='SC_STAGE_CONFIRMATION_CONFIG_INDEPENDENT_REVIEW_V1',
    reviewed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='PASS_ALL_16_CONFIG_BYTES_AND_PAIRED_ROLE_ORDER',
    plan_sha256=sha(p),source_commit=plan['source_commit'],rows=rows,
    checks=['16 unique source/repeat/arm cells','all 16 config SHA exact',
      'all four old sources retained','two fresh repeats, GPU roles 0/1 counterbalanced',
      'per-source paired arm order reversed on repeat 1',
      'common model/backend/full neural-ready warmup, same 2s lookahead',
      'unchanged D2/C8, all offered including EOS',
      'development confirmation, not new-source generalization'],
    gpu_launched=False)
(H/'INDEPENDENT_CONFIRMATION_CONFIG_REVIEW_v1.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=out['status'],cells=len(rows),output_sha256=sha(H/'INDEPENDENT_CONFIRMATION_CONFIG_REVIEW_v1.json'))))
