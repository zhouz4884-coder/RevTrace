"""Format already frozen diagnostic results; no original raw input scan."""
import hashlib,json,pathlib
E=pathlib.Path(__file__).resolve().parents[1];P=E/'EOS_CPU_RESULTS_v1';R=E/'review'
def main():
 raw=(P/'SUMMARY.json').read_bytes();z=json.loads(raw)
 rows=sorted(z['cells'],key=lambda r:(r['strategy'],r['source_id'],r['repeat']))
 lines=['| arm | source | r | EOS D2 / C8 misses | nonEOS D2 / C8 misses | EOS D / C (s) | D99 original / EOS<2 / EOS=0 |','|---|---|---:|---:|---:|---:|---:|']
 for r in rows:
  lines.append('| '+r['strategy']+' | '+r['source_id'].replace('BAC009','')+' | '+str(r['repeat'])+' | '+str(r['EOS_D2_misses'])+' / '+str(r['EOS_C8_misses'])+' | '+str(r['nonEOS_D2_misses'])+' / '+str(r['nonEOS_C8_misses'])+' | '+f"{r['EOS']['D']:.6f} / {r['EOS']['C']:.6f}"+' | '+f"{r['original']['D99']:.6f} / {r['EOS_only_D_just_inside_2']['D99']:.6f} / {r['EOS_only_D_zero_bestcase']['D99']:.6f}"+' |')
 (R/'EOS_DIAGNOSTIC_TABLE_v1.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
 obj=dict(record_type='BOUNDED_COPY_OF_FROZEN_CPU_EOS_DIAGNOSTIC_NOT_NEW_MEASUREMENT',source_summary_sha256=hashlib.sha256(raw).hexdigest(),source_result=str(P/'SUMMARY.json'),**z)
 (R/'EOS_DIAGNOSTIC_v1.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print('\n'.join(lines))
 for r in rows:
  if r['strategy']=='fullcall':print(json.dumps({k:r[k] for k in ('cell_id','first_three','nonEOS_missed_frontiers','EOS','EOS_selected_job_timing','EOS_only_D_just_inside_2','EOS_only_D_zero_bestcase')},indent=2))
if __name__=='__main__':main()
