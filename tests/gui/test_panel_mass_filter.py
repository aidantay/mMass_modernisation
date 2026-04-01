import pytest
import wx

# Handle missing wx.RESIZE_BOX in some wxPython versions
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = getattr(wx, 'RESIZE_BORDER', 0)

from gui.ids import *
from gui import config
from gui import images
from gui import libs
from gui import mwx
from gui import panel_mass_filter

@pytest.fixture
def app():
    app = wx.App(False)
    yield app
    app.Destroy()

@pytest.fixture
def mock_parent(app, mocker):
    parent = wx.Frame(None)
    parent.updateMassPoints = mocker.MagicMock()
    parent.onDocumentChanged = mocker.MagicMock()
    parent.onToolsCalibration = mocker.MagicMock()
    yield parent
    if parent:
        try:
            parent.Destroy()
        except (wx.PyDeadObjectError, RuntimeError):
            pass

@pytest.fixture
def mock_document(mocker):
    doc = mocker.MagicMock()
    doc.backup = mocker.MagicMock()
    doc.annotations = []
    doc.sortAnnotations = mocker.MagicMock()
    doc.spectrum.peaklist.delete = mocker.MagicMock()
    return doc

@pytest.fixture
def panel(app, mock_parent, mocker):
    # Patch config and images before initialization
    mocker.patch.dict(config.main, {'mzDigits': 4, 'ppmDigits': 2, 'macListCtrlGeneric': 0, 'reverseScrolling': 0})
    mocker.patch.dict(config.match, {'units': 'ppm', 'ppmDigits': 2})
    mocker.patch.dict(images.lib, {
        'bgrToolbarNoBorder': wx.Bitmap(1, 1),
        'bgrToolbar': wx.Bitmap(1, 1),
        'bgrBottombar': wx.Bitmap(1, 1)
    })
    # Mock libs.references
    mock_refs = {
        'Test Group': [
            ('Ref 1', 100.0),
            ('Ref 2', 200.0)
        ]
    }
    mocker.patch.object(libs, 'references', mock_refs)
    p = panel_mass_filter.panelMassFilter(mock_parent)
    yield p
    if p:
        try:
            p.Destroy()
        except (wx.PyDeadObjectError, RuntimeError):
            pass

def test_init(panel):
    assert panel.GetTitle() == 'Mass Filter'
    assert hasattr(panel, 'references_choice')
    assert hasattr(panel, 'match_butt')
    assert hasattr(panel, 'annotate_butt')
    assert hasattr(panel, 'remove_butt')
    assert hasattr(panel, 'referencesList')
    assert panel.references_choice.GetCount() > 0

def test_onReferencesSelected(panel, mocker):
    # Set choice selection
    panel.references_choice.SetStringSelection('Test Group')
    
    # Mock libs.references
    mock_refs = {
        'Test Group': [
            ('Ref 1', 100.0),
            ('Ref 2', 200.0)
        ]
    }
    mocker.patch.object(libs, 'references', mock_refs)
    event = mocker.MagicMock(spec=wx.CommandEvent)
    panel.onReferencesSelected(event)
        
    assert panel.currentReferences is not None
    assert len(panel.currentReferences) == 2
    assert panel.currentReferences[0][0] == 'Ref 1'

def test_onListFilter(panel, mocker):
    # Matched only
    event = mocker.MagicMock()
    event.GetId.return_value = ID_listViewMatched
    panel.onListFilter(event)
    assert panel._referencesFilter == 1
    
    # Unmatched only
    event.GetId.return_value = ID_listViewUnmatched
    panel.onListFilter(event)
    assert panel._referencesFilter == -1
    
    # All
    event.GetId.return_value = ID_listViewAll
    panel.onListFilter(event)
    assert panel._referencesFilter == 0

def test_onItemSelected(panel, mock_parent, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, None, True, []]
    ]
    event = mocker.MagicMock()
    event.GetData.return_value = 0
    panel.onItemSelected(event)
    mock_parent.updateMassPoints.assert_called_with([100.0])

def test_onItemActivated(panel, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, None, True, []]
    ]
    # Patch updateReferencesList and EnsureVisible
    mocker.patch.object(panel, 'updateReferencesList')
    mocker.patch.object(panel.referencesList, 'EnsureVisible')
    event = mocker.MagicMock()
    event.GetData.return_value = 0
    event.GetIndex.return_value = 0
    
    # Toggle use (from True to False)
    panel.onItemActivated(event)
    assert panel.currentReferences[0][3] is False
    
    # Toggle use (from False to True)
    panel.onItemActivated(event)
    assert panel.currentReferences[0][3] is True

def test_onMatch(panel, mock_parent, mocker):
    mock_panelMatch = mocker.patch('gui.panel_mass_filter.panelMatch')
    mock_instance = mock_panelMatch.return_value
        
    # Trigger onMatch
    panel.onMatch(mocker.MagicMock())
        
    assert panel.matchPanel == mock_instance
    mock_instance.setData.assert_called()

def test_onAnnotate_no_doc(panel, mocker):
    mock_bell = mocker.patch('wx.Bell')
    panel.currentDocument = None
    panel.onAnnotate(None)
    mock_bell.assert_called()

def test_onAnnotate_no_refs(panel, mock_document, mocker):
    mock_bell = mocker.patch('wx.Bell')
    panel.currentDocument = mock_document
    panel.currentReferences = None
    panel.onAnnotate(None)
    mock_bell.assert_called()

def test_onAnnotate_happy_path(panel, mock_document, mock_parent, mocker):
    panel.currentDocument = mock_document
    mock_ann = mocker.MagicMock()
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, [mock_ann]]
    ]
    
    panel.onAnnotate(None)
    
    mock_document.backup.assert_called_with(('annotations'))
    assert mock_ann in mock_document.annotations
    assert mock_ann.label == 'Ref 1'

def test_onRemove_no_doc(panel, mocker):
    mock_bell = mocker.patch('wx.Bell')
    panel.currentDocument = None
    panel.onRemove(None)
    mock_bell.assert_called()

def test_onRemove_no_refs(panel, mock_document, mocker):
    mock_bell = mocker.patch('wx.Bell')
    panel.currentDocument = mock_document
    panel.currentReferences = None
    panel.onRemove(None)
    mock_bell.assert_called()

def test_onRemove_happy_path(panel, mock_document, mock_parent, mocker):
    panel.currentDocument = mock_document
    mock_ann = mocker.MagicMock()
    mock_ann.peakIndex = 5
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, [mock_ann]]
    ]
    
    panel.onRemove(None)
    
    mock_document.backup.assert_called_with(('spectrum'))
    mock_document.spectrum.peaklist.delete.assert_called_with([5])

def test_setData(panel, mock_document, mocker):
    mock_clear = mocker.patch.object(panel, 'clearMatches')
    panel.setData(mock_document)
    assert panel.currentDocument == mock_document
    mock_clear.assert_called()

def test_clearMatches(panel, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, [mocker.MagicMock()]]
    ]
    mock_update = mocker.patch.object(panel, 'updateReferencesList')
    panel.clearMatches()
    assert panel.currentReferences[0][2] is None
    mock_update.assert_called()

def test_updateReferencesList(panel, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, []], # Matched
        ['Ref 2', 200.0, None, True, []], # Unmatched
        ['Ref 3', 300.0, None, False, []] # Skipped
    ]
    
    mocker.patch.dict(config.main, {'mzDigits': 4, 'ppmDigits': 2})
    mocker.patch.dict(config.match, {'units': 'ppm', 'ppmDigits': 2})
    mocker.patch.object(panel.referencesList, 'InsertItem', return_value=0)
    mocker.patch.object(panel.referencesList, 'SetItem')
    mocker.patch.object(panel.referencesList, 'SetItemData')
    mocker.patch.object(panel.referencesList, 'sort')
    mock_color = mocker.patch.object(panel.referencesList, 'SetItemTextColour')
    mock_font = mocker.patch.object(panel.referencesList, 'SetItemFont')
    
    panel.updateReferencesList()
                                    
    colors = [call[0][1] for call in mock_color.call_args_list]
    assert (0, 200, 0) in colors
    assert (150, 150, 150) in colors

def test_onClose(panel, mocker):
    panel.matchPanel = mocker.MagicMock()
    panel.onClose(None)
    panel.matchPanel.Close.assert_called()

def test_onListRMU(panel, mocker):
    mock_menu = mocker.patch('wx.Menu')
    mock_menu_inst = mock_menu.return_value
    mocker.patch.object(panel, 'PopupMenu')
    panel.onListRMU(None)
    mock_menu_inst.Append.assert_any_call(ID_listViewAll, "Show All", "", wx.ITEM_RADIO)

def test_updateReferencesList_filter_matched(panel, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, []], # Matched
        ['Ref 2', 200.0, None, True, []], # Unmatched
    ]
    panel._referencesFilter = 1 # Show Matched Only
    
    mocker.patch.dict(config.main, {'mzDigits': 4, 'ppmDigits': 2})
    mocker.patch.dict(config.match, {'units': 'ppm', 'ppmDigits': 2})
    mocker.patch.object(panel.referencesList, 'InsertItem', return_value=0)
    mock_set_item = mocker.patch.object(panel.referencesList, 'SetItem')
    mocker.patch.object(panel.referencesList, 'SetItemData')
    mocker.patch.object(panel.referencesList, 'SetItemTextColour')
    mocker.patch.object(panel.referencesList, 'SetItemFont')
    mocker.patch.object(panel.referencesList, 'sort')
    
    panel.updateReferencesList()
    # Check that only Ref 1 was added
    calls = [call[0][2] for call in mock_set_item.call_args_list if call[0][1] == 0]
    assert 'Ref 1' in calls
    assert 'Ref 2' not in calls

def test_updateReferencesList_filter_unmatched(panel, mocker):
    panel.currentReferences = [
        ['Ref 1', 100.0, 0.01, True, []], # Matched
        ['Ref 2', 200.0, None, True, []], # Unmatched
    ]
    panel._referencesFilter = -1 # Show Unmatched Only
    
    mocker.patch.dict(config.main, {'mzDigits': 4, 'ppmDigits': 2})
    mocker.patch.dict(config.match, {'units': 'ppm', 'ppmDigits': 2})
    mocker.patch.object(panel.referencesList, 'InsertItem', return_value=0)
    mock_set_item = mocker.patch.object(panel.referencesList, 'SetItem')
    mocker.patch.object(panel.referencesList, 'SetItemData')
    mocker.patch.object(panel.referencesList, 'sort')
    
    panel.updateReferencesList()
    # Check that only Ref 2 was added
    calls = [call[0][2] for call in mock_set_item.call_args_list if call[0][1] == 0]
    assert 'Ref 2' in calls
    assert 'Ref 1' not in calls

def test_calibrateByMatches(panel, mock_parent):
    panel.calibrateByMatches(['ref1', 'ref2'])
    mock_parent.onToolsCalibration.assert_called_with(references=['ref1', 'ref2'])

def test_updateMatches(panel, mocker):
    mock_update = mocker.patch.object(panel, 'updateReferencesList')
    panel.updateMatches()
    mock_update.assert_called()

