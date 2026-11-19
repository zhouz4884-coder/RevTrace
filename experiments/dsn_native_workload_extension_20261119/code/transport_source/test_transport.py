import hashlib,io,pathlib,tempfile,types,unittest
from unittest.mock import patch
import transport as t
class Controls(unittest.TestCase):
    def test_one_file_three_mirrors_and_connection_bounds(self):
        cmd=t.aria_command('/usr/bin/aria2c','input','dir','file',12345)
        self.assertIn('--split=16',cmd);self.assertIn('--max-connection-per-server=6',cmd);self.assertIn('--max-concurrent-downloads=1',cmd)
        self.assertIn('--enable-rpc=false',cmd);self.assertIn('--allow-overwrite=false',cmd)
        self.assertFalse(any(x.startswith('--out=')for x in cmd))
    def test_input_file_has_explicit_per_entry_dir_and_different_part_name(self):
        value=t.aria_input(t.URLS,'/8TB/datasets/original','test_set.tar.gz.multi.part')
        self.assertEqual(value.splitlines(),['\t'.join(t.URLS),' dir=/8TB/datasets/original',' out=test_set.tar.gz.multi.part'])
    def test_actual_aria_exact_byte_log_progress_not_file_size(self):
        with tempfile.TemporaryDirectory()as d:
            p=pathlib.Path(d)/'aria.log';p.write_text('[#2af991 14139392B/2201936013B(0%) CN:16 DL:350829B ETA:1h43m56s]\n')
            value=t.log_progress(p);self.assertEqual(value['completed_bytes'],14139392);self.assertEqual(value['download_bytes_per_second'],350829)
    def test_header_whitelist_does_not_expose_cookie(self):
        self.assertEqual(t.safe_headers({'ETag':'e','Set-Cookie':'secret'}),{'ETag':'e'})
    def test_arbitrary_mirror_rejected_without_network(self):
        with self.assertRaisesRegex(RuntimeError,'nonofficial'):t.probe('https://example.org/x')
    def test_mirror_probe_requires_same_full_asset_identity(self):
        class Response(io.BytesIO):
            url=t.URLS[0];status=206
            headers={'Content-Range':f'bytes 0-65535/{t.SIZE}','ETag':t.ETAG,'Set-Cookie':'never-log'}
        raw=b'x'*65536
        with patch('transport.PREFIX_SHA',hashlib.sha256(raw).hexdigest()),patch('urllib.request.urlopen',return_value=Response(raw)):
            proof=t.probe(t.URLS[0]);self.assertEqual(proof['range_bytes'],65536);self.assertNotIn('Set-Cookie',proof['headers'])
    def test_publish_is_atomic_preserved_original_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'part';q=pathlib.Path(d)/'archive';p.write_bytes(b'unchanged')
            with patch('transport.SIZE',9):r=t.publish(p,q)
            self.assertEqual(q.read_bytes(),p.read_bytes());self.assertEqual(r['sha256'],t.digest(p));self.assertTrue(p.exists())
    def test_different_existing_original_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'part';q=pathlib.Path(d)/'archive';p.write_bytes(b'first');q.write_bytes(b'other')
            with patch('transport.SIZE',5),self.assertRaisesRegex(RuntimeError,'never_overwritten'):t.publish(p,q)
            self.assertEqual(q.read_bytes(),b'other')
    def test_incomplete_transport_never_published(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'part';q=pathlib.Path(d)/'archive';p.write_bytes(b'short')
            with self.assertRaisesRegex(RuntimeError,'incomplete'):t.publish(p,q)
            self.assertFalse(q.exists())
if __name__=='__main__':unittest.main()
