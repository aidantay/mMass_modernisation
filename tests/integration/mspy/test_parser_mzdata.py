import base64
import struct
import xml.sax
from pathlib import Path

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import parser_mzdata


@pytest.fixture
def mzdata_file(tmp_path):
    """Fixture to create a minimal valid mzData XML file."""
    path = tmp_path / 'test.mzdata'
    content = '<?xml version="1.0" encoding="utf-8"?>\n<mzData version="1.05" accessionNumber="0">\n    <description>\n        <admin>\n            <sampleName>Test Sample</sampleName>\n            <contact>\n                <name>John Doe</name>\n                <institution>Test Institution</institution>\n                <contactInfo>john.doe@example.com</contactInfo>\n            </contact>\n        </admin>\n        <instrument>\n            <instrumentName>Test Instrument</instrumentName>\n        </instrument>\n    </description>\n    <spectrumList count="2">\n        <spectrum id="1">\n            <acqSpecification spectrumType="discrete" />\n            <spectrumInstrument msLevel="1" mzRangeStart="100.0" mzRangeStop="200.0" />\n            <spectrumDesc>\n                <precursor spectrumRef="0" />\n                <mzArrayBinary>\n                    <data precision="32" endian="little" length="1">AACAPw==</data>\n                </mzArrayBinary>\n                <intenArrayBinary>\n                    <data precision="32" endian="little" length="1">AAAAPw==</data>\n                </intenArrayBinary>\n            </spectrumDesc>\n        </spectrum>\n        <spectrum id="2">\n            <acqSpecification spectrumType="continuous" />\n            <spectrumInstrument msLevel="1" />\n            <spectrumDesc>\n                <mzArrayBinary>\n                    <data precision="32" endian="little" length="1">AAAgQA==</data>\n                </mzArrayBinary>\n                <intenArrayBinary>\n                    <data precision="32" endian="little" length="1">AACAPw==</data>\n                </intenArrayBinary>\n            </spectrumDesc>\n        </spectrum>\n    </spectrumList>\n</mzData>\n'
    path.write_text(content)
    return path


@pytest.fixture
def corrupt_mzdata_file(tmp_path):
    """Fixture to create a malformed mzData XML file."""
    path = tmp_path / 'corrupt.mzdata'
    content = '<?xml version="1.0" encoding="utf-8"?>\n<mzData>\n    <unclosedTag>\n</mzData>\n'
    path.write_text(content)
    return path


class TestMZDataHandlers:
    """Tests for SAX handlers in parser_mzdata."""

    def test_infoHandler(self):
        """Step 3: Unit Test InfoHandler."""
        handler = parser_mzdata.InfoHandler()
        handler.startElement('sampleName', {})
        handler.characters('Test Sample')
        handler.endElement('sampleName')
        handler.startElement('contact', {})
        handler.startElement('name', {})
        handler.characters('John Doe')
        handler.endElement('name')
        handler.startElement('institution', {})
        handler.characters('Test Institution')
        handler.endElement('institution')
        handler.startElement('contactInfo', {})
        handler.characters('john.doe@example.com')
        handler.endElement('contactInfo')
        handler.endElement('contact')
        handler.startElement('instrumentName', {})
        handler.characters('Test Instrument')
        handler.endElement('instrumentName')
        assert handler.data['title'] == 'Test Sample'
        assert handler.data['operator'] == 'John Doe'
        assert handler.data['institution'] == 'Test Institution'
        assert handler.data['contact'] == 'john.doe@example.com'
        assert handler.data['instrument'] == 'Test Instrument'
        with pytest.raises(parser_mzdata.StopParsingError):
            handler.endElement('description')

    def test_infoHandler_extra_coverage(self):
        """Improve coverage for InfoHandler characters."""
        handler = parser_mzdata.InfoHandler()
        handler._isInstrumentName = True
        handler.characters('Instrument')
        assert handler.data['instrument'] == 'Instrument'
        handler._isInstrumentName = False
        handler.characters('None')

    def test_runHandler_comprehensive_coverage(self):
        """Hit all remaining branches in RunHandler."""
        handler = parser_mzdata.RunHandler()
        handler.startElement('spectrum', {})
        handler.startElement('spectrum', {'id': '1'})
        handler.currentID = 1
        handler.startElement('acqSpecification', {'spectrumType': ''})
        handler.startElement('acqSpecification', {'spectrumType': 'discrete'})
        handler.startElement('spectrumInstrument', {'msLevel': ''})
        handler.startElement('spectrumInstrument', {'msLevel': '2', 'mzRangeStart': '100', 'mzRangeStop': '200'})
        handler.startElement('userParam', {})
        for name in ['TimeInMinutes', 'TotalIonCurrent', 'MassToChargeRatio', 'ChargeState']:
            handler.startElement('userParam', {'name': name, 'value': '1.0'})
            handler.startElement('userParam', {'name': name, 'value': 'invalid'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'unknown'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'positive'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': ('negative', 'Negative', '-')})
        handler.startElement('precursor', {'spectrumRef': '10'})
        handler.startElement('mzArrayBinary', {})
        handler.startElement('data', {'precision': ''})
        handler.endElement('mzArrayBinary')
        handler.startElement('intenArrayBinary', {})
        handler.startElement('data', {'precision': '32'})
        handler.endElement('intenArrayBinary')
        handler.data[1]['mzData'] = []
        handler.endElement('mzArrayBinary')
        handler.data[1]['intData'] = []
        handler.endElement('intenArrayBinary')

    def test_runHandler_edge_cases(self):
        """Step 4: Unit Test RunHandler state and edge cases."""
        handler = parser_mzdata.RunHandler()
        handler.startElement('spectrum', {'id': '1'})
        handler.startElement('mzArrayBinary', {})
        handler.characters('AAA')
        handler.endElement('mzArrayBinary')
        handler.startElement('spectrum', {'id': '2'})
        handler.startElement('mzArrayBinary', {})
        handler.characters('BBB')
        handler.endElement('mzArrayBinary')
        assert handler.data[1]['mzData'] == 'AAA'
        assert handler.data[2]['mzData'] == 'BBB'
        handler.startElement('spectrum', {'id': '3'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': ('negative', 'Negative', '-')})
        assert handler.data[3]['polarity'] == -1

    def test_scanHandler_comprehensive_coverage(self):
        """Hit all remaining branches in ScanHandler."""
        handler = parser_mzdata.ScanHandler(1)
        handler.startElement('spectrum', {})
        assert not handler._isMatch
        handler = parser_mzdata.ScanHandler(1)
        handler.startElement('spectrum', {'id': '1'})
        handler.startElement('acqSpecification', {'spectrumType': ''})
        handler.startElement('spectrumInstrument', {'msLevel': ''})
        handler.startElement('spectrumInstrument', {'mzRangeStart': '100.0'})
        assert handler.data['lowMZ'] == 100.0
        handler.startElement('spectrumInstrument', {'mzRangeStop': '200.0'})
        assert handler.data['highMZ'] == 200.0
        handler.startElement('userParam', {'name': 'TimeInMinutes', 'value': '1.0'})
        handler.startElement('userParam', {'name': 'TimeInMinutes', 'value': 'invalid'})
        handler.startElement('userParam', {'name': 'TotalIonCurrent', 'value': '1000.0'})
        handler.startElement('userParam', {'name': 'TotalIonCurrent', 'value': 'invalid'})
        handler.startElement('cvParam', {'name': 'MassToChargeRatio', 'value': '250.0'})
        handler.startElement('cvParam', {'name': 'MassToChargeRatio', 'value': 'invalid'})
        handler.startElement('cvParam', {'name': 'ChargeState', 'value': '2'})
        handler.startElement('cvParam', {'name': 'ChargeState', 'value': 'invalid'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'unknown'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'positive'})
        assert handler.data['polarity'] == 1
        handler.startElement('userParam', {'name': 'Polarity', 'value': ('negative', 'Negative', '-')})
        assert handler.data['polarity'] == -1
        handler.startElement('precursor', {'spectrumRef': '10'})
        assert handler.data['parentScanNumber'] == 10
        handler.startElement('mzArrayBinary', {})
        handler.startElement('data', {})
        handler.endElement('mzArrayBinary')
        handler.startElement('mzArrayBinary', {})
        handler.startElement('data', {'length': '1', 'precision': '32'})
        assert handler.data['mzPrecision'] == 32
        handler.endElement('mzArrayBinary')
        handler.startElement('intenArrayBinary', {})
        handler.startElement('data', {'length': '1', 'precision': '64'})
        assert handler.data['intPrecision'] == 64
        handler.characters('data')
        handler.endElement('intenArrayBinary')
        handler.startElement('intenArrayBinary', {})
        handler.endElement('intenArrayBinary')
        assert handler.data['intData'] is None

    def test_scanHandler_edge_cases(self):
        """Step 4: Unit Test ScanHandler state and edge cases."""
        handler = parser_mzdata.ScanHandler(1)
        handler.startElement('spectrum', {'id': '1'})
        assert handler._isMatch
        assert handler.data['scanNumber'] == 1
        handler.startElement('acqSpecification', {'spectrumType': 'continuous'})
        assert handler.data['spectrumType'] == 'continuous'
        handler.startElement('spectrumInstrument', {'msLevel': '2'})
        assert handler.data['msLevel'] == 2
        handler.startElement('userParam', {'name': 'TimeInMinutes', 'value': '1.0'})
        assert handler.data['retentionTime'] == 60.0
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'positive'})
        assert handler.data['polarity'] == 1
        handler.startElement('mzArrayBinary', {})
        assert handler._isMzArray
        handler.characters('ABC')
        handler.characters('DEF')
        handler.startElement('data', {'endian': 'little', 'precision': '64', 'length': '2'})
        assert handler.data['mzEndian'] == 'little'
        assert handler.data['mzPrecision'] == 64
        assert handler.data['pointsCount'] == 2
        handler.endElement('mzArrayBinary')
        assert handler.data['mzData'] == 'ABCDEF'
        assert not handler._isMzArray
        handler.startElement('intenArrayBinary', {})
        assert handler._isIntArray
        handler.characters('GHI')
        handler.startElement('data', {'endian': 'big', 'precision': '32'})
        assert handler.data['intEndian'] == 'big'
        assert handler.data['intPrecision'] == 32
        handler.endElement('intenArrayBinary')
        assert handler.data['intData'] == 'GHI'
        handler2 = parser_mzdata.ScanHandler(2)
        handler2.startElement('spectrum', {'id': '1'})
        assert not handler2._isMatch
        assert not handler2.data
        with pytest.raises(parser_mzdata.StopParsingError):
            handler.endElement('spectrum')
        handler3 = parser_mzdata.ScanHandler(3)
        handler3.startElement('spectrum', {'id': '3'})
        handler3.startElement('mzArrayBinary', {})
        handler3.endElement('mzArrayBinary')
        assert handler3.data['mzData'] is None

    def test_scanlistHandler_comprehensive_coverage(self):
        """Hit all remaining branches in ScanlistHandler."""
        handler = parser_mzdata.ScanlistHandler()
        handler.startElement('spectrum', {'id': '1'})
        handler.currentID = 1
        handler.startElement('spectrumInstrument', {'msLevel': ''})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'unknown'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': 'positive'})
        handler.startElement('userParam', {'name': 'Polarity', 'value': ('negative', 'Negative', '-')})
        handler.startElement('precursor', {})
        handler.startElement('precursor', {'spectrumRef': '10'})
        handler.startElement('data', {})
        handler.startElement('data', {'length': '100'})

    def test_scanlistHandler_edge_cases(self):
        """Step 4: Unit Test ScanlistHandler state and edge cases."""
        handler = parser_mzdata.ScanlistHandler()
        handler.startElement('spectrum', {'id': '1'})
        assert 1 in handler.data
        assert handler.data[1]['scanNumber'] == 1
        handler.startElement('spectrum', {})
        assert None in handler.data
        handler.currentID = 1
        handler.startElement('acqSpecification', {'spectrumType': 'discrete'})
        assert handler.data[1]['spectrumType'] == 'discrete'
        handler.startElement('acqSpecification', {})
        assert handler.data[1]['spectrumType'] == 'discrete'
        handler.startElement('spectrumInstrument', {'msLevel': '2', 'mzRangeStart': '100.5', 'mzRangeStop': '500.5'})
        assert handler.data[1]['msLevel'] == 2
        assert handler.data[1]['lowMZ'] == 100.5
        assert handler.data[1]['highMZ'] == 500.5
        handler.startElement('spectrumInstrument', {})
        assert handler.data[1]['msLevel'] == 1
        handler.startElement('userParam', {'name': 'TimeInMinutes', 'value': '1.5'})
        assert handler.data[1]['retentionTime'] == 90.0
        handler.startElement('userParam', {'name': 'TotalIonCurrent', 'value': '1000.5'})
        assert handler.data[1]['totIonCurrent'] == 1000.5
        handler.startElement('cvParam', {'name': 'MassToChargeRatio', 'value': '250.5'})
        assert handler.data[1]['precursorMZ'] == 250.5
        handler.startElement('cvParam', {'name': 'ChargeState', 'value': '2'})
        assert handler.data[1]['precursorCharge'] == 2
        handler.startElement('userParam', {'name': 'Polarity', 'value': '+'})
        assert handler.data[1]['polarity'] == 1
        handler.startElement('userParam', {'name': 'Polarity', 'value': ('negative', 'Negative', '-')})
        assert handler.data[1]['polarity'] == -1
        handler.startElement('userParam', {'name': 'TimeInMinutes', 'value': 'invalid'})
        assert handler.data[1]['retentionTime'] == 90.0
        handler.startElement('userParam', {'name': 'TotalIonCurrent', 'value': 'invalid'})
        assert handler.data[1]['totIonCurrent'] == 1000.5
        handler.startElement('cvParam', {'name': 'MassToChargeRatio', 'value': 'invalid'})
        assert handler.data[1]['precursorMZ'] == 250.5
        handler.startElement('cvParam', {'name': 'ChargeState', 'value': 'invalid'})
        assert handler.data[1]['precursorCharge'] == 2
        handler.startElement('precursor', {'spectrumRef': '10'})
        assert handler.data[1]['parentScanNumber'] == 10
        handler.startElement('data', {'length': '100'})
        assert handler.data[1]['pointsCount'] == 100

    def test_scanlistHandler_extra_coverage(self):
        """Improve coverage for ScanlistHandler pass methods."""
        handler = parser_mzdata.ScanlistHandler()
        handler.endElement('any')
        handler.characters('any')
        handler.data[1] = {'msLevel': 1}
        handler.currentID = 1
        handler.startElement('spectrumInstrument', {'msLevel': ''})
        assert handler.data[1]['msLevel'] == 1


class TestParseMZData:
    """Tests for ParseMZData class."""

    @pytest.mark.integration
    def test_integration_test_small_mzdata(self):
        """Step 8: Integration Testing with test_small.mzdata."""
        path = 'tests/data/test_small.mzdata'
        if not Path(path).exists():
            import pytest
            pytest.skip('test_small.mzdata not found')
        parser = parser_mzdata.ParseMZData(path)
        info = parser.info()
        assert isinstance(info, dict)
        assert 'title' in info
        sl = parser.scanlist()
        assert isinstance(sl, dict)
        assert len(sl) > 0
        parser.load()
        assert isinstance(parser._scans, dict)
        assert len(parser._scans) == len(sl)
        first_id = sorted(sl.keys())[0]
        scan = parser.scan(first_id)
        assert scan is not None
        assert scan.scanNumber == first_id
        if scan.peaklist:
            assert len(scan.peaklist) > 0
        elif scan.profile is not None:
            assert len(scan.profile) > 0

    def test_makeScan(self, tmp_path):
        """Step 6: Unit Test ParseMZData._makeScan."""
        temp_path = tmp_path / 'init_file'
        temp_path.touch()
        parser = parser_mzdata.ParseMZData(temp_path)
        mz_vals = [100.0, 200.0]
        int_vals = [50.0, 100.0]
        fmt = '<' + 'f' * 2
        mz_bin = struct.pack(fmt, *mz_vals)
        int_bin = struct.pack(fmt, *int_vals)
        scanData = {'title': 'Test Scan', 'scanNumber': 123, 'parentScanNumber': 122, 'msLevel': 2, 'polarity': 1, 'retentionTime': 600.0, 'totIonCurrent': 10000.0, 'basePeakMZ': 200.0, 'basePeakIntensity': 100.0, 'precursorMZ': 500.0, 'precursorIntensity': 5000.0, 'precursorCharge': 2, 'spectrumType': 'discrete', 'mzData': base64.b64encode(mz_bin), 'intData': base64.b64encode(int_bin), 'mzEndian': 'little', 'mzPrecision': 32, 'intEndian': 'little', 'intPrecision': 32}
        scan = parser._makeScan(scanData)
        assert scan.title == 'Test Scan'
        assert scan.scanNumber == 123
        assert scan.parentScanNumber == 122
        assert scan.msLevel == 2
        assert scan.polarity == 1
        assert scan.retentionTime == 600.0
        assert scan.totIonCurrent == 10000.0
        assert scan.basePeakMZ == 200.0
        assert scan.basePeakIntensity == 100.0
        assert scan.precursorMZ == 500.0
        assert scan.precursorIntensity == 5000.0
        assert scan.precursorCharge == 2
        assert scan.peaklist is not None
        assert len(scan.peaklist) == 2
        assert scan.peaklist[0].mz == pytest.approx(100.0)
        assert scan.peaklist[0].intensity == pytest.approx(50.0)
        scanData['spectrumType'] = 'continuous'
        scan_cont = parser._makeScan(scanData)
        assert scan_cont.profile is not None
        assert isinstance(scan_cont.profile, np.ndarray)
        assert scan_cont.profile.shape == (2, 2)
        assert scan_cont.profile[0, 0] == pytest.approx(100.0)
        assert scan_cont.profile[0, 1] == pytest.approx(50.0)

    def test_parseMZDATA_info(self, mocker):
        """Step 7: Unit Test ParseMZData.info."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzdata.ParseMZData('/some/path')
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        mock_file = mocker.mock_open()
        mocker.patch('pathlib.Path.open', mock_file)
        mock_handler = mocker.Mock()
        mock_handler.data = {'title': 'Test'}
        mocker.patch('mmass.mspy.parser_mzdata.InfoHandler', return_value=mock_handler)
        mock_sax_parser.parse.side_effect = parser_mzdata.StopParsingError()
        info = parser.info()
        assert info == {'title': 'Test'}
        assert parser._info == {'title': 'Test'}
        parser._info = None
        mock_sax_parser.parse.side_effect = None
        info = parser.info()
        assert info is None
        assert parser._info is None
        parser._info = {'title': 'Cached'}
        mock_sax_parser.parse.reset_mock()
        info_cached = parser.info()
        assert info_cached == {'title': 'Cached'}
        assert not mock_sax_parser.parse.called
        parser._info = None
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Error')
        info_error = parser.info()
        assert not info_error
        assert not parser._info

    def test_parseMZDATA_init(self, mocker):
        """Step 7: Unit Test ParseMZData.__init__."""
        mocker.patch('pathlib.Path.exists', return_value=False)
        with pytest.raises(IOError, match='File not found!'):
            parser_mzdata.ParseMZData('/non/existent/path')

    def test_parseMZDATA_load(self, mocker):
        """Step 7: Unit Test ParseMZData.load."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzdata.ParseMZData('/some/path')
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        mock_file = mocker.mock_open()
        mocker.patch('pathlib.Path.open', mock_file)
        mock_handler = mocker.Mock()
        mock_handler.data = {1: {'mzData': 'data1', 'mzEndian': 'little', 'mzPrecision': 32, 'intData': 'data2', 'intEndian': 'little', 'intPrecision': 32, 'other': 'value'}, 2: {'mzData': 'data3', 'mzEndian': 'little', 'mzPrecision': 64, 'intData': 'data4', 'intEndian': 'little', 'intPrecision': 64, 'other': 'value2'}}
        mocker.patch('mmass.mspy.parser_mzdata.RunHandler', return_value=mock_handler)
        parser.load()
        assert parser._scans == mock_handler.data
        assert 1 in parser._scanlist
        assert 2 in parser._scanlist
        for scanID in parser._scanlist:
            assert 'mzData' not in parser._scanlist[scanID]
            assert 'mzEndian' not in parser._scanlist[scanID]
            assert 'mzPrecision' not in parser._scanlist[scanID]
            assert 'intData' not in parser._scanlist[scanID]
            assert 'intEndian' not in parser._scanlist[scanID]
            assert 'intPrecision' not in parser._scanlist[scanID]
            assert 'other' in parser._scanlist[scanID]
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Error')
        parser.load()
        assert not parser._scans

    def test_parseMZDATA_scan(self, mocker):
        """Step 7: Unit Test ParseMZData.scan."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzdata.ParseMZData('/some/path')
        mocker.patch.object(parser_mzdata.ParseMZData, '_makeScan', side_effect=lambda x: x)
        parser._scans = {1: {'id': 1}}
        scan = parser.scan(1)
        assert scan == {'id': 1}
        parser._scans = None
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        mocker.patch('pathlib.Path.open', mocker.mock_open())
        mock_handler = mocker.Mock()
        mock_handler.data = {2: {'id': 2}}
        mocker.patch('mmass.mspy.parser_mzdata.ScanHandler', return_value=mock_handler)
        scan2 = parser.scan(2)
        assert scan2 == {2: {'id': 2}}
        mock_sax_parser.parse.side_effect = parser_mzdata.StopParsingError()
        mock_handler.data = {3: {'id': 3}}
        scan3 = parser.scan(3)
        assert scan3 == {3: {'id': 3}}
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Error')
        scan_error = parser.scan(4)
        assert not scan_error
        mock_sax_parser.parse.side_effect = None
        mock_handler.data = None
        scan_empty = parser.scan(5)
        assert not scan_empty

    def test_parseMZDATA_scanlist(self, mocker):
        """Step 7: Unit Test ParseMZData.scanlist."""
        mocker.patch('pathlib.Path.exists', return_value=True)
        parser = parser_mzdata.ParseMZData('/some/path')
        mock_sax_parser = mocker.Mock()
        mocker.patch('xml.sax.make_parser', return_value=mock_sax_parser)
        mock_file = mocker.mock_open()
        mocker.patch('pathlib.Path.open', mock_file)
        mock_handler = mocker.Mock()
        mock_handler.data = {1: {'title': 'Scan 1'}}
        mocker.patch('mmass.mspy.parser_mzdata.ScanlistHandler', return_value=mock_handler)
        sl = parser.scanlist()
        assert sl == {1: {'title': 'Scan 1'}}
        assert parser._scanlist == {1: {'title': 'Scan 1'}}
        mock_sax_parser.parse.reset_mock()
        sl_cached = parser.scanlist()
        assert sl_cached == {1: {'title': 'Scan 1'}}
        assert not mock_sax_parser.parse.called
        parser._scanlist = None
        mock_sax_parser.parse.side_effect = xml.sax.SAXException('Error')
        sl_error = parser.scanlist()
        assert not sl_error
        assert not parser._scanlist

    def test_parsePoints_edge_cases(self, tmp_path):
        """Step 5: Unit Test ParseMZData._parsePoints edge cases."""
        temp_path = tmp_path / 'init_file'
        temp_path.touch()
        parser = parser_mzdata.ParseMZData(temp_path)
        assert parser._parsePoints({'mzData': None, 'intData': 'someData'}) == []
        assert parser._parsePoints({'mzData': 'someData', 'intData': None}) == []
        assert parser._parsePoints({'mzData': None, 'intData': None}) == []
        scanData = {'mzData': base64.b64encode(b''), 'intData': base64.b64encode(b''), 'mzEndian': 'little', 'mzPrecision': 32, 'intEndian': 'little', 'intPrecision': 32, 'spectrumType': 'discrete'}
        assert parser._parsePoints(scanData) == []
        scanData['spectrumType'] = 'continuous'
        assert parser._parsePoints(scanData) == []


class TestMZDataMisc:
    """Miscellaneous tests for parser_mzdata."""

    def test_stopparsing_exception(self):
        """Step 2: Verify that raising StopParsingError works as expected."""
        with pytest.raises(parser_mzdata.StopParsingError):
            raise parser_mzdata.StopParsingError()


class TestPropertyBased:
    """Property-based tests for mzData parsing."""

    @settings(max_examples=20, deadline=1000, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.lists(st.tuples(st.floats(min_value=-10000000000.0, max_value=10000000000.0, allow_infinity=False, allow_nan=False), st.floats(min_value=-10000000000.0, max_value=10000000000.0, allow_infinity=False, allow_nan=False)), min_size=1, max_size=10))
    def test_parsePoints_hypothesis(self, tmp_path, points):
        """Step 5: Unit Test ParseMZData._parsePoints with hypothesis."""
        temp_path = tmp_path / 'init_file'
        temp_path.touch()
        parser = parser_mzdata.ParseMZData(temp_path)
        mz_vals = [p[0] for p in points]
        int_vals = [p[1] for p in points]
        configs = [('little', 32), ('little', 64), ('big', 32), ('big', 64), ('network', 32), ('network', 64)]
        endian_map = {'little': '<', 'big': '>', 'network': '!'}
        precision_map = {32: 'f', 64: 'd'}
        for endian, precision in configs:
            fmt = endian_map[endian] + precision_map[precision] * len(mz_vals)
            mz_bin = struct.pack(fmt, *mz_vals)
            int_bin = struct.pack(fmt, *int_vals)
            scanData = {'mzData': base64.b64encode(mz_bin), 'intData': base64.b64encode(int_bin), 'mzEndian': endian, 'mzPrecision': precision, 'intEndian': endian, 'intPrecision': precision, 'spectrumType': 'discrete'}
            parsed = parser._parsePoints(scanData)
            assert len(parsed) == len(points)
            for i in range(len(points)):
                assert parsed[i][0] == pytest.approx(points[i][0], rel=1e-05 if precision == 32 else 1e-12)
                assert parsed[i][1] == pytest.approx(points[i][1], rel=1e-05 if precision == 32 else 1e-12)
            scanData['spectrumType'] = 'continuous'
            parsed_cont = parser._parsePoints(scanData)
            assert isinstance(parsed_cont, np.ndarray)
            assert parsed_cont.shape == (len(points), 2)
            for i in range(len(points)):
                assert parsed_cont[i, 0] == pytest.approx(points[i][0], rel=1e-05 if precision == 32 else 1e-12)
                assert parsed_cont[i, 1] == pytest.approx(points[i][1], rel=1e-05 if precision == 32 else 1e-12)
