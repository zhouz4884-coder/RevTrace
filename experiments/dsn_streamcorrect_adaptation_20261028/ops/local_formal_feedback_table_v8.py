import pathlib,json
T=pathlib.Path(__file__).resolve().parents[1];p=T/'final_native_v8_evidence/native_campaign_v8_continuation_auditfix_v1/SUMMARY.json';data=json.loads(p.read_text(encoding='utf-8'));table=[]
for arm in ['sequential','drop','joint']:
 cells=[x for x in data['cells'] if x['arm']==arm];updates=[x for c in cells for x in c['meaningful_feedback_updates']];quality=dict(reference_characters=sum(c['quality']['reference_characters'] for c in cells),character_edits=sum(c['quality']['character_edits'] for c in cells))
 row=dict(arm=arm,cells=len(cells),raw_changed=sum(c['corrected_updates'] for c in cells),raw_unchanged=sum(c['unchanged_updates'] for c in cells),nonempty_changed=sum(x['changed'] for x in updates),nonempty_unchanged=sum(not x['changed'] for x in updates),
 actual_completed_ahead_compatible=sum(x['private_ahead'] and x['compatible'] for x in updates),actual_completed_ahead_incompatible_must_discard=sum(x['private_ahead'] and not x['compatible'] for x in updates),
 raw_changed_ahead_compatible=sum(x['changed'] and x['private_ahead'] and x['compatible'] for x in updates),raw_changed_ahead_incompatible=sum(x['changed'] and x['private_ahead'] and not x['compatible'] for x in updates),
 raw_unchanged_ahead_compatible=sum(not x['changed'] and x['private_ahead'] and x['compatible'] for x in updates),raw_unchanged_ahead_incompatible=sum(not x['changed'] and x['private_ahead'] and not x['compatible'] for x in updates),
 nonempty_unchanged_retained_ahead=sum(c['nonempty_unchanged_retained_ahead'] for c in cells),visible_audio_rollbacks=sum(c['metrics']['visible_audio_rollbacks'] for c in cells),quality=quality)
 row['quality']['CER']=quality['character_edits']/quality['reference_characters'];table.append(row)
r=dict(scope='formal12 only; nonempty gate matches frozen original predicate; must-discard counts owner completed-ahead incompatible branches, not necessarily observed visible rollback',table=table)
(T/'final_native_v8_evidence/FORMAL_FEEDBACK_AND_QUALITY_TABLE.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r,indent=2))
