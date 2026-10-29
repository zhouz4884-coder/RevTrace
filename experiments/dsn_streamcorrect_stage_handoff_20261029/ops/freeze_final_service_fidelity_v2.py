"""Only correct non-method fidelity wording; preserve all frozen cell bytes."""
import datetime,hashlib,json,pathlib,copy
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
p=I/'FINAL_SERVICE_v1_FROZEN.json';data=p.read_bytes();assert hashlib.sha256(data).hexdigest()=='26a7303fc9a27e6f1676f75309f8b2fb3285af219827e7b469cbe5338ef69815'
old=json.loads(data);new=copy.deepcopy(old)
new['fidelity']='Unchanged campaign audit plus independent exact full-state, complete-start, selected-C and returned-ID comparison including stage_execution; no field projection needed for these four new speakers. The independent exact comparison is a hard validity gate.'
new['non_method_fidelity_wording_revision']=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),supersedes_unlaunched_plan=p.name,previous_plan_sha256=hashlib.sha256(data).hexdigest(),only_change='Fidelity wording plus this provenance record; all16 configs/settings/source/seed/order/denominators/thresholds unchanged',runtime_auditor_unchanged=True)
assert {k:v for k,v in new.items() if k not in ('fidelity','non_method_fidelity_wording_revision')}=={k:v for k,v in old.items() if k!='fidelity'}
dest=I/'FINAL_SERVICE_v2_FROZEN.json';assert not dest.exists();dest.write_bytes((json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(dict(path=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),all16_configs_unchanged=True)))
