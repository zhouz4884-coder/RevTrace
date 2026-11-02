"""Collect bounded terminal CPU sensitivity tables for authoring."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,O
names=['SUMMARY.json','PAPER_DATA.json','GATE.json','RUN_RECORD.json','CONFIG.json','ENVIRONMENT.json','BANK_GRID.csv','SOURCE_GRID.csv','SOURCE_PAIRED_GRID.csv','SOURCE_PAIRED_D2.csv','REPEAT_PAIRED_D2.csv','BANK_FULL_CDF.csv','SOURCE_FULL_CDF.csv','ORIGINAL_D2_CHECKS.csv']
out=E/'sensitivity/RESULTS_v1';rows=[]
with Remote() as c:
    for name in names:
        b=c.get(O+'/sensitivity_v1/'+name,out/name)
        rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
record=dict(gate='PASS_BOUNDED_SENSITIVITY_TRANSFER',files=len(rows),bytes=sum(r['bytes'] for r in rows),rows=rows)
p=E/'sensitivity/COLLECTION_v1.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in record.items() if k!='rows'}))
