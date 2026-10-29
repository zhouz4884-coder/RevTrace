import copy,json,struct,unittest
from encoder_wire import encode,decode
from run_profile import audit,all_true,economics,check_provenance

class WireTests(unittest.TestCase):
    def setUp(self):
        self.identity={'weights_sha':'a'*64,'precision':'float32'}
        self.prov=dict(worker_gpu=0,job_id='j1',source_id='s',full_birth_start_sha='b'*64,target=100)
        self.w=encode(struct.pack('<4f',1,-2,3,4),shape=(1,2,2),mel_sha256='c'*64,identity=self.identity,provenance=self.prov)
    def test_roundtrip_bits(self):
        h,b=decode(self.w,expected_identity=self.identity,expected_mel='c'*64,expected_shape=(1,2,2));self.assertEqual(struct.unpack('<4f',b),(1,-2,3,4))
    def test_data_corruption(self):
        with self.assertRaises(ValueError):decode(self.w[:-1]+bytes([self.w[-1]^1]))
    def test_truncation(self):
        with self.assertRaises(ValueError):decode(self.w[:-4])
    def test_unknown_identity(self):
        with self.assertRaises(ValueError):decode(self.w,expected_identity={'weights_sha':'d'*64})
    def test_changed_actual_mel(self):
        with self.assertRaises(ValueError):decode(self.w,expected_mel='e'*64)
    def test_shape(self):
        with self.assertRaises(ValueError):decode(self.w,expected_shape=(1,1,4))
    def test_header_bounds(self):
        with self.assertRaises(ValueError):decode(struct.pack('<I',999999999)+self.w[4:])
    def test_output_type(self):
        with self.assertRaises(ValueError):decode(bytearray(self.w))
    def test_zero_shape(self):
        with self.assertRaises(ValueError):encode(b'',shape=(1,0,2),mel_sha256='c',identity={},provenance={})
    def test_extra_header_semantics(self):
        n=struct.unpack_from('<I',self.w)[0];h=json.loads(self.w[4:4+n]);h['forged_C_U_completed']=True;b=json.dumps(h).encode()
        with self.assertRaises(ValueError):decode(struct.pack('<I',len(b))+b+self.w[n+4:])
    def test_owned_channel_and_birth(self):
        h,_=decode(self.w);r=dict(physical_channel_gpu=0,gpu=0,frozen_start_sha='b'*64);cmd=dict(job_id='j1',source_id='s',end=100)
        check_provenance(h,r,cmd,0)
        for field in ('worker_gpu','job_id','source_id','target','full_birth_start_sha'):
            bad=copy.deepcopy(h);bad['execution_provenance'][field]='bad'
            with self.assertRaises(ValueError):check_provenance(bad,r,cmd,0)

class OracleCostTests(unittest.TestCase):
    def test_complete_oracle_not_ids_only(self):
        expected=dict(end={'tokens':[1],'context':'a'},token_ids=[1],selected_correction={'choice':'a'})
        result=dict(end=expected['end'],record=dict(token_ids=[1],selected_correction={'choice':'a'}),full_infer_completed=True)
        self.assertTrue(all_true(audit(result,expected)))
        for key in ('end','selected_correction','token_ids'):
            bad=copy.deepcopy(result)
            if key=='end':bad['end']['context']='b'
            else:bad['record'][key]=None
            self.assertFalse(all_true(audit(bad,expected)))
    def test_absent_completion_rejected(self):
        self.assertFalse(all_true(audit(dict(record={}),dict(end={},token_ids=[],selected_correction=None))))
    def pairs(self,export):
        return [dict(wrong=dict(encoder=dict(actual_capture_export_seconds=export,mel_hash_seconds=0)),producer_to_parent_receipt_seconds=0,parent_wire_decode_seconds=0,
            received=dict(command_received_perf=.02,parent_dispatch_perf=0,encoder=dict(actual_import_verify_finite_seconds=.03,mel_hash_seconds=0)),baseline=dict(encoder=dict(encoder_seconds=.4))) for _ in range(4)]
    def test_four_hits_do_not_make_four_free_exports(self):
        r=economics(self.pairs(.05));self.assertAlmostEqual(r['expected_all14_capture_and_export_seconds'],.7);self.assertAlmostEqual(r['expected_net_work_margin_seconds'],.7)
    def test_internal_hits_can_have_negative_net_cost(self):
        r=economics(self.pairs(.2));self.assertLess(r['expected_net_work_margin_seconds'],0);self.assertFalse(r['plausible_compute_margin_at_least_100ms'])
    def test_100ms_gate_preserves_measured_cost(self):
        r=economics(self.pairs(.1));self.assertAlmostEqual(r['expected_net_work_margin_seconds'],0);self.assertFalse(r['plausible_compute_margin_at_least_100ms'])

if __name__=='__main__':unittest.main()
