import pathlib,subprocess
T=pathlib.Path(__file__).resolve().parent;source=T.parent/'source_v8';commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
for stem in ['freeze_runtime','local_prepare_preflight_manifest','remote_bootstrap_cpu_env','remote_prepare_native_environment','remote_native_source_cpu_gate','remote_native_interface_cpu_gate','remote_build_campaign','remote_start_native_campaign','remote_cpu_environment_pipeline','stage_and_start_cpu_pipeline','remote_start_median_gpu_gate','remote_read_median_gpu_gate']:
 s=(T/(stem+'_v7.py')).read_text().replace('v7','v8').replace('V7','V8').replace('6ec7612d26a6664bc28a656217175637d98e1f5a',commit)
 p=T/(stem+'_v8.py');assert not p.exists();p.write_text(s)
print(commit)
