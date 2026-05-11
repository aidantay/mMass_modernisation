import base64
import struct
import xml.sax
import zlib
from pathlib import Path

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from mmass.mspy import obj_scan, parser_mzml


class TestMZMLHandlers:
    """Tests for SAX handlers in parser_mzml."""

    def test_infoHandler(self):
        """Step 4: Test InfoHandler for metadata extraction and StopParsingError."""
        handler = parser_mzml.InfoHandler()
        handler.startElement('fileDescription', {})
        handler.startElement('cvParam', {'accession': 'MS:1000580', 'name': 'Test Title'})
        handler.startElement('cvParam', {'accession': 'MS:1000586', 'value': 'John Doe'})
        handler.startElement('cvParam', {'accession': 'MS:1000590', 'value': 'Test Inst'})
        handler.startElement('cvParam', {'accession': 'MS:1000589', 'value': 'contact@example.com'})
        assert handler.data['title'] == 'Test Title'
        assert handler.data['operator'] == 'John Doe'
        assert handler.data['institution'] == 'Test Inst'
        assert handler.data['contact'] == 'contact@example.com'
        handler = parser_mzml.InfoHandler()
        handler.startElement('instrumentConfiguration', {})
        handler.startElement('cvParam', {'accession': 'MS:1000169', 'name': 'Mass Spec 2000'})
        assert handler.data['instrument'] == 'Mass Spec 2000'
        with pytest.raises(parser_mzml.StopParsingError):
            handler.endElement('instrumentConfiguration')

    def test_infoHandler_branches(self):
        """Test all branches in InfoHandler."""
        handler = parser_mzml.InfoHandler()
        handler.startElement('fileDescription', {})
        assert handler._isDescription
        handler.startElement('cvParam', {'accession': 'MS:1000580', 'name': 'Title'})
        assert handler.data['title'] == 'Title'
        handler.startElement('cvParam', {'accession': 'MS:1000586', 'value': 'Operator'})
        assert handler.data['operator'] == 'Operator'
        handler.startElement('cvParam', {'accession': 'MS:1000590', 'value': 'Institution'})
        assert handler.data['institution'] == 'Institution'
        handler.startElement('cvParam', {'accession': 'MS:1000589', 'value': 'Contact'})
        assert handler.data['contact'] == 'Contact'
        handler.startElement('cvParam', {'accession': 'OTHER'})
        handler.startElement('other', {})
        handler = parser_mzml.InfoHandler()
        handler.startElement('instrumentConfiguration', {})
        assert handler._isConfig
        handler.startElement('cvParam', {'accession': 'MS:1000169', 'name': 'Instrument'})
        assert handler.data['instrument'] == 'Instrument'
        handler.startElement('cvParam', {'accession': 'OTHER'})
        handler.endElement('other')
        with pytest.raises(parser_mzml.StopParsingError):
            handler.endElement('instrumentConfiguration')

    def test_runHandler(self):
        """Step 4: Test RunHandler for whole run data collection."""
        handler = parser_mzml.RunHandler()
        handler.startElement('spectrum', {'id': 'scan=1'})
        handler.startElement('cvParam', {'name': '32-bit float'})
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'm/z array'})
        handler.startElement('cvParam', {'name': '32-bit float'})
        handler.startElement('binary', {})
        handler.characters('mz1')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        handler.endElement('spectrum')
        handler.startElement('spectrum', {'id': 'scan=2'})
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'intensity array'})
        handler.startElement('cvParam', {'name': '64-bit float'})
        handler.startElement('cvParam', {'name': 'no compression'})
        handler.startElement('binary', {})
        handler.characters('int2')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        handler.endElement('spectrum')
        assert handler.data[1]['mzData'] == 'mz1'
        assert handler.data[1]['mzPrecision'] == 32
        assert handler.data[2]['intData'] == 'int2'
        assert handler.data[2]['intPrecision'] == 64
        assert handler.data[2]['intCompression'] is None

    def test_runHandler_branches(self):
        """Test all branches in RunHandler."""
        handler = parser_mzml.RunHandler()
        handler.startElement('spectrum', {})
        assert None in handler.data
        handler.startElement('precursor', {'spectrumRef': 'scan=0'})
        assert handler.data[None]['parentScanNumber'] == 0
        handler.endElement('precursor')
        handler.startElement('precursor', {})
        handler.startElement('cvParam', {'name': 'selected ion m/z', 'value': '100.5'})
        handler.startElement('cvParam', {'name': 'intensity', 'value': '1000.5'})
        handler.startElement('cvParam', {'name': 'possible charge state', 'value': '2'})
        handler.startElement('cvParam', {'name': 'charge state', 'value': '3'})
        handler.endElement('precursor')
        handler.startElement('binaryDataArray', {})
        handler.startElement('binary', {})
        handler.characters('data')
        handler.endElement('binary')
        handler.startElement('cvParam', {'name': '64-bit float'})
        handler.startElement('cvParam', {'name': '32-bit float'})
        handler.startElement('cvParam', {'name': 'zlib compression'})
        handler.startElement('cvParam', {'name': 'no compression'})
        handler.startElement('cvParam', {'name': 'm/z array'})
        handler.endElement('binaryDataArray')
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'intensity array'})
        handler.startElement('cvParam', {'name': 'unknown binary param'})
        handler.startElement('binary', {})
        handler.characters('int_data')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        handler.startElement('cvParam', {'name': 'profile spectrum'})
        handler.startElement('cvParam', {'name': 'ms level', 'value': '1'})
        handler.startElement('cvParam', {'name': 'positive scan'})
        handler.startElement('cvParam', {'name': 'negative scan'})
        handler.startElement('cvParam', {'name': 'total ion current', 'value': '10.0'})
        handler.startElement('cvParam', {'name': 'base peak m/z', 'value': '5.0'})
        handler.startElement('cvParam', {'name': 'base peak intensity', 'value': '2.0'})
        handler.startElement('cvParam', {'name': 'lowest observed m/z', 'value': '1.0'})
        handler.startElement('cvParam', {'name': 'highest observed m/z', 'value': '10.0'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'minute'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'second'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'unknown'})
        handler.startElement('cvParam', {'name': 'unknown spectrum param'})
        handler.endElement('spectrum')
        handler.endElement('other')

    def test_scanHandler(self):
        """Step 4: Test ScanHandler matching, binary data aggregation, and StopParsingError."""
        handler = parser_mzml.ScanHandler(scanID=1)
        handler.startElement('spectrum', {'id': 'scan=1', 'defaultArrayLength': '10'})
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        handler.startElement('precursor', {'spectrumRef': 'scan=0'})
        handler.startElement('cvParam', {'name': 'possible charge state', 'value': '3'})
        handler.endElement('precursor')
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'm/z array'})
        handler.startElement('cvParam', {'name': '64-bit float'})
        handler.startElement('cvParam', {'name': 'zlib compression'})
        handler.startElement('binary', {})
        handler.characters('encoded_')
        handler.characters('mz_data')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'intensity array'})
        handler.startElement('cvParam', {'name': '32-bit float'})
        handler.startElement('cvParam', {'name': 'no compression'})
        handler.startElement('binary', {})
        handler.characters('encoded_int_data')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        assert handler.data['mzData'] == 'encoded_mz_data'
        assert handler.data['mzPrecision'] == 64
        assert handler.data['mzCompression'] == 'zlib'
        assert handler.data['intData'] == 'encoded_int_data'
        assert handler.data['intPrecision'] == 32
        assert handler.data['intCompression'] is None
        assert handler.data['precursorCharge'] == 3
        with pytest.raises(parser_mzml.StopParsingError):
            handler.endElement('spectrum')

    def test_scanHandler_any_match(self):
        """Step 4: Test ScanHandler matching any scan when scanID is None."""
        handler = parser_mzml.ScanHandler(scanID=None)
        handler.startElement('spectrum', {'id': 'scan=10'})
        assert handler._isMatch
        assert handler.data['scanNumber'] == 10

    def test_scanHandler_branches(self):
        """Test all branches in ScanHandler."""
        handler = parser_mzml.ScanHandler(scanID=1)
        handler.startElement('spectrum', {})
        assert not handler._isMatch
        handler.startElement('spectrum', {'id': 'scan=1', 'defaultArrayLength': '100'})
        assert handler._isMatch
        assert handler.data['pointsCount'] == 100
        handler.startElement('precursor', {'spectrumRef': 'scan=0'})
        assert handler._isPrecursor
        assert handler.data['parentScanNumber'] == 0
        handler.endElement('precursor')
        handler.startElement('precursor', {})
        handler.startElement('cvParam', {'name': 'selected ion m/z', 'value': '100.5'})
        handler.startElement('cvParam', {'name': 'intensity', 'value': '1000.5'})
        handler.startElement('cvParam', {'name': 'possible charge state', 'value': '2'})
        handler.startElement('cvParam', {'name': 'charge state', 'value': '3'})
        assert handler.data['precursorCharge'] == 3
        handler.endElement('precursor')
        handler.startElement('binaryDataArray', {})
        assert handler._isBinaryDataArray
        handler.startElement('binary', {})
        assert handler._isData
        handler.characters('data')
        handler.endElement('binary')
        handler.startElement('cvParam', {'name': '64-bit float'})
        assert handler.tmpPrecision == 64
        handler.startElement('cvParam', {'name': '32-bit float'})
        assert handler.tmpPrecision == 32
        handler.startElement('cvParam', {'name': 'zlib compression'})
        assert handler.tmpCompression == 'zlib'
        handler.startElement('cvParam', {'name': 'no compression'})
        assert handler.tmpCompression is None
        handler.startElement('cvParam', {'name': 'm/z array'})
        assert handler.tmpArrayType == 'mzArray'
        handler.endElement('binaryDataArray')
        assert handler.data['mzData'] == 'data'
        handler.startElement('binaryDataArray', {})
        handler.startElement('cvParam', {'name': 'intensity array'})
        handler.startElement('cvParam', {'name': 'unknown binary param'})
        handler.startElement('binary', {})
        handler.characters('int_data')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        assert handler.data['intData'] == 'int_data'
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        handler.startElement('cvParam', {'name': 'profile spectrum'})
        handler.startElement('cvParam', {'name': 'ms level', 'value': '1'})
        handler.startElement('cvParam', {'name': 'positive scan'})
        handler.startElement('cvParam', {'name': 'negative scan'})
        handler.startElement('cvParam', {'name': 'total ion current', 'value': '10.0'})
        handler.startElement('cvParam', {'name': 'base peak m/z', 'value': '5.0'})
        handler.startElement('cvParam', {'name': 'base peak intensity', 'value': '2.0'})
        handler.startElement('cvParam', {'name': 'lowest observed m/z', 'value': '1.0'})
        handler.startElement('cvParam', {'name': 'highest observed m/z', 'value': '10.0'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'minute'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'second'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'unknown'})
        handler.startElement('cvParam', {'name': 'unknown spectrum param'})
        handler.startElement('other', {})
        handler.endElement('other')
        with pytest.raises(parser_mzml.StopParsingError):
            handler.endElement('spectrum')
        handler.scanID = 2
        handler.startElement('spectrum', {'id': 'scan=1'})
        assert not handler._isMatch
        handler.endElement('spectrum')
        assert not handler._isMatch

    def test_scanHandler_no_match(self):
        """Step 4: Test ScanHandler ignoring non-matching scans."""
        handler = parser_mzml.ScanHandler(scanID=1)
        handler.startElement('spectrum', {'id': 'scan=2'})
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        handler.startElement('binaryDataArray', {})
        handler.startElement('binary', {})
        handler.characters('should_be_ignored')
        handler.endElement('binary')
        handler.endElement('binaryDataArray')
        handler.endElement('spectrum')
        assert not handler.data

    def test_scanlistHandler(self):
        """Step 4: Test ScanlistHandler for metadata extraction and various units."""
        handler = parser_mzml.ScanlistHandler()
        handler.startElement('spectrum', {'id': 'scan=1', 'defaultArrayLength': '100'})
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        handler.startElement('cvParam', {'name': 'ms level', 'value': '1'})
        handler.startElement('cvParam', {'name': 'positive scan'})
        handler.startElement('cvParam', {'name': 'total ion current', 'value': '1000.5'})
        handler.startElement('cvParam', {'name': 'base peak m/z', 'value': '500.1'})
        handler.startElement('cvParam', {'name': 'base peak intensity', 'value': '500.5'})
        handler.startElement('cvParam', {'name': 'lowest observed m/z', 'value': '100.0'})
        handler.startElement('cvParam', {'name': 'highest observed m/z', 'value': '900.0'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '10.5', 'unitName': 'minute'})
        handler.startElement('precursor', {'spectrumRef': 'scan=0'})
        handler.startElement('cvParam', {'name': 'selected ion m/z', 'value': '450.5'})
        handler.startElement('cvParam', {'name': 'intensity', 'value': '200.2'})
        handler.startElement('cvParam', {'name': 'charge state', 'value': '2'})
        handler.endElement('precursor')
        handler.endElement('spectrum')
        handler.startElement('spectrum', {'id': 'scan=2', 'defaultArrayLength': '200'})
        handler.startElement('cvParam', {'name': 'profile spectrum'})
        handler.startElement('cvParam', {'name': 'ms level', 'value': '2'})
        handler.startElement('cvParam', {'name': 'negative scan'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '630', 'unitName': 'second'})
        handler.endElement('spectrum')
        handler.startElement('spectrum', {'id': 'scan=3'})
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '5', 'unitName': 'unknown'})
        handler.endElement('spectrum')
        assert 1 in handler.data
        s1 = handler.data[1]
        assert s1['scanNumber'] == 1
        assert s1['spectrumType'] == 'discrete'
        assert s1['msLevel'] == 1
        assert s1['polarity'] == 1
        assert s1['totIonCurrent'] == 1000.5
        assert s1['basePeakMZ'] == 500.1
        assert s1['basePeakIntensity'] == 500.5
        assert s1['lowMZ'] == 100.0
        assert s1['highMZ'] == 900.0
        assert s1['retentionTime'] == 10.5 * 60
        assert s1['parentScanNumber'] == 0
        assert s1['precursorMZ'] == 450.5
        assert s1['precursorIntensity'] == 200.2
        assert s1['precursorCharge'] == 2
        assert 2 in handler.data
        s2 = handler.data[2]
        assert s2['spectrumType'] == 'continuous'
        assert s2['msLevel'] == 2
        assert s2['polarity'] == -1
        assert s2['retentionTime'] == 630
        assert 3 in handler.data
        assert handler.data[3]['retentionTime'] == 5 * 60

    def test_scanlistHandler_branches(self):
        """Test all branches in ScanlistHandler."""
        handler = parser_mzml.ScanlistHandler()
        handler.startElement('spectrum', {})
        assert None in handler.data
        handler.startElement('precursor', {'spectrumRef': 'scan=0'})
        assert handler.data[None]['parentScanNumber'] == 0
        handler.endElement('precursor')
        handler.startElement('precursor', {})
        handler.startElement('cvParam', {'name': 'selected ion m/z', 'value': '100.5'})
        handler.startElement('cvParam', {'name': 'intensity', 'value': '1000.5'})
        handler.startElement('cvParam', {'name': 'possible charge state', 'value': '2'})
        handler.startElement('cvParam', {'name': 'charge state', 'value': '3'})
        assert handler.data[None]['precursorMZ'] == 100.5
        assert handler.data[None]['precursorIntensity'] == 1000.5
        assert handler.data[None]['precursorCharge'] == 3
        handler.startElement('cvParam', {'name': 'selected ion m/z', 'value': None})
        assert handler.data[None]['precursorMZ'] == 100.5
        handler.endElement('precursor')
        handler.startElement('cvParam', {'name': 'centroid spectrum'})
        assert handler.data[None]['spectrumType'] == 'discrete'
        handler.startElement('cvParam', {'name': 'profile spectrum'})
        assert handler.data[None]['spectrumType'] == 'continuous'
        handler.startElement('cvParam', {'name': 'ms level', 'value': '2'})
        assert handler.data[None]['msLevel'] == 2
        handler.startElement('cvParam', {'name': 'positive scan'})
        assert handler.data[None]['polarity'] == 1
        handler.startElement('cvParam', {'name': 'negative scan'})
        assert handler.data[None]['polarity'] == -1
        handler.startElement('cvParam', {'name': 'total ion current', 'value': '5000.0'})
        assert handler.data[None]['totIonCurrent'] == 5000.0
        handler.startElement('cvParam', {'name': 'base peak m/z', 'value': '250.0'})
        assert handler.data[None]['basePeakMZ'] == 250.0
        handler.startElement('cvParam', {'name': 'base peak intensity', 'value': '1234.0'})
        assert handler.data[None]['basePeakIntensity'] == 1234.0
        handler.startElement('cvParam', {'name': 'lowest observed m/z', 'value': '100.0'})
        assert handler.data[None]['lowMZ'] == 100.0
        handler.startElement('cvParam', {'name': 'highest observed m/z', 'value': '1000.0'})
        assert handler.data[None]['highMZ'] == 1000.0
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '1.0', 'unitName': 'minute'})
        assert handler.data[None]['retentionTime'] == 60.0
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '120.0', 'unitName': 'second'})
        assert handler.data[None]['retentionTime'] == 120.0
        handler.startElement('cvParam', {'name': 'scan start time', 'value': '3.0', 'unitName': 'unknown'})
        assert handler.data[None]['retentionTime'] == 180.0
        handler.startElement('cvParam', {})
        handler.startElement('other', {})
        handler.endElement('spectrum')
        handler.endElement('other')
        handler.characters('some text')


class TestParseMZML:
    """Tests for ParseMZML class."""

    def test_makeScan_continuous(self, mocker):
        """Test _makeScan with continuous spectrum."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        scanData = {'spectrumType': 'continuous', 'title': 'Test Scan', 'scanNumber': 1, 'parentScanNumber': None, 'msLevel': 1, 'polarity': 1, 'retentionTime': 100.0, 'totIonCurrent': 1000.0, 'basePeakMZ': 500.0, 'basePeakIntensity': 500.0, 'precursorMZ': None, 'precursorIntensity': None, 'precursorCharge': None}
        mock_points = np.array([[100.0, 10.0], [200.0, 20.0]])
        mocker.patch.object(parser, '_parsePoints', return_value=mock_points)
        scan = parser._makeScan(scanData)
        assert isinstance(scan, obj_scan.Scan)
        assert np.array_equal(scan.profile, mock_points)
        assert scan.title == 'Test Scan'
        assert scan.msLevel == 1

    def test_parseMZML_caching(self, mocker):
        """Step 5: Test caching of _info, _scanlist, and _scans."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        parser._info = {'title': 'Cached Info'}
        parser._scanlist = {1: {'title': 'Cached Scanlist'}}
        parser._scans = {1: {'title': 'Cached Scan', 'spectrumType': 'discrete', 'mzData': '...', 'intData': '...'}}
        assert parser.info() == {'title': 'Cached Info'}
        assert parser.scanlist() == {1: {'title': 'Cached Scanlist'}}
        mocker.patch.object(parser, '_makeScan', return_value='Mocked Scan')
        assert parser.scan(1) == 'Mocked Scan'
        parser._makeScan.assert_called_once_with(parser._scans[1])

    def test_parseMZML_info_StopParsingError(self, mocker):
        """Step 5: Test info() handling StopParsingError exception."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mock_data = {'title': 'Test Info'}
        mock_handler = mocker.Mock()
        mock_handler.data = mock_data
        mocker.patch('mmass.mspy.parser_mzml.InfoHandler', return_value=mock_handler)
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = parser_mzml.StopParsingError()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert parser.info() == mock_data
        assert parser._info == mock_data

    def test_parseMZML_init_error(self):
        """Step 5: Test ParseMZML initialization with non-existent path."""
        with pytest.raises(IOError, match='File not found!'):
            parser_mzml.ParseMZML('non_existent_file.mzML')

    @pytest.mark.integration
    def test_parseMZML_integration_small(self):
        """Step 6: Integration test using test_small.mzML."""
        path = Path(__file__).resolve().parent.parent.parent / 'data' / 'test_small.mzML'
        parser = parser_mzml.ParseMZML(path)
        info = parser.info()
        assert isinstance(info, dict)
        assert info['title'] == 'MSn spectrum'
        assert info['instrument'] == ''
        scanlist = parser.scanlist()
        assert 10900 in scanlist
        s = scanlist[10900]
        assert s['scanNumber'] == 10900
        assert s['spectrumType'] == 'continuous'
        assert s['msLevel'] == 2
        assert s['polarity'] == 1
        assert np.allclose(s['totIonCurrent'], 97666.0)
        assert np.allclose(s['retentionTime'], 1.957980751991 * 60)
        scan = parser.scan(10900)
        assert isinstance(scan, obj_scan.Scan)
        assert scan.scanNumber == 10900
        assert scan.msLevel == 2
        assert len(scan.profile) == 107
        assert len(scan.peaklist) == 0

    @pytest.mark.integration
    def test_parseMZML_integration_tiny(self):
        """Step 6: Integration test using test_tiny.mzML."""
        path = Path(__file__).resolve().parent.parent.parent / 'data' / 'test_tiny.mzML'
        parser = parser_mzml.ParseMZML(path)
        info = parser.info()
        assert info is None or isinstance(info, dict)
        scanlist = parser.scanlist()
        assert 1 in scanlist
        assert scanlist[1]['scanNumber'] == 1
        assert scanlist[1]['spectrumType'] == 'discrete'
        assert scanlist[1]['msLevel'] == 1
        scan = parser.scan(1)
        assert isinstance(scan, obj_scan.Scan)
        assert scan.scanNumber == 1
        assert scan.msLevel == 1
        assert len(scan.peaklist) == 3
        assert len(scan.profile) == 0

    @pytest.mark.integration
    def test_parseMZML_load_integration(self):
        """Step 6: Integration test for load() with a physical file."""
        path = Path(__file__).resolve().parent.parent.parent / 'data' / 'test_tiny.mzML'
        parser = parser_mzml.ParseMZML(path)
        parser.load()
        assert parser._scans
        assert 1 in parser._scans
        assert parser._scans[1]['scanNumber'] == 1
        assert 1 in parser._scanlist

    def test_parseMZML_load_success(self, mocker):
        """Step 5: Test successful load() and scanlist generation."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mock_scans = {1: {'title': 'Scan 1', 'mzData': 'data', 'mzPrecision': 64, 'mzCompression': None, 'intData': 'data', 'intPrecision': 64, 'intCompression': None}}
        mock_handler = mocker.Mock()
        mock_handler.data = mock_scans
        mocker.patch('mmass.mspy.parser_mzml.RunHandler', return_value=mock_handler)
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        parser.load()
        assert parser._scans == mock_scans
        assert 1 in parser._scanlist
        assert 'mzData' not in parser._scanlist[1]
        assert parser._scanlist[1]['title'] == 'Scan 1'

    def test_parseMZML_sax_exception(self, mocker):
        """Step 5: Test SAX exception handling in load, info, scanlist, and scan."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Test Exception')
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        parser.load()
        assert not parser._scans
        assert not parser.info()
        assert not parser.scanlist()
        assert not parser.scan(1)

    def test_parseMZML_scan_StopParsingError(self, mocker):
        """Step 5: Test Scan() handling StopParsingError exception."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mock_data = {'title': 'Scan 1', 'spectrumType': 'discrete', 'mzData': '', 'intData': ''}
        mock_handler = mocker.Mock()
        mock_handler.data = mock_data
        mocker.patch('mmass.mspy.parser_mzml.ScanHandler', return_value=mock_handler)
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = parser_mzml.StopParsingError()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        mocker.patch.object(parser, '_makeScan', return_value='Made Scan')
        assert parser.scan(1) == 'Made Scan'
        parser._makeScan.assert_called_once_with(mock_data)

    def test_parseMZML_scan_not_found(self, mocker):
        """Step 5: Test Scan() when scanID is not found (ScanHandler returns False)."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mock_handler = mocker.Mock()
        mock_handler.data = False
        mocker.patch('mmass.mspy.parser_mzml.ScanHandler', return_value=mock_handler)
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert not parser.scan(999)

    def test_parseMZML_scanlist_success(self, mocker):
        """Step 5: Test successful scanlist() execution."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        mock_data = {1: {'title': 'Scan 1'}}
        mock_handler = mocker.Mock()
        mock_handler.data = mock_data
        mocker.patch('mmass.mspy.parser_mzml.ScanlistHandler', return_value=mock_handler)
        mocker.patch('pathlib.Path.open', mocker.mock_open(), create=True)
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert parser.scanlist() == mock_data
        assert parser._scanlist == mock_data

    def test_parsePoints_empty(self, mocker):
        """Test _parsePoints with various empty inputs."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        scanData = {'mzData': '', 'intData': 'some_data'}
        assert parser._parsePoints(scanData) == []
        scanData = {'mzData': 'some_data', 'intData': ''}
        assert parser._parsePoints(scanData) == []
        scanData = {'mzData': None, 'intData': 'some_data'}
        assert parser._parsePoints(scanData) == []


class TestMZMLUtils:
    """Utility tests for parser_mzml."""

    def test_parseScanNumber_exception_handling(self, mocker):
        """Test _parseScanNumber exception handling by mocking re.match or group behavior."""
        mock_match = mocker.Mock()
        mock_match.group.return_value = 'not_an_int'
        mock_pattern = mocker.patch('mmass.mspy.parser_mzml.SCAN_NUMBER_PATTERN')
        mock_pattern.search.return_value = mock_match
        assert parser_mzml._parseScanNumber('scan=something') is None
        mock_pattern.search.assert_called_once_with('scan=something')

    def test_parseScanNumber_invalid(self):
        """Test _parseScanNumber with invalid scan ID string."""
        assert parser_mzml._parseScanNumber('no_scan_here') is None
        assert parser_mzml._parseScanNumber('') is None
        assert parser_mzml._parseScanNumber('scan=') is None

    def test_parseScanNumber_valid(self):
        """Test _parseScanNumber with valid scan ID string."""
        assert parser_mzml._parseScanNumber('scan=123') == 123
        assert parser_mzml._parseScanNumber('controllerType=0 controllerNumber=1 scan=456') == 456


class TestPropertyBased:
    """Property-based tests for mzML parsing."""

    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much, HealthCheck.function_scoped_fixture], max_examples=100)
    @given(mz_data=arrays(np.float64, st.integers(0, 50), elements=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False)), int_data=arrays(np.float64, st.integers(0, 50), elements=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False)), mz_precision=st.sampled_from([32, 64]), int_precision=st.sampled_from([32, 64]), mz_compression=st.sampled_from(['zlib', None]), int_compression=st.sampled_from(['zlib', None]), spectrum_type=st.sampled_from(['discrete', 'continuous']))
    def test_parsePoints_property_based(self, mocker, mz_data, int_data, mz_precision, int_precision, mz_compression, int_compression, spectrum_type):
        """Property-based test for _parsePoints iterating through precision and compression."""
        length = min(len(mz_data), len(int_data))
        mz_input = mz_data[:length]
        int_input = int_data[:length]
        mz_type = 'f' if mz_precision == 32 else 'd'
        int_type = 'f' if int_precision == 32 else 'd'
        mz_fmt = '<' + mz_type * length
        int_fmt = '<' + int_type * length
        if mz_precision == 32:
            mz_target = mz_input.astype(np.float32)
        else:
            mz_target = mz_input.astype(np.float64)
        if int_precision == 32:
            int_target = int_input.astype(np.float32)
        else:
            int_target = int_input.astype(np.float64)
        mz_binary = struct.pack(mz_fmt, *mz_target)
        int_binary = struct.pack(int_fmt, *int_target)
        if mz_compression == 'zlib':
            mz_binary_to_encode = zlib.compress(mz_binary)
        else:
            mz_binary_to_encode = mz_binary
        if int_compression == 'zlib':
            int_binary_to_encode = zlib.compress(int_binary)
        else:
            int_binary_to_encode = int_binary
        mz_b64 = base64.b64encode(mz_binary_to_encode)
        int_b64 = base64.b64encode(int_binary_to_encode)
        scanData = {'mzData': mz_b64, 'intData': int_b64, 'mzPrecision': mz_precision, 'intPrecision': int_precision, 'mzCompression': mz_compression, 'intCompression': int_compression, 'spectrumType': spectrum_type}
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzml.ParseMZML('dummy_path')
        result = parser._parsePoints(scanData)
        if length == 0:
            assert len(result) == 0
        elif spectrum_type == 'discrete':
            assert len(result) == length
            for i in range(length):
                assert np.allclose(result[i][0], mz_target[i], atol=1e-06)
                assert np.allclose(result[i][1], int_target[i], atol=1e-06)
        else:
            assert result.shape == (length, 2)
            assert np.allclose(result[:, 0], mz_target, atol=1e-06)
            assert np.allclose(result[:, 1], int_target, atol=1e-06)
