from pathlib import Path

import pytest

from mmass.mspy import parser_mgf

# Step 1: Setup Test Module
# Step 2: Test Initialization & IO Errors


class TestParseMGF:
    """Tests for ParseMGF class."""

    def test_info(self):
        """Verify info() returns a dictionary with expected keys and empty strings."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        info = parser.info()
        expected_keys = ['title', 'operator', 'contact', 'institution', 'date', 'instrument', 'notes']
        assert isinstance(info, dict)
        for key in expected_keys:
            assert key in info
            assert info[key] == ''

    def test_init_invalid_file(self):
        """Verify OSError when the instantiated path does not exist."""
        path = 'non_existent_file.mgf'
        with pytest.raises(OSError, match='File not found!'):
            parser_mgf.ParseMGF(path)

    def test_init_valid_file(self):
        """Verify successful instantiation with a valid file."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        assert parser.path == Path(path)
        assert parser._scans is None
        assert parser._scanlist is None

    def test_load(self):
        """Verify load() executes and populates _scans."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        assert parser._scans is None
        parser.load()
        assert isinstance(parser._scans, dict)
        assert len(parser._scans) > 0
        assert 0 in parser._scans
        assert parser._scans[0]['title'] == 'Test Scan'

    def test_makeScan_large_data(self):
        """Verify Scan(dataType=None) on large data triggers profile mode."""
        path = str(Path(__file__).parent / '../../data/test_large.mgf')
        parser = parser_mgf.ParseMGF(path)
        scan = parser.scan(scanID=1, dataType=None)
        assert scan.haspeaks() is False
        assert scan.hasprofile() is True
        assert len(scan.profile) > 3000

    def test_makeScan_peaklist(self):
        """Verify Scan(dataType='peaklist') creates a peaklist scan."""
        path = str(Path(__file__).parent / '../../data/test_small.mgf')
        parser = parser_mgf.ParseMGF(path)
        scan = parser.scan(dataType='peaklist')
        assert scan.haspeaks() is True
        assert scan.hasprofile() is False
        assert len(scan.peaklist) > 0

    def test_makeScan_profile(self):
        """Verify Scan(dataType='profile') creates a profile scan."""
        path = str(Path(__file__).parent / '../../data/test_small.mgf')
        parser = parser_mgf.ParseMGF(path)
        scan = parser.scan(dataType='profile')
        assert scan.haspeaks() is False
        assert scan.hasprofile() is True
        assert len(scan.profile) > 0

    def test_parseData_comments(self, mocker):
        """Verify that comments and blank lines are skipped during parsing."""
        mock_content = '# Comment\n; Another comment\n! Bang comment\n/ Slash comment\n\nBEGIN IONS\n100.0 1000.0\nEND IONS'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        assert 0 in parser._scans
        assert len(parser._scans[0]['data']) == 1
        assert parser._scans[0]['data'][0] == [100.0, 1000.0]

    def test_parseData_empty_file(self, mocker):
        """Verify _parseData handles a file with no valid scan data."""
        mock_content = '# Only comments\n\n'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        assert parser._scans == {}
        assert parser._scanlist is None

    def test_parseData_headers(self, mocker):
        """Verify parsing of various header formats including invalid ones."""
        mock_content = 'BEGIN IONS\nTITLE=Test Title\nPEPMASS=100.0\nCHARGE=2+\n100.0 1000.0\nEND IONS\nBEGIN IONS\nPEPMASS=Invalid\nCHARGE=3-\n200.0 2000.0\nEND IONS\nBEGIN IONS\nCHARGE=Invalid\n300.0 3000.0\nEND IONS'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        assert parser._scans[0]['title'] == 'Test Title'
        assert parser._scans[0]['precursorMZ'] == 100.0
        assert parser._scans[0]['precursorCharge'] == 2
        assert parser._scans[1].get('precursorMZ') is None
        assert parser._scans[1]['precursorCharge'] == -3
        assert parser._scans[2].get('precursorCharge') is None

    def test_parseData_ioerror(self, mocker):
        """Verify that _parseData() returns False on OSError during file read."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        mocker.patch('pathlib.Path.open', side_effect=OSError('Mocked IO Error'))
        result = parser._parseData()
        assert result is False
        assert parser._scans == {}
        assert parser._scanlist is None

    def test_parseData_multiple_scans(self, mocker):
        """Verify that multiple BEGIN IONS blocks are handled correctly."""
        mock_content = 'BEGIN IONS\nTITLE=Scan 1\n100.0 1000.0\nEND IONS\nBEGIN IONS\nTITLE=Scan 2\n200.0 2000.0\nEND IONS'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        assert len(parser._scans) == 2
        assert parser._scans[0]['title'] == 'Scan 1'
        assert parser._scans[1]['title'] == 'Scan 2'
        assert parser._scans[0]['scanNumber'] == 0
        assert parser._scans[1]['scanNumber'] == 1

    def test_parseData_points(self, mocker):
        """Verify parsing of data points with valid and invalid values."""
        mock_content = 'BEGIN IONS\n100.0 500.0\nInvalid 500.0\n200.0 Invalid\nEND IONS'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        data = parser._scans[0]['data']
        assert len(data) == 2
        assert data[0] == [100.0, 500.0]
        assert data[1] == [200.0, 100.0]

    def test_parseData_unknown_header(self, mocker):
        """Verify unknown headers are skipped."""
        mock_content = 'BEGIN IONS\nUNKNOWN=Value\n100.0 1000.0\nEND IONS'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        parser._parseData()
        assert 0 in parser._scans
        assert len(parser._scans[0]['data']) == 1

    def test_scan_default_and_id(self):
        """Verify retrieving scans with scanID=None (defaults to 0) and scanID=0."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        scan_default = parser.scan(scanID=None)
        scan_0 = parser.scan(scanID=0)
        assert scan_default.scanNumber == 0
        assert scan_0.scanNumber == 0
        assert scan_default.title == scan_0.title

    def test_scan_empty(self, mocker):
        """Verify Scan() returns False if no valid scans found."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        mocker.patch.object(parser, '_parseData', side_effect=lambda: setattr(parser, '_scans', {}))
        assert parser.scan() is False

    def test_scan_invalid_id(self):
        """Verify Scan() raises UnboundLocalError when scanID is not found."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        with pytest.raises(UnboundLocalError):
            parser.scan(scanID=999)

    def test_scan_other_id(self, mocker):
        """Verify retrieving a scan with a specific scanID."""
        mock_content = 'BEGIN IONS\nTITLE=Scan 0\n100.0 1000.0\nEND IONS\nBEGIN IONS\nTITLE=Scan 1\n200.0 2000.0\nEND IONS\n'
        path = 'mock.mgf'
        mocker.patch('pathlib.Path.exists', return_value=True)
        mocker.patch('pathlib.Path.open', mocker.mock_open(read_data=mock_content))
        parser = parser_mgf.ParseMGF(path)
        scan1 = parser.scan(scanID=1)
        assert scan1.scanNumber == 1
        assert scan1.title == 'Scan 1'

    def test_scanlist_caching(self, mocker):
        """Verify calling scanlist() twice relies on populated _scanlist."""
        path = str(Path(__file__).parent / '../../data/test_tiny.mgf')
        parser = parser_mgf.ParseMGF(path)
        scanlist1 = parser.scanlist()
        assert parser._scanlist is not None
        assert len(scanlist1) > 0
        mocker.patch.object(parser, '_parseData')
        scanlist2 = parser.scanlist()
        parser._parseData.assert_not_called()
        assert scanlist1 == scanlist2

