import html
import textwrap
import xml.dom.minidom
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mmass.mspy import blocks


@pytest.fixture(autouse=True)
def backup_globals(mocker):
    """Backup and restore global dictionaries in blocks."""
    mocker.patch.dict(blocks.elements)
    mocker.patch.dict(blocks.monomers)
    mocker.patch.dict(blocks.enzymes)
    mocker.patch.dict(blocks.fragments)
    mocker.patch.dict(blocks.modifications)


class TestElement:
    """Tests for the Element class."""

    @pytest.mark.parametrize(
        ("name", "symbol", "atomic_number", "isotopes", "valence", "expected_mass"),
        [
            ("Test", "Te", 10, {1: (10.0, 1.0)}, 2, (10.0, 10.0)),
            ("Edge", "Ed", 11, {0: (12.0, 0.0)}, None, (12.0, 12.0)),
        ],
        ids=["normal_isotopes", "zero_mass_isotopes"],
    )
    def test_init(self, name, symbol, atomic_number, isotopes, valence, expected_mass):
        """Test Element initialization."""
        # Arrange
        # Parameters handled by parametrize

        # Act
        el = blocks.Element(
            name=name, symbol=symbol, atomicNumber=atomic_number, isotopes=isotopes, valence=valence
        )

        # Assert
        assert el.name == name
        assert el.symbol == symbol
        assert el.atomicNumber == atomic_number
        assert el.isotopes == isotopes
        assert el.valence == valence
        assert el.mass == expected_mass


class TestMonomer:
    """Tests for the Monomer class."""

    @pytest.mark.parametrize(
        ("abbr", "formula", "losses", "name", "category", "expected_composition", "expected_mass"),
        [
            ("X", "C2H5NO", ["H2O"],"TestMonomer", "TestCategory", {"C": 2, "H": 5, "N": 1, "O": 1}, (59.0371137878, 59.0673235851)),
            ("X", "H", ["H2O", "NH3"], "", "", {"H": 1}, (1.0078250321, 1.0079407539257785)),
        ],
        ids=["full_initialization", "losses_parsing"],
    )
    def test_init(self, abbr, formula, losses, name, category, expected_composition, expected_mass):
        """Test Monomer initialization."""
        # Arrange
        # Parameters handled by parametrize

        # Act
        m = blocks.Monomer(
            abbr=abbr, formula=formula, losses=losses, name=name, category=category
        )

        # Assert
        assert m.abbr == abbr
        assert m.formula == formula
        assert m.losses == losses
        assert m.name == name
        assert m.category == category
        assert m.composition == expected_composition
        assert m.mass[0] == pytest.approx(expected_mass[0])
        assert m.mass[1] == pytest.approx(expected_mass[1])


class TestEnzyme:
    """Tests for the Enzyme class."""

    def test_init(self):
        """Test Enzyme initialization."""
        # Arrange
        name = "TestEnzyme"
        expression = "[K][A-Z]"
        n_term_formula = "H"
        c_term_formula = "OH"
        mods_before = False
        mods_after = True

        # Act
        e = blocks.Enzyme(
            name=name, expression=expression,
            nTermFormula=n_term_formula, cTermFormula=c_term_formula,
            modsBefore=mods_before, modsAfter=mods_after,
        )

        # Assert
        assert e.name == name
        assert e.expression == expression
        assert e.nTermFormula == n_term_formula
        assert e.cTermFormula == c_term_formula
        assert e.modsBefore is mods_before
        assert e.modsAfter is mods_after


class TestFragment:
    """Tests for the Fragment class."""

    def test_init(self):
        """Test Fragment initialization."""
        # Arrange
        name = "TestFragment"
        terminus = "N"
        n_term_formula = "H"
        c_term_formula = "OH"
        n_term_filter = True
        c_term_filter = False

        # Act
        f = blocks.Fragment(
            name=name, terminus=terminus,
            nTermFormula=n_term_formula, cTermFormula=c_term_formula,
            nTermFilter=n_term_filter, cTermFilter=c_term_filter,
        )

        # Assert
        assert f.name == name
        assert f.terminus == terminus
        assert f.nTermFormula == n_term_formula
        assert f.cTermFormula == c_term_formula
        assert f.nTermFilter is n_term_filter
        assert f.cTermFilter is c_term_filter


class TestModification:
    """Tests for the Modification class."""

    def test_init(self):
        """Test Modification initialization and mass calculation."""
        # Arrange
        name = "TestMod"
        gain_formula = "O"
        loss_formula = "H"
        amino_specifity = "K"
        term_specifity = "N"
        description = "Test"

        # Act
        mod = blocks.Modification(
            name=name,
            gainFormula=gain_formula, lossFormula=loss_formula,
            aminoSpecifity=amino_specifity, termSpecifity=term_specifity, description=description,
        )

        # Assert
        assert mod.name == name
        assert mod.gainFormula == gain_formula
        assert mod.lossFormula == loss_formula
        assert mod.aminoSpecifity == amino_specifity
        assert mod.termSpecifity == term_specifity
        assert mod.description == description
        assert mod.composition == {"O": 1, "H": -1}
        assert mod.mass[0] == pytest.approx(14.98708959)
        assert mod.mass[1] == pytest.approx(14.99146417)


class TestXMLUtils:
    """Tests for internal XML utility functions."""

    @pytest.mark.parametrize(
        ("xml_input", "expected_text"),
        [
            ("<root>text1<child>ignored</child>text2</root>", "text1text2"),
            ("<root>only_text</root>", "only_text"),
            ("<root><child>all_ignored</child></root>", ""),
            ("<root>  preserves  space  </root>", "  preserves  space  "),
        ],
        ids=[
            "text1_child_ignored_text2",
            "only_text",
            "child_all_ignored",
            "preserves_space",
        ],
    )
    def test_get_node_text(self, xml_input, expected_text):
        """Test extraction of text from a DOM node."""
        # Arrange
        dom = xml.dom.minidom.parseString(xml_input)

        # Act
        actual = blocks._getNodeText(dom.documentElement)

        # Assert
        assert actual == expected_text

    def test_escape(self):
        """Test explicit escaping of special characters."""
        # Arrange
        text = " < & > \" ' "
        expected = "&lt; &amp; &gt; &quot; &apos;"

        # Act
        escaped = blocks._escape(text)

        # Assert
        assert escaped == expected


class TestSerialization:
    """Tests for saving and loading blocks to/from XML."""

    def test_save_load_monomers(self, tmp_path: Path):
        """Test saving and loading monomers to XML file."""
        path = tmp_path / "monomers.xml"
        blocks.monomers["TEST"] = blocks.Monomer(abbr="TEST", formula="CH4", name="Methane", category="Test", losses=["H2O"])
        blocks.monomers["INTERNAL"] = blocks.Monomer(abbr="INTERNAL", formula="H", name="Internal", category="_InternalAA")

        # Save
        assert blocks.saveMonomers(tmp_path) is False
        assert blocks.saveMonomers(path) is True
        assert path.exists()

        # Verify INTERNAL was not saved
        content = path.read_text()
        assert "INTERNAL" not in content
        assert 'losses="H2O"' in content

        # Load
        blocks.loadMonomers(path, clear=True)
        assert "TEST" in blocks.monomers
        assert "INTERNAL" not in blocks.monomers
        assert len(blocks.monomers) == 1
        assert blocks.monomers["TEST"].name == "Methane"
        assert blocks.monomers["TEST"].losses == ["H2O"]

    def test_save_load_enzymes(self, tmp_path: Path):
        """Test saving and loading enzymes to XML file."""
        path = tmp_path / "enzymes.xml"
        blocks.enzymes.clear()
        blocks.enzymes["TEST_ENZ"] = blocks.Enzyme(name="TEST_ENZ", expression="[A][B]")

        # Save
        assert blocks.saveEnzymes(tmp_path) is False
        assert blocks.saveEnzymes(path) is True

        # Load
        blocks.loadEnzymes(path, clear=True)
        assert "TEST_ENZ" in blocks.enzymes
        assert len(blocks.enzymes) == 1

    def test_save_load_modifications(self, tmp_path: Path):
        """Test saving and loading modifications to XML file."""
        path = tmp_path / "modifications.xml"
        blocks.modifications.clear()
        blocks.modifications["TEST_MOD"] = blocks.Modification(
            name="TEST_MOD", gainFormula="O", description="desc"
        )

        # Save
        assert blocks.saveModifications(tmp_path) is False
        assert blocks.saveModifications(path) is True

        # Load
        blocks.loadModifications(path, clear=True)
        assert "TEST_MOD" in blocks.modifications
        assert len(blocks.modifications) == 1
        assert blocks.modifications["TEST_MOD"].description == "desc"

    def test_load_replace_monomers(self, tmp_path: Path):
        """Test the replace logic when loading monomers."""
        path = tmp_path / "monomers.xml"
        blocks.monomers["TEST"] = blocks.Monomer(abbr="TEST", formula="H2O", name="Old")

        # Create XML with 'A' (New) and 'B'
        buff = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8" ?>
            <mspyMonomers>
                <monomer abbr="TEST" name="New" formula="CH4" />
            </mspyMonomers>
        """)
        path.write_text(buff)

        # Load with replace=False
        blocks.loadMonomers(path, replace=False, clear=False)
        assert blocks.monomers["TEST"].name == "Old"

        # Load with replace=True
        blocks.loadMonomers(path, replace=True, clear=False)
        assert blocks.monomers["TEST"].name == "New"

    def test_load_replace_enzymes(self, tmp_path: Path):
        """Test the replace logic when loading enzymes."""
        path = tmp_path / "enzymes.xml"
        blocks.enzymes["TEST"] = blocks.Enzyme(name="TEST", expression="[A]")

        buff = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8" ?>
            <mspyEnzymes>
                <enzyme name="TEST">
                <expression>B</expression>
                <formula nTerm="" cTerm="" />
                <allowMods before="0" after="0" />
                </enzyme>
            </mspyEnzymes>
        """)
        path.write_text(buff)

        # Load with replace=False
        blocks.loadEnzymes(path, replace=False, clear=False)
        assert blocks.enzymes["TEST"].expression == "[A]"

        # Load with replace=True
        blocks.loadEnzymes(path, replace=True, clear=False)
        assert blocks.enzymes["TEST"].expression == "B"

    def test_load_replace_modifications(self, tmp_path: Path):
        """Test the replace logic when loading modifications."""
        path = tmp_path / "modifications.xml"
        blocks.modifications["TEST"] = blocks.Modification(name="TEST", gainFormula="O")

        buff = textwrap.dedent("""\
            <?xml version="1.0" encoding="utf-8" ?>
            <mspyModifications>
                <modification name="TEST">
                    <description>New</description>
                    <formula gain="N" loss="" />
                    <specifity amino="" terminus="" />
                </modification>
            </mspyModifications>
        """)
        path.write_text(buff)

        # Load with replace=False
        blocks.loadModifications(path, replace=False, clear=False)
        assert blocks.modifications["TEST"].gainFormula == "O"

        # Load with replace=True
        blocks.loadModifications(path, replace=True, clear=False)
        assert blocks.modifications["TEST"].gainFormula == "N"

    def test_load_clear_false(self, tmp_path: Path):
        """Test that clear=False preserves existing items."""
        path = tmp_path / "modifications.xml"
        blocks.modifications["TEST_1"] = blocks.Modification(name="TEST_1", gainFormula="O")
        blocks.saveModifications(path)

        blocks.modifications["TEST_2"] = blocks.Modification(name="TEST_2", gainFormula="H")
        blocks.loadModifications(path, clear=False)
        assert "TEST_1" in blocks.modifications
        assert "TEST_2" in blocks.modifications  # Should still be there because clear=False


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.lists(st.text(), min_size=1, max_size=10))
    def test_get_node_text(self, texts):
        """Property-based test for _getNodeText using DOM manipulation."""
        doc = xml.dom.minidom.Document()
        root = doc.createElement("root")
        doc.appendChild(root)

        # Programmatically add text nodes.
        # This automatically handles special characters without manual escaping.
        for t in texts:
            text_node = doc.createTextNode(t)
            root.appendChild(text_node)

        result = blocks._getNodeText(root)
        assert result == "".join(texts)

    @given(st.text())
    def test_escape(self, text):
        """Property-based test for _escape using html.unescape."""
        escaped = blocks._escape(text)
        # Reversing escape should return the original string
        assert html.unescape(escaped) == text.strip()
