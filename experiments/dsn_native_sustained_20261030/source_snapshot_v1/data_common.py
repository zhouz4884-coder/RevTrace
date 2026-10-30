"""Standard-library provenance and exact public-ZIP/PCM utilities; no models."""
import hashlib,io,json,pathlib,struct,subprocess,wave,zlib

def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def read(path):return json.loads(pathlib.Path(path).read_bytes())
def put(path,value):pathlib.Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8'))

def verify_source(root,manifest_path,expected):
 root=pathlib.Path(root).resolve();manifest=read(manifest_path)
 run=lambda *args:subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
 if run('rev-parse','HEAD')!=manifest['source_commit'] or manifest['source_commit']!=expected:raise ValueError('source commit differs')
 if run('status','--porcelain','--untracked-files=all'):raise ValueError('source checkout dirty')
 if {p for p in run('ls-files','-z').split('\0') if p}!={r['path'] for r in manifest['files']}:raise ValueError('source manifest incomplete')
 for row in manifest['files']:
  p=root/row['path']
  if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('source bytes differ: '+row['path'])
 return dict(source_commit=expected,source_manifest_sha256=sha(manifest_path),files=len(manifest['files']),source_clean=True)

def extract_member(raw,entry):
 if len(raw)<30:raise ValueError('truncated ZIP local header')
 header=struct.unpack_from('<4s5H3L2H',raw)
 if header[0]!=b'PK\x03\x04' or header[3]!=entry['method']:raise ValueError('ZIP header/method differs')
 start=30+header[-2]+header[-1]
 if start>4096 or raw[30:30+header[-2]].decode('utf8')!=entry['path']:raise ValueError('ZIP member name/header span differs')
 body=raw[start:start+entry['compressed']]
 if len(body)!=entry['compressed']:raise ValueError('truncated ZIP member')
 data=zlib.decompress(body,-15) if entry['method']==8 else body if entry['method']==0 else None
 if data is None or len(data)!=entry['bytes'] or zlib.crc32(data)!=entry['crc32']:raise ValueError('ZIP CRC/size differs')
 return data

def inspect_wave(data):
 with wave.open(io.BytesIO(data)) as w:
  header=dict(channels=w.getnchannels(),sample_width=w.getsampwidth(),sample_rate=w.getframerate(),frames=w.getnframes(),compression=w.getcomptype())
  pcm=w.readframes(w.getnframes())
 if header['channels']!=1 or header['sample_width']!=2 or header['sample_rate']!=16000 or header['compression']!='NONE' or header['frames']<=0:raise ValueError('requires positive PCM16 mono16k source')
 if len(pcm)!=2*header['frames']:raise ValueError('truncated PCM')
 return dict(header,PCM_sha256=hashlib.sha256(pcm).hexdigest(),duration=header['frames']/16000),pcm

def joined_wave(pcms):
 if not pcms or any(not p or len(p)%2 for p in pcms):raise ValueError('requires nonempty PCM16 pieces')
 out=io.BytesIO()
 with wave.open(out,'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
  for p in pcms:w.writeframesraw(p)
 return out.getvalue()
