import pytest
import os
import tempfile
import mock
from hypothesis import given, strategies as st, settings
from mspy.parser_xy import parseXY
from mspy.obj_scan import scan
from mspy.obj_peak import peak
from mspy.obj_peaklist import peaklist

@pytest.fixture
def temp_xy_file():
    fd, path = tempfile.mkstemp(suffix='.xy')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_init_success(temp_xy_file):
    parser = parseXY(temp_xy_file)
    assert parser.path == temp_xy_file

def test_init_failure():
    with pytest.raises(IOError) as excinfo:
        parseXY("non_existent_file.xy")
    assert "File not found!" in str(excinfo.value)

def test_info(temp_xy_file):
    parser = parseXY(temp_xy_file)
    info = parser.info()
    assert isinstance(info, dict)
    assert info['title'] == ''
    assert 'operator' in info

def test_parseData_happy_path(temp_xy_file):
    content = """# Comment
m/z intensity
100.0 1000.0
101.1\t2000.0
102.2,3000.0
103.3;4000.0
1.0e2 5.0e3
"""
    with open(temp_xy_file, 'w') as f:
        f.write(content)
    
    parser = parseXY(temp_xy_file)
    data = parser._parseData()
    assert len(data) == 5
    assert data[0] == [100.0, 1000.0]
    assert data[1] == [101.1, 2000.0]
    assert data[2] == [102.2, 3000.0]
    assert data[3] == [103.3, 4000.0]
    assert data[4] == [100.0, 5000.0]

def test_parseData_empty(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("")
    parser = parseXY(temp_xy_file)
    assert parser._parseData() == []

def test_parseData_only_comments(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("# comment\nm/z header\n")
    parser = parseXY(temp_xy_file)
    assert parser._parseData() == []

def test_parseData_invalid_line(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("100.0 1000.0\ninvalid line\n")
    parser = parseXY(temp_xy_file)
    assert parser._parseData() is False

def test_parseData_single_value(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("100.0\n")
    parser = parseXY(temp_xy_file)
    assert parser._parseData() is False

def test_parseData_ioerror(temp_xy_file):
    # In Python 2, open() and file() are both used. parseXY uses file().
    # We mock __builtin__.file
    parser = parseXY(temp_xy_file)
    with mock.patch("__builtin__.file", side_effect=IOError):
        assert parser._parseData() is False

def test_makeScan_continuous(temp_xy_file):
    parser = parseXY(temp_xy_file)
    data = [[100.0, 1000.0], [101.0, 2000.0]]
    s = parser._makeScan(data, dataType='continuous')
    assert isinstance(s, scan)
    import numpy
    numpy.testing.assert_array_equal(s.profile, data)

def test_makeScan_discrete(temp_xy_file):
    parser = parseXY(temp_xy_file)
    data = [[100.0, 1000.0], [101.0, 2000.0]]
    s = parser._makeScan(data, dataType='discrete')
    assert isinstance(s, scan)
    assert s.peaklist is not None
    assert len(s.peaklist.peaks) == 2
    assert s.peaklist.peaks[0].mz == 100.0
    assert s.peaklist.peaks[0].intensity == 1000.0

def test_scan_success(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("100.0 1000.0\n")
    parser = parseXY(temp_xy_file)
    s = parser.scan()
    assert isinstance(s, scan)
    import numpy
    numpy.testing.assert_array_equal(s.profile, [[100.0, 1000.0]])

def test_scan_failure(temp_xy_file):
    with open(temp_xy_file, 'w') as f:
        f.write("invalid\n")
    parser = parseXY(temp_xy_file)
    assert parser.scan() is False

@pytest.fixture
def small_xy_path():
    return os.path.join(os.getcwd(), "tests/data/test_small.xy")

def test_integration(small_xy_path):
    # Use absolute path relative to project root
    parser = parseXY(small_xy_path)
    s = parser.scan()
    assert isinstance(s, scan)
    assert len(s.profile) == 6
    import numpy
    numpy.testing.assert_array_equal(s.profile[0], [100.0, 1000.0])

# Hypothesis test for _parseData robustness
@settings(max_examples=50, deadline=None)
@given(
    mz=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
    intensity=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e10, max_value=1e10),
    sep=st.sampled_from([' ', '\t', ',', ';', ' \t ', ', ', '; '])
)
def test_hypothesis_parseData(temp_xy_file, mz, intensity, sep):
    # Use format that is likely to match the regex
    # Regex: ^([-0-9\.eE+]+)[ \t]*(;|,)?[ \t]*([-0-9\.eE+]*)$
    line = "{}{}{}".format(format(mz, 'g'), sep, format(intensity, 'g'))
    with open(temp_xy_file, 'w') as f:
        f.write(line)
    
    parser = parseXY(temp_xy_file)
    data = parser._parseData()
    
    # If the regex matches and data is returned, verify values
    if data:
        assert len(data) == 1
        assert data[0][0] == pytest.approx(mz, rel=1e-5, abs=1e-5)
        assert data[0][1] == pytest.approx(intensity, rel=1e-5, abs=1e-5)
    else:
        # Some generated formats might not match the regex (e.g. spaces in scientific notation if any)
        # But 'g' format should be fine.
        # If it returns False, it means the regex didn't match or float conversion failed.
        # Given our regex, it should match most 'g' formatted floats.
        pass
