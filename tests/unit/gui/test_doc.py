import xml.dom.minidom

import numpy as np
import pytest

from mmass import mspy
from mmass.gui import doc


@pytest.fixture
def mock_config(mocker):
    """Fixture to patch gui.config.main and gui.config.replacements."""
    mocker.patch.dict(
        "mmass.gui.config.main",
        {"mzDigits": 4, "intDigits": 0, "ppmDigits": 1, "dataPrecision": 32},
    )
    mocker.patch.dict(
        "mmass.gui.config.replacements",
        {
            "sequences": {
                "sp": {
                    "pattern": r"^sp\|?([A-Z][A-Z0-9]+)$",
                    "url": "http://www.uniprot.org/uniprot/%s",
                }
            },
            "compounds": {},
        },
    )


@pytest.fixture
def sample_spectrum():
    """Fixture returning an mspy.scan populated with basic profile data and a peaklist."""
    scan = mspy.Scan()
    # Create profile data: (mz, intensity)
    profile = np.array(
        [
            [100.0, 10.0],
            [100.1, 50.0],
            [100.2, 10.0],
            [200.0, 20.0],
            [200.1, 100.0],
            [200.2, 20.0],
        ]
    )
    scan.setprofile(profile)

    # Create peaklist
    p1 = mspy.Peak(mz=100.1, ai=50.0)
    p2 = mspy.Peak(mz=200.1, ai=100.0)
    scan.setpeaklist(mspy.Peaklist([p1, p2]))

    return scan


def test_annotation_delta():
    """Test annotation object instantiation and the delta method."""
    # Test with theoretical m/z
    annot = doc.Annotation(
        label="Test", mz=100.1234, ai=1000.0, theoretical=100.1200
    )
    assert annot.label == "Test"
    assert annot.mz == 100.1234
    assert annot.ai == 1000.0
    assert annot.theoretical == 100.1200

    # Check delta in Da and ppm
    # Delta = 100.1234 - 100.1200 = 0.0034
    assert round(annot.delta("Da"), 4) == 0.0034
    # ppm = 0.0034 / 100.1200 * 10^6 = 33.959...
    assert round(annot.delta("ppm"), 2) == round(0.0034 / 100.1200 * 1e6, 2)

    # Test without theoretical m/z
    annot2 = doc.Annotation(label="NoTheo", mz=100.0, ai=500.0)
    assert annot2.delta("Da") is None


def test_match_delta():
    """Test match object instantiation and the delta method."""
    m = doc.Match(label="Match", mz=200.5678, ai=2000.0, theoretical=200.5600)
    assert m.label == "Match"
    assert m.mz == 200.5678
    assert m.ai == 2000.0
    assert m.theoretical == 200.5600

    # Delta = 200.5678 - 200.5600 = 0.0078
    assert round(m.delta("Da"), 4) == 0.0078

    # Test without theoretical m/z
    m2 = doc.Match(label="NoTheo", mz=200.0, ai=1000.0)
    assert m2.delta("Da") is None


def test_document_backup_restore(wx_app, mock_config, sample_spectrum):
    """Test document backup and restore functionality."""
    d = doc.Document()
    d.spectrum = sample_spectrum
    d.annotations = [doc.Annotation("A1", 100.1, 50.0)]

    # Initial state assertions
    assert len(d.annotations) == 1
    assert d.spectrum.profile[0][0] == 100.0

    # Test backup(None) and backup([])
    d.backup(None)
    assert d.undo is None
    d.backup([])
    assert d.undo == []
    assert d.restore() is False

    # Backup spectrum and annotations
    d.backup(["spectrum", "annotations"])

    # Modify original data
    d.spectrum.profile[0][0] = 999.9
    d.annotations.append(doc.Annotation("A2", 200.1, 100.0))
    d.annotations[0].label = "Modified"

    assert d.spectrum.profile[0][0] == 999.9
    assert len(d.annotations) == 2

    # Restore
    res = d.restore()
    assert res == ["spectrum", "annotations"]

    # Verify restoration
    assert d.spectrum.profile[0][0] == 100.0
    assert len(d.annotations) == 1
    assert d.annotations[0].label == "A1"

    # Test backup 'sequences'
    seq = mspy.Sequence("ACD", title="TestSeq")
    seq.matches = [doc.Match("M1", 123.4, 10.0)]
    d.sequences = [seq]
    d.backup(["sequences"])
    d.sequences[0].title = "Changed"
    d.sequences.append(mspy.Sequence("ACD"))
    d.restore()
    assert len(d.sequences) == 1
    assert d.sequences[0].title == "TestSeq"

    # Test backup 'notations'
    # 'notations' backup stores annotations and sequences
    # 'notations' restore reverts annotations and sequences[x].matches
    d.annotations = [doc.Annotation("A1", 100.1, 50.0)]
    seq = mspy.Sequence("ACD", title="TestSeq")
    seq.matches = [doc.Match("M1", 123.4, 10.0)]
    d.sequences = [seq]

    d.backup(["notations"])

    d.annotations.append(doc.Annotation("A2", 200.2, 60.0))
    d.sequences[0].matches.append(doc.Match("M2", 234.5, 20.0))
    d.sequences[0].title = "ShouldNotBeRestored"

    d.restore()

    assert len(d.annotations) == 1
    assert len(d.sequences[0].matches) == 1
    assert (
        d.sequences[0].title == "ShouldNotBeRestored"
    )  # Only matches are restored for sequences

    # Test restoring when no backup is present
    assert d.restore() is False


def test_document_sorting():
    """Test document sorting algorithms: Annotations, sequences, and sequence matches."""
    d = doc.Document()

    # Add annotations out of order
    d.annotations = [
        doc.Annotation(label="A300", mz=300.0, ai=10.0),
        doc.Annotation(label="A100", mz=100.0, ai=10.0),
        doc.Annotation(label="A200", mz=200.0, ai=10.0),
    ]

    # Add sequences out of order
    # Note: mspy.sequence constructor: (chain, chainType, title, accession)
    seq_b = mspy.Sequence("AAA", title="B")
    seq_b.matches = []
    seq_a = mspy.Sequence("AAA", title="A")
    seq_a.matches = []
    seq_c = mspy.Sequence("AAA", title="C")
    seq_c.matches = []

    # Add matches out of order to seq_a
    seq_a.matches = [
        doc.Match(label="M300", mz=300.0, ai=10.0),
        doc.Match(label="M100", mz=100.0, ai=10.0),
        doc.Match(label="M200", mz=200.0, ai=10.0),
    ]

    d.sequences = [seq_b, seq_a, seq_c]

    # Execute sorting
    d.sortAnnotations()
    d.sortSequences()
    d.sortSequenceMatches()

    # Assertions for annotations
    assert d.annotations[0].mz == 100.0
    assert d.annotations[1].mz == 200.0
    assert d.annotations[2].mz == 300.0

    # Assertions for sequences
    assert d.sequences[0].title == "A"
    assert d.sequences[1].title == "B"
    assert d.sequences[2].title == "C"

    # Assertions for sequence matches (seq_a is now at index 0)
    assert d.sequences[0].matches[0].mz == 100.0
    assert d.sequences[0].matches[1].mz == 200.0
    assert d.sequences[0].matches[2].mz == 300.0


def test_document_msd(mock_config, sample_spectrum):
    """Test document mSD (XML) serialization."""
    d = doc.Document()
    d.title = "Test Doc"
    d.spectrum = sample_spectrum
    d.spectrum.scanNumber = 42
    d.spectrum.msLevel = 1
    d.spectrum.retentionTime = 60.5
    d.spectrum.precursorMZ = 500.1
    d.spectrum.precursorCharge = 2
    d.spectrum.polarity = 1

    # Add an annotation with optional attributes
    d.annotations = [
        doc.Annotation(
            label="Annot1",
            mz=150.0,
            ai=50.0,
            formula="H2O",
            charge=1,
            radical=True,
            theoretical=150.005,
        )
    ]

    # Add a peak with optional attributes
    p_opt = mspy.Peak(
        mz=300.1,
        ai=500.0,
        base=10.0,
        sn=15.5,
        charge=2,
        isotope=0,
        fwhm=0.01,
        group="Group1",
    )
    d.spectrum.peaklist.append(p_opt)

    # Add an aminoacid sequence with a modification and a match with optional attributes
    seq1 = mspy.Sequence("PEPTIDE", title="Seq1")
    seq1.matches = []
    # type: 'f' for fixed, 'v' for variable
    # position is 1-based index or 'N'/'C'
    # Ensure 'Oxidation' exists in mspy.modifications (it does by default in mspy.blocks)
    seq1.modifications = [("Oxidation", 1, "v")]

    m_opt = doc.Match(
        label="y1",
        mz=147.1,
        ai=200.0,
        base=5.0,
        charge=1,
        radical=True,
        theoretical=147.11,
        formula="C6H11NO3",
    )
    m_opt.sequenceRange = [7, 7]
    m_opt.fragmentSerie = "y"
    m_opt.fragmentIndex = 1
    seq1.matches.append(m_opt)

    # Add a custom (non-aminoacid) sequence to test monomer serialization
    # 'X' and 'Y' must be in mspy.monomers
    mspy.monomers["X"] = mspy.Monomer("X", "C2H3")
    mspy.monomers["Y"] = mspy.Monomer("Y", "C3H5")
    # Custom sequences must have monomers separated by '|'
    seq2 = mspy.Sequence("X|Y", chainType="custom", title="Seq2")
    seq2.matches = []
    seq2.cyclic = True

    d.sequences = [seq1, seq2]

    msd_xml = d.msd()

    # Basic validation of the returned string
    assert '<?xml version="1.0" encoding="utf-8" ?>' in msd_xml
    assert '<mSD version="2.2">' in msd_xml
    assert "<title>Test Doc</title>" in msd_xml
    assert 'scanNumber="42"' in msd_xml
    assert 'msLevel="1"' in msd_xml
    assert 'retentionTime="60.5"' in msd_xml
    assert 'precursorMZ="500.1"' in msd_xml
    assert 'precursorCharge="2"' in msd_xml
    assert 'polarity="1"' in msd_xml
    assert 'precision="32"' in msd_xml
    assert 'compression="zlib"' in msd_xml
    assert "<mzArray" in msd_xml
    assert "<intArray" in msd_xml
    assert "<annotation" in msd_xml
    assert 'formula="H2O"' in msd_xml
    assert 'charge="1"' in msd_xml
    assert 'radical="1"' in msd_xml
    assert 'calcMZ="150.005000"' in msd_xml
    assert "Annot1" in msd_xml
    assert 'sn="15.500"' in msd_xml
    assert 'charge="2"' in msd_xml
    assert 'isotope="0"' in msd_xml
    assert 'fwhm="0.010000"' in msd_xml
    assert 'group="Group1"' in msd_xml
    assert '<sequence index="0">' in msd_xml
    assert '<sequence index="1">' in msd_xml
    assert 'cyclic="1"' in msd_xml
    assert '<modification name="Oxidation"' in msd_xml
    assert 'type="variable"' in msd_xml
    assert 'sequenceRange="7-7"' in msd_xml
    assert 'fragmentSerie="y"' in msd_xml
    assert 'fragmentIndex="1"' in msd_xml
    assert '<monomer abbr="X" formula="C2H3" />' in msd_xml
    assert '<monomer abbr="Y" formula="C3H5" />' in msd_xml

    # Parse to ensure it's valid XML
    dom = xml.dom.minidom.parseString(msd_xml)
    assert dom.documentElement.tagName == "mSD"

    # Verify scan number in spectrum tag
    spectrum_tag = dom.getElementsByTagName("spectrum")[0]
    assert spectrum_tag.getAttribute("scanNumber") == "42"

    # Verify modification tag
    mod_tag = dom.getElementsByTagName("modification")[0]
    assert mod_tag.getAttribute("name") == "Oxidation"
    assert mod_tag.getAttribute("type") == "variable"


def test_document_msd_empty(mock_config):
    """Test mSD generation with empty document."""
    d = doc.Document()
    d.spectrum = mspy.Scan()
    msd_xml = d.msd()
    assert '<spectrum points="0">' in msd_xml
    assert "<mzArray" not in msd_xml
    assert "<peaklist" not in msd_xml
    assert "<annotations" not in msd_xml
    assert "<sequences" not in msd_xml


def test_document_report(mock_config, sample_spectrum, mocker):
    """Test HTML report generation."""
    # Mock time.time for stable output
    mocker.patch("time.time", return_value=123456789.0)

    d = doc.Document()
    d.title = "Report Test"
    d.date = "2023-10-27"
    d.notes = "Some notes\nwith newlines."
    d.spectrum = sample_spectrum
    d.spectrum.polarity = -1  # Negative polarity

    # Add an annotation with theoretical value for delta
    d.annotations = [
        doc.Annotation(
            label="Annot1",
            mz=150.0,
            ai=500.0,
            theoretical=150.005,
            formula="H2O",
            charge=1,
            radical=True,
        )
    ]

    # Add a sequence with an accession that should be linked
    seq = mspy.Sequence("PEPTIDE", title="Seq1", accession="sp|P12345")
    seq.cyclic = True
    seq.modify("Oxidation", 1, "v")
    seq.matches = [
        doc.Match(
            label="Match1",
            mz=200.0,
            ai=1000.0,
            theoretical=200.001,
            charge=2,
            radical=False,
            formula="C10H20",
        )
    ]
    seq.matches[0].sequenceRange = [1, 7]
    d.sequences = [seq]

    # Test with image and all data
    report_html = d.report(image=True)

    # Verify report contains key elements
    assert "<h1>mMass Report: <span>Report Test</span></h1>" in report_html
    assert "<td>2023-10-27</td>" in report_html
    assert "<td>negative</td>" in report_html
    assert '<div id="spectrum"><img src="mmass_spectrum.png?123456789.0"' in report_html
    assert "Some notes<br />with newlines." in report_html
    assert "Annot1" in report_html
    assert "1 &bull;" in report_html  # Radical charge representation
    assert "Seq1" in report_html
    assert "P12345" in report_html
    assert "Match1" in report_html
    assert "(Cyclic)" in report_html
    assert "Oxidation" in report_html

    # Verify replacements (P12345 should be linked to UniProt based on sp| pattern)
    assert 'href="http://www.uniprot.org/uniprot/P12345"' in report_html

    # Test without image and without notes/sequences/annotations
    d.notes = ""
    d.annotations = []
    d.sequences = []
    report_html_minimal = d.report(image=False)
    assert '<div id="spectrum">' not in report_html_minimal
    assert "<h2>Notes</h2>" not in report_html_minimal
    assert "<h2>Annotations</h2>" not in report_html_minimal
    assert "<h2>Sequence" not in report_html_minimal


def test_parseMSD_integration(tmp_path, mock_config, sample_spectrum, mocker):
    """Test ParseMSD integration by serializing and deserializing a document."""
    # Mock save methods to avoid side effects during deserialization
    mocker.patch("mmass.mspy.blocks.saveMonomers")
    mocker.patch("mmass.mspy.blocks.saveModifications")

    d = doc.Document()
    d.title = "Integration Test"
    d.spectrum = sample_spectrum
    d.spectrum.scanNumber = 123

    # Add annotation
    d.annotations = [
        doc.Annotation(label="Annot1", mz=150.0, ai=500.0, formula="H2O", charge=1)
    ]

    # Add sequence with modification
    seq = mspy.Sequence("PEPTIDE", title="Seq1")
    # 'Oxidation' should be in mspy.modifications by default
    seq.modify("Oxidation", 1, "v")

    # Add match
    m = doc.Match(
        label="y1", mz=147.1, ai=200.0, theoretical=147.11, formula="C6H11NO3"
    )
    m.sequenceRange = [7, 7]
    seq.matches = [m]

    d.sequences = [seq]

    # Serialize
    xml_data = d.msd()

    # Write to temp file
    file_path = tmp_path / "test.msd"
    file_path.write_text(str(xml_data))

    # Deserialize
    parser = doc.ParseMSD(str(file_path))
    new_d = parser.getDocument()

    # Assertions
    assert new_d.title == d.title
    assert new_d.spectrum.scanNumber == 123

    # Spectrum data
    np.testing.assert_allclose(new_d.spectrum.profile, d.spectrum.profile)

    # Peaklist
    assert len(new_d.spectrum.peaklist) == len(d.spectrum.peaklist)
    assert new_d.spectrum.peaklist[0].mz == d.spectrum.peaklist[0].mz

    # Annotations
    assert len(new_d.annotations) == 1
    assert new_d.annotations[0].label == "Annot1"
    assert new_d.annotations[0].formula == "H2O"

    # Sequences
    assert len(new_d.sequences) == 1
    assert new_d.sequences[0].title == "Seq1"
    assert len(new_d.sequences[0].modifications) == 1
    assert new_d.sequences[0].modifications[0][0] == "Oxidation"

    # Matches
    assert len(new_d.sequences[0].matches) == 1
    assert new_d.sequences[0].matches[0].label == "y1"
    assert new_d.sequences[0].matches[0].sequenceRange == [7, 7]


def test_parseMSD_errors(tmp_path):
    """Test error handling in ParseMSD."""
    # Test missing mzArray/intArray
    # getDocument returns a doc always if the XML is valid, but handleSpectrum fails silently.
    xml_missing = '<mSD version="2.2"><spectrum points="10"></spectrum></mSD>'
    file_path = tmp_path / "missing.msd"
    file_path.write_text(str(xml_missing))
    parser = doc.ParseMSD(str(file_path))
    d = parser.getDocument()
    assert len(d.spectrum.profile) == 0

    # Test corrupted data
    xml_corrupt = '<mSD version="2.2"><spectrum points="1"><mzArray compression="zlib">!!!</mzArray><intArray compression="zlib">!!!</intArray></spectrum></mSD>'
    file_path = tmp_path / "corrupt.msd"
    file_path.write_text(str(xml_corrupt))
    parser = doc.ParseMSD(str(file_path))
    d = parser.getDocument()
    assert len(d.spectrum.profile) == 0
    assert "Incorrect spectrum data." in parser.errors

    # Test incorrect peak/annotation/sequence data
    xml_bad_attr = """<mSD version="2.2">
  <peaklist><peak mz="abc" intensity="100.0" /></peaklist>
  <annotations><annotation peakMZ="def">Label</annotation></annotations>
  <sequences><sequence><seq>PEPTIDE</seq><match peakMZ="ghi">Match</match></sequence></sequences>
</mSD>"""
    file_path = tmp_path / "bad_attr.msd"
    file_path.write_text(str(xml_bad_attr))
    parser = doc.ParseMSD(str(file_path))
    d = parser.getDocument()
    assert "Incorrect peak data." in parser.errors
    assert "Incorrect annotation data." in parser.errors
    assert "Incorrect sequence match data." in parser.errors

    # Test unknown monomer
    xml_bad_monomer = '<mSD version="2.2"><sequences><sequence><seq>UNKNOWN</seq></sequence></sequences></mSD>'
    file_path = tmp_path / "bad_monomer.msd"
    file_path.write_text(str(xml_bad_monomer))
    parser = doc.ParseMSD(str(file_path))
    d = parser.getDocument()
    assert "Unknown monomers in sequence data." in parser.errors


def test_parseMSD_helpers(tmp_path, mocker):
    """Test internal helper methods of ParseMSD."""
    mocker.patch("mmass.mspy.blocks.saveMonomers")
    mocker.patch("mmass.mspy.blocks.saveModifications")

    # Test _getVersion with mMassDoc tag
    xml_mmassdoc = '<mMassDoc version="1.0"></mMassDoc>'
    file_path = tmp_path / "legacy.msd"
    file_path.write_text(str(xml_mmassdoc))
    parser = doc.ParseMSD(str(file_path))
    parser._parsedData = xml.dom.minidom.parseString(xml_mmassdoc)
    assert parser._getVersion() == "1.0"

    # Test _addMonomer failures
    assert parser._addMonomer("", "C2H3") is False
    assert parser._addMonomer("X", "") is False
    assert parser._addMonomer("X!", "C2H3") is False  # Invalid characters

    # Test _addModification failures
    assert parser._addModification("", "H2O", "") is False
    assert parser._addModification("Mod", "", "") is False


def test_parseMSD_version10(tmp_path):
    """Test parsing mSD version 1.0."""
    xml_v10 = """<mSD version="1.0">
  <description>
    <title>V1.0 Test</title>
  </description>
  <spectrum scanNumber="10" />
  <peaklist>
    <peak mass="100.1" intens="50.0" annots="Annot1" />
  </peaklist>
  <sequences>
    <sequence>
      <title>Seq1</title>
      <seq>PEPTIDE</seq>
      <modification name="Oxidation" position="1" />
    </sequence>
  </sequences>
</mSD>"""
    file_path = tmp_path / "v10.msd"
    file_path.write_text(str(xml_v10))
    parser = doc.ParseMSD(str(file_path))
    d = parser.getDocument()

    assert d.title == "v10"  # Filename base in handleDescription/getDocument for v1.0
    assert d.spectrum.scanNumber == 10
    assert len(d.spectrum.peaklist) == 1
    assert d.spectrum.peaklist[0].mz == 100.1
    assert len(d.annotations) == 1
    assert d.annotations[0].label == "Annot1"
    assert len(d.sequences) == 1
    assert d.sequences[0].title == "Seq1"

    # Test getSequences for v1.0
    sequences = parser.getSequences()
    assert len(sequences) == 1
    assert sequences[0].title == "Seq1"
