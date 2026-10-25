from make_delivery import write_binary_attributes
import pytest

def test_attributes_are_exact_LF_bytes_on_current_platform(tmp_path):
    p=tmp_path/'.gitattributes'
    write_binary_attributes(p)
    assert p.read_bytes()==b'* -text\n'
    with pytest.raises(FileExistsError):write_binary_attributes(p)
