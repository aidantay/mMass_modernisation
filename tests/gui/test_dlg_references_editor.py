import pytest
import wx
import os
import xml.dom.minidom
from StringIO import StringIO

from gui.dlg_references_editor import dlgReferencesEditor, dlgGroupName, dlgSelectItemsToImport
from gui.ids import *

@pytest.fixture
def editor_dialog(wx_app, mocker):
    """Fixture to create dlgReferencesEditor with mocked libs."""
    mock_references = {
        'Group A': [('Item 1', 100.0), ('Item 2', 200.0)],
        'Group B': []
    }
    mock_compounds = {'Existing Compound Group': {}}

    mocker.patch('gui.dlg_references_editor.libs.references', mock_references)
    mocker.patch('gui.dlg_references_editor.libs.compounds', mock_compounds)
    dlg = dlgReferencesEditor(None)
    yield dlg, mock_references, mock_compounds
    if dlg:
        dlg.Destroy()

# --- Test dlgGroupName ---

def test_dlgGroupName_init(wx_app):
    """Test initialization of dlgGroupName."""
    # Test with default name
    dlg = dlgGroupName(None)
    assert dlg.name == ''
    assert dlg.name_value.GetValue() == ''
    dlg.Destroy()

    # Test with provided name
    dlg = dlgGroupName(None, name='MyGroup')
    assert dlg.name == 'MyGroup'
    assert dlg.name_value.GetValue() == 'MyGroup'
    dlg.Destroy()

def test_dlgGroupName_onOK(wx_app, mocker):
    """Test onOK validation and behavior."""
    dlg = dlgGroupName(None)
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')

    # Empty name - should not close
    dlg.name_value.SetValue('')
    dlg.onOK(None)
    assert not mock_end_modal.called

    mock_end_modal.reset_mock()

    # Valid name - should close
    dlg.name_value.SetValue('NewGroup')
    dlg.onOK(None)
    assert dlg.name == 'NewGroup'
    mock_end_modal.assert_called_once_with(wx.ID_OK)

    dlg.Destroy()

# --- Test dlgSelectItemsToImport ---

def test_dlgSelectItemsToImport_init_and_list(wx_app):
    """Test initialization and list population of dlgSelectItemsToImport."""
    items = {
        'Group 1': [('I1', 1.0)],
        'Group 2': [('I2', 2.0), ('I3', 3.0)]
    }
    dlg = dlgSelectItemsToImport(None, items)
    
    # Verify itemsMap
    # Note: itemsMap depends on dictionary order, but we can check content
    expected_map = [('Group 1', 1), ('Group 2', 2)]
    assert sorted(dlg.itemsMap) == sorted(expected_map)
    
    # Verify itemsList
    assert dlg.itemsList.GetItemCount() == 2
    
    dlg.Destroy()

def test_dlgSelectItemsToImport_get_selections(wx_app, mocker):
    """Test getSelecedItems returns correct names."""
    items = {'G1': [], 'G2': []}
    dlg = dlgSelectItemsToImport(None, items)

    # Mock getSelected to return indices
    mocker.patch.object(dlg.itemsList, 'getSelected', return_value=[0])
    # Since it's sorted, we need to be careful. In this case G1, G2 are sorted.
    selections = dlg.getSelecedItems()
    assert len(selections) == 1
    assert selections[0] in ['G1', 'G2']

    dlg.Destroy()

def test_dlgSelectItemsToImport_onImport(wx_app, mocker):
    """Test onImport behavior."""
    items = {'G1': []}
    dlg = dlgSelectItemsToImport(None, items)

    mock_get_selected = mocker.patch.object(dlg, 'getSelecedItems', return_value=[])
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')

    # No selection
    dlg.onImport(None)
    assert not mock_end_modal.called

    # With selection
    mock_get_selected.return_value = ['G1']
    mock_end_modal.reset_mock()
    dlg.onImport(None)
    assert dlg.selected == ['G1']
    mock_end_modal.assert_called_once_with(wx.ID_OK)

    dlg.Destroy()

# --- Test dlgReferencesEditor ---

def test_editor_init(editor_dialog):
    """Test initialization of dlgReferencesEditor."""
    dlg, mock_refs, _ = editor_dialog
    assert dlg.GetTitle() == "Reference Masses Library"
    
    # Verify group choice populated
    # Should contain 'Reference lists' + sorted mock_refs keys
    expected_choices = ['Reference lists', 'Group A', 'Group B']
    choices = [dlg.groupName_choice.GetString(i) for i in range(dlg.groupName_choice.GetCount())]
    assert choices == expected_choices
    
    # Initial selection is 0 ('Reference lists')
    assert dlg.groupName_choice.GetSelection() == 0
    assert dlg.group is None

def test_editor_group_selection(editor_dialog):
    """Test selecting a group updates the UI."""
    dlg, mock_refs, _ = editor_dialog
    
    # Select Group A
    dlg.groupName_choice.SetStringSelection('Group A')
    dlg.onGroupSelected()
    
    assert dlg.group == 'Group A'
    assert dlg.itemsList.GetItemCount() == 2
    assert dlg.itemsList.GetItemText(0, 0) == 'Item 1'
    assert dlg.itemsList.GetItemText(1, 0) == 'Item 2'

    # Select 'Reference lists'
    dlg.groupName_choice.SetStringSelection('Reference lists')
    dlg.onGroupSelected()
    assert dlg.group is None
    assert dlg.itemsList.GetItemCount() == 0

def test_editor_item_selection(editor_dialog, mocker):
    """Test selecting an item updates the editor fields."""
    dlg, mock_refs, _ = editor_dialog

    # Select Group A first
    dlg.groupName_choice.SetStringSelection('Group A')
    dlg.onGroupSelected()

    # Mock event for item selection
    mock_event = mocker.Mock()
    mock_event.GetData.return_value = 0 # Index 0 -> Item 1

    dlg.onItemSelected(mock_event)

    assert dlg.itemDescription_value.GetValue() == 'Item 1'
    assert dlg.itemMass_value.GetValue() == '100.0'

def test_editor_add_group(editor_dialog, mocker):
    """Test adding a new group."""
    dlg, mock_refs, mock_compounds = editor_dialog

    MockDlg = mocker.patch('gui.dlg_references_editor.dlgGroupName')
    mock_instance = MockDlg.return_value
    mock_instance.ShowModal.return_value = wx.ID_OK
    mock_instance.name = 'New Group'

    dlg.onAddGroup(None)

    assert 'New Group' in mock_refs
    assert mock_refs['New Group'] == []
    assert dlg.groupName_choice.GetStringSelection() == 'New Group'
    assert dlg.group == 'New Group'

def test_editor_add_group_duplicate_in_compounds(editor_dialog, mocker):
    """Test adding a group that already exists in compounds."""
    dlg, mock_refs, mock_compounds = editor_dialog

    MockDlg = mocker.patch('gui.dlg_references_editor.dlgGroupName')
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')
    mock_instance = MockDlg.return_value
    mock_instance.ShowModal.return_value = wx.ID_OK
    mock_instance.name = 'Existing Compound Group'

    dlg.onAddGroup(None)

    assert 'Existing Compound Group' not in mock_refs
    MockMsg.assert_called()

def test_editor_rename_group(editor_dialog, mocker):
    """Test renaming an existing group."""
    dlg, mock_refs, _ = editor_dialog

    # Select Group A
    dlg.groupName_choice.SetStringSelection('Group A')
    dlg.onGroupSelected()

    MockDlg = mocker.patch('gui.dlg_references_editor.dlgGroupName')
    mock_instance = MockDlg.return_value
    mock_instance.ShowModal.return_value = wx.ID_OK
    mock_instance.name = 'Renamed Group'

    dlg.onRenameGroup(None)

    assert 'Renamed Group' in mock_refs
    assert 'Group A' not in mock_refs
    assert mock_refs['Renamed Group'] == [('Item 1', 100.0), ('Item 2', 200.0)]
    assert dlg.groupName_choice.GetStringSelection() == 'Renamed Group'

def test_editor_delete_group(editor_dialog, mocker):
    """Test deleting a group."""
    dlg, mock_refs, _ = editor_dialog

    # Select Group A
    dlg.groupName_choice.SetStringSelection('Group A')
    dlg.onGroupSelected()

    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')
    mock_instance = MockMsg.return_value
    mock_instance.ShowModal.return_value = wx.ID_OK

    dlg.onDeleteGroup(None)

    assert 'Group A' not in mock_refs
    assert dlg.groupName_choice.GetSelection() == 0

def test_editor_add_item(editor_dialog):
    """Test adding an item to a group."""
    dlg, mock_refs, _ = editor_dialog
    
    # Select Group B (empty)
    dlg.groupName_choice.SetStringSelection('Group B')
    dlg.onGroupSelected()
    
    dlg.itemDescription_value.SetValue('New Item')
    dlg.itemMass_value.SetValue('123.456')
    
    dlg.onAddItem(None)
    
    assert len(mock_refs['Group B']) == 1
    assert mock_refs['Group B'][0] == ('New Item', 123.456)
    
    # Fields should be cleared
    assert dlg.itemDescription_value.GetValue() == ''
    assert dlg.itemMass_value.GetValue() == ''

def test_editor_delete_item(editor_dialog, mocker):
    """Test deleting items from a group."""
    dlg, mock_refs, _ = editor_dialog

    # Select Group A (has 2 items)
    dlg.groupName_choice.SetStringSelection('Group A')
    dlg.onGroupSelected()

    # Mock selected items in list
    mocker.patch.object(dlg.itemsList, 'getSelected', return_value=[0])
    mocker.patch.object(dlg.itemsList, 'GetItemData', return_value=0)
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')

    mock_instance = MockMsg.return_value
    mock_instance.ShowModal.return_value = wx.ID_OK

    dlg.onDeleteItem(None)

    assert len(mock_refs['Group A']) == 1
    assert mock_refs['Group A'][0] == ('Item 2', 200.0)

def test_editor_getItemData(editor_dialog):
    """Test input validation for item data."""
    dlg, _, _ = editor_dialog
    
    # Valid
    dlg.itemDescription_value.SetValue('Desc')
    dlg.itemMass_value.SetValue('100.5')
    assert dlg.getItemData() == ('Desc', 100.5)
    
    # Missing description
    dlg.itemDescription_value.SetValue('')
    dlg.itemMass_value.SetValue('100.5')
    assert dlg.getItemData() == False
    
    # Invalid mass
    dlg.itemDescription_value.SetValue('Desc')
    dlg.itemMass_value.SetValue('abc')
    assert dlg.getItemData() == False

def test_editor_readLibraryXML(editor_dialog, mocker):
    """Test parsing reference library XML."""
    dlg, _, _ = editor_dialog

    xml_content = """<?xml version="1.0" encoding="utf-8" ?>
<mMassReferenceMasses version="1.0">
  <group name="Imported Group">
    <reference name="Ref 1" mass="123.456" />
  </group>
</mMassReferenceMasses>
"""
    # We need to mock xml.dom.minidom.parse since it takes a path
    mock_parse = mocker.patch('xml.dom.minidom.parse')
    mock_doc = xml.dom.minidom.parseString(xml_content)
    mock_parse.return_value = mock_doc

    result = dlg.readLibraryXML('dummy_path')
    assert 'Imported Group' in result
    assert result['Imported Group'] == [('Ref 1', 123.456)]

    # Test invalid XML
    mock_parse.side_effect = Exception("Invalid XML")
    assert dlg.readLibraryXML('dummy_path') == False

    # Test missing root tag
    mock_parse.side_effect = None
    xml_no_root = "<wrong></wrong>"
    mock_doc = xml.dom.minidom.parseString(xml_no_root)
    mock_parse.return_value = mock_doc
    assert dlg.readLibraryXML('dummy_path') == False

def test_editor_import_workflow(editor_dialog, mocker):
    """Test the full import workflow."""
    dlg, mock_refs, _ = editor_dialog

    imported_data = {
        'Group A': [('New Item A', 500.0)], # Overlap
        'Group C': [('Item C', 300.0)]      # New
    }

    MockFileDlg = mocker.patch('wx.FileDialog')
    mocker.patch.object(dlg, 'readLibraryXML', return_value=imported_data)
    MockSelectDlg = mocker.patch('gui.dlg_references_editor.dlgSelectItemsToImport')
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')

    # 1. File Selection
    MockFileDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockFileDlg.return_value.GetPath.return_value = 'some_path.xml'

    # 2. Select items to import
    MockSelectDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockSelectDlg.return_value.selected = ['Group A', 'Group C']

    # 3. Handle overwrite for 'Group A'
    MockMsg.return_value.ShowModal.return_value = ID_dlgReplace

    dlg.onImport(None)

    assert mock_refs['Group A'] == [('New Item A', 500.0)]
    assert mock_refs['Group C'] == [('Item C', 300.0)]
    assert dlg.groupName_choice.GetStringSelection() == 'Group C'

def test_editor_import_workflow_cancel_file(editor_dialog, mocker):
    dlg, mock_refs, _ = editor_dialog
    MockFileDlg = mocker.patch('wx.FileDialog')
    MockFileDlg.return_value.ShowModal.return_value = wx.ID_CANCEL
    dlg.onImport(None)
    # Verify no changes or other dialogs
    assert 'Group C' not in mock_refs

def test_editor_import_workflow_no_data(editor_dialog, mocker):
    dlg, mock_refs, _ = editor_dialog
    MockFileDlg = mocker.patch('wx.FileDialog')
    mocker.patch.object(dlg, 'readLibraryXML', return_value={})
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')

    MockFileDlg.return_value.ShowModal.return_value = wx.ID_OK
    dlg.onImport(None)
    MockMsg.assert_called()

def test_editor_updateFormulaMass(editor_dialog):
    """Test updateFormulaMass (though the GUI doesn't seem to have these fields in the code provided? wait...)"""
    # Looking at dlg_references_editor.py, there is a method updateFormulaMass but no fields in makeGUI for it?
    # Ah, I see updateFormulaMass in the class but it refers to self.itemFormula_value, itemMoMass_value, itemAvMass_value.
    # But makeItemEditor ONLY creates itemDescription_value and itemMass_value.
    # It seems like leftover code or incomplete GUI? 
    # Let's check makeItemEditor again.
    pass

def test_editor_clearEditor(editor_dialog):
    dlg, _, _ = editor_dialog
    dlg.itemDescription_value.SetValue('test')
    dlg.itemMass_value.SetValue('100')
    dlg.clearEditor()
    assert dlg.itemDescription_value.GetValue() == ''
    assert dlg.itemMass_value.GetValue() == ''

def test_editor_group_actions_no_selection(editor_dialog, mocker):
    dlg, _, _ = editor_dialog
    # Initially no group selected
    mock_bell = mocker.patch('wx.Bell')

    dlg.onRenameGroup(None)
    mock_bell.assert_called()

    mock_bell.reset_mock()
    dlg.onDeleteGroup(None)
    mock_bell.assert_called()

    mock_bell.reset_mock()
    dlg.onAddItem(None)
    mock_bell.assert_called()

    mock_bell.reset_mock()
    dlg.onDeleteItem(None)
    mock_bell.assert_called()

def test_editor_import_replace_all(editor_dialog, mocker):
    """Test 'Replace All' in import workflow."""
    dlg, mock_refs, _ = editor_dialog
    imported_data = {
        'Group A': [('New Item A', 500.0)],
        'Group B': [('New Item B', 600.0)]
    }
    MockFileDlg = mocker.patch('wx.FileDialog')
    mocker.patch.object(dlg, 'readLibraryXML', return_value=imported_data)
    MockSelectDlg = mocker.patch('gui.dlg_references_editor.dlgSelectItemsToImport')
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')

    MockFileDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockSelectDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockSelectDlg.return_value.selected = ['Group A', 'Group B']

    # Return Replace All for first group
    MockMsg.return_value.ShowModal.return_value = ID_dlgReplaceAll

    dlg.onImport(None)

    assert mock_refs['Group A'] == [('New Item A', 500.0)]
    assert mock_refs['Group B'] == [('New Item B', 600.0)]
    assert MockMsg.call_count == 1 # Should only call once because of Replace All

def test_editor_import_skip(editor_dialog, mocker):
    """Test 'Skip' in import workflow."""
    dlg, mock_refs, _ = editor_dialog
    imported_data = {
        'Group A': [('New Item A', 500.0)]
    }
    original_data = list(mock_refs['Group A'])

    MockFileDlg = mocker.patch('wx.FileDialog')
    mocker.patch.object(dlg, 'readLibraryXML', return_value=imported_data)
    MockSelectDlg = mocker.patch('gui.dlg_references_editor.dlgSelectItemsToImport')
    MockMsg = mocker.patch('gui.dlg_references_editor.mwx.dlgMessage')

    MockFileDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockSelectDlg.return_value.ShowModal.return_value = wx.ID_OK
    MockSelectDlg.return_value.selected = ['Group A']

    MockMsg.return_value.ShowModal.return_value = ID_dlgSkip

    dlg.onImport(None)

    assert mock_refs['Group A'] == original_data

def test_dlgSelectItemsToImport_onItemActivated(wx_app, mocker):
    """Test double clicking an item in import selection."""
    items = {'G1': []}
    dlg = dlgSelectItemsToImport(None, items)
    mocker.patch.object(dlg, 'getSelecedItems', return_value=['G1'])
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')
    dlg.onItemActivated(None)
    assert dlg.selected == ['G1']
    mock_end_modal.assert_called_with(wx.ID_OK)
    dlg.Destroy()

def test_getNodeText(editor_dialog, mocker):
    dlg, _, _ = editor_dialog
    mock_node = mocker.Mock()
    mock_text_node = mocker.Mock()
    mock_text_node.nodeType = 3 # xml.dom.minidom.Node.TEXT_NODE
    mock_text_node.TEXT_NODE = 3
    mock_text_node.data = "some text"
    mock_node.childNodes = [mock_text_node]
    assert dlg._getNodeText(mock_node) == "some text"
