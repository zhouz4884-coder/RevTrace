"""Inspect only official metadata documentation and speaker-info header."""
import json,sys
from pathlib import Path

CODE=r'''
import hashlib,io,json,pathlib,tarfile,zipfile,xml.etree.ElementTree as ET
p=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/metadata_options_v1/magicdata_metadata.tar.gz')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='1f71e2dfea4706e76177158a6d45f2be838042af5ecc442f447f8369d40764c9'
rows=[];ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with tarfile.open(p,'r:gz') as tar:
 for name in ('Usage_Instruction.txt','SPKINFO.txt','MAGICDATA_Mandarin_Chinese_Read_Speech.docx'):
  raw=tar.extractfile(name).read();tables=None
  if name.endswith('.docx'):
   with zipfile.ZipFile(io.BytesIO(raw)) as doc:
    root=ET.fromstring(doc.read('word/document.xml'))
    text='\n'.join(''.join(t.text or '' for t in row.iter(ns+'t')) for row in root.iter(ns+'p'))
    tables=[[[''.join(t.text or '' for t in cell.iter(ns+'t')) for cell in tr.findall(ns+'tc')] for tr in tbl.findall(ns+'tr')] for tbl in root.iter(ns+'tbl')]
  else:text=raw.decode('utf-8-sig')
  rows.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),text=text if name!='SPKINFO.txt' else '\n'.join(text.splitlines()[:4]),speaker_info_lines=len(text.splitlines()) if name=='SPKINFO.txt' else None,tables=tables))
print(json.dumps(dict(scope='official metadata documentation/speaker header only; scp/audio/transcript contents unopened',rows=rows)))
'''

def main():
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        i,o,e=c.exec_command('python3 -B -',timeout=60);i.write(CODE);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace')
        x=json.loads(raw);p=Path(__file__).resolve().parents[1]/'review/MAGICDATA_METADATA_DOCUMENTS_v1.json';assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf8');print(json.dumps(x,indent=2,ensure_ascii=True))
    finally:c.close()

if __name__=='__main__':main()
