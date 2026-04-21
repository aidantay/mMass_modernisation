import pytest
import wx

from mmass.gui.dlg_modifications_editor import dlgModificationsEditor


class MockModification:
    def __init__(
        self,
        name="",
        gainFormula="",
        lossFormula="",
        aminoSpecifity="",
        termSpecifity="",
        description="",
    ):
        self.name = name
        self.gainFormula = gainFormula
        self.lossFormula = lossFormula
        self.aminoSpecifity = aminoSpecifity
        self.termSpecifity = termSpecifity
        self.description = description
        self.mass = (10.0, 10.1)


class MockCompound:
    def __init__(self, formula):
        self.formula = formula

    def mass(self):
        if not self.formula:
            return (0.0, 0.0)
        if "invalid" in self.formula:
            raise ValueError("Invalid formula")
        return (float(len(self.formula)), float(len(self.formula)) + 0.1)


@pytest.fixture
def mock_mspy(mocker):
    mock_mspy = mocker.patch("mmass.gui.dlg_modifications_editor.mspy")
    mock_mspy.modifications = {}
    mock_mspy.modification = mocker.Mock(side_effect=MockModification)
    mock_mspy.compound = MockCompound
    return mock_mspy


@pytest.fixture
def mock_config(mocker):
    mock_config = mocker.patch("mmass.gui.dlg_modifications_editor.config")
    mock_config.main = {"mzDigits": 4}
    return mock_config


@pytest.fixture
def mock_mwx(mocker):
    mock_mwx = mocker.patch("mmass.gui.dlg_modifications_editor.mwx")
    # Mock mwx constants
    mock_mwx.LISTCTRL_STYLE_MULTI = wx.LC_REPORT
    mock_mwx.LISTCTRL_SPACE = 5
    mock_mwx.PANEL_SPACE_MAIN = 10
    mock_mwx.LISTCTRL_ALTCOLOUR = wx.Colour(240, 240, 240)
    mock_mwx.CHOICE_HEIGHT = -1
    mock_mwx.GRIDBAG_VSPACE = 5
    mock_mwx.GRIDBAG_HSPACE = 10

    # Mock formulaCtrl
    class MockFormulaCtrl(wx.TextCtrl):
        def __init__(self, *args, **kwargs):
            wx.TextCtrl.__init__(self, *args, **kwargs)

    mock_mwx.formulaCtrl = MockFormulaCtrl

    # Mock sortListCtrl
    class MockSortListCtrl(wx.ListCtrl):
        def __init__(self, *args, **kwargs):
            wx.ListCtrl.__init__(self, *args, **kwargs)
            self.dataMap = []
            self.selected = []

            # Mock columns for ListCtrl
            self.columns = []

        def setAltColour(self, color):
            pass

        def setDataMap(self, dataMap):
            self.dataMap = dataMap

        def sort(self):
            pass

        def getSelected(self):
            return self.selected

        def InsertColumn(self, col, heading, format=wx.LIST_FORMAT_LEFT, width=-1):
            self.columns.append(heading)

        def SetColumnWidth(self, col, width):
            pass

        def DeleteAllItems(self):
            pass

        def InsertItem(self, index, label):
            return index

        def SetItem(self, index, col, label):
            pass

        def SetItemData(self, item, data):
            pass

        def GetItemData(self, item):
            return item  # Simple mapping for tests

    mock_mwx.sortListCtrl = MockSortListCtrl

    # Mock dlgMessage
    mock_dlg = mocker.Mock()
    mock_dlg.ShowModal.return_value = wx.ID_OK
    mock_mwx.dlgMessage.return_value = mock_dlg

    return mock_mwx


@pytest.fixture
def dialog(wx_app, mock_mspy, mock_config, mock_mwx, mocker):
    parent = wx.Frame(None)
    parent.getUsedModifications = mocker.Mock(return_value=["UsedMod"])

    # Initialize some modifications
    mod1 = MockModification("Mod1", "H", "", "A", "N", "Desc1")
    mod2 = MockModification("UsedMod", "O", "", "", "", "Used modification")

    mock_mspy.modifications = {"Mod1": mod1, "UsedMod": mod2}

    dlg = dlgModificationsEditor(parent)
    yield dlg
    dlg.Destroy()
    parent.Destroy()


def test_init(dialog):
    """Test initialization and GUI setup."""
    assert dialog.GetTitle() == "Modifications Library"
    assert "Mod1" in dialog.itemsMap[0]
    assert "UsedMod" in dialog.itemsMap[1]
    assert dialog.used == ["UsedMod"]


def test_on_item_selected(dialog, mock_mspy, mocker):
    """Test updating editor when an item is selected."""
    # Mock event
    evt = mocker.Mock()

    # Test Mod1 (N-terminus)
    evt.GetText.return_value = "Mod1"
    dialog.onItemSelected(evt)
    assert dialog.itemName_value.GetValue() == "Mod1"
    assert dialog.itemDescription_value.GetValue() == "Desc1"
    assert dialog.itemTermSpecifity_choice.GetStringSelection() == "N-terminus"

    # Test UsedMod (None terminus)
    evt.GetText.return_value = "UsedMod"
    dialog.onItemSelected(evt)
    assert dialog.itemTermSpecifity_choice.GetStringSelection() == "None"

    # Test C-terminus
    mock_mspy.modifications["ModC"] = MockModification("ModC", "H", "", "", "C", "")
    evt.GetText.return_value = "ModC"
    dialog.onItemSelected(evt)
    assert dialog.itemTermSpecifity_choice.GetStringSelection() == "C-terminus"


def test_on_add_item_new(dialog, mock_mspy):
    """Test adding a new modification."""
    dialog.itemName_value.SetValue("NewMod")
    dialog.itemGainFormula_value.SetValue("H2O")
    dialog.itemDescription_value.SetValue("New Description")

    dialog.onAddItem(None)

    assert "NewMod" in mock_mspy.modifications
    assert mock_mspy.modifications["NewMod"].description == "New Description"
    # Editor should be cleared
    assert dialog.itemName_value.GetValue() == ""


def test_on_add_item_replace(dialog, mock_mspy, mock_mwx):
    """Test replacing an existing modification."""
    dialog.itemName_value.SetValue("Mod1")
    dialog.itemGainFormula_value.SetValue("H2O")

    # User clicks "Replace" (wx.ID_OK is default in mock)
    dialog.onAddItem(None)

    assert mock_mspy.modifications["Mod1"].gainFormula == "H2O"
    mock_mwx.dlgMessage.assert_called()


def test_on_add_item_cancel_replace(dialog, mock_mspy, mock_mwx):
    """Test canceling replacement of an existing modification."""
    dialog.itemName_value.SetValue("Mod1")
    dialog.itemGainFormula_value.SetValue("H2O")

    # User clicks "Cancel"
    mock_mwx.dlgMessage.return_value.ShowModal.return_value = wx.ID_CANCEL

    dialog.onAddItem(None)

    # Should NOT be changed to H2O
    assert mock_mspy.modifications["Mod1"].gainFormula == "H"


def test_on_add_item_invalid(dialog, mock_mspy):
    """Test adding invalid modification (missing name or formula)."""
    # Missing name
    dialog.itemName_value.SetValue("")
    dialog.itemGainFormula_value.SetValue("H")
    dialog.onAddItem(None)
    assert len(mock_mspy.modifications) == 2

    # Missing formula
    dialog.itemName_value.SetValue("InvalidMod")
    dialog.itemGainFormula_value.SetValue("")
    dialog.itemLossFormula_value.SetValue("")
    dialog.onAddItem(None)
    assert "InvalidMod" not in mock_mspy.modifications


def test_on_delete_item_success(dialog, mock_mspy, mock_mwx):
    """Test deleting a modification."""
    # Mock selection
    dialog.itemsList.selected = [0]  # Mod1 is at index 0
    dialog.itemsMap = [("Mod1", "H", "", 1.0, 1.1, "A", "N", "Desc1")]

    # User clicks "Delete"
    dialog.onDeleteItem(None)

    assert "Mod1" not in mock_mspy.modifications
    mock_mwx.dlgMessage.assert_called()


def test_on_delete_item_used(dialog, mock_mspy, mock_mwx):
    """Test deleting a modification that is in use."""
    # Mock selection
    dialog.itemsList.selected = [0]  # UsedMod
    dialog.itemsMap = [("UsedMod", "O", "", 16.0, 16.0, "", "", "")]

    # User clicks "Delete" for UsedMod
    dialog.onDeleteItem(None)

    # Should still be there
    assert "UsedMod" in mock_mspy.modifications
    # Should show error message (at least 2 calls to dlgMessage: confirm and error)
    assert mock_mwx.dlgMessage.call_count >= 2


def test_on_delete_item_cancel(dialog, mock_mspy, mock_mwx):
    """Test canceling deletion."""
    dialog.itemsList.selected = [0]
    mock_mwx.dlgMessage.return_value.ShowModal.return_value = wx.ID_CANCEL

    dialog.onDeleteItem(None)

    assert "Mod1" in mock_mspy.modifications


def test_on_formula_edited(dialog, mocker):
    """Test that formula editing triggers mass update."""
    mock_callafter = mocker.patch.object(wx, "CallAfter")
    dialog.onFormulaEdited(mocker.Mock())
    mock_callafter.assert_called_with(dialog.updateFormulaMass)


def test_update_formula_mass_valid(dialog):
    """Test mass update with valid formulas."""
    dialog.itemGainFormula_value.SetValue("H2O")  # length 3
    dialog.itemLossFormula_value.SetValue("H")  # length 1
    # Mock compound returns length for mass
    # Gain: (3.0, 3.1), Loss: (1.0, 1.1)
    # Expected Mo: 3.0 - 1.0 = 2.0, Av: 3.1 - 1.1 = 2.0
    dialog.updateFormulaMass()
    assert dialog.itemMoMass_value.GetValue() == "2.0"
    assert dialog.itemAvMass_value.GetValue() == "2.0"


def test_update_formula_mass_invalid(dialog):
    """Test mass update with invalid formula."""
    dialog.itemGainFormula_value.SetValue("invalid")
    dialog.updateFormulaMass()
    assert dialog.itemMoMass_value.GetValue() == ""
    assert dialog.itemAvMass_value.GetValue() == ""


def test_get_item_data_validation(dialog, mock_mspy):
    """Test data extraction and validation in getItemData."""
    dialog.itemName_value.SetValue("Test")
    dialog.itemTermSpecifity_choice.SetStringSelection("N-terminus")
    dialog.itemGainFormula_value.SetValue("H")

    res = dialog.getItemData()
    assert res.name == "Test"
    assert res.termSpecifity == "N"

    dialog.itemTermSpecifity_choice.SetStringSelection("C-terminus")
    res = dialog.getItemData()
    assert res.termSpecifity == "C"

    dialog.itemTermSpecifity_choice.SetStringSelection("None")
    res = dialog.getItemData()
    assert res.termSpecifity == ""

    # Test unexpected termSpecifity (to cover the skip-all branch)
    dialog.itemTermSpecifity_choice.Append("unexpected")
    dialog.itemTermSpecifity_choice.SetStringSelection("unexpected")
    res = dialog.getItemData()
    # It should not have been changed from "unexpected" by any branch
    assert res.termSpecifity == "unexpected"


def test_get_item_data_exception(dialog, mock_mspy):
    """Test getItemData when mspy.modification raises an exception."""
    mock_mspy.modification.side_effect = Exception("error")
    dialog.itemName_value.SetValue("Test")
    dialog.itemGainFormula_value.SetValue("H")

    assert dialog.getItemData() is False


def test_update_items_list_empty(dialog, mock_mspy):
    """Test updateItemsList when there are no modifications."""
    mock_mspy.modifications = {}
    dialog.updateItemsList()
    assert dialog.itemsMap == []


def test_clear_editor(dialog):
    """Test clearing the editor."""
    dialog.itemName_value.SetValue("SomeName")
    dialog.clearEditor()
    assert dialog.itemName_value.GetValue() == ""
    assert dialog.itemTermSpecifity_choice.GetStringSelection() == "None"
