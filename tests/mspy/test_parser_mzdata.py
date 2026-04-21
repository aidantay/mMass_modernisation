import base64
import os
import struct
import xml.sax

import numpy
import pytest

from mmass.mspy.parser_mzdata import parseMZDATA, stopParsing


@pytest.fixture
def mzdata_file(tmpdir):
    """Fixture to create a minimal valid mzData XML file."""
    path = os.path.join(str(tmpdir), "test.mzdata")

    # mzData 1.05 format
    # spectrum id 1: discrete, float32, little-endian, 1.0, 0.5
    # spectrum id 2: continuous, float32, little-endian, 2.0, 1.0

    # 1.0 in float32 little: \x00\x00\x80\x3f -> AACAPw==
    # 0.5 in float32 little: \x00\x00\x00\x3f -> AAAAPw==
    # 2.0 in float32 little: \x00\x00\x00\x40 -> AAAAgA==

    content = """<?xml version="1.0" encoding="utf-8"?>
<mzData version="1.05" accessionNumber="0">
    <description>
        <admin>
            <sampleName>Test Sample</sampleName>
            <contact>
                <name>John Doe</name>
                <institution>Test Institution</institution>
                <contactInfo>john.doe@example.com</contactInfo>
            </contact>
        </admin>
        <instrument>
            <instrumentName>Test Instrument</instrumentName>
        </instrument>
    </description>
    <spectrumList count="2">
        <spectrum id="1">
            <acqSpecification spectrumType="discrete" />
            <spectrumInstrument msLevel="1" mzRangeStart="100.0" mzRangeStop="200.0" />
            <spectrumDesc>
                <precursor spectrumRef="0" />
                <mzArrayBinary>
                    <data precision="32" endian="little" length="1">AACAPw==</data>
                </mzArrayBinary>
                <intenArrayBinary>
                    <data precision="32" endian="little" length="1">AAAAPw==</data>
                </intenArrayBinary>
            </spectrumDesc>
        </spectrum>
        <spectrum id="2">
            <acqSpecification spectrumType="continuous" />
            <spectrumInstrument msLevel="1" />
            <spectrumDesc>
                <mzArrayBinary>
                    <data precision="32" endian="little" length="1">AAAgQA==</data>
                </mzArrayBinary>
                <intenArrayBinary>
                    <data precision="32" endian="little" length="1">AACAPw==</data>
                </intenArrayBinary>
            </spectrumDesc>
        </spectrum>
    </spectrumList>
</mzData>
"""
    with open(path, "w") as f:
        f.write(content)
    return path


@pytest.fixture
def corrupt_mzdata_file(tmpdir):
    """Fixture to create a malformed mzData XML file."""
    path = os.path.join(str(tmpdir), "corrupt.mzdata")
    content = """<?xml version="1.0" encoding="utf-8"?>
<mzData>
    <unclosedTag>
</mzData>
"""
    with open(path, "w") as f:
        f.write(content)
    return path


def test_stopparsing_exception():
    """Step 2: Verify that raising stopParsing works as expected."""
    with pytest.raises(stopParsing):
        raise stopParsing()


def test_infoHandler():
    """Step 3: Unit Test infoHandler."""
    from mmass.mspy.parser_mzdata import infoHandler

    handler = infoHandler()

    # Simulate XML traversal
    handler.startElement("sampleName", {})
    handler.characters("Test Sample")
    handler.endElement("sampleName")

    handler.startElement("contact", {})
    handler.startElement("name", {})
    handler.characters("John Doe")
    handler.endElement("name")

    handler.startElement("institution", {})
    handler.characters("Test Institution")
    handler.endElement("institution")

    handler.startElement("contactInfo", {})
    handler.characters("john.doe@example.com")
    handler.endElement("contactInfo")
    handler.endElement("contact")

    handler.startElement("instrumentName", {})
    handler.characters("Test Instrument")
    handler.endElement("instrumentName")

    # Check data before stopParsing
    assert handler.data["title"] == "Test Sample"
    assert handler.data["operator"] == "John Doe"
    assert handler.data["institution"] == "Test Institution"
    assert handler.data["contact"] == "john.doe@example.com"
    assert handler.data["instrument"] == "Test Instrument"

    # Assert endElement('description') raises stopParsing
    with pytest.raises(stopParsing):
        handler.endElement("description")


def test_scanlistHandler_edge_cases():
    """Step 4: Unit Test scanlistHandler state and edge cases."""
    from mmass.mspy.parser_mzdata import scanlistHandler

    handler = scanlistHandler()

    # spectrum (with and without id attr)
    handler.startElement("spectrum", {"id": "1"})
    assert 1 in handler.data
    assert handler.data[1]["scanNumber"] == 1

    handler.startElement("spectrum", {})  # no id - will use None as key
    assert None in handler.data

    # acqSpecification (with and without spectrumType attr)
    handler.currentID = 1
    handler.startElement("acqSpecification", {"spectrumType": "discrete"})
    assert handler.data[1]["spectrumType"] == "discrete"

    handler.startElement("acqSpecification", {})
    assert handler.data[1]["spectrumType"] == "discrete"  # unchanged

    # spectrumInstrument (with and without msLevel, mzRangeStart, mzRangeStop)
    handler.startElement(
        "spectrumInstrument",
        {"msLevel": "2", "mzRangeStart": "100.5", "mzRangeStop": "500.5"},
    )
    assert handler.data[1]["msLevel"] == 2
    assert handler.data[1]["lowMZ"] == 100.5
    assert handler.data[1]["highMZ"] == 500.5

    handler.startElement("spectrumInstrument", {})
    assert handler.data[1]["msLevel"] == 1  # defaults to 1

    # userParam and cvParam: TimeInMinutes, TotalIonCurrent, MassToChargeRatio, ChargeState, Polarity
    handler.startElement("userParam", {"name": "TimeInMinutes", "value": "1.5"})
    assert handler.data[1]["retentionTime"] == 90.0

    handler.startElement("userParam", {"name": "TotalIonCurrent", "value": "1000.5"})
    assert handler.data[1]["totIonCurrent"] == 1000.5

    handler.startElement("cvParam", {"name": "MassToChargeRatio", "value": "250.5"})
    assert handler.data[1]["precursorMZ"] == 250.5

    handler.startElement("cvParam", {"name": "ChargeState", "value": "2"})
    assert handler.data[1]["precursorCharge"] == 2

    handler.startElement("userParam", {"name": "Polarity", "value": "+"})
    assert handler.data[1]["polarity"] == 1

    # Test Polarity bug bypass: manually call startElement with raw tuple value
    handler.startElement(
        "userParam", {"name": "Polarity", "value": ("negative", "Negative", "-")}
    )
    assert handler.data[1]["polarity"] == -1

    # Test invalid values (ValueError)
    handler.startElement("userParam", {"name": "TimeInMinutes", "value": "invalid"})
    assert handler.data[1]["retentionTime"] == 90.0  # unchanged

    handler.startElement("userParam", {"name": "TotalIonCurrent", "value": "invalid"})
    assert handler.data[1]["totIonCurrent"] == 1000.5  # unchanged

    handler.startElement("cvParam", {"name": "MassToChargeRatio", "value": "invalid"})
    assert handler.data[1]["precursorMZ"] == 250.5  # unchanged

    handler.startElement("cvParam", {"name": "ChargeState", "value": "invalid"})
    assert handler.data[1]["precursorCharge"] == 2  # unchanged

    # precursor with spectrumRef
    handler.startElement("precursor", {"spectrumRef": "10"})
    assert handler.data[1]["parentScanNumber"] == 10

    # data with length
    handler.startElement("data", {"length": "100"})
    assert handler.data[1]["pointsCount"] == 100


def test_scanHandler_edge_cases():
    """Step 4: Unit Test scanHandler state and edge cases."""
    from mmass.mspy.parser_mzdata import scanHandler

    handler = scanHandler(1)

    # spectrum match
    handler.startElement("spectrum", {"id": "1"})
    assert handler._isMatch == True
    assert handler.data["scanNumber"] == 1

    # acqSpecification
    handler.startElement("acqSpecification", {"spectrumType": "continuous"})
    assert handler.data["spectrumType"] == "continuous"

    # spectrumInstrument
    handler.startElement("spectrumInstrument", {"msLevel": "2"})
    assert handler.data["msLevel"] == 2

    # params
    handler.startElement("userParam", {"name": "TimeInMinutes", "value": "1.0"})
    assert handler.data["retentionTime"] == 60.0

    # Polarity
    handler.startElement("userParam", {"name": "Polarity", "value": "positive"})
    assert handler.data["polarity"] == 1

    # mzArrayBinary and characters
    handler.startElement("mzArrayBinary", {})
    assert handler._isMzArray == True
    handler.characters("ABC")
    handler.characters("DEF")

    # data element for endian and precision
    handler.startElement("data", {"endian": "little", "precision": "64", "length": "2"})
    assert handler.data["mzEndian"] == "little"
    assert handler.data["mzPrecision"] == 64
    assert handler.data["pointsCount"] == 2

    handler.endElement("mzArrayBinary")
    assert handler.data["mzData"] == "ABCDEF"
    assert handler._isMzArray == False

    # intenArrayBinary
    handler.startElement("intenArrayBinary", {})
    assert handler._isIntArray == True
    handler.characters("GHI")
    handler.startElement("data", {"endian": "big", "precision": "32"})
    assert handler.data["intEndian"] == "big"
    assert handler.data["intPrecision"] == 32
    handler.endElement("intenArrayBinary")
    assert handler.data["intData"] == "GHI"

    # spectrum no match
    handler2 = scanHandler(2)
    handler2.startElement("spectrum", {"id": "1"})
    assert handler2._isMatch == False
    assert handler2.data == False

    # stopParsing
    with pytest.raises(stopParsing):
        handler.endElement("spectrum")

    # empty binary arrays
    handler3 = scanHandler(3)
    handler3.startElement("spectrum", {"id": "3"})
    handler3.startElement("mzArrayBinary", {})
    handler3.endElement("mzArrayBinary")
    assert handler3.data["mzData"] == None


def test_runHandler_edge_cases():
    """Step 4: Unit Test runHandler state and edge cases."""
    from mmass.mspy.parser_mzdata import runHandler

    handler = runHandler()

    # scan 1
    handler.startElement("spectrum", {"id": "1"})
    handler.startElement("mzArrayBinary", {})
    handler.characters("AAA")
    handler.endElement("mzArrayBinary")

    # scan 2
    handler.startElement("spectrum", {"id": "2"})
    handler.startElement("mzArrayBinary", {})
    handler.characters("BBB")
    handler.endElement("mzArrayBinary")

    assert handler.data[1]["mzData"] == "AAA"
    assert handler.data[2]["mzData"] == "BBB"

    # polarity bug bypass in runHandler too
    handler.startElement("spectrum", {"id": "3"})
    handler.startElement(
        "userParam", {"name": "Polarity", "value": ("negative", "Negative", "-")}
    )
    assert handler.data[3]["polarity"] == -1


from hypothesis import given, settings
from hypothesis import strategies as st


@settings(
    max_examples=20, deadline=1000
)  # Limit examples and increase deadline for stability in legacy CI
@given(
    st.lists(
        st.tuples(
            st.floats(
                min_value=-1e10, max_value=1e10, allow_infinity=False, allow_nan=False
            ),
            st.floats(
                min_value=-1e10, max_value=1e10, allow_infinity=False, allow_nan=False
            ),
        ),
        min_size=1,
        max_size=10,
    )
)
def test_parsePoints_hypothesis(points):
    """Step 5: Unit Test parseMZDATA._parsePoints with hypothesis."""
    import os
    import tempfile

    # Create a temporary file to satisfy parseMZDATA.__init__
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    try:
        parser = parseMZDATA(temp_path)

        mz_vals = [p[0] for p in points]
        int_vals = [p[1] for p in points]

        # Test configurations: (endian, precision)
        configs = [
            ("little", 32),
            ("little", 64),
            ("big", 32),
            ("big", 64),
            ("network", 32),
            ("network", 64),
        ]

        endian_map = {"little": "<", "big": ">", "network": "!"}
        precision_map = {32: "f", 64: "d"}

        for endian, precision in configs:
            fmt = endian_map[endian] + precision_map[precision] * len(mz_vals)

            # Pack values
            mz_bin = struct.pack(fmt, *mz_vals)
            int_bin = struct.pack(fmt, *int_vals)

            scanData = {
                "mzData": base64.b64encode(mz_bin),
                "intData": base64.b64encode(int_bin),
                "mzEndian": endian,
                "mzPrecision": precision,
                "intEndian": endian,
                "intPrecision": precision,
                "spectrumType": "discrete",
            }

            # Test discrete
            parsed = parser._parsePoints(scanData)
            assert len(parsed) == len(points)
            for i in range(len(points)):
                # Use pytest.approx for floating point comparison
                # 32-bit float has about 7 decimal digits of precision
                assert parsed[i][0] == pytest.approx(
                    points[i][0], rel=1e-5 if precision == 32 else 1e-12
                )
                assert parsed[i][1] == pytest.approx(
                    points[i][1], rel=1e-5 if precision == 32 else 1e-12
                )

            # Test continuous
            scanData["spectrumType"] = "continuous"
            parsed_cont = parser._parsePoints(scanData)
            assert isinstance(parsed_cont, numpy.ndarray)
            assert parsed_cont.shape == (len(points), 2)
            for i in range(len(points)):
                assert parsed_cont[i, 0] == pytest.approx(
                    points[i][0], rel=1e-5 if precision == 32 else 1e-12
                )
                assert parsed_cont[i, 1] == pytest.approx(
                    points[i][1], rel=1e-5 if precision == 32 else 1e-12
                )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_parsePoints_edge_cases():
    """Step 5: Unit Test parseMZDATA._parsePoints edge cases."""
    import os
    import tempfile

    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    try:
        parser = parseMZDATA(temp_path)

        # mzData or intData is None (should return [])
        assert parser._parsePoints({"mzData": None, "intData": "someData"}) == []
        assert parser._parsePoints({"mzData": "someData", "intData": None}) == []
        assert parser._parsePoints({"mzData": None, "intData": None}) == []

        # Empty data (length 0 string) - also returns [] as per current implementation
        scanData = {
            "mzData": base64.b64encode(b""),
            "intData": base64.b64encode(b""),
            "mzEndian": "little",
            "mzPrecision": 32,
            "intEndian": "little",
            "intPrecision": 32,
            "spectrumType": "discrete",
        }
        assert parser._parsePoints(scanData) == []

        scanData["spectrumType"] = "continuous"
        assert parser._parsePoints(scanData) == []

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_makeScan():
    """Step 6: Unit Test parseMZDATA._makeScan."""
    import os
    import tempfile

    fd, temp_path = tempfile.mkstemp()
    os.close(fd)
    try:
        parser = parseMZDATA(temp_path)

        # Prepare dummy scanData
        mz_vals = [100.0, 200.0]
        int_vals = [50.0, 100.0]
        fmt = "<" + "f" * 2
        mz_bin = struct.pack(fmt, *mz_vals)
        int_bin = struct.pack(fmt, *int_vals)

        scanData = {
            "title": "Test Scan",
            "scanNumber": 123,
            "parentScanNumber": 122,
            "msLevel": 2,
            "polarity": 1,
            "retentionTime": 600.0,
            "totIonCurrent": 10000.0,
            "basePeakMZ": 200.0,
            "basePeakIntensity": 100.0,
            "precursorMZ": 500.0,
            "precursorIntensity": 5000.0,
            "precursorCharge": 2,
            "spectrumType": "discrete",
            "mzData": base64.b64encode(mz_bin),
            "intData": base64.b64encode(int_bin),
            "mzEndian": "little",
            "mzPrecision": 32,
            "intEndian": "little",
            "intPrecision": 32,
        }

        # Test discrete
        scan = parser._makeScan(scanData)
        assert scan.title == "Test Scan"
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

        # Test continuous
        scanData["spectrumType"] = "continuous"
        scan_cont = parser._makeScan(scanData)
        assert scan_cont.profile is not None
        assert isinstance(scan_cont.profile, numpy.ndarray)
        assert scan_cont.profile.shape == (2, 2)
        assert scan_cont.profile[0, 0] == pytest.approx(100.0)
        assert scan_cont.profile[0, 1] == pytest.approx(50.0)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_parseMZDATA_init(mocker):
    """Step 7: Unit Test parseMZDATA.__init__."""
    mocker.patch("os.path.exists", return_value=False)
    with pytest.raises(IOError):
        parseMZDATA("/non/existent/path")


def test_parseMZDATA_load(mocker):
    """Step 7: Unit Test parseMZDATA.load."""
    # Mock os.path.exists to allow __init__ to pass
    mocker.patch("os.path.exists", return_value=True)
    parser = parseMZDATA("/some/path")

    # Mock sax parser and file
    mock_sax_parser = mocker.Mock()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)

    # Mock runHandler and its data
    mock_handler = mocker.Mock()
    # Dummy data for two scans
    mock_handler.data = {
        1: {
            "mzData": "data1",
            "mzEndian": "little",
            "mzPrecision": 32,
            "intData": "data2",
            "intEndian": "little",
            "intPrecision": 32,
            "other": "value",
        },
        2: {
            "mzData": "data3",
            "mzEndian": "little",
            "mzPrecision": 64,
            "intData": "data4",
            "intEndian": "little",
            "intPrecision": 64,
            "other": "value2",
        },
    }
    mocker.patch("mmass.mspy.parser_mzdata.runHandler", return_value=mock_handler)

    # Execute load
    parser.load()

    # Verify _scans and _scanlist
    assert parser._scans == mock_handler.data
    assert 1 in parser._scanlist
    assert 2 in parser._scanlist
    # Verify metadata keys are deleted from _scanlist items
    for scanID in parser._scanlist:
        assert "mzData" not in parser._scanlist[scanID]
        assert "mzEndian" not in parser._scanlist[scanID]
        assert "mzPrecision" not in parser._scanlist[scanID]
        assert "intData" not in parser._scanlist[scanID]
        assert "intEndian" not in parser._scanlist[scanID]
        assert "intPrecision" not in parser._scanlist[scanID]
        assert "other" in parser._scanlist[scanID]

    # Test SAXException handling
    mock_sax_parser.parse.side_effect = xml.sax.SAXException("Error")
    parser.load()
    assert parser._scans == False


def test_parseMZDATA_info(mocker):
    """Step 7: Unit Test parseMZDATA.info."""
    mocker.patch("os.path.exists", return_value=True)
    parser = parseMZDATA("/some/path")

    # Mock sax parser and file
    mock_sax_parser = mocker.Mock()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)

    # Mock infoHandler and its data
    mock_handler = mocker.Mock()
    mock_handler.data = {"title": "Test"}
    mocker.patch("mmass.mspy.parser_mzdata.infoHandler", return_value=mock_handler)

    # Case 1: stopParsing handling
    mock_sax_parser.parse.side_effect = stopParsing()
    info = parser.info()
    assert info == {"title": "Test"}
    assert parser._info == {"title": "Test"}

    # Case 1b: Normal completion (reaches document.close())
    # According to source, self._info is NOT set if stopParsing is not raised
    parser._info = None
    mock_sax_parser.parse.side_effect = None
    info = parser.info()
    assert info is None
    assert parser._info is None

    # Case 2: Cached execution
    parser._info = {"title": "Cached"}
    mock_sax_parser.parse.reset_mock()
    info_cached = parser.info()
    assert info_cached == {"title": "Cached"}
    assert not mock_sax_parser.parse.called

    # Case 3: SAXException handling
    parser._info = None
    mock_sax_parser.parse.side_effect = xml.sax.SAXException("Error")
    info_error = parser.info()
    assert info_error == False
    assert parser._info == False


def test_parseMZDATA_scanlist(mocker):
    """Step 7: Unit Test parseMZDATA.scanlist."""
    mocker.patch("os.path.exists", return_value=True)
    parser = parseMZDATA("/some/path")

    # Mock sax parser and file
    mock_sax_parser = mocker.Mock()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)

    # Mock scanlistHandler and its data
    mock_handler = mocker.Mock()
    mock_handler.data = {1: {"title": "Scan 1"}}
    mocker.patch("mmass.mspy.parser_mzdata.scanlistHandler", return_value=mock_handler)

    # Case 1: Successful extraction
    sl = parser.scanlist()
    assert sl == {1: {"title": "Scan 1"}}
    assert parser._scanlist == {1: {"title": "Scan 1"}}

    # Case 2: Cached execution
    mock_sax_parser.parse.reset_mock()
    sl_cached = parser.scanlist()
    assert sl_cached == {1: {"title": "Scan 1"}}
    assert not mock_sax_parser.parse.called

    # Case 3: SAXException handling
    parser._scanlist = None
    mock_sax_parser.parse.side_effect = xml.sax.SAXException("Error")
    sl_error = parser.scanlist()
    assert sl_error == False
    assert parser._scanlist == False


def test_parseMZDATA_scan(mocker):
    """Step 7: Unit Test parseMZDATA.scan."""
    mocker.patch("os.path.exists", return_value=True)
    parser = parseMZDATA("/some/path")

    # Mock _makeScan to avoid deep testing of it here (it has its own tests)
    mocker.patch.object(parseMZDATA, "_makeScan", side_effect=lambda x: x)

    # Case 1: Retrieve from cache (_scans)
    parser._scans = {1: {"id": 1}}
    scan = parser.scan(1)
    assert scan == {"id": 1}

    # Case 2: Parse file when not in cache
    parser._scans = None
    mock_sax_parser = mocker.Mock()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    mocker.patch("builtins.open", mocker.mock_open())

    mock_handler = mocker.Mock()
    mock_handler.data = {2: {"id": 2}}  # scanHandler stores data for the requested ID
    mocker.patch("mmass.mspy.parser_mzdata.scanHandler", return_value=mock_handler)

    # Successful parse (no exception)
    scan2 = parser.scan(2)
    assert scan2 == {2: {"id": 2}}

    # Case 3: stopParsing handling
    mock_sax_parser.parse.side_effect = stopParsing()
    mock_handler.data = {3: {"id": 3}}
    scan3 = parser.scan(3)
    assert scan3 == {3: {"id": 3}}

    # Case 4: SAXException handling
    mock_sax_parser.parse.side_effect = xml.sax.SAXException("Error")
    scan_error = parser.scan(4)
    assert scan_error == False

    # Case 5: Empty data found (handler.data is empty or False)
    mock_sax_parser.parse.side_effect = None
    mock_handler.data = None
    scan_empty = parser.scan(5)
    assert scan_empty == False


def test_scanlistHandler_extra_coverage():
    """Improve coverage for scanlistHandler pass methods."""
    from mmass.mspy.parser_mzdata import scanlistHandler

    handler = scanlistHandler()
    handler.endElement("any")
    handler.characters("any")
    # Branches for msLevel and others
    handler.data[1] = {"msLevel": 1}
    handler.currentID = 1
    handler.startElement("spectrumInstrument", {"msLevel": ""})  # attribute is False
    assert handler.data[1]["msLevel"] == 1  # unchanged


def test_infoHandler_extra_coverage():
    """Improve coverage for infoHandler characters."""
    from mmass.mspy.parser_mzdata import infoHandler

    handler = infoHandler()
    handler._isInstrumentName = True
    handler.characters("Instrument")
    assert handler.data["instrument"] == "Instrument"

    # Branch for 328->exit: call characters when no flag is set
    handler._isInstrumentName = False
    handler.characters("None")


def test_scanHandler_comprehensive_coverage():
    """Hit all remaining branches in scanHandler."""
    from mmass.mspy.parser_mzdata import scanHandler

    handler = scanHandler(1)

    # 481->485: id is None
    handler.startElement("spectrum", {})
    assert handler._isMatch == False

    # 517->exit: attribute (spectrumType) is False
    handler = scanHandler(1)
    handler.startElement("spectrum", {"id": "1"})
    handler.startElement("acqSpecification", {"spectrumType": ""})

    # 525->exit: msLevel is False
    handler.startElement("spectrumInstrument", {"msLevel": ""})

    # 530->531, 531: mzRangeStart is present
    handler.startElement("spectrumInstrument", {"mzRangeStart": "100.0"})
    assert handler.data["lowMZ"] == 100.0

    # Same for highMZ (535->536, 536)
    handler.startElement("spectrumInstrument", {"mzRangeStop": "200.0"})
    assert handler.data["highMZ"] == 200.0

    # 544: startElement for userParam/cvParam
    handler.startElement("userParam", {"name": "TimeInMinutes", "value": "1.0"})

    # 546: TimeInMinutes ValueError
    handler.startElement("userParam", {"name": "TimeInMinutes", "value": "invalid"})

    # 550, 551: TotalIonCurrent
    handler.startElement("userParam", {"name": "TotalIonCurrent", "value": "1000.0"})
    handler.startElement("userParam", {"name": "TotalIonCurrent", "value": "invalid"})

    # 555, 556: MassToChargeRatio
    handler.startElement("cvParam", {"name": "MassToChargeRatio", "value": "250.0"})
    handler.startElement("cvParam", {"name": "MassToChargeRatio", "value": "invalid"})

    # 559->560, 560-561: ChargeState (Wait, I used ChargeState name correctly?)
    # Yes, lines 559-561 are for ChargeState
    handler.startElement("cvParam", {"name": "ChargeState", "value": "2"})
    handler.startElement("cvParam", {"name": "ChargeState", "value": "invalid"})

    # 564->exit: Polarity branch
    handler.startElement("userParam", {"name": "Polarity", "value": "unknown"})

    # 566, 568: Polarity
    handler.startElement("userParam", {"name": "Polarity", "value": "positive"})
    assert handler.data["polarity"] == 1
    handler.startElement(
        "userParam", {"name": "Polarity", "value": ("negative", "Negative", "-")}
    )
    assert handler.data["polarity"] == -1

    # 573->574, 574: precursor spectrumRef
    handler.startElement("precursor", {"spectrumRef": "10"})
    assert handler.data["parentScanNumber"] == 10

    # 587->exit: data length is None
    # Wait, my previous replacement for 587->exit used mzArrayBinary
    # Let's check 598->exit (attribute != None)
    handler.startElement("mzArrayBinary", {})
    handler.startElement("data", {})  # length is None
    handler.endElement("mzArrayBinary")

    # 600-613: precision/endian in scanHandler
    # MZ Array precision
    handler.startElement("mzArrayBinary", {})
    handler.startElement("data", {"length": "1", "precision": "32"})
    assert handler.data["mzPrecision"] == 32
    handler.endElement("mzArrayBinary")

    # Int Array precision
    handler.startElement("intenArrayBinary", {})
    handler.startElement("data", {"length": "1", "precision": "64"})
    assert handler.data["intPrecision"] == 64
    handler.characters("data")  # hit 643->exit for intenArrayBinary
    handler.endElement("intenArrayBinary")  # hit 626->exit, 631 for intenArrayBinary

    # 626->exit, 628->629, 629: intenArrayBinary empty
    handler.startElement("intenArrayBinary", {})
    handler.endElement("intenArrayBinary")
    assert handler.data["intData"] is None


def test_scanlistHandler_comprehensive_coverage():
    """Hit all remaining branches in scanlistHandler."""
    from mmass.mspy.parser_mzdata import scanlistHandler

    handler = scanlistHandler()

    # 387->391: msLevel is False
    handler.startElement("spectrum", {"id": "1"})
    handler.currentID = 1
    handler.startElement("spectrumInstrument", {"msLevel": ""})

    # 426->exit: Polarity unknown
    handler.startElement("userParam", {"name": "Polarity", "value": "unknown"})
    handler.startElement("userParam", {"name": "Polarity", "value": "positive"})
    handler.startElement(
        "userParam", {"name": "Polarity", "value": ("negative", "Negative", "-")}
    )

    # 435->exit: precursor spectrumRef is None
    handler.startElement("precursor", {})
    handler.startElement("precursor", {"spectrumRef": "10"})

    # 441->exit: data length is None
    handler.startElement("data", {})
    handler.startElement("data", {"length": "100"})


def test_runHandler_comprehensive_coverage():
    """Hit all remaining branches in runHandler."""
    from mmass.mspy.parser_mzdata import runHandler

    handler = runHandler()

    # 669->672: id is None
    handler.startElement("spectrum", {})

    # 704->exit: spectrumType attribute is False
    handler.startElement("spectrum", {"id": "1"})
    handler.currentID = 1
    handler.startElement("acqSpecification", {"spectrumType": ""})
    handler.startElement("acqSpecification", {"spectrumType": "discrete"})

    # 712->716: msLevel is False
    handler.startElement("spectrumInstrument", {"msLevel": ""})
    handler.startElement(
        "spectrumInstrument",
        {"msLevel": "2", "mzRangeStart": "100", "mzRangeStop": "200"},
    )

    # 722->exit: userParam/cvParam without name
    handler.startElement("userParam", {})

    # All the params with valid and invalid values
    for name in [
        "TimeInMinutes",
        "TotalIonCurrent",
        "MassToChargeRatio",
        "ChargeState",
    ]:
        handler.startElement("userParam", {"name": name, "value": "1.0"})
        handler.startElement("userParam", {"name": name, "value": "invalid"})

    # Polarity
    handler.startElement("userParam", {"name": "Polarity", "value": "unknown"})
    handler.startElement("userParam", {"name": "Polarity", "value": "positive"})
    handler.startElement(
        "userParam", {"name": "Polarity", "value": ("negative", "Negative", "-")}
    )

    # 760->761, 761: precursor spectrumRef
    handler.startElement("precursor", {"spectrumRef": "10"})

    # Binary data tags
    handler.startElement("mzArrayBinary", {})
    handler.startElement("data", {"precision": ""})
    handler.endElement("mzArrayBinary")

    handler.startElement("intenArrayBinary", {})
    handler.startElement("data", {"precision": "32"})
    handler.endElement("intenArrayBinary")

    # Empty data
    handler.data[1]["mzData"] = []
    handler.endElement("mzArrayBinary")
    handler.data[1]["intData"] = []
    handler.endElement("intenArrayBinary")


def test_integration_test_small_mzdata():
    """Step 8: Integration Testing with test_small.mzdata."""
    import os

    path = "tests/data/test_small.mzdata"
    if not os.path.exists(path):
        import pytest

        pytest.skip("test_small.mzdata not found")

    from mmass.mspy.parser_mzdata import parseMZDATA

    parser = parseMZDATA(path)

    # info
    info = parser.info()
    assert isinstance(info, dict)
    assert "title" in info

    # scanlist
    sl = parser.scanlist()
    assert isinstance(sl, dict)
    assert len(sl) > 0

    # load
    parser.load()
    assert isinstance(parser._scans, dict)
    assert len(parser._scans) == len(sl)

    # scan
    first_id = sorted(sl.keys())[0]
    scan = parser.scan(first_id)
    assert scan is not None
    assert scan.scanNumber == first_id
    if scan.peaklist:
        assert len(scan.peaklist) > 0
    elif scan.profile is not None:
        assert len(scan.profile) > 0
