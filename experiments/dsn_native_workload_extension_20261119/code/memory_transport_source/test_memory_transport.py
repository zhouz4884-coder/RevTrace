import hashlib,io,unittest
from unittest.mock import patch
import memory_transport as m
class Controls(unittest.TestCase):
    def test_exact_piece_boundaries_cover_original_once(self):
        count=(m.SIZE+m.PIECE-1)//m.PIECE;rows=[m.bounds(i)for i in range(count)]
        self.assertEqual(rows[0][0],0);self.assertEqual(rows[-1][1],m.SIZE-1)
        self.assertEqual(sum(b-a+1 for a,b in rows),m.SIZE);self.assertTrue(all(rows[i-1][1]+1==rows[i][0]for i in range(1,count)))
    def test_out_of_range_piece_fails(self):
        for i in (-1,(m.SIZE+m.PIECE-1)//m.PIECE):
            with self.assertRaises(RuntimeError):m.bounds(i)
    def test_piece_response_requires_exact_range_etag_size_hash(self):
        data=b'x'*m.PIECE
        class Response(io.BytesIO):
            url=m.URL;status=206;headers={'Content-Length':str(m.PIECE),'Content-Range':f'bytes {m.PIECE}-{2*m.PIECE-1}/{m.SIZE}','ETag':m.ETAG}
        with patch('urllib.request.urlopen',return_value=Response(data)):
            raw,record=m.fetch(1)
        self.assertEqual(raw,data);self.assertEqual(record['sha256'],hashlib.sha256(data).hexdigest())
    def test_changed_etag_or_short_body_rejected(self):
        class Response(io.BytesIO):
            url=m.URL;status=206;headers={'Content-Length':str(m.PIECE),'Content-Range':f'bytes {m.PIECE}-{2*m.PIECE-1}/{m.SIZE}','ETag':'changed'}
        with patch('urllib.request.urlopen',return_value=Response(b'x')),self.assertRaises(RuntimeError):m.fetch(1)
