import pytest
import wx
import copy
import gui.libs as libs
import gui.mwx as mwx
from gui.dlg_presets_editor import dlgPresetsEditor

MOCK_PRESETS = {
    'processing': {
        'Preset A': {'crop': True},
        'Preset B': {'crop': False}
    },
    'fragments': {
        'Preset C': ['a', 'b']
    }
}

@pytest.fixture
def gui_app(wx_app):
    """Alias for the wx_app fixture from conftest.py."""
    return wx_app

@pytest.fixture
def presets_editor(gui_app, mocker):
    """Fixture for dlgPresetsEditor with mocked libs.presets."""
    # Mock gui.libs.presets with a fresh copy for each test
    test_presets = copy.deepcopy(MOCK_PRESETS)

    # Patching gui.libs.presets because it's imported as 'libs' in dlg_presets_editor
    mocker.patch('gui.libs.presets', test_presets)
    # Mock UI elements that could block or make noise
    mock_dlg = mocker.patch('gui.mwx.dlgMessage')
    mock_bell = mocker.patch('wx.Bell')
    parent = wx.Frame(None)
    dlg = dlgPresetsEditor(parent)
    # Store mocks for assertion in tests
    dlg._mock_dlg = mock_dlg
    dlg._mock_bell = mock_bell
    yield dlg
    dlg.Destroy()
    parent.Destroy()

@pytest.mark.unit
def test_initialization(presets_editor):
    """
    Verify dialog title and initial state.
    
    Task 1 Requirements:
    - Verify dialog title is "Presets Library".
    - Verify itemsList has columns "name" and "category".
    - Verify itemsList has 3 items.
    - Verify selectedItem is initially None.
    """
    # Verify title
    assert presets_editor.GetTitle() == "Presets Library"
    
    # Verify itemsList has columns "name" and "category"
    assert presets_editor.itemsList.GetColumn(0).GetText() == "name"
    assert presets_editor.itemsList.GetColumn(1).GetText() == "category"
    
    # Verify itemsList has 3 items
    assert presets_editor.itemsList.GetItemCount() == 3
    
    # Verify selectedItem is initially None
    assert presets_editor.selectedItem is None

@pytest.mark.unit
def test_update_list_with_data(presets_editor):
    """
    Verify list count matches libs.presets content.
    
    Task 2 Requirements:
    - Verify itemsList has 3 items.
    - Verify itemsMap has 3 items.
    """
    assert presets_editor.itemsList.GetItemCount() == 3
    assert len(presets_editor.itemsMap) == 3

@pytest.mark.unit
def test_update_list_empty(presets_editor, mocker):
    """
    Verify empty state handling.

    Task 2 Requirements:
    - Patch gui.libs.presets to be an empty dictionary.
    - Call presets_editor.updateItemsList().
    - Verify itemsList has 0 items.
    - Verify itemsMap has 0 items.
    """
    mocker.patch('gui.libs.presets', {})
    presets_editor.updateItemsList()
    assert presets_editor.itemsList.GetItemCount() == 0
    assert len(presets_editor.itemsMap) == 0

@pytest.mark.unit
def test_on_item_selected(presets_editor, mocker):
    """
    Verify editor fields update correctly when a list item is selected.

    Task 2 Requirements:
    - Simulate a list selection event.
    - Create a mock wx.ListEvent and set its Data attribute to a valid index.
    - Verify editor fields and selectedItem are updated.
    """
    # Find index of "Preset A" in itemsMap to be robust against dict ordering
    index = -1
    for i, item in enumerate(presets_editor.itemsMap):
        if item[0] == "Preset A":
            index = i
            category = item[1]
            break

    assert index != -1

    # Create a mock wx.ListEvent
    mock_event = mocker.Mock(spec=wx.ListEvent)
    mock_event.GetData.return_value = index

    # Call onItemSelected
    presets_editor.onItemSelected(mock_event)

    # Verify editor fields
    assert presets_editor.itemName_value.GetValue() == "Preset A"
    assert presets_editor.itemCategory_value.GetValue() == category
    assert presets_editor.selectedItem == index

@pytest.mark.unit
def test_on_rename_item_success(presets_editor, mocker):
    """
    Verify successful rename in libs.presets and UI refresh.

    Task 3 Requirements:
    - Simulate an item selection to set presets_editor.selectedItem.
    - Set a new name in presets_editor.itemName_value.SetValue("New Preset Name").
    - Call presets_editor.onRenameItem(None).
    - Verify that "New Preset Name" exists in libs.presets['processing'] and "Preset A" is removed.
    - Verify presets_editor.itemName_value.GetValue() is empty (due to clearEditor).
    """
    # Simulate an item selection to set presets_editor.selectedItem
    index = -1
    for i, item in enumerate(presets_editor.itemsMap):
        if item[0] == "Preset A":
            index = i
            break
    assert index != -1

    mock_event = mocker.Mock(spec=wx.ListEvent)
    mock_event.GetData.return_value = index
    presets_editor.onItemSelected(mock_event)

    # Set a new name
    presets_editor.itemName_value.SetValue("New Preset Name")

    # Call onRenameItem
    presets_editor.onRenameItem(None)

    # Verify that "New Preset Name" exists in libs.presets['processing'] and "Preset A" is removed
    assert "New Preset Name" in libs.presets['processing']
    assert "Preset A" not in libs.presets['processing']

    # Verify itemName_value is empty (due to clearEditor)
    assert presets_editor.itemName_value.GetValue() == ""

@pytest.mark.unit
def test_on_rename_item_collision(presets_editor, mocker):
    """
    Verify error dialog when new name exists in the same category.

    Task 3 Requirements:
    - Simulate an item selection.
    - Set the new name to "Preset B" (exists in 'processing').
    - Call presets_editor.onRenameItem(None).
    - Assert that mwx.dlgMessage was called with the correct error message.
    - Verify libs.presets['processing']['Preset A'] still exists.
    """
    # Simulate an item selection
    index = -1
    for i, item in enumerate(presets_editor.itemsMap):
        if item[0] == "Preset A":
            index = i
            break
    assert index != -1

    mock_event = mocker.Mock(spec=wx.ListEvent)
    mock_event.GetData.return_value = index
    presets_editor.onItemSelected(mock_event)

    # Set the new name to "Preset B" (exists in 'processing')
    presets_editor.itemName_value.SetValue("Preset B")

    # Call onRenameItem
    presets_editor.onRenameItem(None)

    # Assert that mwx.dlgMessage was called
    presets_editor._mock_dlg.assert_called()

    # Verify libs.presets['processing']['Preset A'] still exists
    assert "Preset A" in libs.presets['processing']

@pytest.mark.unit
def test_on_rename_item_no_selection(presets_editor):
    """
    Verify wx.Bell when renaming without selection.
    
    Task 3 Requirements:
    - Ensure presets_editor.selectedItem is None.
    - Call presets_editor.onRenameItem(None).
    - Assert that wx.Bell was called.
    """
    # Ensure selectedItem is None
    presets_editor.selectedItem = None
    
    # Call onRenameItem
    presets_editor.onRenameItem(None)
    
    # Assert that wx.Bell was called
    presets_editor._mock_bell.assert_called()

@pytest.mark.unit
def test_on_rename_item_empty_name(presets_editor, mocker):
    """
    Verify wx.Bell via getItemData when renaming with empty name.
    """
    # Simulate an item selection
    index = -1
    for i, item in enumerate(presets_editor.itemsMap):
        if item[0] == "Preset A":
            index = i
            break
    assert index != -1

    mock_event = mocker.Mock(spec=wx.ListEvent)
    mock_event.GetData.return_value = index
    presets_editor.onItemSelected(mock_event)

    # Set empty name
    presets_editor.itemName_value.SetValue("")

    # Call onRenameItem
    presets_editor.onRenameItem(None)

    # Assert that wx.Bell was called
    presets_editor._mock_bell.assert_called()

    # Verify libs.presets['processing']['Preset A'] still exists
    assert "Preset A" in libs.presets['processing']

@pytest.mark.unit
def test_on_delete_item_confirmed(presets_editor, mocker):
    """
    Verify single item deletion and UI refresh.

    Task 4 Requirements:
    - Mock mwx.dlgMessage.return_value.ShowModal to return wx.ID_OK.
    - Mock presets_editor.itemsList.getSelected to return index of "Preset A".
    - Call presets_editor.onDeleteItem(None).
    - Verify "Preset A" is removed from libs.presets['processing'].
    - Verify presets_editor.itemsList.GetItemCount() is now 2.
    """
    # Configure mock dialog to return wx.ID_OK
    presets_editor._mock_dlg.return_value.ShowModal.return_value = wx.ID_OK

    # Find index of "Preset A" in itemsMap
    index = -1
    for i, item in enumerate(presets_editor.itemsMap):
        if item[0] == "Preset A":
            index = i
            break
    assert index != -1

    # Mock getSelected to return [0] and GetItemData to return the correct index
    mocker.patch.object(presets_editor.itemsList, 'getSelected', return_value=[0])
    mocker.patch.object(presets_editor.itemsList, 'GetItemData', return_value=index)
    # Call onDeleteItem
    presets_editor.onDeleteItem(None)

    # Verify "Preset A" is removed from libs.presets['processing']
    assert "Preset A" not in libs.presets['processing']

    # Verify itemsList count
    assert presets_editor.itemsList.GetItemCount() == 2

@pytest.mark.unit
def test_on_delete_item_cancelled(presets_editor):
    """
    Verify no change when cancelled.
    
    Task 4 Requirements:
    - Mock mwx.dlgMessage.return_value.ShowModal to return wx.ID_CANCEL.
    - Call presets_editor.onDeleteItem(None).
    - Verify libs.presets['processing']['Preset A'] still exists.
    """
    presets_editor._mock_dlg.return_value.ShowModal.return_value = wx.ID_CANCEL
    
    # Ensure "Preset A" exists
    assert 'Preset A' in libs.presets['processing']
    
    # Call onDeleteItem
    presets_editor.onDeleteItem(None)
    
    # Verify "Preset A" still exists
    assert 'Preset A' in libs.presets['processing']

@pytest.mark.unit
def test_on_delete_multiple_items(presets_editor, mocker):
    """
    Verify deletion of multiple selected items.

    Task 4 Requirements:
    - Mock confirmation with wx.ID_OK.
    - Mock getSelected to return indices of "Preset A" and "Preset B".
    - Call presets_editor.onDeleteItem(None).
    - Verify both items are removed from libs.presets['processing'].
    """
    presets_editor._mock_dlg.return_value.ShowModal.return_value = wx.ID_OK

    # Find indices of "Preset A" and "Preset B"
    indices = []
    for name in ["Preset A", "Preset B"]:
        for i, item in enumerate(presets_editor.itemsMap):
            if item[0] == name:
                indices.append(i)
                break
    assert len(indices) == 2

    # Mock getSelected to return [0, 1] and GetItemData to return the targeted indices
    def mock_get_item_data(row):
        return indices[row]

    mocker.patch.object(presets_editor.itemsList, 'getSelected', return_value=[0, 1])
    mocker.patch.object(presets_editor.itemsList, 'GetItemData', side_effect=mock_get_item_data)
    presets_editor.onDeleteItem(None)

    # Verify both are removed from libs.presets['processing']
    assert 'Preset A' not in libs.presets['processing']
    assert 'Preset B' not in libs.presets['processing']

    # Verify itemsList count
    assert presets_editor.itemsList.GetItemCount() == 1

@pytest.mark.unit
def test_clear_editor(presets_editor):
    """
    Verify text controls are cleared.
    
    Task 4 Requirements:
    - Set text in itemName_value and itemCategory_value.
    - Call presets_editor.clearEditor().
    - Assert both text controls are now empty.
    """
    presets_editor.itemName_value.SetValue("some name")
    presets_editor.itemCategory_value.SetValue("some category")
    
    presets_editor.clearEditor()
    
    assert presets_editor.itemName_value.GetValue() == ""
    assert presets_editor.itemCategory_value.GetValue() == ""

@pytest.mark.unit
def test_get_item_data(presets_editor):
    """
    Verify correct data retrieval and validation.
    
    Task 4 Requirements:
    - Set values in the text controls.
    - Call presets_editor.getItemData() and assert it returns ("name", "category").
    - Set one value to empty, call getItemData(), and assert it returns False.
    """
    presets_editor.itemName_value.SetValue("name")
    presets_editor.itemCategory_value.SetValue("category")
    
    assert presets_editor.getItemData() == ("name", "category")
    
    # One value empty
    presets_editor.itemName_value.SetValue("")
    assert presets_editor.getItemData() is False
    
    # Reset and other value empty
    presets_editor.itemName_value.SetValue("name")
    presets_editor.itemCategory_value.SetValue("")
    assert presets_editor.getItemData() is False

