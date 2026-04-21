import pytest
import wx

# Handle missing wx.RESIZE_BOX in wxPython 4.x
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = getattr(wx, "RESIZE_BORDER", 0)

from mmass import mspy
from mmass.gui import config, mwx
from mmass.gui.ids import *
from mmass.gui.panel_sequence import panelSequence


class MockParent(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None)
        self.onDocumentChanged_called = False
        self.updateMassPoints_called = False
        self.onToolsMassCalculator_called = False
        self.onToolsEnvelopeFit_called = False
        self.onToolsCalibration_called = False

    def onDocumentChanged(self, items=None):
        self.onDocumentChanged_called = True

    def updateMassPoints(self, mz_list):
        self.updateMassPoints_called = True

    def onToolsMassCalculator(self, **kwargs):
        self.onToolsMassCalculator_called = True

    def onToolsEnvelopeFit(self, **kwargs):
        self.onToolsEnvelopeFit_called = True

    def onToolsCalibration(self, **kwargs):
        self.onToolsCalibration_called = True


class MockEvent:
    def __init__(self, id=0, string_selection="", key_code=0, cmd_down=False):
        self.id = id
        self.string_selection = string_selection
        self.key_code = key_code
        self.cmd_down = cmd_down

    def GetId(self):
        return self.id

    def GetStringSelection(self):
        return self.string_selection

    def GetKeyCode(self):
        return self.key_code

    def CmdDown(self):
        return self.cmd_down

    def Skip(self):
        pass


@pytest.fixture
def panel(wx_app, mocker):
    # Ensure mspy is somewhat initialized with at least one monomer and modification for tests
    if "A" not in mspy.monomers:
        mspy.monomers["A"] = mspy.blocks.monomer(
            abbr="A", name="Alanine", formula="C3H5NO", category="_InternalAA"
        )
    if "M" not in mspy.monomers:
        mspy.monomers["M"] = mspy.blocks.monomer(
            abbr="M", name="Methionine", formula="C5H9NOS", category="_InternalAA"
        )

    if "Oxidation" not in mspy.modifications:
        mod = mspy.blocks.modification(
            name="Oxidation", gainFormula="O", lossFormula="", aminoSpecifity="M"
        )
        mspy.modifications["Oxidation"] = mod

    if "Trypsin" not in mspy.enzymes:
        enz = mspy.blocks.enzyme(
            name="Trypsin", expression="[KR][^P]", nTermFormula="H", cTermFormula="OH"
        )
        mspy.enzymes["Trypsin"] = enz

    # Patch sequence to always have 'matches' attribute
    original_init = mspy.sequence.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.matches = []

    mocker.patch.object(mspy.sequence, "__init__", patched_init)

    parent = MockParent()
    panel = panelSequence(parent)

    # Mock MakeModal if it doesn't exist (wxPython 4 compatibility)
    if not hasattr(panel, "MakeModal"):
        panel.MakeModal = mocker.Mock()

    yield panel
    panel.Destroy()
    parent.Destroy()


def test_init(panel):
    assert panel.currentTool == "editor"
    assert isinstance(panel.currentSequence, mspy.sequence)
    assert hasattr(panel.currentSequence, "matches")


def test_onToolSelected(panel, mocker):
    mocker.patch.object(mwx, "layout")
    mocker.patch.object(mwx, "dlgMessage")

    panel.onToolSelected(tool="modifications")
    assert panel.currentTool == "modifications"

    panel.onToolSelected(tool="digest")
    assert panel.currentTool == "digest"

    panel.onToolSelected(tool="fragment")
    assert panel.currentTool == "fragment"

    panel.onToolSelected(tool="search")
    assert panel.currentTool == "search"


def test_setData(panel):
    seq = mspy.sequence("ACDEF")
    seq.title = "Test Sequence"
    seq.accession = "ACC123"

    panel.setData(seq)

    assert panel.currentSequence == seq
    assert panel.sequenceTitle_value.GetValue() == "Test Sequence"
    assert panel.sequenceAccession_value.GetValue() == "ACC123"


def test_onSequenceType(panel, mocker):
    mocker.patch.object(mwx.dlgMessage, "ShowModal", return_value=wx.ID_OK)
    mocker.patch.object(mwx, "layout")

    assert panel.currentSequence.chainType == "aminoacids"

    panel.sequenceType_choice.SetStringSelection("Custom")
    panel.onSequenceType(None)

    assert panel.currentSequence.chainType == "custom"

    panel.sequenceType_choice.SetStringSelection("Regular amino acids")
    panel.onSequenceType(None)

    assert panel.currentSequence.chainType == "aminoacids"


def test_onSequenceCyclic(panel):
    panel.sequenceCyclic_check.SetValue(True)
    panel.onSequenceCyclic(None)
    assert panel.currentSequence.cyclic == True

    panel.sequenceCyclic_check.SetValue(False)
    panel.onSequenceCyclic(None)
    assert panel.currentSequence.cyclic == False


def test_modifications(panel, mocker):
    seq = mspy.sequence("MAGA")
    panel.setData(seq)

    panel.onToolSelected(tool="modifications")

    panel.updateAvailableResidues()
    assert "Methionine (M)" in panel.modsResidue_choice.GetStrings()

    panel.modsResidue_choice.SetStringSelection("Methionine (M)")
    panel.updateAvailablePositions()
    panel.modsPosition_choice.SetStringSelection("M 1")

    # Mock mspy.modifications for Oxidation using the proper blocks.modification class
    oxidation_mod = mspy.blocks.modification(
        name="Oxidation", gainFormula="O", lossFormula="", aminoSpecifity="M"
    )
    mocker.patch.dict(mspy.modifications, {"Oxidation": oxidation_mod})

    panel.updateAvailableModifications()
    panel.modsMod_choice.SetStringSelection("Oxidation")
    panel.modsType_choice.SetStringSelection("Fixed")

    mocker.patch.object(panel, "checkModifications", return_value=True)

    panel.onAddModification(None)

    assert len(seq.modifications) > 0
    assert seq.modifications[0][0] == "Oxidation"
    assert seq.modifications[0][1] == 0

    panel.modificationsList.Select(0)
    panel.onRemoveModifications(None)
    assert len(seq.modifications) == 0


def test_processing_digestion(panel, mocker):
    seq = mspy.sequence("MAGAMAGA")
    panel.setData(seq)
    panel.onToolSelected(tool="digest")

    # Mock threading.Thread to run synchronously
    mocker.patch.object(mwx, "dlgMessage")
    mock_thread = mocker.patch("threading.Thread")
    mock_thread_instance = mock_thread.return_value
    mock_thread_instance.is_alive.return_value = False

    # Simulate runDigestion when start is called
    def simulate_start():
        panel.runDigestion()

    mock_thread_instance.start.side_effect = simulate_start

    peptide = mspy.sequence("MAGA")
    peptide.history = [["digest", 0, 3]]
    peptide.miscleavages = 0
    mocker.patch("mmass.mspy.digest", return_value=[peptide])

    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch("mmass.mspy.coverage", return_value=50.0)
    config.sequence["digest"]["lowMass"] = 0

    panel.onDigest(None)

    assert panel.currentDigest is not None
    assert len(panel.currentDigest) > 0
    assert panel.digestList.GetItemCount() > 0


def test_processing_fragmentation(panel, mocker):
    seq = mspy.sequence("MAGA")
    panel.setData(seq)
    panel.onToolSelected(tool="fragment")

    mock_thread = mocker.patch("threading.Thread")
    mock_thread_instance = mock_thread.return_value
    mock_thread_instance.is_alive.return_value = False

    def simulate_start():
        panel.runFragmentation()

    mock_thread_instance.start.side_effect = simulate_start

    frag = mspy.sequence("MA")
    frag.history = [["fragment", 0, 1]]
    frag.fragmentFiltered = False
    mocker.patch("mmass.mspy.fragment", return_value=[frag])
    mocker.patch("mmass.mspy.fragmentlosses", return_value=[])
    mocker.patch("mmass.mspy.fragmentgains", return_value=[])

    mocker.patch.object(panel, "getParams", return_value=True)

    panel.onFragment(None)

    assert panel.currentFragments is not None
    assert len(panel.currentFragments) > 0
    assert panel.fragmentsList.GetItemCount() > 0


def test_processing_search(panel, mocker):
    seq = mspy.sequence("MAGAMAGA")
    panel.setData(seq)
    panel.onToolSelected(tool="search")

    mock_thread = mocker.patch("threading.Thread")
    mock_thread_instance = mock_thread.return_value
    mock_thread_instance.is_alive.return_value = False

    def simulate_start():
        panel.runSearch()

    mock_thread_instance.start.side_effect = simulate_start

    match_pep = mspy.sequence("MAGA")
    match_pep.history = [["search", 0, 3]]
    mocker.patch.object(mspy.sequence, "search", return_value=[match_pep])

    mocker.patch.object(panel, "getParams", return_value=True)
    panel.searchMass_value.SetValue("400.0")

    panel.onSearch(None)

    assert panel.currentSearch is not None
    assert len(panel.currentSearch) > 0
    assert panel.searchList.GetItemCount() > 0


def test_sequenceCanvas_keys(panel, mocker):
    canvas = panel.sequenceCanvas
    seq = mspy.sequence("AA")
    canvas.setData(seq)

    # Mock GetSelection to return (0,0)
    mocker.patch.object(canvas, "GetSelection", return_value=(0, 0))
    # Mock GetRange to return empty string for (0,0)
    mocker.patch.object(canvas, "GetRange", return_value="")

    evt = MockEvent(key_code=ord("C"))
    canvas._onText(evt)

    assert "C" in seq.format("S")
    assert seq[0] == "C"


def test_sequenceGrid_logic(panel):
    grid = panel.sequenceGrid
    seq = mspy.sequence([], chainType="custom")
    grid.setData(seq)

    grid.items[0].SetValue("M1")

    if "M1" not in mspy.monomers:
        mspy.monomers["M1"] = mspy.blocks.monomer(abbr="M1", name="M1", formula="CH2")

    grid._onSequence(None)

    assert len(seq) == 1
    assert seq[0] == "M1"
