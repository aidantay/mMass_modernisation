import pytest
import wx
import mspy

# Workaround for missing RESIZE_BOX in some wxPython versions
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = getattr(wx, 'RESIZE_BORDER', 0)

import gui.panel_monomer_library as panel_lib

class MockMonomer(object):
    def __init__(self, abbr, name, category):
        self.abbr = abbr
        self.name = name
        self.category = category

@pytest.fixture
def mock_mspy_monomers(mocker):
    monomers = {
        'Gly': MockMonomer('Gly', 'Glycine', 'Amino Acid'),
        'Ala': MockMonomer('Ala', 'Alanine', 'Amino Acid'),
        'H2O': MockMonomer('H2O', 'Water', 'Solvent'),
        'MeOH': MockMonomer('MeOH', 'Methanol', 'Solvent'),
        'UNK': MockMonomer('UNK', 'Unknown', 'Other')
    }
    mocker.patch('mspy.monomers', monomers)
    return monomers

@pytest.fixture
def mock_gui_deps(mocker):
    mock_mwx = mocker.patch('gui.panel_monomer_library.mwx')
    mock_images = mocker.patch('gui.panel_monomer_library.images')
    
    # Setup mock_mwx constants
    mock_mwx.TOOLBAR_HEIGHT = 30
    mock_mwx.SMALL_SEARCH_HEIGHT = 20
    mock_mwx.TOOLBAR_LSPACE = 5
    mock_mwx.LISTCTRL_NO_SPACE = 0
    mock_mwx.LISTCTRL_STYLE_SINGLE = wx.LC_REPORT | wx.LC_SINGLE_SEL
    mock_mwx.LISTCTRL_ALTCOLOUR = (255, 255, 255)
    
    # Setup mock_images.lib
    mock_images.lib = {'bgrToolbarNoBorder': mocker.Mock()}
    
    # Mock bgrPanel and sortListCtrl
    class MockBgrPanel(wx.Panel):
        def __init__(self, *args, **kwargs):
            wx.Panel.__init__(self, args[0], args[1], size=kwargs.get('size', (-1, -1)))
    
    class MockSortListCtrl(wx.ListCtrl):
        def __init__(self, *args, **kwargs):
            wx.ListCtrl.__init__(self, *args, **kwargs)
            self._dataMap = None
            self._selected = []
        def setAltColour(self, color): pass
        def setDataMap(self, dataMap): self._dataMap = dataMap
        def getSelected(self): return self._selected
        def sort(self): pass
        
    mock_mwx.bgrPanel = MockBgrPanel
    mock_mwx.sortListCtrl = MockSortListCtrl

    return {
        'mwx': mock_mwx,
        'images': mock_images
    }

@pytest.fixture
def panel(wx_app, mock_mspy_monomers, mock_gui_deps):
    parent = wx.Frame(None)
    p = panel_lib.panelMonomerLibrary(parent)
    yield p
    if p:
        p.Destroy()
    parent.Destroy()

def test_init(panel, mock_mspy_monomers):
    """Test initialization."""
    assert panel.GetTitle() == 'Monomer Library'
    assert panel.filterIn == []
    assert panel.filterOut == []
    assert panel.DnD is True
    # Initial updateMonomerList should have happened
    assert len(panel.monomerMap) == len(mock_mspy_monomers)

def test_makeToolbar_mac(wx_app, mock_gui_deps, mock_mspy_monomers, mocker):
    """Test toolbar creation on Mac."""
    mocker.patch('wx.Platform', '__WXMAC__')
    parent = wx.Frame(None)
    p = panel_lib.panelMonomerLibrary(parent)
    assert isinstance(p.search_value, wx.SearchCtrl)
    
    # Test cancel button handler (lambda)
    p.search_value.SetValue('test')
    # Simulate EVT_SEARCHCTRL_CANCEL_BTN
    evt = wx.PyCommandEvent(wx.wxEVT_COMMAND_SEARCHCTRL_CANCEL_BTN, p.search_value.GetId())
    p.search_value.GetEventHandler().ProcessEvent(evt)
    assert p.search_value.GetValue() == ''
    
    p.Destroy()
    parent.Destroy()

def test_makeToolbar_other(wx_app, mock_gui_deps, mock_mspy_monomers, mocker):
    """Test toolbar creation on other platforms."""
    mocker.patch('wx.Platform', '__WXMSW__')
    parent = wx.Frame(None)
    p = panel_lib.panelMonomerLibrary(parent)
    assert isinstance(p.search_value, wx.TextCtrl)
    assert not isinstance(p.search_value, wx.SearchCtrl)
    p.Destroy()
    parent.Destroy()

def test_onClose(panel, mocker):
    """Test closing the panel."""
    mock_destroy = mocker.patch.object(panel, 'Destroy')
    panel.onClose(None)
    mock_destroy.assert_called_once()

def test_onSearch(panel, mocker):
    """Test search event."""
    mock_update = mocker.patch.object(panel, 'updateMonomerList')
    panel.onSearch(None)
    mock_update.assert_called_once()

def test_setFilter(panel, mocker):
    """Test setting filters."""
    mock_update = mocker.patch.object(panel, 'updateMonomerList')
    panel.setFilter(filterIn=['Amino Acid'], filterOut=['Solvent'])
    assert panel.filterIn == ['Amino Acid']
    assert panel.filterOut == ['Solvent']
    mock_update.assert_called_once()

def test_enableDnD(panel):
    """Test enabling/disabling DnD."""
    panel.enableDnD(False)
    assert panel.DnD is False
    panel.enableDnD(True)
    assert panel.DnD is True

def test_updateMonomerMap_filters(panel, mock_mspy_monomers):
    """Test filtering logic in updateMonomerMap."""
    # filterIn
    panel.filterIn = ['Amino Acid']
    panel.filterOut = []
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 2 # Gly, Ala
    assert all(x[0] in ['Gly', 'Ala'] for x in panel.monomerMap)
    
    # filterOut
    panel.filterIn = []
    panel.filterOut = ['Solvent']
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 3 # Gly, Ala, UNK
    assert all(x[0] not in ['H2O', 'MeOH'] for x in panel.monomerMap)
    
    # Both filters
    panel.filterIn = ['Amino Acid', 'Solvent']
    panel.filterOut = ['Solvent']
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 2 # Gly, Ala (Solvent is excluded by filterOut)

def test_updateMonomerMap_search(panel, mock_mspy_monomers):
    """Test search logic in updateMonomerMap."""
    # Search by abbr (case insensitive)
    panel.search_value.SetValue('GL')
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 1
    assert panel.monomerMap[0][0] == 'Gly'
    
    # Search by name (case insensitive)
    panel.search_value.SetValue('WATER')
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 1
    assert panel.monomerMap[0][0] == 'H2O'
    
    # Multi-term search (all terms must be in abbr OR all terms must be in name)
    panel.search_value.SetValue('gly cine')
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 1
    assert panel.monomerMap[0][1] == 'Glycine'
    
    # Terms not found in either
    panel.search_value.SetValue('gly water')
    panel.updateMonomerMap()
    assert len(panel.monomerMap) == 0

def test_updateMonomerList_empty(panel, mocker):
    """Test updateMonomerList when map is empty."""
    mocker.patch('mspy.monomers', {})
    panel.updateMonomerList()
    assert panel.monomerMap == []
    # Ensure it doesn't crash and returns early after setDataMap

def test_onBeginDrag(panel, mocker):
    """Test drag and drop start."""
    # Scenario 1: Disabled DnD
    panel.DnD = False
    evt = mocker.Mock()
    panel.onBeginDrag(evt)
    evt.Veto.assert_called_once()
    
    # Scenario 2: No selection
    panel.DnD = True
    panel.monomerList._selected = []
    panel.onBeginDrag(evt)
    # Should return early
    
    # Scenario 3: Successful drag
    panel.monomerList._selected = [0]
    panel.monomerMap = [('Gly', 'Glycine')]
    
    mock_data_obj = mocker.patch('wx.TextDataObject')
    mock_drop_source = mocker.patch('wx.DropSource')
    
    # We need to mock return value of DoDragDrop
    mock_drop_source.return_value.DoDragDrop.return_value = wx.DragCopy
    
    panel.onBeginDrag(evt)
    
    mock_data_obj.return_value.SetText.assert_called_with('Gly')
    mock_drop_source.assert_called_with(panel)
    mock_drop_source.return_value.SetData.assert_called_with(mock_data_obj.return_value)
    mock_drop_source.return_value.DoDragDrop.assert_called_with(flags=wx.Drag_CopyOnly)
