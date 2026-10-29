"""Typed binary feature carrier. Integrity checks do not authenticate a channel."""
import hashlib,json,math,struct
PROTOCOL='protected_original_audio_encoder_fp32_v1'
MAX_BYTES=32*1024*1024
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def encode(data,*,shape,mel_sha256,identity,provenance):
    shape=list(shape)
    if len(shape)!=3 or any(type(n)!=int or n<=0 for n in shape):raise ValueError('feature shape')
    if len(data)!=math.prod(shape)*4 or len(data)>MAX_BYTES:raise ValueError('feature bytes')
    header=dict(protocol=PROTOCOL,dtype='float32-le',shape=shape,bytes=len(data),
        feature_sha256=hashlib.sha256(data).hexdigest(),mel_sha256=mel_sha256,
        encoder_identity=identity,execution_provenance=provenance)
    h=canonical(header).encode();return struct.pack('<I',len(h))+h+data
def decode(wire,*,expected_identity=None,expected_mel=None,expected_shape=None):
    if not isinstance(wire,bytes) or len(wire)<4:raise ValueError('wire type/length')
    n=struct.unpack_from('<I',wire)[0]
    if n>1024*1024 or n<2 or n+4>len(wire):raise ValueError('header bounds')
    h=json.loads(wire[4:4+n]);data=wire[4+n:]
    if set(h)!=set(('protocol','dtype','shape','bytes','feature_sha256','mel_sha256','encoder_identity','execution_provenance')):raise ValueError('header keys')
    if h['protocol']!=PROTOCOL or h['dtype']!='float32-le':raise ValueError('protocol/dtype')
    if len(h['shape'])!=3 or any(type(x)!=int or x<=0 for x in h['shape']):raise ValueError('shape')
    if len(data)!=h['bytes'] or len(data)!=math.prod(h['shape'])*4 or len(data)>MAX_BYTES:raise ValueError('data bounds')
    if hashlib.sha256(data).hexdigest()!=h['feature_sha256']:raise ValueError('feature digest')
    if expected_identity is not None and h['encoder_identity']!=expected_identity:raise ValueError('encoder identity')
    if expected_mel is not None and h['mel_sha256']!=expected_mel:raise ValueError('actual mel input mismatch')
    if expected_shape is not None and h['shape']!=list(expected_shape):raise ValueError('expected shape')
    return h,data
