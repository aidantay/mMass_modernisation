import os
import sys
import pytest
import wx

from gui.dlg_select_sequences import dlgSelectSequences

def mock_list_ctrl_factory(mocker, *args, **kwargs):
    """Factory to create a real ListCtrl with mocked methods."""
    lc = wx.ListCtrl(args[0], *args[1:], **kwargs)
    lc.setDataMap = mocker.Mock()
    lc.setAltColour = mocker.Mock()
    lc.sort = mocker.Mock()
    lc.getSelected = mocker.Mock(return_value=[])
    
    lc._item_data = {}
    def set_item_data(item, data):
        lc._item_data[item] = data
    def get_item_data(item):
        return lc._item_data.get(item)
    
    lc.SetItemData = mocker.Mock(side_effect=set_item_data)
    lc.GetItemData = mocker.Mock(side_effect=get_item_data)
    lc.InsertItem = mocker.Mock(return_value=0)
    lc.SetItem = mocker.Mock()
    lc.InsertColumn = mocker.Mock()
    lc.SetColumnWidth = mocker.Mock()
    
    return lc

@pytest.fixture
def mock_sequences(mocker):
    seq1 = mocker.Mock()
    seq1.accession = "ACC1"
    seq1.title = "Title 1"
    seq1.__len__ = mocker.Mock(return_value=100)
    
    seq2 = mocker.Mock()
    seq2.accession = None
    seq2.title = "Title 2"
    seq2.__len__ = mocker.Mock(return_value=200)
    
    seq3 = mocker.Mock()
    seq3.accession = "ACC3"
    seq3.title = "Title 3"
    seq3.__len__ = mocker.Mock(return_value=300)
    
    return [seq1, seq2, seq3]

@pytest.fixture
def dlg(wx_app, mock_sequences, mocker):
    # Patch mwx.sortListCtrl in the module where it's used
    mocker.patch('gui.dlg_select_sequences.mwx.sortListCtrl', 
                 side_effect=lambda *args, **kwargs: mock_list_ctrl_factory(mocker, *args, **kwargs))
    mocker.patch('wx.Dialog.EndModal')
    mocker.patch('wx.Bell')
    mocker.patch('wx.Dialog.Centre')
    mocker.patch('wx.Dialog.Fit')
    mocker.patch('wx.Dialog.Layout')
    
    parent = wx.Frame(None)
    dialog = dlgSelectSequences(parent, mock_sequences)
    yield dialog
    dialog.Destroy()
    parent.Destroy()

def test_init(dlg, mock_sequences):
    assert dlg.sequences == mock_sequences
    assert len(dlg.sequencesMap) == len(mock_sequences)
    # Check if updateSequenceList was called implicitly by checking setDataMap
    dlg.sequenceList.setDataMap.assert_called_with(dlg.sequencesMap)

def test_makeGUI(dlg):
    sizer = dlg.GetSizer()
    assert isinstance(sizer, wx.BoxSizer)
    assert sizer.GetOrientation() == wx.VERTICAL
    assert len(sizer.GetChildren()) == 2

def test_makeButtons(dlg):
    # Find buttons in the dialog
    cancel_butt = None
    import_butt = None
    
    for child in dlg.GetChildren():
        if isinstance(child, wx.Button):
            if child.GetId() == wx.ID_CANCEL:
                cancel_butt = child
            elif child.GetId() == wx.ID_OK:
                import_butt = child
    
    assert cancel_butt is not None
    assert cancel_butt.GetLabel() == "Cancel"
    assert import_butt is not None
    assert import_butt.GetLabel() == "Import"

def test_updateSequenceList_valid(dlg, mock_sequences):
    # Clear mocks to verify calls in updateSequenceList
    dlg.sequenceList.InsertItem.reset_mock()
    dlg.sequenceList.SetItem.reset_mock()
    dlg.sequenceList.SetItemData.reset_mock()
    
    dlg.updateSequenceList()
    
    assert dlg.sequenceList.InsertItem.call_count == len(mock_sequences)
    assert dlg.sequenceList.SetItem.call_count == len(mock_sequences) * 3
    assert dlg.sequenceList.SetItemData.call_count == len(mock_sequences)

def test_updateSequenceList_none_accession(dlg, mock_sequences):
    # sequence[1] has accession = None
    dlg.sequenceList.SetItem.reset_mock()
    dlg.updateSequenceList()
    
    calls = dlg.sequenceList.SetItem.call_args_list
    found = False
    for call in calls:
        args = call[0]
        if args[0] == 1 and args[1] == 1: # row 1, col 1
            assert args[2] == ''
            found = True
            break
    assert found

def test_updateSequenceList_empty(wx_app, mocker):
    mocker.patch('gui.dlg_select_sequences.mwx.sortListCtrl', 
                 side_effect=lambda *args, **kwargs: mock_list_ctrl_factory(mocker, *args, **kwargs))
    mocker.patch('wx.Dialog.EndModal')
    mocker.patch('wx.Dialog.Centre')
    mocker.patch('wx.Dialog.Fit')
    mocker.patch('wx.Dialog.Layout')

    parent = wx.Frame(None)
    dlg = dlgSelectSequences(parent, [])
    
    dlg.sequenceList.InsertItem.reset_mock()
    dlg.updateSequenceList()
    
    assert dlg.sequenceList.InsertItem.call_count == 0
    dlg.sequenceList.setDataMap.assert_called_with([])
    
    dlg.Destroy()
    parent.Destroy()

def test_onItemActivated(dlg, mocker):
    dlg.getSelecedSequences = mocker.Mock(return_value=[dlg.sequences[0]])
    
    evt = mocker.Mock()
    dlg.onItemActivated(evt)
    
    assert dlg.selected == [dlg.sequences[0]]
    dlg.EndModal.assert_called_once_with(wx.ID_OK)

def test_onImport_with_selection(dlg, mocker):
    dlg.getSelecedSequences = mocker.Mock(return_value=[dlg.sequences[0]])
    
    evt = mocker.Mock()
    dlg.onImport(evt)
    
    assert dlg.selected == [dlg.sequences[0]]
    dlg.EndModal.assert_called_once_with(wx.ID_OK)

def test_onImport_no_selection(dlg, mocker):
    dlg.getSelecedSequences = mocker.Mock(return_value=[])
    
    evt = mocker.Mock()
    dlg.onImport(evt)
    
    assert dlg.selected == []
    wx.Bell.assert_called_once()
    assert not dlg.EndModal.called

def test_getSelecedSequences(dlg, mock_sequences):
    # Set up selected items in the mock list control
    dlg.sequenceList.getSelected.return_value = [0, 2]
    dlg.sequenceList.SetItemData(0, 0)
    dlg.sequenceList.SetItemData(2, 2)
    
    selected = dlg.getSelecedSequences()
    
    assert len(selected) == 2
    assert selected[0] == mock_sequences[0]
    assert selected[1] == mock_sequences[2]
