import sys
import os
import pytest
import wx
from gui import mwx
from gui import libs
from gui.dlg_mascot_editor import dlgMascotEditor

@pytest.fixture
def dialog_fixture(mocker, wx_app):
    """Fixture to setup and teardown the dlgMascotEditor."""
    
    # Mock libs.mascot
    mock_mascot = {
        'Server A': {
            'protocol': 'http',
            'host': 'hostA',
            'path': 'pathA',
            'search': 'searchA',
            'results': 'resultsA',
            'export': 'exportA',
            'params': 'paramsA'
        }
    }
    mocker.patch.dict('gui.libs.mascot', mock_mascot, clear=True)

    # Mock wx components to prevent actual GUI creation
    mocker.patch('wx.Dialog.__init__', return_value=None)
    mocker.patch('wx.Dialog.Layout')
    mocker.patch('wx.Dialog.Fit')
    mocker.patch('wx.Dialog.SetSizer')
    mocker.patch('wx.Dialog.GetSize', return_value=(800, 600))
    mocker.patch('wx.Dialog.SetMinSize')
    mocker.patch('wx.Dialog.Centre')
    mocker.patch('wx.Dialog.SetFont')
    mocker.patch('wx.Dialog.Bind')

    # Mock other wx classes
    mocker.patch('wx.BoxSizer')
    mocker.patch('wx.StaticBoxSizer')
    mocker.patch('wx.StaticBox')
    mocker.patch('wx.StaticText')
    mocker.patch('wx.TextCtrl', side_effect=lambda *args, **kwargs: mocker.Mock())
    mocker.patch('wx.Button')
    mocker.patch('wx.GridBagSizer')
    mocker.patch('wx.Bell')

    # Mock mwx components
    # We patch them in the gui.mwx module which is what's being used
    mocker.patch('gui.mwx.sortListCtrl')
    mocker.patch('gui.mwx.dlgMessage')

    # Mock parent
    parent = mocker.Mock()

    # Spy on updateItemsList
    mocker.spy(dlgMascotEditor, 'updateItemsList')

    # Instantiate dialog
    dialog = dlgMascotEditor(parent)
    
    return dialog, parent

def test_dialog_initialization(dialog_fixture):
    """Verify that the dialog is correctly initialized."""
    dialog, parent = dialog_fixture
    
    # Verify that wx.Dialog.__init__ was called correctly
    # Note: When using super().__init__ in the implementation, the mock
    # receives the call. Depending on how it's called, self might be present or not.
    # In the actual output, it seems self was not captured in the way expected by assert_called_once_with.
    # We use ANY for the first argument if it's self, or just check the other args.
    wx.Dialog.__init__.assert_called_once_with(
        parent, id=wx.ID_ANY, title="Mascot Servers Library", 
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    
    # Verify that the dialog's updateItemsList method was called once on initialization
    assert dialog.updateItemsList.call_count == 1
    
    # Verify that the itemsList mock's setDataMap method was called with the initial data
    expected_map = [('Server A', 'hostA', 'pathA')]
    dialog.itemsList.setDataMap.assert_called_once_with(expected_map)
    
    # Verify that InsertItem was called for each server in the initial set
    # In our fixture, we have only 'Server A'
    dialog.itemsList.InsertItem.assert_called_once_with(0, 'Server A')
    dialog.itemsList.SetItem.assert_any_call(0, 1, 'hostA')
    dialog.itemsList.SetItem.assert_any_call(0, 2, 'pathA')

def test_on_item_selected(dialog_fixture, mocker):
    """Verify that onItemSelected updates the editor with server data."""
    dialog, parent = dialog_fixture
    
    # Configure the mock event object
    mock_event = mocker.Mock()
    mock_event.GetText.return_value = 'Server A'
    
    # Call onItemSelected
    dialog.onItemSelected(mock_event)
    
    # Assert that editor fields were updated with 'Server A' data
    dialog.itemName_value.SetValue.assert_called_with('Server A')
    dialog.itemHost_value.SetValue.assert_called_with('hostA')
    dialog.itemPath_value.SetValue.assert_called_with('pathA')
    dialog.itemSearch_value.SetValue.assert_called_with('searchA')
    dialog.itemResults_value.SetValue.assert_called_with('resultsA')
    dialog.itemExport_value.SetValue.assert_called_with('exportA')
    dialog.itemParams_value.SetValue.assert_called_with('paramsA')

def test_on_add_item_new(dialog_fixture, mocker):
    """Verify that a new server can be added."""
    dialog, parent = dialog_fixture
    
    # Mock getItemData to return new server data
    new_server_data = {
        'host': 'hostNew',
        'path': 'pathNew',
        'search': 'searchNew',
        'results': 'resultsNew',
        'export': 'exportNew',
        'params': 'paramsNew'
    }
    mocker.patch.object(dialog, 'getItemData', return_value=new_server_data)
    
    # Mock itemName_value.GetValue to return 'New Server'
    dialog.itemName_value.GetValue.return_value = 'New Server'
    
    # Spy on clearEditor
    mocker.spy(dialog, 'clearEditor')
    
    # Call onAddItem
    dialog.onAddItem(None)
    
    # Assert that the new server exists in libs.mascot
    assert 'New Server' in libs.mascot
    assert libs.mascot['New Server'] == new_server_data
    
    # Assert that updateItemsList and clearEditor were called
    assert dialog.updateItemsList.call_count == 2 # 1 (init) + 1 (onAddItem)
    assert dialog.clearEditor.call_count == 1

def test_on_add_item_replace_confirm(dialog_fixture, mocker):
    """Verify that an existing server can be replaced after confirmation."""
    dialog, parent = dialog_fixture
    
    # Mock getItemData to return updated server data for 'Server A'
    updated_server_data = {
        'host': 'hostA_updated',
        'path': 'pathA_updated',
        'search': 'searchA_updated',
        'results': 'resultsA_updated',
        'export': 'exportA_updated',
        'params': 'paramsA_updated'
    }
    mocker.patch.object(dialog, 'getItemData', return_value=updated_server_data)
    
    # Mock itemName_value.GetValue to return 'Server A'
    dialog.itemName_value.GetValue.return_value = 'Server A'
    
    # Mock mwx.dlgMessage to confirm replacement
    mock_dlg = mocker.Mock()
    mock_dlg.ShowModal.return_value = wx.ID_OK
    mocker.patch('gui.mwx.dlgMessage', return_value=mock_dlg)
    
    # Call onAddItem
    dialog.onAddItem(None)
    
    # Assert that the server data was updated in libs.mascot
    assert libs.mascot['Server A'] == updated_server_data
    
    # Assert that mwx.dlgMessage was instantiated and Destroy was called
    mwx.dlgMessage.assert_called_once()
    mock_dlg.Destroy.assert_called_once()

def test_on_add_item_replace_cancel(dialog_fixture, mocker):
    """Verify that replacement can be canceled."""
    dialog, parent = dialog_fixture
    
    original_data = libs.mascot['Server A'].copy()
    
    # Mock getItemData to return updated server data
    updated_server_data = {'host': 'new_host'} # simplified for test
    mocker.patch.object(dialog, 'getItemData', return_value=updated_server_data)
    
    # Mock itemName_value.GetValue to return 'Server A'
    dialog.itemName_value.GetValue.return_value = 'Server A'
    
    # Mock mwx.dlgMessage to cancel replacement
    mock_dlg = mocker.Mock()
    mock_dlg.ShowModal.return_value = wx.ID_CANCEL
    mocker.patch('gui.mwx.dlgMessage', return_value=mock_dlg)
    
    # Call onAddItem
    dialog.onAddItem(None)
    
    # Assert that the original server data remains unchanged
    assert libs.mascot['Server A'] == original_data
    
    # Assert that Destroy was called on the dialog
    mock_dlg.Destroy.assert_called_once()

def test_on_add_item_invalid_data(dialog_fixture, mocker):
    """Verify that invalid data (missing required fields) is handled."""
    dialog, parent = dialog_fixture
    
    initial_count = len(libs.mascot)
    
    # Mock getItemData to return False (invalid data)
    mocker.patch.object(dialog, 'getItemData', return_value=False)
    
    # Call onAddItem
    dialog.onAddItem(None)
    
    # Assert that libs.mascot was not modified
    assert len(libs.mascot) == initial_count

def test_on_delete_item_confirm(dialog_fixture, mocker):
    """Verify that selected items are deleted after confirmation."""
    dialog, parent = dialog_fixture
    
    # Ensure 'Server A' is in libs.mascot
    assert 'Server A' in libs.mascot
    
    # Mock itemsList.getSelected to return index 0
    dialog.itemsList.getSelected.return_value = [0]
    
    # Mock itemsList.GetItemData(0) to return 0 (which points to 'Server A' in itemsMap)
    dialog.itemsList.GetItemData.return_value = 0
    
    # Mock mwx.dlgMessage to confirm deletion
    mock_dlg = mocker.Mock()
    mock_dlg.ShowModal.return_value = wx.ID_OK
    mocker.patch('gui.mwx.dlgMessage', return_value=mock_dlg)
    
    # Spy on clearEditor
    mocker.spy(dialog, 'clearEditor')
    
    # Call onDeleteItem
    dialog.onDeleteItem(None)
    
    # Assert that 'Server A' has been removed from libs.mascot
    assert 'Server A' not in libs.mascot
    
    # Assert that updateItemsList and clearEditor were called
    assert dialog.updateItemsList.call_count == 2 # 1 (init) + 1 (onDeleteItem)
    assert dialog.clearEditor.call_count == 1
    
    # Assert that Destroy was called on the dialog
    mock_dlg.Destroy.assert_called_once()

def test_on_delete_item_cancel(dialog_fixture, mocker):
    """Verify that deletion can be canceled."""
    dialog, parent = dialog_fixture
    
    # Ensure 'Server A' is in libs.mascot
    assert 'Server A' in libs.mascot
    
    # Mock itemsList.getSelected to return index 0
    dialog.itemsList.getSelected.return_value = [0]
    
    # Mock mwx.dlgMessage to cancel deletion
    mock_dlg = mocker.Mock()
    mock_dlg.ShowModal.return_value = wx.ID_CANCEL
    mocker.patch('gui.mwx.dlgMessage', return_value=mock_dlg)
    
    # Call onDeleteItem
    dialog.onDeleteItem(None)
    
    # Assert that 'Server A' is still in libs.mascot
    assert 'Server A' in libs.mascot
    
    # Assert that updateItemsList was not called again
    assert dialog.updateItemsList.call_count == 1 # only init
    
    # Assert that Destroy was called on the dialog
    mock_dlg.Destroy.assert_called_once()

def test_clear_editor(dialog_fixture):
    """Verify that clearEditor resets the editor fields."""
    dialog, parent = dialog_fixture
    
    # Call clearEditor
    dialog.clearEditor()
    
    # Verify that SetValue was called on each editor text control mock with correct defaults
    dialog.itemName_value.SetValue.assert_any_call('')
    dialog.itemHost_value.SetValue.assert_any_call('')
    dialog.itemPath_value.SetValue.assert_any_call('/')
    dialog.itemSearch_value.SetValue.assert_any_call('cgi/nph-mascot.exe')
    dialog.itemResults_value.SetValue.assert_any_call('cgi/master_results.pl')
    dialog.itemExport_value.SetValue.assert_any_call('cgi/export_dat_2.pl')
    dialog.itemParams_value.SetValue.assert_any_call('cgi/get_params.pl')

def test_get_item_data_success(dialog_fixture):
    """Verify that getItemData returns correct server data when all fields are valid."""
    dialog, parent = dialog_fixture
    
    # Set return values for GetValue mocks
    dialog.itemName_value.GetValue.return_value = 'New Server'
    dialog.itemHost_value.GetValue.return_value = 'new.host'
    dialog.itemPath_value.GetValue.return_value = '/new/path'
    dialog.itemSearch_value.GetValue.return_value = 'new_search'
    dialog.itemResults_value.GetValue.return_value = 'new_results'
    dialog.itemExport_value.GetValue.return_value = 'new_export'
    dialog.itemParams_value.GetValue.return_value = 'new_params'
    
    # Call getItemData
    result = dialog.getItemData()
    
    # Assert that the returned dictionary matches the input values (minus name)
    expected = {
        'host': 'new.host',
        'path': '/new/path',
        'search': 'new_search',
        'results': 'new_results',
        'export': 'new_export',
        'params': 'new_params',
    }
    assert result == expected

def test_get_item_data_fail(dialog_fixture):
    """Verify that getItemData returns False and rings bell when a field is empty."""
    dialog, parent = dialog_fixture
    
    # Set one GetValue mock to return an empty string
    dialog.itemName_value.GetValue.return_value = ''
    dialog.itemHost_value.GetValue.return_value = 'some.host'
    
    # Call getItemData
    result = dialog.getItemData()
    
    # Assert that the function returns False
    assert result is False
    
    # Assert that wx.Bell was called
    wx.Bell.assert_called_once()
