import sys
import os
import datetime
import pytest
import wx

import mspy.plot
from gui.dlg_select_scans import dlgSelectScans
import gui.mwx as mwx

def mock_list_ctrl_factory(mocker, *args, **kwargs):
    """Factory to create a real ListCtrl with mocked methods."""
    lc = wx.ListCtrl(args[0], *args[1:], **kwargs)
    lc.setDataMap = mocker.Mock()
    lc.setAltColour = mocker.Mock()
    lc.sort = mocker.Mock()
    lc.unselectAll = mocker.Mock()
    lc.InsertColumn = mocker.Mock()
    lc.SetColumnWidth = mocker.Mock()
    lc.InsertItem = mocker.Mock(return_value=0)
    lc.SetItem = mocker.Mock()
    lc.SetItemData = mocker.Mock()
    lc.GetNextItem = mocker.Mock(return_value=-1)
    lc.GetItem = mocker.Mock()
    lc.EnsureVisible = mocker.Mock()
    return lc

def mock_canvas_factory(mocker, *args, **kwargs):
    """Factory to create a real Panel with mocked methods."""
    c = wx.Panel(args[0], *args[1:], **kwargs)
    c.setProperties = mocker.Mock()
    c.setLMBFunction = mocker.Mock()
    c.setMFunction = mocker.Mock()
    c.draw = mocker.Mock()
    c.highlightXPoints = mocker.Mock()
    c.getCursorPosition = mocker.Mock(return_value=(10.0, 1000.0))
    c.onLMU = mocker.Mock()
    return c

@pytest.fixture
def mock_scans():
    """Mock scans data (multiple MS1 and one MS2)."""
    scans = {}
    # Create 12 MS1 scans to trigger chromatogram plot (> 10)
    for i in range(1, 13):
        scans[i] = {
            'scanNumber': i,
            'retentionTime': i * 60.0, # 1 to 12 minutes
            'msLevel': 1,
            'precursorMZ': None,
            'precursorCharge': None,
            'lowMZ': 100.0,
            'highMZ': 1000.0,
            'totIonCurrent': 10000.0 * i,
            'pointsCount': 500,
            'spectrumType': 'Centroid',
            'polarity': 1,
            'basePeakIntensity': 5000.0 * i
        }
    
    # Add an MS2 scan with precursor
    scans[13] = {
        'scanNumber': 13,
        'retentionTime': 800.0, # ~13.3 min
        'msLevel': 2,
        'precursorMZ': 500.1234,
        'precursorCharge': 2,
        'lowMZ': 50.0,
        'highMZ': 1500.0,
        'totIonCurrent': 5000.0,
        'pointsCount': 200,
        'spectrumType': 'Centroid',
        'polarity': -1, # negative
        'basePeakIntensity': 2500.0
    }
    return scans

@pytest.fixture
def dlg(wx_app, mock_scans, mocker):
    """Fixture to set up dlgSelectScans with mocked dependencies."""
    
    # Mock config
    mocker.patch('gui.dlg_select_scans.config.spectrum', {
        'showMinorTicks': True,
        'axisFontSize': 10,
        'labelFontSize': 10,
        'tickColour': [0, 0, 0]
    })
    mocker.patch('gui.dlg_select_scans.config.main', {
        'reverseScrolling': False
    })
    mocker.patch('gui.dlg_select_scans.config.colours', [[255, 0, 0], [0, 255, 0]])

    # Patch mwx.sortListCtrl to return a real ListCtrl but with mock methods
    mocker.patch('gui.dlg_select_scans.mwx.sortListCtrl', side_effect=lambda *a, **k: mock_list_ctrl_factory(mocker, *a, **k))

    # Patch mspy.plot.canvas to return a real Panel but with mock methods
    mocker.patch('gui.dlg_select_scans.mspy.plot.canvas', side_effect=lambda *a, **k: mock_canvas_factory(mocker, *a, **k))
    
    # Patch points and container
    mocker.patch('gui.dlg_select_scans.mspy.plot.points', return_value=mocker.Mock())
    mocker.patch('gui.dlg_select_scans.mspy.plot.container', return_value=mocker.Mock())
    
    # Patch wx methods
    mocker.patch('wx.Dialog.EndModal')
    mocker.patch('wx.Bell')
    
    parent = wx.Frame(None)
    dialog = dlgSelectScans(parent, mock_scans)
    
    yield dialog
    
    if dialog:
        dialog.Destroy()
    parent.Destroy()

def test_init(dlg, mock_scans):
    """Test initialization of dlgSelectScans (Step 2)."""
    assert dlg.scans == mock_scans
    assert dlg.selected is None
    
    # Since we have 12 MS1 scans, showChromCanvas should be True
    assert dlg.showChromCanvas is True
    
    # Check if UI components are created
    assert isinstance(dlg.scanList, wx.ListCtrl)
    assert isinstance(dlg.chromCanvas, wx.Panel)
    
    # Verify that updateScanList and updateChromPlot were called during __init__
    assert dlg.scanList.setDataMap.called
    assert dlg.scanList.sort.called
    
    assert dlg.chromCanvas.setProperties.called
    assert dlg.chromCanvas.draw.called

def test_gui_structure(dlg):
    """Verify GUI structure and sizer configuration (Step 2)."""
    sizer = dlg.GetSizer()
    assert isinstance(sizer, wx.BoxSizer)
    
    # Children: scanList, spacer, chromCanvas, buttons_sizer
    # Wait, makeGUI adds:
    # sizer.Add(self.scanList, ...)
    # sizer.AddSpacer(3)
    # sizer.Add(self.chromCanvas, ...)
    # sizer.Add(buttons, ...)
    assert sizer.GetItemCount() == 4
    
    # Check minimum size is set
    assert dlg.GetMinSize().GetWidth() > 0
    assert dlg.GetMinSize().GetHeight() > 0

def test_makeButtons(dlg):
    """Verify buttons are created correctly (Step 2)."""
    # Find buttons only among children of this dialog
    cancel_butt = None
    ok_butt = None
    for child in dlg.GetChildren():
        if child.GetId() == wx.ID_CANCEL:
            cancel_butt = child
        elif child.GetId() == wx.ID_OK:
            ok_butt = child
    
    assert isinstance(cancel_butt, wx.Button)
    assert isinstance(ok_butt, wx.Button)
    assert cancel_butt.GetLabel() == "Cancel"
    assert ok_butt.GetLabel() == "Open Selected"

def test_updateScanList_valid(dlg, mock_scans):
    """Test updateScanList with valid scan data (Step 3)."""
    # Reset mocks to clear calls from __init__
    dlg.scanList.setDataMap.reset_mock()
    dlg.scanList.InsertItem.reset_mock()
    dlg.scanList.SetItem.reset_mock()
    
    dlg.updateScanList()
    
    assert dlg.scanList.setDataMap.called
    # 13 scans in mock_scans
    assert dlg.scanList.InsertItem.call_count == 13
    # 8 columns set via SetItem for each row (columns 1-8)
    assert dlg.scanList.SetItem.call_count == 13 * 8

def test_updateScanList_none_values(wx_app, mocker):
    """Test updateScanList with None values in scan data (Step 3)."""
    scans = {
        1: {
            'scanNumber': 1,
            'retentionTime': None,
            'msLevel': None,
            'precursorMZ': None,
            'precursorCharge': None,
            'lowMZ': None,
            'highMZ': None,
            'totIonCurrent': None,
            'pointsCount': None,
            'spectrumType': 'Profile',
            'polarity': 0
        }
    }
    
    # Mocking for constructor
    mocker.patch('gui.dlg_select_scans.config.spectrum', {
        'showMinorTicks': True, 
        'axisFontSize': 10, 
        'labelFontSize': 10, 
        'tickColour': [0, 0, 0]
    })
    mocker.patch('gui.dlg_select_scans.config.main', {
        'reverseScrolling': False
    })
    mocker.patch('gui.dlg_select_scans.config.colours', [[255, 0, 0]])
    
    # Use factories
    mocker.patch('gui.dlg_select_scans.mwx.sortListCtrl', side_effect=lambda *a, **k: mock_list_ctrl_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.canvas', side_effect=lambda *a, **k: mock_canvas_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.points')
    mocker.patch('gui.dlg_select_scans.mspy.plot.container')
    
    parent = wx.Frame(None)
    try:
        dlg = dlgSelectScans(parent, scans)
        
        # Verify calls for row 0
        calls = dlg.scanList.SetItem.call_args_list
        row0_calls = [c for c in calls if c[0][0] == 0]
        
        # Col 1: retentionTime should be ''
        assert any(c[0][1] == 1 and c[0][2] == '' for c in row0_calls)
        # Col 2: msLevel should be ''
        assert any(c[0][1] == 2 and c[0][2] == '' for c in row0_calls)
        # Col 3: precursorMZ should be ''
        assert any(c[0][1] == 3 and c[0][2] == '' for c in row0_calls)
        # Col 8: spectrumType should be 'Profile'
        assert any(c[0][1] == 8 and c[0][2] == 'Profile' for c in row0_calls)
        
    finally:
        parent.Destroy()

def test_updateScanList_empty(wx_app, mocker):
    """Test updateScanList with empty scan dictionary (Step 3)."""
    scans = {}
    mocker.patch('gui.dlg_select_scans.config.spectrum', {
        'showMinorTicks': True, 
        'axisFontSize': 10, 
        'labelFontSize': 10, 
        'tickColour': [0, 0, 0]
    })
    mocker.patch('gui.dlg_select_scans.config.main', {
        'reverseScrolling': False
    })
    mocker.patch('gui.dlg_select_scans.config.colours', [[255, 0, 0]])
    
    mocker.patch('gui.dlg_select_scans.mwx.sortListCtrl', side_effect=lambda *a, **k: mock_list_ctrl_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.canvas', side_effect=lambda *a, **k: mock_canvas_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.points')
    mocker.patch('gui.dlg_select_scans.mspy.plot.container')

    parent = wx.Frame(None)
    try:
        dlg = dlgSelectScans(parent, scans)
        dlg.scanList.setDataMap.assert_called_with([])
        assert dlg.scanList.InsertItem.call_count == 0
    finally:
        parent.Destroy()

def test_updateChromPlot_many_scans(dlg, mock_scans):
    """Test updateChromPlot with > 10 MS1 scans (Step 4)."""
    # mock_scans has 12 MS1 scans
    dlg.showChromCanvas = False
    dlg.updateChromPlot()
    assert dlg.showChromCanvas is True
    assert dlg.chromCanvas.draw.called

def test_updateChromPlot_few_scans(wx_app, mocker):
    """Test updateChromPlot with < 10 MS1 scans (Step 4)."""
    scans = {}
    for i in range(1, 6): # 5 MS1 scans
        scans[i] = {
            'scanNumber': i,
            'retentionTime': i * 60.0,
            'msLevel': 1,
            'precursorMZ': None,
            'precursorCharge': None,
            'lowMZ': 100.0,
            'highMZ': 1000.0,
            'totIonCurrent': 10000.0 * i,
            'pointsCount': 500,
            'spectrumType': 'Centroid',
            'polarity': 1,
            'basePeakIntensity': 5000.0 * i
        }
    
    mocker.patch('gui.dlg_select_scans.config.spectrum', {
        'showMinorTicks': True, 
        'axisFontSize': 10, 
        'labelFontSize': 10, 
        'tickColour': [0, 0, 0]
    })
    mocker.patch('gui.dlg_select_scans.config.main', {
        'reverseScrolling': False
    })
    mocker.patch('gui.dlg_select_scans.config.colours', [[255, 0, 0]])
    
    mocker.patch('gui.dlg_select_scans.mwx.sortListCtrl', side_effect=lambda *a, **k: mock_list_ctrl_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.canvas', side_effect=lambda *a, **k: mock_canvas_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.points')
    mocker.patch('gui.dlg_select_scans.mspy.plot.container')

    parent = wx.Frame(None)
    try:
        dlg = dlgSelectScans(parent, scans)
        # With only 5 scans, showChromCanvas should be False
        assert dlg.showChromCanvas is False
    finally:
        parent.Destroy()

def test_updateScanList_invalid_values(wx_app, mocker):
    """Test updateScanList with invalid values triggering except blocks (Step 3)."""
    scans = {
        1: {
            'scanNumber': 1,
            'retentionTime': 'invalid', 
            'msLevel': 2, # Set to 2 to skip updateChromPlot crash
            'precursorMZ': 'invalid', 
            'precursorCharge': 1,
            'lowMZ': 'invalid', 
            'highMZ': 1000.0,
            'totIonCurrent': 'invalid', 
            'pointsCount': 'invalid', 
            'spectrumType': 'Centroid',
            'polarity': 1
        }
    }
    
    mocker.patch('gui.dlg_select_scans.config.spectrum', {
        'showMinorTicks': True, 
        'axisFontSize': 10, 
        'labelFontSize': 10, 
        'tickColour': [0, 0, 0]
    })
    mocker.patch('gui.dlg_select_scans.config.main', {
        'reverseScrolling': False
    })
    mocker.patch('gui.dlg_select_scans.config.colours', [[255, 0, 0]])
    
    mocker.patch('gui.dlg_select_scans.mwx.sortListCtrl', side_effect=lambda *a, **k: mock_list_ctrl_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.canvas', side_effect=lambda *a, **k: mock_canvas_factory(mocker, *a, **k))
    mocker.patch('gui.dlg_select_scans.mspy.plot.points')
    mocker.patch('gui.dlg_select_scans.mspy.plot.container')

    parent = wx.Frame(None)
    try:
        dlg = dlgSelectScans(parent, scans)
        
        calls = dlg.scanList.SetItem.call_args_list
        row0_calls = [c for c in calls if c[0][0] == 0]
        
        # Check that they are empty strings due to 'except: pass'
        assert any(c[0][1] == 1 and c[0][2] == '' for c in row0_calls)
        assert any(c[0][1] == 3 and c[0][2] == '' for c in row0_calls)
        assert any(c[0][1] == 5 and c[0][2] == '' for c in row0_calls)
        assert any(c[0][1] == 6 and c[0][2] == '' for c in row0_calls)
        # str('invalid') won't raise, so col 7 will be 'invalid'
        assert any(c[0][1] == 7 and c[0][2] == 'invalid' for c in row0_calls)
        
    finally:
        parent.Destroy()

def test_onItemSelected(dlg, mocker):
    """Test onItemSelected (Step 5)."""
    # mock getSelecedScans to return [1, 2]
    mocker.patch.object(dlg, 'getSelecedScans', return_value=[1, 2])
    dlg.onItemSelected(None)
    # scan 1: retentionTime = 60.0 -> 1.0 min
    # scan 2: retentionTime = 120.0 -> 2.0 min
    dlg.chromCanvas.highlightXPoints.assert_called_once_with([1.0, 2.0])

def test_onItemSelected_no_chrom(dlg):
    """Test onItemSelected when no chromatogram is shown (Step 5)."""
    dlg.showChromCanvas = False
    dlg.onItemSelected(None)
    assert not dlg.chromCanvas.highlightXPoints.called

def test_onItemActivated(dlg, mocker):
    """Test onItemActivated (Step 5)."""
    mocker.patch.object(dlg, 'getSelecedScans', return_value=[5])
    dlg.onItemActivated(None)
    assert dlg.selected == [5]
    dlg.EndModal.assert_called_once_with(wx.ID_OK)

def test_onCanvasLMU(dlg, mocker):
    """Test onCanvasLMU (Step 5)."""
    # Mock cursor position to be near scan 3 (retentionTime 180.0s = 3.0min)
    # getCursorPosition returns (x, y) where x is in min
    dlg.chromCanvas.getCursorPosition.return_value = (3.1, 5000.0)
    
    # Mock scanList.GetNextItem to simulate iteration
    # We want it to find '3'
    # Iteration 1: i=0, item text '1'
    # Iteration 2: i=1, item text '2'
    # Iteration 3: i=2, item text '3' -> match
    
    mock_item1 = mocker.Mock()
    mock_item1.GetText.return_value = '1'
    mock_item2 = mocker.Mock()
    mock_item2.GetText.return_value = '2'
    mock_item3 = mocker.Mock()
    mock_item3.GetText.return_value = '3'
    
    dlg.scanList.GetNextItem.side_effect = [0, 1, 2, -1]
    dlg.scanList.GetItem.side_effect = [mock_item1, mock_item2, mock_item3]
    
    dlg.onCanvasLMU(None)
    
    assert dlg.chromCanvas.onLMU.called
    dlg.scanList.EnsureVisible.assert_called_once_with(2)

def test_onCanvasLMU_no_chrom(dlg):
    """Test onCanvasLMU when no chromatogram is shown (Step 5)."""
    dlg.showChromCanvas = False
    dlg.onCanvasLMU(None)
    assert not dlg.chromCanvas.onLMU.called

def test_onOpen_selected(dlg, mocker):
    """Test onOpen when scans are selected (Step 5)."""
    mocker.patch.object(dlg, 'getSelecedScans', return_value=[1, 2, 3])
    dlg.onOpen(None)
    assert dlg.selected == [1, 2, 3]
    dlg.EndModal.assert_called_once_with(wx.ID_OK)

def test_onOpen_none_selected(dlg, mocker):
    """Test onOpen when no scans are selected (Step 5)."""
    mocker.patch.object(dlg, 'getSelecedScans', return_value=[])
    dlg.onOpen(None)
    assert dlg.selected == []
    assert not dlg.EndModal.called
    assert wx.Bell.called

def test_getSelecedScans(dlg, mocker):
    """Test getSelecedScans helper method (Step 6)."""
    # Mock GetNextItem to return indices 0 and 2
    dlg.scanList.GetNextItem.side_effect = [0, 2, -1]
    
    mock_item0 = mocker.Mock()
    mock_item0.GetText.return_value = '1'
    mock_item2 = mocker.Mock()
    mock_item2.GetText.return_value = '3'
    
    dlg.scanList.GetItem.side_effect = [mock_item0, mock_item2]
    
    result = dlg.getSelecedScans()
    assert result == [1, 3]

def test_getFreeColour_from_config(dlg):
    """Test getFreeColour returns colour from config (Step 6)."""
    dlg.usedColours = [[255, 0, 0]]
    # Next one in config.colours is [0, 255, 0]
    result = dlg.getFreeColour()
    assert result == [0, 255, 0]
    assert [0, 255, 0] in dlg.usedColours

def test_getFreeColour_random(dlg, mocker):
    """Test getFreeColour generates random colour when config is exhausted (Step 6)."""
    # Filling up config.colours to trigger the random part
    # config.colours is mocked as [[255, 0, 0], [0, 255, 0]] in fixture
    dlg.usedColours = [[255, 0, 0], [0, 255, 0]]
    
    # Mock random.randrange to return specific values
    # Each call to getFreeColour will call it 3 times
    mocker.patch('gui.dlg_select_scans.random.randrange', side_effect=[100, 150, 200])
    
    result = dlg.getFreeColour()
    assert result == [100, 150, 200]
    assert [100, 150, 200] in dlg.usedColours
