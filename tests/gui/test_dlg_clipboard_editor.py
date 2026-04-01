import pytest
import wx
from gui.dlg_clipboard_editor import dlgClipboardEditor

@pytest.fixture
def dialog(wx_app):
    """Fixture to create the dialog."""
    # Ensure wx_app is initialized
    data = "123.456 789.012\n345.678 901.234"
    dlg = dlgClipboardEditor(None, data)
    yield dlg
    # Cleanup: destroy the dialog to free resources
    if dlg:
        dlg.Destroy()

def test_dlg_clipboard_editor_init(dialog):
    """Test that the dialog initializes correctly."""
    assert dialog.GetTitle() == "Import Data Points"
    # The value set in __init__
    expected_data = "123.456 789.012\n345.678 901.234"
    assert dialog.data_value.GetValue() == expected_data
    assert dialog.data == expected_data

def test_dlg_clipboard_editor_onOK_with_data(dialog, mocker):
    """Test onOK with data."""
    # Set text in the TextCtrl
    new_data = "111.222 333.444"
    dialog.data_value.SetValue(new_data)
    
    # Patch EndModal on the dialog instance
    mock_end_modal = mocker.patch.object(dialog, 'EndModal')
    
    # Call onOK directly with a dummy event
    dialog.onOK(None)
    
    # Verify self.data is updated and EndModal is called
    assert dialog.data == new_data
    mock_end_modal.assert_called_once_with(wx.ID_OK)

def test_dlg_clipboard_editor_onOK_empty_data(dialog, mocker):
    """Test onOK with empty data."""
    # Set empty text in the TextCtrl
    dialog.data_value.SetValue("")
    
    # Patch EndModal and wx.Bell
    mock_end_modal = mocker.patch.object(dialog, 'EndModal')
    mock_bell = mocker.patch('wx.Bell')
    
    # Call onOK
    dialog.onOK(None)
    
    # Verify EndModal is NOT called and wx.Bell is called
    assert dialog.data == ""
    mock_bell.assert_called_once()
    mock_end_modal.assert_not_called()

def test_dlg_clipboard_editor_replace_double_newline(wx_app):
    """Test that double newlines are replaced in __init__."""
    data = "data1\n\ndata2\n\n\ndata3"
    # "data1\n\ndata2\n\n\ndata3" -> "data1\ndata2\n\ndata3"
    # because it replaces '\n\n' with '\n'
    # Wait, "data1\n\ndata2" -> "data1\ndata2"
    # "\n\n\n" -> "\n\n"
    dlg = dlgClipboardEditor(None, data)
    expected = data.replace('\n\n', '\n')
    assert dlg.data == expected
    assert dlg.data_value.GetValue() == expected
    dlg.Destroy()
