import base64
import os
import struct
import xml.sax
import zlib

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays
from mspy.parser_mzxml import (
    _convertRetentionTime,
    infoHandler,
    parseMZXML,
    runHandler,
    scanHandler,
    scanlistHandler,
    stopParsing,
)

from mspy import obj_scan


# Test _convertRetentionTime
@pytest.mark.parametrize(
    "retention, expected",
    [
        ("PT1M30S", 90.0),
        ("PT2.5M", 150.0),
        ("PT45S", 45.0),
        ("PT1M", 60.0),
        ("PT0.5M30S", 60.0),
        ("invalid", None),
        ("1M30S", None),
        ("PT", 0.0),  # Current implementation returns 0 for "PT"
    ],
)
def test_convertRetentionTime(retention, expected):
    assert _convertRetentionTime(retention) == expected


# Test parseMZXML.__init__
def test_parseMZXML_init(tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")

    parser = parseMZXML(path)
    assert parser.path == path
    assert parser._scans is None
    assert parser._scanlist is None
    assert parser._info is None


def test_parseMZXML_init_nonexistent():
    with pytest.raises(IOError):
        parseMZXML("nonexistent_file.mzXML")


# Helper for creating a parser instance for internal method tests
@pytest.fixture
def parser_instance(tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    return parseMZXML(path)


# Property-based tests for _parsePoints
@settings(
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    deadline=None,
)
@given(
    points=arrays(
        np.float64,
        (10, 2),
        elements=st.floats(
            min_value=1e-10, max_value=1000, allow_nan=False, allow_infinity=False
        ),
    ),
    precision=st.sampled_from([32, 64]),
    byte_order=st.sampled_from(["little", "big", "network"]),
    compression=st.sampled_from(["zlib", "none"]),
    spectrum_type=st.sampled_from(["discrete", "continuous"]),
)
def test_parsePoints_property(
    parser_instance, points, precision, byte_order, compression, spectrum_type
):
    # Flatten points for packing
    flat_points = points.flatten()

    # Get precision format
    fmt_char = "f" if precision == 32 else "d"

    # Get endian format
    if byte_order == "little":
        endian = "<"
    elif byte_order == "big":
        endian = ">"
    else:
        endian = "!"

    # Pack data
    packed_data = struct.pack(endian + fmt_char * len(flat_points), *flat_points)

    # Compress data
    if compression == "zlib":
        compressed_data = zlib.compress(packed_data)
    else:
        compressed_data = packed_data

    # Base64 encode
    b64_data = base64.b64encode(compressed_data)

    # Prepare scanData
    scanData = {
        "points": b64_data,
        "precision": precision,
        "byteOrder": byte_order,
        "compression": compression,
        "spectrumType": spectrum_type,
    }

    # Parse points
    result = parser_instance._parsePoints(scanData)

    if spectrum_type == "discrete":
        # result is list of [mz, intensity]
        assert len(result) == len(points)
        for i in range(len(points)):
            np.testing.assert_allclose(
                result[i],
                points[i],
                rtol=1e-5 if precision == 32 else 1e-10,
                atol=1e-12,
            )
    else:
        # result is numpy array
        assert isinstance(result, np.ndarray)
        np.testing.assert_allclose(
            result, points, rtol=1e-5 if precision == 32 else 1e-10, atol=1e-12
        )


def test_parsePoints_empty(parser_instance):
    assert parser_instance._parsePoints({"points": None}) == []
    assert parser_instance._parsePoints({"points": ""}) == []


# Test SAX Handlers
def test_infoHandler():
    handler = infoHandler()
    handler.startElement("msManufacturer", {"value": "Manufacturer"})
    handler.startElement("msModel", {"value": "Model"})
    handler.startElement("msIonisation", {"value": "Ionisation"})
    handler.startElement("msMassAnalyzer", {"value": "Analyzer"})

    assert "Manufacturer" in handler.data["instrument"]
    assert "Model" in handler.data["instrument"]
    assert "Ionisation" in handler.data["instrument"]
    assert "Analyzer" in handler.data["instrument"]

    # Test missing value
    handler.startElement("msManufacturer", {})

    # Test non-matching endElement (coverage for exit branch)
    handler.endElement("somethingElse")

    with pytest.raises(stopParsing):
        handler.endElement("msInstrument")


def test_scanlistHandler_comprehensive():
    h = scanlistHandler()

    # Test dataProcessing
    h.startElement("dataProcessing", {"centroided": "1"})
    assert h._spectrumType == "discrete"
    h.startElement("dataProcessing", {"centroided": "0"})  # Covered branch
    h.endElement("dataProcessing")  # Cover exit branch

    # Scan with all attributes
    h.startElement(
        "scan",
        {
            "num": "1",
            "msLevel": "2",
            "peaksCount": "10",
            "polarity": "+",
            "retentionTime": "PT1S",
            "lowMz": "10",
            "highMz": "20",
            "basePeakMz": "15",
            "basePeakIntensity": "100",
            "totIonCurrent": "1000",
        },
    )
    h.startElement("precursorMz", {"precursorIntensity": "50", "precursorCharge": "2"})
    h.characters("100.5")
    h.endElement("precursorMz")
    h.endElement("scan")

    # Scan with all attributes missing/empty
    h.startElement("scan", {"num": "2", "msLevel": ""})
    h.startElement("precursorMz", {})
    h.endElement("precursorMz")
    h.endElement("scan")

    # Polarity variations
    h.startElement("scan", {"num": "3", "polarity": "negative"})
    h.startElement("scan", {"num": "4", "polarity": "-"})
    h.startElement("scan", {"num": "5", "polarity": "positive"})
    h.startElement("scan", {"num": "6", "polarity": "Positive"})
    h.startElement("scan", {"num": "7", "polarity": "Negative"})
    h.startElement("scan", {"num": "8", "polarity": "unknown"})

    # Scan without num attribute (coverage for 310->314)
    h.startElement("scan", {})
    h.endElement("scan")


def test_scanHandler_comprehensive():
    # Match scan 1
    h = scanHandler(1)
    h.startElement("dataProcessing", {"centroided": "1"})
    h.startElement(
        "scan",
        {
            "num": "1",
            "msLevel": "2",
            "peaksCount": "10",
            "polarity": "+",
            "retentionTime": "PT1S",
            "lowMz": "10",
            "highMz": "20",
            "basePeakMz": "15",
            "basePeakIntensity": "100",
            "totIonCurrent": "1000",
        },
    )
    h.startElement(
        "peaks", {"byteOrder": "little", "compressionType": "zlib", "precision": "64"}
    )
    h.characters("data")
    h.endElement("peaks")
    h.startElement("precursorMz", {"precursorIntensity": "50", "precursorCharge": "2"})
    h.characters("100.5")
    h.endElement("precursorMz")
    with pytest.raises(stopParsing):
        h.endElement("scan")

    # Match scan with missing attributes and negative polarity
    h = scanHandler(1)
    h.startElement("scan", {"num": "1", "msLevel": "", "polarity": "negative"})
    assert h.data["polarity"] == -1
    h.startElement("peaks", {"compressionType": "none", "precision": ""})
    h.endElement("peaks")
    h.startElement("precursorMz", {})
    h.endElement("precursorMz")

    # Polarity variations
    h = scanHandler(1)
    h.startElement("scan", {"num": "1", "polarity": "-"})
    assert h.data["polarity"] == -1

    # Non-match scan
    h = scanHandler(1)
    h.startElement("scan", {"num": "2"})
    h.endElement("scan")

    # Nested scans
    h = scanHandler(1)
    h.startElement("scan", {"num": "1"})
    h.startElement("scan", {"num": "2"})
    h.endElement("scan")

    # Scan without num attribute (coverage for 462->466)
    h = scanHandler(None)
    h.startElement("scan", {})
    assert h._isMatch == True
    h.endElement("dataProcessing")  # Cover exit branch of endElement


def test_runHandler_comprehensive():
    h = runHandler()
    h.startElement("dataProcessing", {"centroided": "1"})
    h.endElement("dataProcessing")  # Cover exit branch of endElement
    h.startElement("dataProcessing", {"centroided": "0"})

    h.startElement(
        "scan",
        {
            "num": "1",
            "msLevel": "2",
            "peaksCount": "10",
            "polarity": "+",
            "retentionTime": "PT1S",
            "lowMz": "10",
            "highMz": "20",
            "basePeakMz": "15",
            "basePeakIntensity": "100",
            "totIonCurrent": "1000",
        },
    )
    h.startElement(
        "peaks", {"byteOrder": "little", "compressionType": "zlib", "precision": "64"}
    )
    h.characters("data")
    h.endElement("peaks")
    h.startElement("precursorMz", {"precursorIntensity": "50", "precursorCharge": "2"})
    h.characters("100.5")
    h.endElement("precursorMz")
    h.endElement("scan")

    # Negative polarity and empty msLevel
    h.startElement("scan", {"num": "2", "msLevel": "", "polarity": "negative"})
    assert h.data[2]["polarity"] == -1
    h.startElement("peaks", {"compressionType": "none", "precision": ""})
    h.endElement("peaks")
    h.startElement("precursorMz", {})
    h.endElement("precursorMz")
    h.endElement("scan")

    # Scan without num attribute (coverage for 652->656)
    h.startElement("scan", {})
    h.endElement("scan")

    # Test 751->exit coverage
    h.startElement("unknownElement", {})


# Test parseMZXML methods with mocking
def test_parseMZXML_load(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mock_handler = mocker.Mock(spec=runHandler)
    mock_handler.data = {
        1: {
            "points": "data",
            "byteOrder": "network",
            "compression": None,
            "precision": 32,
            "title": "",
            "scanNumber": 1,
            "parentScanNumber": None,
            "msLevel": 1,
            "polarity": 1,
            "retentionTime": 60.0,
            "totIonCurrent": 1000.0,
            "basePeakMZ": 500.0,
            "basePeakIntensity": 1000.0,
            "precursorMZ": None,
            "precursorIntensity": None,
            "precursorCharge": None,
            "spectrumType": "discrete",
        }
    }
    mocker.patch("mspy.parser_mzxml.runHandler", return_value=mock_handler)
    parser.load()
    assert 1 in parser._scanlist


def test_parseMZXML_info(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mock_handler = mocker.Mock(spec=infoHandler)
    mock_handler.data = {"title": "Test"}
    mocker.patch("mspy.parser_mzxml.infoHandler", return_value=mock_handler)
    mock_sax_parser = mocker.Mock()
    mock_sax_parser.parse.side_effect = stopParsing()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    assert parser.info() == {"title": "Test"}
    assert parser.info() == {"title": "Test"}


def test_parseMZXML_info_no_stop_parsing(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mocker.patch("xml.sax.make_parser")
    assert parser.info() is None


def test_parseMZXML_scanlist(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mock_handler = mocker.Mock(spec=scanlistHandler)
    mock_handler.data = {1: {"scanNumber": 1}}
    mocker.patch("mspy.parser_mzxml.scanlistHandler", return_value=mock_handler)
    assert parser.scanlist() == {1: {"scanNumber": 1}}


def test_parseMZXML_scan(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    scan_data = {
        "points": None,
        "byteOrder": "network",
        "compression": None,
        "precision": 32,
        "title": "Scan 1",
        "scanNumber": 1,
        "parentScanNumber": None,
        "msLevel": 1,
        "polarity": 1,
        "retentionTime": 60.0,
        "totIonCurrent": 1000.0,
        "basePeakMZ": 500.0,
        "basePeakIntensity": 1000.0,
        "precursorMZ": None,
        "precursorIntensity": None,
        "precursorCharge": None,
        "spectrumType": "discrete",
    }
    mock_handler = mocker.Mock(spec=scanHandler)
    mock_handler.data = scan_data
    mocker.patch("mspy.parser_mzxml.scanHandler", return_value=mock_handler)
    mock_sax_parser = mocker.Mock()
    mock_sax_parser.parse.side_effect = stopParsing()
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    assert isinstance(parser.scan(1), obj_scan.scan)
    parser._scans = {1: scan_data}
    assert isinstance(parser.scan(1), obj_scan.scan)


def test_parseMZXML_scan_not_found(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mock_handler = mocker.Mock(spec=scanHandler)
    mock_handler.data = False
    mocker.patch("mspy.parser_mzxml.scanHandler", return_value=mock_handler)
    mocker.patch("xml.sax.make_parser")
    assert parser.scan(1) is False


def test_makeScan_direct(parser_instance, mocker):
    scan_data = {
        "spectrumType": "discrete",
        "title": "Scan 1",
        "scanNumber": 1,
        "parentScanNumber": None,
        "msLevel": 1,
        "polarity": 1,
        "retentionTime": 60.0,
        "totIonCurrent": 1000.0,
        "basePeakMZ": 500.0,
        "basePeakIntensity": 1000.0,
        "precursorMZ": None,
        "precursorIntensity": None,
        "precursorCharge": None,
    }
    mocker.patch.object(parser_instance, "_parsePoints", return_value=[[100.0, 1000.0]])
    scan = parser_instance._makeScan(scan_data)
    assert scan.peaklist[0].mz == 100.0
    scan_data["spectrumType"] = "continuous"
    points = np.array([[100.0, 1000.0]])
    mocker.patch.object(parser_instance, "_parsePoints", return_value=points)
    scan = parser_instance._makeScan(scan_data)
    assert scan.profile is points


# Integration tests
def test_integration_small():
    path = "tests/data/test_small.mzXML"
    if not os.path.exists(path):
        pytest.skip("Integration test file not found")
    parser = parseMZXML(path)
    assert isinstance(parser.info(), dict)
    assert len(parser.scanlist()) > 0
    first_scan_id = sorted(parser.scanlist().keys())[0]
    assert isinstance(parser.scan(first_scan_id), obj_scan.scan)


def test_integration_large():
    path = "tests/data/test_large.mzXML"
    if not os.path.exists(path):
        pytest.skip("Integration test file not found")
    parser = parseMZXML(path)
    assert len(parser.scanlist()) > 0


def test_parseMZXML_sax_exceptions(mocker, tmpdir):
    path = str(tmpdir.join("test.mzXML"))
    with open(path, "w") as f:
        f.write("<mzXML></mzXML>")
    parser = parseMZXML(path)
    mock_sax_parser = mocker.Mock()
    mock_sax_parser.parse.side_effect = xml.sax.SAXException("Error")
    mocker.patch("xml.sax.make_parser", return_value=mock_sax_parser)
    assert parser.load() is None
    assert parser.info() is False
    assert parser.scanlist() is False
    assert parser.scan(1) is False


def test_characters_coverage():
    h = scanlistHandler()
    h.data[1] = {"precursorMZ": ""}
    h.currentID = 1
    h._isPrecursor = True
    h.characters("500.5")
    assert h.data[1]["precursorMZ"] == "500.5"
    h._isPrecursor = False
    h.characters("skip")
    assert h.data[1]["precursorMZ"] == "500.5"

    h2 = scanHandler(1)
    h2.data = {"points": [], "precursorMZ": ""}
    h2._isPeaks = True
    h2.characters("data")
    assert h2.data["points"] == ["data"]
    h2._isPeaks = False
    h2._isPrecursor = True
    h2.characters("200")
    assert h2.data["precursorMZ"] == "200"

    h3 = runHandler()
    h3.data[1] = {"points": [], "precursorMZ": ""}
    h3.currentID = 1
    h3._isPeaks = True
    h3.characters("data")
    assert h3.data[1]["points"] == ["data"]
    h3._isPeaks = False
    h3._isPrecursor = True
    h3.characters("300")
    assert h3.data[1]["precursorMZ"] == "300"


def test_infoHandler_accumulation():
    h = infoHandler()
    h.startElement("msManufacturer", {"value": "A"})
    h.startElement("msModel", {"value": "B"})
    h.startElement("msIonisation", {"value": "C"})
    h.startElement("msMassAnalyzer", {"value": "D"})
    assert h.data["instrument"] == "A B C D "
