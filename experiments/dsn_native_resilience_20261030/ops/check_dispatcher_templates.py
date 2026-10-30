"""Static compile only: no dispatcher, SSH, model or raw-data execution."""
import ast,pathlib
F=pathlib.Path(__file__).resolve().parent
names=['run_formal_actual_traces_v1.py','run_native_work_recount_v1.py','run_final_bounded_exports_v3.py']
substitutions={'NNPROJECT':repr('/tmp/native'),'PROJECT':repr('/tmp/project'),'OUTPUT':repr('/tmp/results'),'MSHA':repr('0'*64),'BINDERSHA':repr('0'*64),'PLANS':'[]'}
for name in names:
 tree=ast.parse((F/name).read_bytes(),name);value=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
 while isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='replace':value=value.func.value
 script=ast.literal_eval(value)
 for before in sorted(substitutions,key=len,reverse=True):script=script.replace(before,substitutions[before])
 compile(script,'<remote-template-'+name+'>','exec')
 print('PASS static remote Python template '+name)
