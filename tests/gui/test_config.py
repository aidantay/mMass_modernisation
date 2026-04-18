import copy
import os
import xml.dom.minidom
from xml.parsers.expat import ExpatError

import pytest

from gui import config


@pytest.fixture
def backup_config():
    """Fixture to backup and restore the global configuration."""
    # List of configuration dictionaries/lists
    config_vars = [
        "internal",
        "main",
        "recent",
        "colours",
        "export",
        "spectrum",
        "match",
        "processing",
        "calibration",
        "sequence",
        "massCalculator",
        "massToFormula",
        "massDefectPlot",
        "compoundsSearch",
        "peakDifferences",
        "comparePeaklists",
        "spectrumGenerator",
        "envelopeFit",
        "mascot",
        "profound",
        "prospector",
        "links",
    ]

    # Backup
    backup = {}
    for var in config_vars:
        if hasattr(config, var):
            backup[var] = copy.deepcopy(getattr(config, var))

    yield

    # Restore
    for var in config_vars:
        if var in backup:
            setattr(config, var, backup[var])


def test_default_values():
    """Verify default values are correctly initialized."""
    assert config.version == "5.5.0"
    assert config.main["appWidth"] == 1050
    assert config.main["mzDigits"] == 4
    assert "m/z" in config.spectrum["xLabel"]
    assert config.match["tolerance"] == 0.2
    assert isinstance(config.recent, list)
    assert isinstance(config.colours, list)


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("normal", "normal"),
        ("  trimmed  ", "trimmed"),
        ("a < b", "a &lt; b"),
        ("a > b", "a &gt; b"),
        ('He said "Hi"', "He said &quot;Hi&quot;"),
        ("It's me", "It&apos;s me"),
        ("a & b", "a &amp; b"),
        ("<tag>", "&lt;tag&gt;"),
    ],
)
def test_escape(input_str, expected):
    """Test the _escape helper function."""
    assert config._escape(input_str) == expected


def test_getParams():
    """Test the _getParams helper function."""
    xml_data = """
    <section>
        <param name="intVal" value="123" type="int" />
        <param name="floatVal" value="1.23" type="float" />
        <param name="strVal" value="hello" type="str" />
        <param name="unicodeVal" value="world" type="unicode" />
    </section>
    """
    doc = xml.dom.minidom.parseString(xml_data)
    section_tag = doc.getElementsByTagName("section")[0]

    section = {
        "intVal": 0,
        "floatVal": 0.0,
        "strVal": "",
        "unicodeVal": "",
        "exists": True,
    }

    config._getParams(section_tag, section)

    assert section["intVal"] == 123
    assert section["floatVal"] == 1.23
    assert section["strVal"] == "hello"
    assert section["unicodeVal"] == "world"
    assert section["exists"] is True


def test_getParams_exceptions():
    """Test the _getParams helper function with bad inputs."""
    xml_data = """
    <section>
        <param name="failFloat" value="abc" type="float" />
    </section>
    """
    doc = xml.dom.minidom.parseString(xml_data)
    section_tag = doc.getElementsByTagName("section")[0]

    section = {
        "failFloat": 1.0,
    }
    config._getParams(section_tag, section)
    assert section["failFloat"] == 1.0  # Unchanged on failure


def test_save_and_load_config(tmpdir, backup_config):
    """Test saving and loading the configuration."""
    temp_file = str(tmpdir.join("test_config.xml"))

    # Modify some values of different types
    config.main["appWidth"] = 2000
    config.main["lastDir"] = "/home/test/directory"
    config.main["cursorInfo"] = ["mz", "z"]
    config.recent = ["/home/test/file1.mzML", "/home/test/file2.mzML"]
    config.colours = [[255, 0, 0], [0, 255, 0]]
    config.spectrum["showGrid"] = 0
    config.spectrum["tickColour"] = [0, 0, 255]
    config.processing["crop"]["lowMass"] = 100
    config.processing["crop"]["highMass"] = 10000
    config.mascot["common"]["userName"] = "Test User"
    config.mascot["pmf"]["fixedMods"] = ["Mod1", "Mod2"]

    # Save config
    assert config.saveConfig(temp_file) is True
    assert os.path.exists(temp_file)

    # Reset some values to different ones to verify load
    config.main["appWidth"] = 1050
    config.main["lastDir"] = ""
    config.main["cursorInfo"] = []
    config.recent = []
    config.colours = []
    config.spectrum["showGrid"] = 1
    config.spectrum["tickColour"] = [255, 75, 75]
    config.processing["crop"]["lowMass"] = 500
    config.processing["crop"]["highMass"] = 5000
    config.mascot["common"]["userName"] = ""
    config.mascot["pmf"]["fixedMods"] = []

    # Load config
    config.loadConfig(temp_file)

    # Verify values match modified ones
    assert config.main["appWidth"] == 2000
    assert config.main["lastDir"] == "/home/test/directory"
    assert config.main["cursorInfo"] == ["mz", "z"]
    assert config.recent == ["/home/test/file1.mzML", "/home/test/file2.mzML"]
    assert config.colours == [[255, 0, 0], [0, 255, 0]]
    assert config.spectrum["showGrid"] == 0
    assert config.spectrum["tickColour"] == [0, 0, 255]
    assert config.processing["crop"]["lowMass"] == 100
    assert config.processing["crop"]["highMass"] == 10000
    assert config.mascot["common"]["userName"] == "Test User"
    assert config.mascot["pmf"]["fixedMods"] == ["Mod1", "Mod2"]


def test_load_config_missing_file():
    """Verify behavior when loading from a non-existent file."""
    with pytest.raises(IOError):
        config.loadConfig("/non/existent/path/config.xml")


def test_save_config_error(tmpdir, mocker):
    """Mock file writing to test error handling in saveConfig."""
    # Use mock to simulate IOError during file open
    mocker.patch("gui.config.open", side_effect=IOError, create=True)
    assert config.saveConfig("/any/path/config.xml") is False


def test_load_config_malformed_xml(tmpdir):
    """Test behavior with invalid XML content."""
    temp_file = str(tmpdir.join("malformed.xml"))
    with open(temp_file, "w") as f:
        f.write("this is not XML")

    with pytest.raises(ExpatError):
        config.loadConfig(temp_file)


def test_load_config_all_sections(tmpdir, backup_config):
    """Test loading with an XML containing all expected sections to maximize coverage."""
    temp_file = str(tmpdir.join("full_config.xml"))

    # Ensure all sections are present by saving current config
    assert config.saveConfig(temp_file) is True

    # Load it back
    config.loadConfig(temp_file)

    # Just verify it didn't crash and some values are still there
    assert config.main["appWidth"] > 0
    assert config.spectrum["labelFontSize"] > 0


def test_load_config_type_conversions(tmpdir, backup_config):
    """Test automatic type conversions and splitting in loadConfig."""
    temp_file = str(tmpdir.join("conversion_test.xml"))

    xml_content = """<?xml version="1.0" encoding="utf-8" ?>
<mMassConfig version="1.0">
  <main>
    <param name="cursorInfo" value="mz;z;ppm" type="str" />
    <param name="peaklistColumns" value="mz;int;sn" type="str" />
  </main>
  <colours>
    <colour value="ff0000" />
    <colour value="00ff00" />
  </colours>
  <export>
    <param name="peaklistColumns" value="mz;int" type="str" />
  </export>
  <spectrum>
    <param name="tickColour" value="0000ff" type="str" />
    <param name="tmpSpectrumColour" value="ff00ff" type="str" />
    <param name="notationMarksColour" value="ffff00" type="str" />
  </spectrum>
  <sequence>
    <fragment>
      <param name="fragments" value="a;b;y" type="str" />
    </fragment>
  </sequence>
  <massToFormula>
    <param name="rules" value="HC;NOPSC" type="str" />
  </massToFormula>
  <compoundsSearch>
    <param name="adducts" value="Na;K" type="str" />
  </compoundsSearch>
  <mascot>
    <pmf>
      <param name="fixedMods" value="ModA;ModB" type="str" />
      <param name="variableMods" value="ModC" type="str" />
    </pmf>
  </mascot>
</mMassConfig>
"""
    with open(temp_file, "w") as f:
        f.write(xml_content)

    config.loadConfig(temp_file)

    assert config.main["cursorInfo"] == ["mz", "z", "ppm"]
    assert config.main["peaklistColumns"] == ["mz", "int", "sn"]
    assert config.colours[0] == [255, 0, 0]
    assert config.colours[1] == [0, 255, 0]
    assert config.export["peaklistColumns"] == ["mz", "int"]
    assert config.spectrum["tickColour"] == [0, 0, 255]
    assert config.spectrum["tmpSpectrumColour"] == [255, 0, 255]
    assert config.spectrum["notationMarksColour"] == [255, 255, 0]
    assert config.sequence["fragment"]["fragments"] == ["a", "b", "y"]
    assert config.massToFormula["rules"] == ["HC", "NOPSC"]
    assert config.compoundsSearch["adducts"] == ["Na", "K"]
    assert config.mascot["pmf"]["fixedMods"] == ["ModA", "ModB"]
    assert config.mascot["pmf"]["variableMods"] == ["ModC"]


def test_load_config_links(tmpdir, backup_config):
    """Test loading links section."""
    temp_file = str(tmpdir.join("links_test.xml"))

    xml_content = """<?xml version="1.0" encoding="utf-8" ?>
<mMassConfig version="1.0">
  <links>
    <link name="CustomLink" value="http://example.com" />
    <link name="mMassHomepage" value="should_not_overwrite" />
  </links>
</mMassConfig>
"""
    with open(temp_file, "w") as f:
        f.write(xml_content)

    config.links["mMassHomepage"] = "http://www.mmass.org/"
    config.loadConfig(temp_file)

    assert config.links["CustomLink"] == "http://example.com"
    # mMassHomepage should NOT be overwritten because of the check in loadConfig
    assert config.links["mMassHomepage"] == "http://www.mmass.org/"
