"""CPU journal-container fixtures; original v1 failure and metrics retained."""
from pathlib import Path
import ast,contextlib,hashlib,io,json,struct,tempfile,unittest
from unittest.mock import patch
import analyze_closed_diagnostics as v1
import analyze_closed_diagnostics_v2 as v2
from test_closed_diagnostics import fixture,write
HERE=Path(__file__).resolve().parent

def declared_journal(stage,cell):
    directory=stage/'journals';directory.mkdir(exist_ok=True)
    path=directory/(cell+'.wal')
    payload=json.dumps({'kind':'genesis','schema_version':1,'sequence':0}).encode()
    path.write_bytes(struct.pack('>I',len(payload))+payload+hashlib.sha256(payload).digest())
    path.with_name(path.name+'.lock').write_bytes(b'')
    write(stage/cell/'provenance.json',{'code_commit':'CPU-FIXTURE','journal_mode':'durable',
        'durability_mode':'wal','durable_journal_path':str(path.resolve())})
    return path

class JournalClassificationTests(unittest.TestCase):
    def test_declared_journal_not_cell_but_unknown_cell_still_rejected(self):
        with tempfile.TemporaryDirectory(prefix='cpu_journals_',dir=HERE) as d:
            stage=Path(d);C,spec=fixture(stage,'fine');declared_journal(stage,C.name)
            extras,inv,errors=v2.classify_stage_directories(stage,{C.name:spec},'CPU-FIXTURE')
            self.assertEqual(extras,[]);self.assertEqual(errors,[]);self.assertEqual(len(inv),1)
            (stage/'undeclared-extra-cell').mkdir()
            self.assertEqual(v2.classify_stage_directories(stage,{C.name:spec},'CPU-FIXTURE')[0],['undeclared-extra-cell'])

    def test_unknown_nested_cell_and_redirected_wal_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='cpu_journals_',dir=HERE) as d:
            stage=Path(d);C,spec=fixture(stage,'fine');path=declared_journal(stage,C.name)
            (path.parent/'hidden-cell').mkdir()
            extras,_,errors=v2.classify_stage_directories(stage,{C.name:spec},'CPU-FIXTURE')
            self.assertIn('journals',extras);self.assertTrue(errors)
        with tempfile.TemporaryDirectory(prefix='cpu_journals_',dir=HERE) as d:
            stage=Path(d);C,spec=fixture(stage,'fine');path=declared_journal(stage,C.name)
            p=v2.read(C/'provenance.json');p['durable_journal_path']=str(stage/'outside.wal')
            write(C/'provenance.json',p)
            self.assertTrue(v2.classify_stage_directories(stage,{C.name:spec},'CPU-FIXTURE')[2])

    def test_core_metric_function_AST_unchanged(self):
        def funcs(module):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(module.__file__).read_text()).body if isinstance(n,ast.FunctionDef)}
        before,after=funcs(v1),funcs(v2)
        for name,body in before.items():
            if name!='main':self.assertEqual(body,after[name],name)

    def test_new_output_retains_old_failure_and_all_CSV_bytes(self):
        with tempfile.TemporaryDirectory(prefix='cpu_journals_',dir=HERE) as d:
            root=Path(d);stage=root/'formal';stage.mkdir();C,spec=fixture(stage,'fine')
            declared_journal(stage,C.name);plan=root/'PLAN.json'
            write(plan,{'runtime_commit':'CPU-FIXTURE','stages':{'formal':{'cells':[spec],'expected_repeats':3}}})
            audit=root/'formal_audit';audit.mkdir()
            write(audit/'SUMMARY.json',{'status':'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT','cells':1,'expected_cells':1,'failures':[]})
            old=root/'v1';new=root/'v2'
            args=['analyze','--root',str(root),'--stage','formal','--plan',str(plan)]
            with patch('sys.argv',args+['--output',str(old)]),contextlib.redirect_stdout(io.StringIO()):v1.main()
            old_summary=(old/'SUMMARY.json').read_bytes()
            self.assertEqual(v1.read(old/'SUMMARY.json')['failures'][0]['cells'],['journals'])
            with patch('sys.argv',args+['--output',str(new),'--compare-v1',str(old)]),contextlib.redirect_stdout(io.StringIO()):v2.main()
            summary=v2.read(new/'SUMMARY.json')
            self.assertEqual(summary['status'],'PASS_COMPLETE_OBSERVED_DIAGNOSTICS')
            self.assertEqual(summary['verified_journal_files'],1)
            self.assertTrue(summary['core_CSV_comparison'])
            self.assertTrue(all(r['byte_identical'] for r in summary['core_CSV_comparison']))
            self.assertEqual(old_summary,(old/'SUMMARY.json').read_bytes())

if __name__=='__main__':unittest.main()
