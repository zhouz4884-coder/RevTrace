"""Bind actual frozen CPU inputs and root/explicit source receipts before run."""
from pathlib import Path
import argparse,datetime
from provenance import *

def main():
    p=argparse.ArgumentParser()
    for k in ('config','environment','manifest','root-noarg','analysis-explicit','out'):p.add_argument('--'+k,required=True)
    a=p.parse_args();c=read(a.config);idle(c['idle_receipt'])
    own=source(Path(__file__).resolve().parent,a.manifest,c['actual_analysis_source']['code_commit'])
    for path,commit,manifest_sha in ((a.root_noarg,NN,c['runtime']['source_manifest_sha256']),(a.analysis_explicit,own['code_commit'],sha(a.manifest))):
        g=read(path)
        if g['gate']!='SOURCE_IDENTITY_PASS' or g['code_commit']!=commit or g['manifest_sha256']!=manifest_sha:raise ValueError('preflight source receipt differs')
    pre=dict(experiment_id=EXPERIMENT,code_commit=own['code_commit'],source_manifest_sha256=sha(a.manifest),
        frozen_config=str(Path(a.config).resolve()),frozen_config_sha256=sha(a.config),environment_record=str(Path(a.environment).resolve()),
        environment_record_sha256=sha(a.environment),environment_sha256=sha(a.environment),
        raw_result_location=c['raw_result_location'],aggregate_summary_location=c['aggregate_summary_location'],gate_decision_location=c['gate_decision_location'],
        root_noarg_preflight=str(Path(a.root_noarg).resolve()),root_noarg_preflight_sha256=sha(a.root_noarg),
        analysis_explicit_preflight=str(Path(a.analysis_explicit).resolve()),analysis_explicit_preflight_sha256=sha(a.analysis_explicit),
        actual_execution_roles=dict(analysis=own,NN=c['runtime'],driver=c['driver'],binding_auditor=c['actual_binding_auditor']),
        new_model_calls=0,run_kind='FORMAL_CPU_OFFLINE_SHADOW_NOT_NEW_SERVING',utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    put(a.out,pre)
if __name__=='__main__':main()
