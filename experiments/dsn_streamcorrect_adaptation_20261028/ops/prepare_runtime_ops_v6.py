import pathlib
T=pathlib.Path(__file__).resolve().parent
for stem in ['freeze_runtime','local_prepare_preflight_manifest','remote_bootstrap_cpu_env','remote_prepare_native_environment','remote_native_source_cpu_gate','remote_native_interface_cpu_gate','remote_build_campaign','remote_start_native_campaign','remote_cpu_environment_pipeline','stage_and_start_cpu_pipeline']:
 s=(T/(stem+'_v5.py')).read_text().replace('v5','v6').replace('V5','V6').replace('a652f6097c2269232b332ad046e399f9968b16e2','a720d02a8cb81db6545d7d9ec6bdc31419dd091d')
 p=T/(stem+'_v6.py');assert not p.exists();p.write_text(s)
print('Prepared distinct v6 operations sources; no remote launch')
