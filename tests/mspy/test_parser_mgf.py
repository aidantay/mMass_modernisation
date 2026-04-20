import pytest
import os
from mspy.parser_mgf import parseMGF

# Step 1: Setup Test Module
# Step 2: Test Initialization & IO Errors

def test_init_valid_file():
    """Verify successful instantiation with a valid file."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    assert parser.path == path
    assert parser._scans is None
    assert parser._scanlist is None

def test_init_invalid_file():
    """Verify OSError when the instantiated path does not exist."""
    path = 'non_existent_file.mgf'
    with pytest.raises(OSError) as excinfo:
        parseMGF(path)
    assert 'File not found!' in str(excinfo.value)

def test_parseData_ioerror(mocker):
    """Verify that _parseData() returns False on OSError during file read."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    
    # Mocking 'builtins.open' to raise OSError
    mocker.patch('builtins.open', side_effect=OSError("Mocked IO Error"))
    
    result = parser._parseData()
    assert result is False
    assert parser._scans == {}
    assert parser._scanlist is None

# Step 3: Test Metadata and Basic Accessors

def test_info():
    """Verify info() returns a dictionary with expected keys and empty strings."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    info = parser.info()
    expected_keys = ['title', 'operator', 'contact', 'institution', 'date', 'instrument', 'notes']
    assert isinstance(info, dict)
    for key in expected_keys:
        assert key in info
        assert info[key] == ''

def test_load():
    """Verify load() executes and populates _scans."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    assert parser._scans is None
    parser.load()
    assert isinstance(parser._scans, dict)
    assert len(parser._scans) > 0
    assert 0 in parser._scans
    assert parser._scans[0]['title'] == 'Test Scan'

# Step 4: Test MGF Parsing Logic (_parseData)

def test_parseData_comments(mocker):
    """Verify that comments and blank lines are skipped during parsing."""
    mock_content = (
        "# Comment\n"
        "; Another comment\n"
        "! Bang comment\n"
        "/ Slash comment\n"
        "\n"
        "BEGIN IONS\n"
        "100.0 1000.0\n"
        "END IONS"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    
    assert 0 in parser._scans
    assert len(parser._scans[0]['data']) == 1
    assert parser._scans[0]['data'][0] == [100.0, 1000.0]

def test_parseData_headers(mocker):
    """Verify parsing of various header formats including invalid ones."""
    mock_content = (
        "BEGIN IONS\n"
        "TITLE=Test Title\n"
        "PEPMASS=100.0\n"
        "CHARGE=2+\n"
        "100.0 1000.0\n"
        "END IONS\n"
        "BEGIN IONS\n"
        "PEPMASS=Invalid\n"
        "CHARGE=3-\n"
        "200.0 2000.0\n"
        "END IONS\n"
        "BEGIN IONS\n"
        "CHARGE=Invalid\n"
        "300.0 3000.0\n"
        "END IONS"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    
    # Scan 0
    assert parser._scans[0]['title'] == 'Test Title'
    assert parser._scans[0]['precursorMZ'] == 100.0
    assert parser._scans[0]['precursorCharge'] == 2
    
    # Scan 1
    # Note: Invalid floats/ints fail silently due to 'except: pass'
    assert parser._scans[1].get('precursorMZ') is None
    assert parser._scans[1]['precursorCharge'] == -3
    
    # Scan 2
    assert parser._scans[2].get('precursorCharge') is None

def test_parseData_points(mocker):
    """Verify parsing of data points with valid and invalid values."""
    # Note: re.split('[ \t]?') in Python 2.7 only splits on non-empty matches.
    # Note: 'except ValueError, IndexError: pass' in Python 2.7 catches ValueError 
    # and names it IndexError, but it does NOT catch actual IndexError.
    # Lines with only one value (e.g. "300.0") would crash with IndexError
    # because strip() removes all spaces and parts[1] would not exist.
    mock_content = (
        "BEGIN IONS\n"
        "100.0 500.0\n"      # Valid
        "Invalid 500.0\n"    # Invalid m/z, skip line
        "200.0 Invalid\n"    # Invalid intensity, fallback to 100.0 (triggers ValueError)
        "END IONS"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    
    data = parser._scans[0]['data']
    assert len(data) == 2
    assert data[0] == [100.0, 500.0]
    assert data[1] == [200.0, 100.0] # Fallback

def test_parseData_multiple_scans(mocker):
    """Verify that multiple BEGIN IONS blocks are handled correctly."""
    mock_content = (
        "BEGIN IONS\n"
        "TITLE=Scan 1\n"
        "100.0 1000.0\n"
        "END IONS\n"
        "BEGIN IONS\n"
        "TITLE=Scan 2\n"
        "200.0 2000.0\n"
        "END IONS"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    
    assert len(parser._scans) == 2
    assert parser._scans[0]['title'] == 'Scan 1'
    assert parser._scans[1]['title'] == 'Scan 2'
    assert parser._scans[0]['scanNumber'] == 0
    assert parser._scans[1]['scanNumber'] == 1

# Step 5: Test Data Access and Object Creation (scan, scanlist, _makeScan)

def test_scanlist_caching(mocker):
    """Verify calling scanlist() twice relies on populated _scanlist."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    
    # First call: parses data and populates _scanlist
    scanlist1 = parser.scanlist()
    assert parser._scanlist is not None
    assert len(scanlist1) > 0
    
    # Mock _parseData to ensure it's not called again
    mocker.patch.object(parser, '_parseData')
    
    # Second call: should use cached _scanlist
    scanlist2 = parser.scanlist()
    parser._parseData.assert_not_called()
    assert scanlist1 == scanlist2

def test_scan_empty(mocker):
    """Verify scan() returns False if no valid scans found."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    # Mock _parseData to clear _scans
    mocker.patch.object(parser, '_parseData', side_effect=lambda: setattr(parser, '_scans', {}))
    
    assert parser.scan() is False

def test_scan_default_and_id():
    """Verify retrieving scans with scanID=None (defaults to 0) and scanID=0."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    
    scan_default = parser.scan(scanID=None)
    scan_0 = parser.scan(scanID=0)
    
    assert scan_default.scanNumber == 0
    assert scan_0.scanNumber == 0
    assert scan_default.title == scan_0.title

def test_makeScan_peaklist():
    """Verify scan(dataType='peaklist') creates a peaklist scan."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_small.mgf')
    parser = parseMGF(path)
    
    # DataType='peaklist'
    scan = parser.scan(dataType='peaklist')
    assert scan.haspeaks() is True
    assert scan.hasprofile() is False
    assert len(scan.peaklist) > 0

def test_makeScan_profile():
    """Verify scan(dataType='profile') creates a profile scan."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_small.mgf')
    parser = parseMGF(path)
    
    # DataType='profile'
    scan = parser.scan(dataType='profile')
    assert scan.haspeaks() is False
    assert scan.hasprofile() is True
    assert len(scan.profile) > 0

def test_makeScan_large_data():
    """Verify scan(dataType=None) on large data triggers profile mode."""
    path = os.path.join(os.path.dirname(__file__), '../data/test_large.mgf')
    parser = parseMGF(path)
    
    # DataType=None, points > 3000 should trigger profile
    # Scan 1 should have > 3000 points
    scan = parser.scan(scanID=1, dataType=None)
    assert scan.haspeaks() is False
    assert scan.hasprofile() is True
    assert len(scan.profile) > 3000

def test_scan_other_id(mocker):
    """Verify retrieving a scan with a specific scanID."""
    mock_content = (
        "BEGIN IONS\nTITLE=Scan 0\n100.0 1000.0\nEND IONS\n"
        "BEGIN IONS\nTITLE=Scan 1\n200.0 2000.0\nEND IONS\n"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    scan1 = parser.scan(scanID=1)
    assert scan1.scanNumber == 1
    assert scan1.title == "Scan 1"

def test_parseData_empty_file(mocker):
    """Verify _parseData handles a file with no valid scan data."""
    mock_content = "# Only comments\n\n"
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    assert parser._scans == {}
    assert parser._scanlist is None

def test_parseData_unknown_header(mocker):
    """Verify unknown headers are skipped."""
    mock_content = (
        "BEGIN IONS\n"
        "UNKNOWN=Value\n"
        "100.0 1000.0\n"
        "END IONS"
    )
    path = "mock.mgf"
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=mock_content))
    
    parser = parseMGF(path)
    parser._parseData()
    assert 0 in parser._scans
    assert len(parser._scans[0]['data']) == 1

def test_scan_invalid_id():
    """Verify scan() raises UnboundLocalError when scanID is not found."""
    # This is a known bug in the source code where 'data' remains undefined.
    path = os.path.join(os.path.dirname(__file__), '../data/test_tiny.mgf')
    parser = parseMGF(path)
    with pytest.raises(UnboundLocalError):
        parser.scan(scanID=999)
