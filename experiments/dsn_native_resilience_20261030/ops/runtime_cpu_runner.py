"""File-backed guarded CPU reporter so multiprocessing spawn can import main."""
import argparse,hashlib,io,json,pathlib,sys,unittest

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,indent=2)+'\n').encode('utf8'))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--manifest',type=pathlib.Path,required=True);parser.add_argument('--out',type=pathlib.Path,required=True);parser.add_argument('--minimum-tests',type=int,required=True);args=parser.parse_args()
 source=args.source.resolve();out=args.out.resolve();config=json.loads((out/'CONFIG.json').read_bytes())
 if sha(__file__)!=config['operator_cpu_runner_sha256']:raise RuntimeError('CPU reporter bytes differ from prelaunch record')
 sys.path.insert(0,str(source));from native_service import verify_source
 identity=verify_source(args.manifest)
 if identity['source_commit']!=config['source_commit']:raise RuntimeError('CPU actual source differs')
 for name in ('SUMMARY.json','GATE.json','unittest.log'):
  if (out/name).exists():raise RuntimeError('refuse to overwrite prior CPU run: '+name)
 suite=unittest.defaultTestLoader.discover(str(source),pattern='test_*.py');expected=suite.countTestCases()
 if expected<args.minimum_tests:raise RuntimeError('frozen source test discovery incomplete')
 log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite);(out/'unittest.log').write_text(log.getvalue(),encoding='utf8')
 ok=result.wasSuccessful() and result.testsRun==expected and not result.skipped
 summary=dict(status='PASS_ALL_FROZEN_SOURCE_CPU_ZERO_SKIP' if ok else 'FAIL_COMPLETE_CPU_GATE_PRESERVED',source_commit=identity['source_commit'],expected_discovered_tests=expected,tests=result.testsRun,skipped=len(result.skipped),trained_neural_models_loaded=False,actual_serving_cells=0,operator_cpu_runner_sha256=sha(__file__),runner_mode='real_file_if_main_guard',scope='Frozen source CPU controls only; no serving or trained-model result.')
 put(out/'SUMMARY.json',summary);put(out/'GATE.json',summary);verify_source(args.manifest);print(json.dumps(summary),flush=True)
 return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
