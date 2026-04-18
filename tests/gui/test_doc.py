import gui.doc
import numpy
import pytest

import mspy


@pytest.fixture
def mock_config(mocker):
    """Fixture to patch gui.config.main and gui.config.replacements."""
    mocker.patch.dict(
        "gui.config.main",
        {"mzDigits": 4, "intDigits": 0, "ppmDigits": 1, "dataPrecision": 32},
    )
    mocker.patch.dict(
        "gui.config.replacements",
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
    scan = mspy.scan()
    # Create profile data: (mz, intensity)
    profile = numpy.array(
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
    p1 = mspy.peak(mz=100.1, ai=50.0)
    p2 = mspy.peak(mz=200.1, ai=100.0)
    scan.setpeaklist(mspy.peaklist([p1, p2]))

    return scan


def test_annotation_delta():
    """Test annotation object instantiation and the delta method."""
    # Test with theoretical m/z
    annot = gui.doc.annotation(
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
    annot2 = gui.doc.annotation(label="NoTheo", mz=100.0, ai=500.0)
    assert annot2.delta("Da") is None


def test_match_delta():
    """Test match object instantiation and the delta method."""
    m = gui.doc.match(label="Match", mz=200.5678, ai=2000.0, theoretical=200.5600)
    assert m.label == "Match"
    assert m.mz == 200.5678
    assert m.ai == 2000.0
    assert m.theoretical == 200.5600

    # Delta = 200.5678 - 200.5600 = 0.0078
    assert round(m.delta("Da"), 4) == 0.0078

    # Test without theoretical m/z
    m2 = gui.doc.match(label="NoTheo", mz=200.0, ai=1000.0)
    assert m2.delta("Da") is None


def test_document_backup_restore(wx_app, mock_config, sample_spectrum):
    """Test document backup and restore functionality."""
    doc = gui.doc.document()
    doc.spectrum = sample_spectrum
    doc.annotations = [gui.doc.annotation("A1", 100.1, 50.0)]

    # Initial state assertions
    assert len(doc.annotations) == 1
    assert doc.spectrum.profile[0][0] == 100.0

    # Test backup(None) and backup([])
    doc.backup(None)
    assert doc.undo is None
    doc.backup([])
    assert doc.undo == []
    assert doc.restore() is False

    # Backup spectrum and annotations
    doc.backup(["spectrum", "annotations"])

    # Modify original data
    doc.spectrum.profile[0][0] = 999.9
    doc.annotations.append(gui.doc.annotation("A2", 200.1, 100.0))
    doc.annotations[0].label = "Modified"

    assert doc.spectrum.profile[0][0] == 999.9
    assert len(doc.annotations) == 2

    # Restore
    res = doc.restore()
    assert res == ["spectrum", "annotations"]

    # Verify restoration
    assert doc.spectrum.profile[0][0] == 100.0
    assert len(doc.annotations) == 1
    assert doc.annotations[0].label == "A1"

    # Test backup 'sequences'
    seq = mspy.sequence("ACD", title="TestSeq")
    seq.matches = [gui.doc.match("M1", 123.4, 10.0)]
    doc.sequences = [seq]
    doc.backup(["sequences"])
    doc.sequences[0].title = "Changed"
    doc.sequences.append(mspy.sequence("ACD"))
    doc.restore()
    assert len(doc.sequences) == 1
    assert doc.sequences[0].title == "TestSeq"

    # Test backup 'notations'
    # 'notations' backup stores annotations and sequences
    # 'notations' restore reverts annotations and sequences[x].matches
    doc.annotations = [gui.doc.annotation("A1", 100.1, 50.0)]
    seq = mspy.sequence("ACD", title="TestSeq")
    seq.matches = [gui.doc.match("M1", 123.4, 10.0)]
    doc.sequences = [seq]

    doc.backup(["notations"])

    doc.annotations.append(gui.doc.annotation("A2", 200.2, 60.0))
    doc.sequences[0].matches.append(gui.doc.match("M2", 234.5, 20.0))
    doc.sequences[0].title = "ShouldNotBeRestored"

    doc.restore()

    assert len(doc.annotations) == 1
    assert len(doc.sequences[0].matches) == 1
    assert (
        doc.sequences[0].title == "ShouldNotBeRestored"
    )  # Only matches are restored for sequences

    # Test restoring when no backup is present
    assert doc.restore() is False


def test_document_sorting():
    """Test document sorting algorithms: annotations, sequences, and sequence matches."""
    doc = gui.doc.document()

    # Add annotations out of order
    doc.annotations = [
        gui.doc.annotation(label="A300", mz=300.0, ai=10.0),
        gui.doc.annotation(label="A100", mz=100.0, ai=10.0),
        gui.doc.annotation(label="A200", mz=200.0, ai=10.0),
    ]

    # Add sequences out of order
    # Note: mspy.sequence constructor: (chain, chainType, title, accession)
    seq_b = mspy.sequence("AAA", title="B")
    seq_b.matches = []
    seq_a = mspy.sequence("AAA", title="A")
    seq_a.matches = []
    seq_c = mspy.sequence("AAA", title="C")
    seq_c.matches = []

    # Add matches out of order to seq_a
    seq_a.matches = [
        gui.doc.match(label="M300", mz=300.0, ai=10.0),
        gui.doc.match(label="M100", mz=100.0, ai=10.0),
        gui.doc.match(label="M200", mz=200.0, ai=10.0),
    ]

    doc.sequences = [seq_b, seq_a, seq_c]

    # Execute sorting
    doc.sortAnnotations()
    doc.sortSequences()
    doc.sortSequenceMatches()

    # Assertions for annotations
    assert doc.annotations[0].mz == 100.0
    assert doc.annotations[1].mz == 200.0
    assert doc.annotations[2].mz == 300.0

    # Assertions for sequences
    assert doc.sequences[0].title == "A"
    assert doc.sequences[1].title == "B"
    assert doc.sequences[2].title == "C"

    # Assertions for sequence matches (seq_a is now at index 0)
    assert doc.sequences[0].matches[0].mz == 100.0
    assert doc.sequences[0].matches[1].mz == 200.0
    assert doc.sequences[0].matches[2].mz == 300.0


def test_document_msd(mock_config, sample_spectrum):
    """Test document mSD (XML) serialization."""
    import xml.dom.minidom

    doc = gui.doc.document()
    doc.title = "Test Doc"
    doc.spectrum = sample_spectrum
    doc.spectrum.scanNumber = 42
    doc.spectrum.msLevel = 1
    doc.spectrum.retentionTime = 60.5
    doc.spectrum.precursorMZ = 500.1
    doc.spectrum.precursorCharge = 2
    doc.spectrum.polarity = 1

    # Add an annotation with optional attributes
    doc.annotations = [
        gui.doc.annotation(
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
    p_opt = mspy.peak(
        mz=300.1,
        ai=500.0,
        base=10.0,
        sn=15.5,
        charge=2,
        isotope=0,
        fwhm=0.01,
        group="Group1",
    )
    doc.spectrum.peaklist.append(p_opt)

    # Add an aminoacid sequence with a modification and a match with optional attributes
    seq1 = mspy.sequence("PEPTIDE", title="Seq1")
    seq1.matches = []
    # type: 'f' for fixed, 'v' for variable
    # position is 1-based index or 'N'/'C'
    # Ensure 'Oxidation' exists in mspy.modifications (it does by default in mspy.blocks)
    seq1.modifications = [("Oxidation", 1, "v")]

    m_opt = gui.doc.match(
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
    mspy.monomers["X"] = mspy.monomer("X", "C2H3")
    mspy.monomers["Y"] = mspy.monomer("Y", "C3H5")
    # Custom sequences must have monomers separated by '|'
    seq2 = mspy.sequence("X|Y", chainType="custom", title="Seq2")
    seq2.matches = []
    seq2.cyclic = True

    doc.sequences = [seq1, seq2]

    msd_xml = doc.msd()

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
    doc = gui.doc.document()
    doc.spectrum = mspy.scan()
    msd_xml = doc.msd()
    assert '<spectrum points="0">' in msd_xml
    assert "<mzArray" not in msd_xml
    assert "<peaklist" not in msd_xml
    assert "<annotations" not in msd_xml
    assert "<sequences" not in msd_xml


def test_document_report(mock_config, sample_spectrum, mocker):
    """Test HTML report generation."""
    # Mock time.time for stable output
    mocker.patch("time.time", return_value=123456789.0)

    doc = gui.doc.document()
    doc.title = "Report Test"
    doc.date = "2023-10-27"
    doc.notes = "Some notes\nwith newlines."
    doc.spectrum = sample_spectrum
    doc.spectrum.polarity = -1  # Negative polarity

    # Add an annotation with theoretical value for delta
    doc.annotations = [
        gui.doc.annotation(
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
    seq = mspy.sequence("PEPTIDE", title="Seq1", accession="sp|P12345")
    seq.cyclic = True
    seq.modify("Oxidation", 1, "v")
    seq.matches = [
        gui.doc.match(
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
    doc.sequences = [seq]

    # Test with image and all data
    report_html = doc.report(image=True)

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
    doc.notes = ""
    doc.annotations = []
    doc.sequences = []
    report_html_minimal = doc.report(image=False)
    assert '<div id="spectrum">' not in report_html_minimal
    assert "<h2>Notes</h2>" not in report_html_minimal
    assert "<h2>Annotations</h2>" not in report_html_minimal
    assert "<h2>Sequence" not in report_html_minimal


def test_parseMSD_integration(tmp_path, mock_config, sample_spectrum, mocker):
    """Test parseMSD integration by serializing and deserializing a document."""
    # Mock save methods to avoid side effects during deserialization
    mocker.patch("mspy.saveMonomers")
    mocker.patch("mspy.saveModifications")

    doc = gui.doc.document()
    doc.title = "Integration Test"
    doc.spectrum = sample_spectrum
    doc.spectrum.scanNumber = 123

    # Add annotation
    doc.annotations = [
        gui.doc.annotation(label="Annot1", mz=150.0, ai=500.0, formula="H2O", charge=1)
    ]

    # Add sequence with modification
    seq = mspy.sequence("PEPTIDE", title="Seq1")
    # 'Oxidation' should be in mspy.modifications by default
    seq.modify("Oxidation", 1, "v")

    # Add match
    m = gui.doc.match(
        label="y1", mz=147.1, ai=200.0, theoretical=147.11, formula="C6H11NO3"
    )
    m.sequenceRange = [7, 7]
    seq.matches = [m]

    doc.sequences = [seq]

    # Serialize
    xml_data = doc.msd()

    # Write to temp file
    file_path = tmp_path / "test.msd"
    file_path.write_text(str(xml_data))

    # Deserialize
    parser = gui.doc.parseMSD(str(file_path))
    new_doc = parser.getDocument()

    # Assertions
    assert new_doc.title == doc.title
    assert new_doc.spectrum.scanNumber == 123

    # Spectrum data
    numpy.testing.assert_allclose(new_doc.spectrum.profile, doc.spectrum.profile)

    # Peaklist
    assert len(new_doc.spectrum.peaklist) == len(doc.spectrum.peaklist)
    assert new_doc.spectrum.peaklist[0].mz == doc.spectrum.peaklist[0].mz

    # Annotations
    assert len(new_doc.annotations) == 1
    assert new_doc.annotations[0].label == "Annot1"
    assert new_doc.annotations[0].formula == "H2O"

    # Sequences
    assert len(new_doc.sequences) == 1
    assert new_doc.sequences[0].title == "Seq1"
    assert len(new_doc.sequences[0].modifications) == 1
    assert new_doc.sequences[0].modifications[0][0] == "Oxidation"

    # Matches
    assert len(new_doc.sequences[0].matches) == 1
    assert new_doc.sequences[0].matches[0].label == "y1"
    assert new_doc.sequences[0].matches[0].sequenceRange == [7, 7]


def test_parseMSD_errors(tmp_path):
    """Test error handling in parseMSD."""
    # Test missing mzArray/intArray
    # getDocument returns a doc always if the XML is valid, but handleSpectrum fails silently.
    xml_missing = '<mSD version="2.2"><spectrum points="10"></spectrum></mSD>'
    file_path = tmp_path / "missing.msd"
    file_path.write_text(str(xml_missing))
    parser = gui.doc.parseMSD(str(file_path))
    doc = parser.getDocument()
    assert len(doc.spectrum.profile) == 0

    # Test corrupted data
    xml_corrupt = '<mSD version="2.2"><spectrum points="1"><mzArray compression="zlib">!!!</mzArray><intArray compression="zlib">!!!</intArray></spectrum></mSD>'
    file_path = tmp_path / "corrupt.msd"
    file_path.write_text(str(xml_corrupt))
    parser = gui.doc.parseMSD(str(file_path))
    doc = parser.getDocument()
    assert len(doc.spectrum.profile) == 0
    assert "Incorrect spectrum data." in parser.errors

    # Test incorrect peak/annotation/sequence data
    xml_bad_attr = """<mSD version="2.2">
  <peaklist><peak mz="abc" intensity="100.0" /></peaklist>
  <annotations><annotation peakMZ="def">Label</annotation></annotations>
  <sequences><sequence><seq>PEPTIDE</seq><match peakMZ="ghi">Match</match></sequence></sequences>
</mSD>"""
    file_path = tmp_path / "bad_attr.msd"
    file_path.write_text(str(xml_bad_attr))
    parser = gui.doc.parseMSD(str(file_path))
    doc = parser.getDocument()
    assert "Incorrect peak data." in parser.errors
    assert "Incorrect annotation data." in parser.errors
    assert "Incorrect sequence match data." in parser.errors

    # Test unknown monomer
    xml_bad_monomer = '<mSD version="2.2"><sequences><sequence><seq>UNKNOWN</seq></sequence></sequences></mSD>'
    file_path = tmp_path / "bad_monomer.msd"
    file_path.write_text(str(xml_bad_monomer))
    parser = gui.doc.parseMSD(str(file_path))
    doc = parser.getDocument()
    assert "Unknown monomers in sequence data." in parser.errors


def test_parseMSD_helpers(tmp_path, mocker):
    """Test internal helper methods of parseMSD."""
    import xml.dom.minidom

    mocker.patch("mspy.saveMonomers")
    mocker.patch("mspy.saveModifications")

    # Test _getVersion with mMassDoc tag
    xml_mmassdoc = '<mMassDoc version="1.0"></mMassDoc>'
    file_path = tmp_path / "legacy.msd"
    file_path.write_text(str(xml_mmassdoc))
    parser = gui.doc.parseMSD(str(file_path))
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
    parser = gui.doc.parseMSD(str(file_path))
    doc = parser.getDocument()

    assert doc.title == "v10"  # Filename base in handleDescription/getDocument for v1.0
    assert doc.spectrum.scanNumber == 10
    assert len(doc.spectrum.peaklist) == 1
    assert doc.spectrum.peaklist[0].mz == 100.1
    assert len(doc.annotations) == 1
    assert doc.annotations[0].label == "Annot1"
    assert len(doc.sequences) == 1
    assert doc.sequences[0].title == "Seq1"

    # Test getSequences for v1.0
    sequences = parser.getSequences()
    assert len(sequences) == 1
    assert sequences[0].title == "Seq1"
