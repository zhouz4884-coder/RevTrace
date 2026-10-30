"""Prepare the narrow sparse-compatible observer freeze without shell quoting."""
import pathlib,subprocess
F=pathlib.Path(__file__).resolve().parents[1];S=F/'long_memory_diagnostic_source_v3';p=S/'diagnose_long_memory.py';x=p.read_text(encoding='utf8');old="max((r['storage']['g_exclusive_storage_bytes'] for r in releases),default=None)";assert x.count(old)==1;x=x.replace(old,"max((r['storage']['g_exclusive_storage_bytes'] for r in releases if isinstance(r['storage'].get('g_exclusive_storage_bytes'),int)),default=None)");p.write_bytes(x.encode())
subprocess.run(['git','-C',str(S),'add','.'],check=True);subprocess.run(['git','-C',str(S),'commit','-qm','Keep optional unsupported inventory explicitly unknown while preserving direct lifetime measurements'],check=True)
text=(F/'ops/freeze_long_memory_release_v2.py').read_text(encoding='utf8').replace('v2','v3').replace('V2','V3')
for before,after in [('expected_tests=13','expected_tests=16'),('result.testsRun==13','result.testsRun==16'),("gate['tests']==13","gate['tests']==16"),('PASS_DIAGNOSTIC13','PASS_DIAGNOSTIC16'),('SOURCE13_LINUX_CPU_V3','SOURCE16_LINUX_CPU_V3'),('CPU_expected=13','CPU_expected=16')]:text=text.replace(before,after)
out=F/'ops/freeze_long_memory_release_v3.py';assert not out.exists();out.write_bytes(text.encode())
