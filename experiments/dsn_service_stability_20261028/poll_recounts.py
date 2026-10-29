from pathlib import Path
import hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_service_stability_20261028';O=B/'results/revtrace/physical_retirement_20261028/dsn_service_stability_analysis_v1'
h=json.loads((P/'CPU_HANDLE_v1.json').read_text());p=Path('/proc',str(h['pid']))
alive=p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==h['start_ticks'] and hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['command_sha256']
print(json.dumps(dict(exact_handle_alive=alive,gate=json.loads((O/'GATE.json').read_text()) if (O/'GATE.json').exists() else None)))
if (O/'SUMMARY.json').exists():
 s=json.loads((O/'SUMMARY.json').read_text())
 print(json.dumps({k:dict(returncode=v['returncode'],accepted=v['accepted'],summary={x:y for x,y in (v.get('summary') or {}).items() if x not in ['inputs','input_files','limits','command','environment']}) for k,v in s.items()}))
else:
 print('COMPLETED',sorted(x.name for x in O.glob('*/ANALYSIS_RECORD.json')))
for f in O.glob('*.log'):
 text=f.read_text(errors='replace')
 if 'Traceback' in text:print(f.name,text[-3000:])
