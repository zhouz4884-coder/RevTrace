import pathlib,subprocess
T=pathlib.Path(__file__).resolve().parent;source=T.parent/'source_v7';commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
for stem in ['freeze_runtime','local_prepare_preflight_manifest','remote_bootstrap_cpu_env','remote_prepare_native_environment','remote_native_source_cpu_gate','remote_native_interface_cpu_gate','remote_build_campaign','remote_start_native_campaign','remote_cpu_environment_pipeline','stage_and_start_cpu_pipeline']:
 s=(T/(stem+'_v6.py')).read_text().replace('v6','v7').replace('V6','V7').replace('a720d02a8cb81db6545d7d9ec6bdc31419dd091d',commit)
 p=T/(stem+'_v7.py');assert not p.exists();p.write_text(s)
print(commit)
