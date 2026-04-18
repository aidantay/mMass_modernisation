import os
import tempfile

import gui.dlg_compounds_editor as dlg_editor
import gui.libs as libs
import pytest
import wx
from gui.ids import *


@pytest.fixture
def compounds_lib(mocker):
    """Fixture to mock libs.compounds and isolate tests."""
    mocker.patch("gui.libs.compounds", {})
    mocked_compounds = libs.compounds
    yield mocked_compounds


@pytest.fixture
def dlg_editor_instance(wx_app, compounds_lib, mocker):
    """Fixture for dlgCompoundsEditor instance."""
    parent = wx.Frame(None)
    # Ensure config values are present for UI formatting
    mocker.patch("gui.config.main", {"mzDigits": 4})
    dlg = dlg_editor.dlgCompoundsEditor(parent)
    yield dlg
    dlg.Destroy()
    parent.Destroy()


# --- Tests for dlgGroupName ---


def test_dlgGroupName_init(wx_app):
    """Test initialization of dlgGroupName."""
    parent = wx.Frame(None)

    # Test without initial name
    dlg = dlg_editor.dlgGroupName(parent)
    assert dlg.name == ""
    assert dlg.name_value.GetValue() == ""
    dlg.Destroy()

    # Test with initial name
    dlg = dlg_editor.dlgGroupName(parent, name="TestGroup")
    assert dlg.name == "TestGroup"
    assert dlg.name_value.GetValue() == "TestGroup"
    dlg.Destroy()

    parent.Destroy()


def test_dlgGroupName_onOK(wx_app, mocker):
    """Test OK button logic in dlgGroupName."""
    parent = wx.Frame(None)
    dlg = dlg_editor.dlgGroupName(parent)

    # Valid input scenario
    dlg.name_value.SetValue("ValidName")
    mock_end_modal = mocker.patch.object(dlg, "EndModal")
    dlg.onOK(None)
    mock_end_modal.assert_called_once_with(wx.ID_OK)
    assert dlg.name == "ValidName"

    # Empty input scenario (should trigger bell)
    dlg.name_value.SetValue("")
    mock_bell = mocker.patch("wx.Bell")
    dlg.onOK(None)
    mock_bell.assert_called_once()

    dlg.Destroy()
    parent.Destroy()


# --- Tests for dlgSelectItemsToImport ---


def test_dlgSelectItemsToImport_init(wx_app, mocker):
    """Test initialization and list population of dlgSelectItemsToImport."""
    parent = wx.Frame(None)
    items = {
        "Group1": {"C1": mocker.Mock(), "C2": mocker.Mock()},
        "Group2": {"C3": mocker.Mock()},
    }
    dlg = dlg_editor.dlgSelectItemsToImport(parent, items)

    assert dlg.items == items
    assert dlg.itemsList.GetItemCount() == 2

    # Verify mapping
    groups = [item[0] for item in dlg.itemsMap]
    assert "Group1" in groups
    assert "Group2" in groups

    dlg.Destroy()
    parent.Destroy()


def test_dlgSelectItemsToImport_onItemActivated(wx_app, mocker):
    """Test double-click activation in dlgSelectItemsToImport."""
    parent = wx.Frame(None)
    items = {"Group1": {}}
    dlg = dlg_editor.dlgSelectItemsToImport(parent, items)

    mocker.patch.object(dlg, "getSelecedItems", return_value=["Group1"])
    mock_end_modal = mocker.patch.object(dlg, "EndModal")
    dlg.onItemActivated(None)
    mock_end_modal.assert_called_once_with(wx.ID_OK)
    assert dlg.selected == ["Group1"]

    dlg.Destroy()
    parent.Destroy()


def test_dlgSelectItemsToImport_onImport(wx_app, mocker):
    """Test Import button logic in dlgSelectItemsToImport."""
    parent = wx.Frame(None)
    items = {"Group1": {}}
    dlg = dlg_editor.dlgSelectItemsToImport(parent, items)

    # Case: Selection exists
    mocker.patch.object(dlg, "getSelecedItems", return_value=["Group1"])
    mock_end_modal = mocker.patch.object(dlg, "EndModal")
    dlg.onImport(None)
    mock_end_modal.assert_called_once_with(wx.ID_OK)

    # Case: No selection
    mocker.patch.object(dlg, "getSelecedItems", return_value=[])
    mock_bell = mocker.patch("wx.Bell")
    dlg.onImport(None)
    mock_bell.assert_called_once()

    dlg.Destroy()
    parent.Destroy()


# --- Tests for dlgCompoundsEditor ---


def test_dlgCompoundsEditor_init(dlg_editor_instance):
    """Verify default state after initialization."""
    assert dlg_editor_instance.group is None
    assert dlg_editor_instance.groupName_choice.GetCount() == 1
    assert dlg_editor_instance.groupName_choice.GetString(0) == "Compounds lists"


def test_dlgCompoundsEditor_onGroupSelected(dlg_editor_instance, compounds_lib):
    """Test switching between compound groups."""
    compounds_lib["Group1"] = {}
    dlg_editor_instance.updateGroups()

    # Select specific group
    dlg_editor_instance.groupName_choice.SetStringSelection("Group1")
    dlg_editor_instance.onGroupSelected()
    assert dlg_editor_instance.group == "Group1"

    # Select the default header
    dlg_editor_instance.groupName_choice.SetStringSelection("Compounds lists")
    dlg_editor_instance.onGroupSelected()
    assert dlg_editor_instance.group is None


def test_dlgCompoundsEditor_onItemSelected(dlg_editor_instance, compounds_lib, mocker):
    """Test loading compound details into the editor on selection."""
    compound = mocker.Mock()
    compound.description = "Desc1"
    compound.expression = "H2O"
    compounds_lib["Group1"] = {"C1": compound}
    dlg_editor_instance.group = "Group1"

    evt = mocker.Mock()
    evt.GetText.return_value = "C1"
    dlg_editor_instance.onItemSelected(evt)

    assert dlg_editor_instance.itemName_value.GetValue() == "C1"
    assert dlg_editor_instance.itemDescription_value.GetValue() == "Desc1"
    assert dlg_editor_instance.itemFormula_value.GetValue() == "H2O"


def test_dlgCompoundsEditor_onAddGroup(dlg_editor_instance, compounds_lib, mocker):
    """Test adding a new compound group."""
    mock_dlg = mocker.patch("gui.dlg_compounds_editor.dlgGroupName")
    inst = mock_dlg.return_value
    inst.ShowModal.return_value = wx.ID_OK
    inst.name = "NewGroup"

    dlg_editor_instance.onAddGroup(None)
    assert "NewGroup" in compounds_lib
    assert dlg_editor_instance.group == "NewGroup"

    # Test duplicate group name
    inst.name = "NewGroup"
    mock_msg = mocker.patch("gui.mwx.dlgMessage")
    mock_bell = mocker.patch("wx.Bell")
    dlg_editor_instance.onAddGroup(None)
    mock_bell.assert_called_once()


def test_dlgCompoundsEditor_onRenameGroup(dlg_editor_instance, compounds_lib, mocker):
    """Test renaming an existing group."""
    compound = mocker.Mock()
    compound.mass.return_value = (10.0, 11.0)
    compound.expression = "H2O"
    compound.description = "desc"
    compounds_lib["Group1"] = {"C1": compound}
    dlg_editor_instance.group = "Group1"

    mock_dlg = mocker.patch("gui.dlg_compounds_editor.dlgGroupName")
    inst = mock_dlg.return_value
    inst.ShowModal.return_value = wx.ID_OK
    inst.name = "RenamedGroup"

    dlg_editor_instance.onRenameGroup(None)
    assert "RenamedGroup" in compounds_lib
    assert "Group1" not in compounds_lib
    assert dlg_editor_instance.group == "RenamedGroup"


def test_dlgCompoundsEditor_onDeleteGroup(dlg_editor_instance, compounds_lib, mocker):
    """Test deleting a group."""
    compounds_lib["Group1"] = {}
    dlg_editor_instance.group = "Group1"

    mock_msg = mocker.patch("gui.mwx.dlgMessage")
    mock_msg.return_value.ShowModal.return_value = wx.ID_OK
    dlg_editor_instance.onDeleteGroup(None)
    assert "Group1" not in compounds_lib
    assert dlg_editor_instance.group is None


def test_dlgCompoundsEditor_onAddItem(dlg_editor_instance, compounds_lib, mocker):
    """Test adding a compound to the current group."""
    compounds_lib["Group1"] = {}
    dlg_editor_instance.group = "Group1"

    compound = mocker.Mock()
    compound.name = "C1"
    compound.mass.return_value = (10.0, 11.0)
    compound.expression = "H2O"
    compound.description = "desc"
    mocker.patch.object(dlg_editor_instance, "getItemData", return_value=compound)
    dlg_editor_instance.onAddItem(None)
    assert compounds_lib["Group1"]["C1"] == compound


def test_dlgCompoundsEditor_onDeleteItem(dlg_editor_instance, compounds_lib, mocker):
    """Test deleting selected compounds from a group."""
    compound = mocker.Mock()
    compound.mass.return_value = (10.0, 11.0)
    compound.expression = "H2O"
    compound.description = "desc"
    compounds_lib["Group1"] = {"C1": compound}
    dlg_editor_instance.group = "Group1"
    dlg_editor_instance.updateItemsList()

    mock_msg = mocker.patch("gui.mwx.dlgMessage")
    mock_msg.return_value.ShowModal.return_value = wx.ID_OK
    mocker.patch.object(dlg_editor_instance.itemsList, "getSelected", return_value=[0])
    dlg_editor_instance.onDeleteItem(None)
    assert "C1" not in compounds_lib["Group1"]


def test_dlgCompoundsEditor_updateFormulaMass(dlg_editor_instance, mocker):
    """Test real-time mass calculation from formula."""
    # Valid formula (Water)
    dlg_editor_instance.itemFormula_value.SetValue("H2O")
    dlg_editor_instance.updateFormulaMass()
    assert dlg_editor_instance.itemMoMass_value.GetValue() != ""
    assert dlg_editor_instance.itemAvMass_value.GetValue() != ""

    # Invalid formula
    dlg_editor_instance.itemFormula_value.SetValue("InvalidFormula")
    mock_bell = mocker.patch("wx.Bell")
    dlg_editor_instance.updateFormulaMass()
    mock_bell.assert_called_once()
    assert dlg_editor_instance.itemMoMass_value.GetValue() == ""


def test_dlgCompoundsEditor_readLibraryXML(dlg_editor_instance):
    """Test parsing of compound library XML files."""
    xml_content = """<?xml version="1.0" encoding="utf-8" ?>
<mMassCompounds version="1.0">
  <group name="TestGroup">
    <compound name="C1" formula="H2O">Description 1</compound>
  </group>
</mMassCompounds>"""

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(xml_content)
        path = f.name

    try:
        data = dlg_editor_instance.readLibraryXML(path)
        assert "TestGroup" in data
        assert "C1" in data["TestGroup"]
        assert data["TestGroup"]["C1"].expression == "H2O"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_dlgCompoundsEditor_onImport_replace_logic(
    dlg_editor_instance, compounds_lib, mocker
):
    """Test the 'Replace/Skip/Replace All' logic during library import."""
    old_compound = mocker.Mock()
    old_compound.mass.return_value = (50.0, 50.1)
    old_compound.expression = "H2O"
    old_compound.description = "old"
    compounds_lib["Group1"] = {"old": old_compound}

    mock_file_dlg = mocker.patch("wx.FileDialog")
    mock_file_dlg.return_value.ShowModal.return_value = wx.ID_OK
    mock_file_dlg.return_value.GetPath.return_value = "dummy.xml"

    new_compound = mocker.Mock()
    new_compound.mass.return_value = (100.0, 100.1)
    new_compound.expression = "CO2"
    new_compound.description = "new"
    imported_items = {"Group1": {"new": new_compound}}

    mocker.patch.object(
        dlg_editor_instance, "readLibraryXML", return_value=imported_items
    )
    mock_select_dlg = mocker.patch("gui.dlg_compounds_editor.dlgSelectItemsToImport")
    mock_select_dlg.return_value.ShowModal.return_value = wx.ID_OK
    mock_select_dlg.return_value.selected = ["Group1"]

    # Test 'Replace'
    mock_msg = mocker.patch("gui.mwx.dlgMessage")
    mock_msg.return_value.ShowModal.return_value = ID_dlgReplace
    dlg_editor_instance.onImport(None)
    assert "new" in compounds_lib["Group1"]

    # Test 'Skip'
    compounds_lib["Group1"] = {"old": old_compound}
    mock_msg.return_value.ShowModal.return_value = ID_dlgSkip
    dlg_editor_instance.onImport(None)
    assert "old" in compounds_lib["Group1"]


def test_dlgCompoundsEditor_getItemData(dlg_editor_instance):
    """Test data extraction from editor fields."""
    # Scenario: Valid data
    dlg_editor_instance.itemName_value.SetValue("Water")
    dlg_editor_instance.itemFormula_value.SetValue("H2O")
    compound = dlg_editor_instance.getItemData()
    assert compound.name == "Water"
    assert compound.expression == "H2O"

    # Scenario: Missing name (should fail)
    dlg_editor_instance.itemName_value.SetValue("")
    assert dlg_editor_instance.getItemData() is False


def test_dlgCompoundsEditor_getNodeText(dlg_editor_instance, mocker):
    """Test the internal XML helper _getNodeText."""
    mock_node = mocker.Mock()
    mock_child1 = mocker.Mock()
    mock_child1.nodeType = 3  # Node.TEXT_NODE
    mock_child1.TEXT_NODE = 3
    mock_child1.data = "text1"
    mock_child2 = mocker.Mock()
    mock_child2.nodeType = 1  # Node.ELEMENT_NODE
    mock_child2.TEXT_NODE = 3
    mock_node.childNodes = [mock_child1, mock_child2]

    assert dlg_editor_instance._getNodeText(mock_node) == "text1"


def test_dlgCompoundsEditor_clearEditor(dlg_editor_instance):
    """Test clearing editor fields."""
    dlg_editor_instance.itemName_value.SetValue("Data")
    dlg_editor_instance.clearEditor()
    assert dlg_editor_instance.itemName_value.GetValue() == ""


def test_dlgCompoundsEditor_updateItemsMap(dlg_editor_instance, compounds_lib, mocker):
    """Test mapping of internal compound objects to list display format."""
    compound = mocker.Mock()
    compound.expression = "H2O"
    compound.description = "desc"
    compound.mass.return_value = (18.0, 18.1)

    compounds_lib["Group1"] = {"C1": compound}
    dlg_editor_instance.group = "Group1"

    dlg_editor_instance.updateItemsMap()
    assert len(dlg_editor_instance.itemsMap) == 1
    assert dlg_editor_instance.itemsMap[0] == ("C1", "H2O", 18.0, 18.1, "desc")


def test_dlgCompoundsEditor_readLibraryXML_errors(dlg_editor_instance):
    """Test error handling in XML reading."""
    # Case: File does not exist
    assert dlg_editor_instance.readLibraryXML("non_existent.xml") is False

    # Case: Invalid root tag
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("<wrong></wrong>")
        path = f.name
    try:
        assert dlg_editor_instance.readLibraryXML(path) is False
    finally:
        os.remove(path)


def test_dlgCompoundsEditor_onImport_edge_cases(dlg_editor_instance, mocker):
    """Test various FileDialog and logic edge cases in onImport."""
    # User cancels FileDialog
    mock_file_dlg = mocker.patch("wx.FileDialog")
    mock_file_dlg.return_value.ShowModal.return_value = wx.ID_CANCEL
    dlg_editor_instance.onImport(None)

    # Library format unrecognized
    mock_file_dlg.return_value.ShowModal.return_value = wx.ID_OK
    mock_file_dlg.return_value.GetPath.return_value = "dummy.xml"
    mocker.patch.object(dlg_editor_instance, "readLibraryXML", return_value=False)
    mock_msg = mocker.patch("gui.mwx.dlgMessage")
    dlg_editor_instance.onImport(None)
    mock_msg.assert_called()


def test_dlgCompoundsEditor_onFormulaEdited(dlg_editor_instance, mocker):
    """Test event handling for formula editing."""
    mock_call_after = mocker.patch("wx.CallAfter")
    evt = mocker.Mock()
    dlg_editor_instance.onFormulaEdited(evt)
    evt.Skip.assert_called_once()
    mock_call_after.assert_called_once_with(dlg_editor_instance.updateFormulaMass)
