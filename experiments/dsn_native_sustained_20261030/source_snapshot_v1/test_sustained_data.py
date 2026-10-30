import hashlib,io,json,pathlib,struct,subprocess,tempfile,unittest,wave,zlib
from data_common import extract_member,inspect_wave,joined_wave,sha,verify_source
from select_recipe import select,EXCLUDED
from acquire_recipe import source_references

def metadata():
 return [dict(path=f'StreamCorrect/aishell1_testset/BAC009S{speaker:04d}W{i:04d}.wav',bytes=9*32000+44,method=8,compressed=25,local_offset=i*100,crc32=i) for speaker in (1001,1002,1003,1004) for i in range(1,29)]
def pcm_wave(pcm=b'\x01\x00\x02\x00',channels=1,rate=16000,width=2):
 b=io.BytesIO()
 with wave.open(b,'wb') as w:w.setnchannels(channels);w.setsampwidth(width);w.setframerate(rate);w.writeframes(pcm)
 return b.getvalue()
def member(data):
 name='StreamCorrect/aishell1_testset/BAC009S1001W0001.wav';c=zlib.compressobj(wbits=-15);compressed=c.compress(data)+c.flush();crc=zlib.crc32(data)
 h=struct.pack('<4s5H3L2H',b'PK\x03\x04',20,0,8,0,0,crc,len(compressed),len(data),len(name.encode()),0)
 return h+name.encode()+compressed,dict(path=name,method=8,compressed=len(compressed),bytes=len(data),crc32=crc)

class DataControls(unittest.TestCase):
 def test_two_by24_unique_and_deterministic(self):
  a=select(metadata(),seed=2026103011);self.assertEqual(a,select(list(reversed(metadata())),seed=2026103011));self.assertEqual(2,len(a['recipes']));self.assertEqual(48,len({x['source_id'] for r in a['recipes'] for x in r['members']}))
 def test_fixed_seed_no_implicit_widen(self):
  with self.assertRaisesRegex(ValueError,'insufficient'):select(metadata()[:28],seed=1)
 def test_excluded_speakers_not_chosen(self):
  e=metadata()+[dict(x,path=x['path'].replace('S1001','S0764')) for x in metadata() if 'S1001' in x['path']];a=select(e,seed=3);self.assertNotIn('S0764',a['eligible_speakers'])
 def test_size_band_is_metadata_only(self):
  e=metadata();e.extend(dict(e[0],path=e[0]['path'].replace('W0001','W9999'),bytes=13*32000+44) for _ in range(1));a=select(e,seed=5);self.assertFalse(any('W9999' in x['path'] for x in a['eligible_pool']))
 def test_insufficient_members_not_replaced(self):
  e=[x for x in metadata() if 'S1001' in x['path'] or int(pathlib.PurePosixPath(x['path']).stem[-4:])<24]
  with self.assertRaises(ValueError):select(e,seed=1)
 def test_wrong_recipe_shape_rejected(self):
  with self.assertRaises(ValueError):select(metadata(),seed=1,members=12)
 def test_duplicate_metadata_rejected(self):
  e=metadata();e.append(e[0].copy())
  with self.assertRaises(ValueError):select(e,seed=1)
 def test_original_zip_deflate_exact(self):
  data=pcm_wave();raw,e=member(data);self.assertEqual(extract_member(raw,e),data)
 def test_zip_crc_mismatch_rejected(self):
  raw,e=member(pcm_wave());e['crc32']^=1
  with self.assertRaises(ValueError):extract_member(raw,e)
 def test_zip_filename_mismatch_rejected(self):
  raw,e=member(pcm_wave());e['path']+='bad'
  with self.assertRaises(ValueError):extract_member(raw,e)
 def test_zip_truncation_rejected(self):
  raw,e=member(pcm_wave())
  with self.assertRaises(ValueError):extract_member(raw[:-2],e)
 def test_nonmono_non16k_rejected(self):
  for data in (pcm_wave(channels=2),pcm_wave(rate=8000),pcm_wave(width=1)):
   with self.assertRaises(ValueError):inspect_wave(data)
 def test_pcm_no_duration_filter(self):
  h,p=inspect_wave(pcm_wave());self.assertEqual(h['frames'],2);self.assertEqual(p,b'\x01\x00\x02\x00')
 def test_concat_exact_no_gap_resample(self):
  pieces=[b'\x01\x00\x02\x00',b'\x03\x00'];h,p=inspect_wave(joined_wave(pieces));self.assertEqual(p,b''.join(pieces));self.assertEqual(h['frames'],3)
 def test_empty_or_unaligned_pcm_rejected(self):
  for p in ([],[b''],[b'x']):
   with self.assertRaises(ValueError):joined_wave(p)
 def test_reference_conflict_rejected(self):
  with self.assertRaises(ValueError):source_references([dict(audio_path='x/a.wav',text_zh='one'),dict(audio_path='x/a.wav',text_zh='two')])
 def test_reference_missing_not_synthesized(self):
  self.assertEqual(source_references([dict(audio_path='x/a.wav',text_zh='one'),dict(audio_path='x/b.wav',text_zh='')]),{'a':'one'})
 def test_complete_git_manifest_and_mutation(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td);f=p/'one.txt';f.write_bytes(b'one\n')
   run=lambda *args:subprocess.run(['git','-C',str(p),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   run('init','-q');run('config','user.name','Sustained CPU control');run('config','user.email','cpu-control@example.invalid');run('config','core.autocrlf','false');run('add','one.txt');run('commit','-qm','synthetic control')
   commit=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip();manifest=p.parent/(p.name+'_manifest.json')
   try:
    manifest.write_text(json.dumps(dict(source_commit=commit,files=[dict(path='one.txt',bytes=4,sha256=sha(f))])))
    self.assertEqual(verify_source(p,manifest,commit)['files'],1);f.write_bytes(b'two\n')
    with self.assertRaises(ValueError):verify_source(p,manifest,commit)
   finally:manifest.unlink(missing_ok=True)
if __name__=='__main__':unittest.main()
