"""Whole-cell GNU-time observer; no model/scheduling/result modification."""
import hashlib,json,runpy,subprocess,sys,time
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';O=B/'results/revtrace/phaseD_20261021';original=subprocess.run
def measured(command,*args,**kwargs):
 if isinstance(command,list) and any(str(c).endswith('run_tc_live_qwen.py') for c in command):
  folder=Path(command[command.index('--output')+1]);report=folder.parent/(folder.name+'.CPU_IO.txt');actual=['/usr/bin/time','-v','-o',str(report)]+command
  (folder.parent/(folder.name+'.OBSERVER_COMMAND.json')).write_text(json.dumps({'actual_command':actual,'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'full process group CPU/IO/RSS including model initialization; not serving-only CPU or CPU joules'},indent=2)+'\n')
  return original(actual,*args,**kwargs)
 return original(command,*args,**kwargs)
assert Path('/usr/bin/time').exists();subprocess.run=measured
runpy.run_path(str(P/'d1_v1/scripts/phase_d_controller.py'),run_name='__main__')
