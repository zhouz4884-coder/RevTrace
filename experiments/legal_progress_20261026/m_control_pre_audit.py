"""Inspect formatting confound and same-target native alternative controls."""
from pathlib import Path
import json,tarfile,collections
W=Path(__file__).resolve().parent
def main():
    with tarfile.open(W/'RAW_EVIDENCE.tar.gz') as arc:s=json.load(arc.extractfile('m_gpu_v2/SUMMARY.json'))
    groups=collections.defaultdict(dict);style=[]
    for r in s['rows']:
        groups[r['task'],r['condition'],r['repeat']][r['method']]=r
        if r['split']=='validation' and r['condition']=='current-coherent':
            original=r['proposal']['decoded'];modified=r['returned_candidate']['decoded']
            old=r['proposal']['value']['destination'];new=r['returned_candidate']['value']['destination']
            expected=original.replace(json.dumps(old),json.dumps(new))
            style.append(dict(task=r['task'],method=r['method'],repeat=r['repeat'],original=original,returned=modified,
                content_only_expected=expected,format_preserved=expected==modified))
    compared=[]
    for key,g in groups.items():
        ref=g['trusted-regenerate-occ']['selected']
        for method in ['standard-strict-occ','revtrace-strict']:
            r=g[method]['selected'];compared.append(dict(task=key[0],condition=key[1],repeat=key[2],method=method,
                identical_processed_request=r['request_identity']==ref['request_identity'],full_Z_equal=r['new_tokens']==ref['new_tokens'],value_equal=r['value']==ref['value']))
    result=dict(status='COMPLETE_CPU_CONFOUND_AND_NATIVE_ALTERNATIVE_AUDIT',format_cases=len(style),format_preserved=sum(r['format_preserved'] for r in style),
        format_rows=style,native_comparisons=compared,identical_target_requests=sum(r['identical_processed_request'] for r in compared),
        full_Z_matches=sum(r['full_Z_equal'] for r in compared),
        next_gate='If formatting is not preserved, add a bounded validation current-content-only return substitution control; preserve full original320 matrix.')
    (W/'M_CONTROL_PREAUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['format_rows','native_comparisons']}))
if __name__=='__main__':main()
