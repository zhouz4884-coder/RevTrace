"""Byte identity and complete object identity are distinct launch obligations."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from joint_recount import verify_fixture_identity

class FixtureIdentityTests(unittest.TestCase):
    def fixture(self,root):
        original=root/'original.json';episode=root/'episode';episode.mkdir()
        value={'schema':'physical-retirement-f2-input-fixture-v1','targets':{'0:3':{'donor_index':2}},'donors':[{'tokens':[11,22]}]}
        original.write_text(json.dumps(value,sort_keys=True,separators=(',',':')),encoding='utf8')
        copied=episode/'fixture.json';copied.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        return original,copied,episode,dict(fixture=str(original),fixture_sha256=sha(original)),dict(fixture_sha256=sha(copied)),sha

    def test_reformatted_but_complete_object_equal_is_accepted(self):
        with tempfile.TemporaryDirectory() as name:
            original,copied,episode,cell,frozen,sha=self.fixture(Path(name))
            self.assertNotEqual(sha(original),sha(copied))
            verify_fixture_identity(cell,episode,frozen)

    def test_changed_original_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            original,copied,episode,cell,frozen,sha=self.fixture(Path(name));original.write_text('{}',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'original fixture bytes'):verify_fixture_identity(cell,episode,frozen)

    def test_changed_run_copy_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            original,copied,episode,cell,frozen,sha=self.fixture(Path(name));copied.write_text('{}',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'materialized fixture bytes'):verify_fixture_identity(cell,episode,frozen)

    def test_equal_rehashed_but_semantically_changed_copy_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            original,copied,episode,cell,frozen,sha=self.fixture(Path(name));value=json.loads(copied.read_text());value['donors'][0]['tokens']=[11,23]
            copied.write_text(json.dumps(value),encoding='utf8');frozen['fixture_sha256']=sha(copied)
            with self.assertRaisesRegex(ValueError,'materialized fixture object'):verify_fixture_identity(cell,episode,frozen)

if __name__=='__main__':unittest.main()
