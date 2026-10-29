"""Prepare verified references for the protected new draft; no body edits."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];T=Path(__file__).resolve().parent
paper=R/'Paper_DSN/revisions/20261028_dsn2027_progress'
src=T/'NOVELTY_NEIGHBORS_ROUND3.bib'
near=re.sub(r'^  note = \{.*\}\n','',src.read_text(encoding='utf8'),flags=re.M)
extra=r'''
@inproceedings{vu2026streamcorrect,
  author = {Vu, Tung D. and Xie, Zeying and Zhao, Weiwei and Wei, Victor Junqiu and Jiang, Di and Fung, Yi R.},
  title = {{StreamCorrect}: Self-Supervised Error Correction for Real-Time {ASR} with Offline Recognizers},
  booktitle = {Proceedings of the 2026 Conference on Empirical Methods in Natural Language Processing: Industry Track},
  year = {2026},
  month = oct,
  pages = {2391--2403},
  publisher = {Association for Computational Linguistics},
  url = {https://aclanthology.org/2026.emnlp-industry.142/}
}

@misc{zhang2026retire,
  author = {Zhang, Yanxin and Sharma, Rahul and Vegesna, Nitin and Fu, Zheyu and Liu, Chang and Krishnamurthy, Trivikram},
  title = {Serving a Revisable World: Versioned Execution for Interruptible Agents},
  year = {2026},
  eprint = {2610.01160},
  archivePrefix = {arXiv},
  primaryClass = {cs.DC},
  doi = {10.48550/arXiv.2610.01160},
  url = {https://arxiv.org/abs/2610.01160v1}
}
'''
out=paper/'coordination_refs.bib'
assert not out.exists()
out.write_text(near+extra,encoding='utf8',newline='\n')
keys=re.findall(r'@\w+\s*\{\s*([^,\s]+)',out.read_text())
other='\n'.join((paper/n).read_text(encoding='utf8') for n in ['refs.bib','formal_refs.bib'])
assert len(keys)==len(set(keys))==8 and not set(keys)&set(re.findall(r'@\w+\s*\{\s*([^,\s]+)',other))
record=dict(status='BIBLIOGRAPHY_PREPARATION_ONLY_BODY_UNCHANGED',verified_date='2026-10-29',keys=keys,
  file=str(out.relative_to(R)),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
  original_six_metadata='NOVELTY_NEIGHBORS_ROUND3_METADATA.json',
  newly_verified=[dict(key='vu2026streamcorrect',primary_url='https://aclanthology.org/2026.emnlp-industry.142/',fields='authors,title,venue,year,month,pages,publisher; no DOI supplied by official page'),
                 dict(key='zhang2026retire',primary_url='https://arxiv.org/abs/2610.01160v1',fields='authors,title,v1date,arxivID,DOI')],
  existing_references_rechecked=[dict(key='shi2026qwen3asr',primary_url='https://arxiv.org/abs/2601.21337'),dict(key='bu2017aishell',primary_url='https://openslr.org/33/')])
(T/'BIBLIOGRAPHY_PREPARATION_v1.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status=record['status'],references=len(keys),keys=keys)))
