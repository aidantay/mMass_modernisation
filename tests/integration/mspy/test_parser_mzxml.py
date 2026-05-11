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

from mmass.mspy import obj_scan, parser_mzxml

# Test _convertRetentionTime


@pytest.fixture
def parser_instance(tmp_path):
    path = tmp_path / 'test.mzXML'
    path.write_text('<mzXML></mzXML>')
    return parser_mzxml.ParseMZXML(path)


class TestMZXMLHandlers:
    """Tests for SAX handlers in parser_mzxml."""

    def test_characters_coverage(self):
        h = parser_mzxml.ScanlistHandler()
        h.data[1] = {'precursorMZ': ''}
        h.currentID = 1
        h._isPrecursor = True
        h.characters('500.5')
        assert h.data[1]['precursorMZ'] == '500.5'
        h._isPrecursor = False
        h.characters('skip')
        assert h.data[1]['precursorMZ'] == '500.5'
        h2 = parser_mzxml.ScanHandler(1)
        h2.data = {'points': [], 'precursorMZ': ''}
        h2._isPeaks = True
        h2.characters('data')
        assert h2.data['points'] == ['data']
        h2._isPeaks = False
        h2._isPrecursor = True
        h2.characters('200')
        assert h2.data['precursorMZ'] == '200'
        h3 = parser_mzxml.RunHandler()
        h3.data[1] = {'points': [], 'precursorMZ': ''}
        h3.currentID = 1
        h3._isPeaks = True
        h3.characters('data')
        assert h3.data[1]['points'] == ['data']
        h3._isPeaks = False
        h3._isPrecursor = True
        h3.characters('300')
        assert h3.data[1]['precursorMZ'] == '300'

    def test_infoHandler(self):
        handler = parser_mzxml.InfoHandler()
        handler.startElement('msManufacturer', {'value': 'Manufacturer'})
        handler.startElement('msModel', {'value': 'Model'})
        handler.startElement('msIonisation', {'value': 'Ionisation'})
        handler.startElement('msMassAnalyzer', {'value': 'Analyzer'})
        assert 'Manufacturer' in handler.data['instrument']
        assert 'Model' in handler.data['instrument']
        assert 'Ionisation' in handler.data['instrument']
        assert 'Analyzer' in handler.data['instrument']
        handler.startElement('msManufacturer', {})
        handler.endElement('somethingElse')
        with pytest.raises(parser_mzxml.StopParsingError):
            handler.endElement('msInstrument')

    def test_infoHandler_accumulation(self):
        h = parser_mzxml.InfoHandler()
        h.startElement('msManufacturer', {'value': 'A'})
        h.startElement('msModel', {'value': 'B'})
        h.startElement('msIonisation', {'value': 'C'})
        h.startElement('msMassAnalyzer', {'value': 'D'})
        assert h.data['instrument'] == 'A B C D '

    def test_runHandler_comprehensive(self):
        h = parser_mzxml.RunHandler()
        h.startElement('dataProcessing', {'centroided': '1'})
        h.endElement('dataProcessing')
        h.startElement('dataProcessing', {'centroided': '0'})
        h.startElement('scan', {'num': '1', 'msLevel': '2', 'peaksCount': '10', 'polarity': '+', 'retentionTime': 'PT1S', 'lowMz': '10', 'highMz': '20', 'basePeakMz': '15', 'basePeakIntensity': '100', 'totIonCurrent': '1000'})
        h.startElement('peaks', {'byteOrder': 'little', 'compressionType': 'zlib', 'precision': '64'})
        h.characters('data')
        h.endElement('peaks')
        h.startElement('precursorMz', {'precursorIntensity': '50', 'precursorCharge': '2'})
        h.characters('100.5')
        h.endElement('precursorMz')
        h.endElement('scan')
        h.startElement('scan', {'num': '2', 'msLevel': '', 'polarity': 'negative'})
        assert h.data[2]['polarity'] == -1
        h.startElement('peaks', {'compressionType': 'none', 'precision': ''})
        h.endElement('peaks')
        h.startElement('precursorMz', {})
        h.endElement('precursorMz')
        h.endElement('scan')
        h.startElement('scan', {})
        h.endElement('scan')
        h.startElement('unknownElement', {})

    def test_scanHandler_comprehensive(self):
        h = parser_mzxml.ScanHandler(1)
        h.startElement('dataProcessing', {'centroided': '1'})
        h.startElement('scan', {'num': '1', 'msLevel': '2', 'peaksCount': '10', 'polarity': '+', 'retentionTime': 'PT1S', 'lowMz': '10', 'highMz': '20', 'basePeakMz': '15', 'basePeakIntensity': '100', 'totIonCurrent': '1000'})
        h.startElement('peaks', {'byteOrder': 'little', 'compressionType': 'zlib', 'precision': '64'})
        h.characters('data')
        h.endElement('peaks')
        h.startElement('precursorMz', {'precursorIntensity': '50', 'precursorCharge': '2'})
        h.characters('100.5')
        h.endElement('precursorMz')
        with pytest.raises(parser_mzxml.StopParsingError):
            h.endElement('scan')
        h = parser_mzxml.ScanHandler(1)
        h.startElement('scan', {'num': '1', 'msLevel': '', 'polarity': 'negative'})
        assert h.data['polarity'] == -1
        h.startElement('peaks', {'compressionType': 'none', 'precision': ''})
        h.endElement('peaks')
        h.startElement('precursorMz', {})
        h.endElement('precursorMz')
        h = parser_mzxml.ScanHandler(1)
        h.startElement('scan', {'num': '1', 'polarity': '-'})
        assert h.data['polarity'] == -1
        h = parser_mzxml.ScanHandler(1)
        h.startElement('scan', {'num': '2'})
        h.endElement('scan')
        h = parser_mzxml.ScanHandler(1)
        h.startElement('scan', {'num': '1'})
        h.startElement('scan', {'num': '2'})
        h.endElement('scan')
        h = parser_mzxml.ScanHandler(None)
        h.startElement('scan', {})
        assert h._isMatch
        h.endElement('dataProcessing')

    def test_scanlistHandler_comprehensive(self):
        h = parser_mzxml.ScanlistHandler()
        h.startElement('dataProcessing', {'centroided': '1'})
        assert h._spectrumType == 'discrete'
        h.startElement('dataProcessing', {'centroided': '0'})
        h.endElement('dataProcessing')
        h.startElement('scan', {'num': '1', 'msLevel': '2', 'peaksCount': '10', 'polarity': '+', 'retentionTime': 'PT1S', 'lowMz': '10', 'highMz': '20', 'basePeakMz': '15', 'basePeakIntensity': '100', 'totIonCurrent': '1000'})
        h.startElement('precursorMz', {'precursorIntensity': '50', 'precursorCharge': '2'})
        h.characters('100.5')
        h.endElement('precursorMz')
        h.endElement('scan')
        h.startElement('scan', {'num': '2', 'msLevel': ''})
        h.startElement('precursorMz', {})
        h.endElement('precursorMz')
        h.endElement('scan')
        h.startElement('scan', {'num': '3', 'polarity': 'negative'})
        h.startElement('scan', {'num': '4', 'polarity': '-'})
        h.startElement('scan', {'num': '5', 'polarity': 'positive'})
        h.startElement('scan', {'num': '6', 'polarity': 'Positive'})
        h.startElement('scan', {'num': '7', 'polarity': 'Negative'})
        h.startElement('scan', {'num': '8', 'polarity': 'unknown'})
        h.startElement('scan', {})
        h.endElement('scan')


class TestParseMZXML:
    """Tests for ParseMZXML class."""

    @pytest.mark.integration
    def test_integration_large(self):
        path = Path('tests/data/test_large.mzXML')
        if not path.exists():
            pytest.skip('Integration test file not found')
        parser = parser_mzxml.ParseMZXML(path)
        assert len(parser.scanlist()) > 0

    @pytest.mark.integration
    def test_integration_small(self):
        path = Path('tests/data/test_small.mzXML')
        if not path.exists():
            pytest.skip('Integration test file not found')
        parser = parser_mzxml.ParseMZXML(path)
        assert isinstance(parser.info(), dict)
        assert len(parser.scanlist()) > 0
        first_scan_id = sorted(parser.scanlist().keys())[0]
        assert isinstance(parser.scan(first_scan_id), obj_scan.Scan)

    def test_makeScan_direct(self, parser_instance, mocker):
        scan_data = {'spectrumType': 'discrete', 'title': 'Scan 1', 'scanNumber': 1, 'parentScanNumber': None, 'msLevel': 1, 'polarity': 1, 'retentionTime': 60.0, 'totIonCurrent': 1000.0, 'basePeakMZ': 500.0, 'basePeakIntensity': 1000.0, 'precursorMZ': None, 'precursorIntensity': None, 'precursorCharge': None}
        mocker.patch.object(parser_instance, '_parsePoints', return_value=[[100.0, 1000.0]])
        scan = parser_instance._makeScan(scan_data)
        assert scan.peaklist[0].mz == 100.0
        scan_data['spectrumType'] = 'continuous'
        points = np.array([[100.0, 1000.0]])
        mocker.patch.object(parser_instance, '_parsePoints', return_value=points)
        scan = parser_instance._makeScan(scan_data)
        assert scan.profile is points

    def test_parseMZXML_info(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mock_handler = mocker.Mock(spec=parser_mzxml.InfoHandler)
        mock_handler.data = {'title': 'Test'}
        mocker.patch('mmass.mspy.parser_mzxml.InfoHandler', return_value=mock_handler)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = parser_mzxml.StopParsingError()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert parser.info() == {'title': 'Test'}
        assert parser.info() == {'title': 'Test'}

    def test_parseMZXML_info_no_stop_parsing(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mocker.patch('xml.sax.make_parser')
        assert parser.info() is None

    def test_parseMZXML_init(self, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        assert parser.path == path
        assert parser._scans is None
        assert parser._scanlist is None
        assert parser._info is None

    def test_parseMZXML_init_nonexistent(self):
        with pytest.raises(IOError, match='File not found!'):
            parser_mzxml.ParseMZXML('nonexistent_file.mzXML')

    def test_parseMZXML_load(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mock_handler = mocker.Mock(spec=parser_mzxml.RunHandler)
        mock_handler.data = {1: {'points': 'data', 'byteOrder': 'network', 'compression': None, 'precision': 32, 'title': '', 'scanNumber': 1, 'parentScanNumber': None, 'msLevel': 1, 'polarity': 1, 'retentionTime': 60.0, 'totIonCurrent': 1000.0, 'basePeakMZ': 500.0, 'basePeakIntensity': 1000.0, 'precursorMZ': None, 'precursorIntensity': None, 'precursorCharge': None, 'spectrumType': 'discrete'}}
        mocker.patch('mmass.mspy.parser_mzxml.RunHandler', return_value=mock_handler)
        parser.load()
        assert 1 in parser._scanlist

    def test_parseMZXML_sax_exceptions(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Error')
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert parser.load() is None
        assert parser.info() is False
        assert parser.scanlist() is False
        assert parser.scan(1) is False

    def test_parseMZXML_scan(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        scan_data = {'points': None, 'byteOrder': 'network', 'compression': None, 'precision': 32, 'title': 'Scan 1', 'scanNumber': 1, 'parentScanNumber': None, 'msLevel': 1, 'polarity': 1, 'retentionTime': 60.0, 'totIonCurrent': 1000.0, 'basePeakMZ': 500.0, 'basePeakIntensity': 1000.0, 'precursorMZ': None, 'precursorIntensity': None, 'precursorCharge': None, 'spectrumType': 'discrete'}
        mock_handler = mocker.Mock(spec=parser_mzxml.ScanHandler)
        mock_handler.data = scan_data
        mocker.patch('mmass.mspy.parser_mzxml.ScanHandler', return_value=mock_handler)
        mock_sax_parser = mocker.Mock()
        mock_sax_parser.parse.side_effect = parser_mzxml.StopParsingError()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        assert isinstance(parser.scan(1), obj_scan.Scan)
        parser._scans = {1: scan_data}
        assert isinstance(parser.scan(1), obj_scan.Scan)

    def test_parseMZXML_scan_not_found(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mock_handler = mocker.Mock(spec=parser_mzxml.ScanHandler)
        mock_handler.data = False
        mocker.patch('mmass.mspy.parser_mzxml.ScanHandler', return_value=mock_handler)
        mocker.patch('xml.sax.make_parser')
        assert parser.scan(1) is False

    def test_parseMZXML_scanlist(self, mocker, tmp_path):
        path = tmp_path / 'test.mzXML'
        path.write_text('<mzXML></mzXML>')
        parser = parser_mzxml.ParseMZXML(path)
        mock_handler = mocker.Mock(spec=parser_mzxml.ScanlistHandler)
        mock_handler.data = {1: {'scanNumber': 1}}
        mocker.patch('mmass.mspy.parser_mzxml.ScanlistHandler', return_value=mock_handler)
        assert parser.scanlist() == {1: {'scanNumber': 1}}

    def test_parsePoints_empty(self, parser_instance):
        assert parser_instance._parsePoints({'points': None}) == []
        assert parser_instance._parsePoints({'points': ''}) == []


class TestMZXMLUtils:
    """Utility tests for parser_mzxml."""

    @pytest.mark.parametrize(('retention', 'expected'), [('PT1M30S', 90.0), ('PT2.5M', 150.0), ('PT45S', 45.0), ('PT1M', 60.0), ('PT0.5M30S', 60.0), ('invalid', None), ('1M30S', None), ('PT', 0.0)])
    def test_convertRetentionTime(self, retention, expected):
        assert parser_mzxml._convertRetentionTime(retention) == expected


class TestPropertyBased:
    """Property-based tests for mzXML parsing."""

    @settings(suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
    @given(points=arrays(np.float64, (10, 2), elements=st.floats(min_value=1e-10, max_value=1000, allow_nan=False, allow_infinity=False)), precision=st.sampled_from([32, 64]), byte_order=st.sampled_from(['little', 'big', 'network']), compression=st.sampled_from(['zlib', 'none']), spectrum_type=st.sampled_from(['discrete', 'continuous']))
    def test_parsePoints_property(self, parser_instance, points, precision, byte_order, compression, spectrum_type):
        flat_points = points.flatten()
        fmt_char = 'f' if precision == 32 else 'd'
        if byte_order == 'little':
            endian = '<'
        elif byte_order == 'big':
            endian = '>'
        else:
            endian = '!'
        packed_data = struct.pack(endian + fmt_char * len(flat_points), *flat_points)
        if compression == 'zlib':
            compressed_data = zlib.compress(packed_data)
        else:
            compressed_data = packed_data
        b64_data = base64.b64encode(compressed_data)
        scanData = {'points': b64_data, 'precision': precision, 'byteOrder': byte_order, 'compression': compression, 'spectrumType': spectrum_type}
        result = parser_instance._parsePoints(scanData)
        if spectrum_type == 'discrete':
            assert len(result) == len(points)
            for i in range(len(points)):
                np.testing.assert_allclose(result[i], points[i], rtol=1e-05 if precision == 32 else 1e-10, atol=1e-12)
        else:
            assert isinstance(result, np.ndarray)
            np.testing.assert_allclose(result, points, rtol=1e-05 if precision == 32 else 1e-10, atol=1e-12)
