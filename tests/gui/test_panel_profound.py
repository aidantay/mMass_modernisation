import pytest
import wx
import os
import tempfile
import webbrowser
import gui.panel_profound
import gui.config as config
import gui.images as images
from gui.ids import *

@pytest.fixture
def mock_parent(wx_app, mocker):
    """Fixture to provide a mock wx parent Frame."""
    parent = wx.Frame(None)
    parent.getCurrentPeaklist = mocker.Mock(return_value=[])
    yield parent
    if parent:
        parent.Destroy()

@pytest.fixture
def profound_panel(wx_app, mock_parent, mocker):
    """Fixture to initialize panelProfound with mocked dependencies."""
    # Mocking images.lib to provide required bitmaps
    mock_images = {
        'bgrToolbar': wx.Bitmap(1, 1),
        'bgrControlbar': wx.Bitmap(1, 1),
        'profoundPMFOff': wx.Bitmap(1, 1),
        'profoundQueryOff': wx.Bitmap(1, 1),
        'profoundPMFOn': wx.Bitmap(1, 1),
        'profoundQueryOn': wx.Bitmap(1, 1),
    }

    # Mock config.profound
    mock_config = {
        'title': '',
        'database': 'NCBI nr',
        'taxonomy': 'All taxa',
        'enzyme': 'Trypsin',
        'miscleavages': 1,
        'proteinMassLow': 0,
        'proteinMassHigh': 300,
        'proteinPILow': 0,
        'proteinPIHigh': 14,
        'peptideTol': 0.1,
        'peptideTolUnits': 'Da',
        'massType': 'Monoisotopic',
        'charge': 'MH+',
        'expectation': 0.01,
        'candidates': 500,
        'ranking': 'expect',
        'fixedMods': [],
        'variableMods': [],
        'filterAnnotations': False,
        'filterMatches': False,
        'filterUnselected': False,
        'filterIsotopes': False,
        'filterUnknown': False,
        'script': 'http://prowl.rockefeller.edu/cgi-bin/ProFound',
    }

    mocker.patch.dict(images.lib, mock_images)
    mocker.patch.dict(config.profound, mock_config, clear=True)
    mocker.patch('wx.RESIZE_BOX', 0, create=True)
    mocker.patch('wx.MAXIMIZE_BOX', 0, create=True)
    # Ensure we don't try to actually create a real modal dialog
    mocker.patch('wx.MiniFrame.Show')

    panel = gui.panel_profound.panelProfound(mock_parent)
    yield panel
    if panel:
        try:
            panel.Destroy()
        except wx.PyDeadObjectError:
            pass

def test_initialization(profound_panel):
    """Verify panelProfound instantiates correctly and sets currentTool."""
    assert isinstance(profound_panel, gui.panel_profound.panelProfound)
    assert profound_panel.currentTool in ['pmf', 'query']

def test_gui_creation(profound_panel):
    """Verify all child elements are created."""
    assert profound_panel.mainSizer.GetItemCount() == 3 # toolbar, pmf, query
    
    assert hasattr(profound_panel, 'pmf_butt')
    assert hasattr(profound_panel, 'query_butt')
    assert hasattr(profound_panel, 'search_butt')
    assert hasattr(profound_panel, 'paramTitle_value')
    assert hasattr(profound_panel, 'paramTaxonomy_choice')
    assert hasattr(profound_panel, 'paramDatabase_choice')
    assert hasattr(profound_panel, 'paramEnzyme_choice')
    assert hasattr(profound_panel, 'paramFixedMods_listbox')
    assert hasattr(profound_panel, 'paramVariableMods_listbox')
    assert hasattr(profound_panel, 'paramQuery_value')

def test_onClose(profound_panel, mocker):
    """Verify onClose deletes temp file and destroys frame."""
    mocker.patch('tempfile.gettempdir', return_value='/tmp')
    mock_unlink = mocker.patch('os.unlink')
    mock_destroy = mocker.patch.object(profound_panel, 'Destroy')
    profound_panel.onClose(None)
    mock_unlink.assert_called_with('/tmp/mmass_profound_search.html')
    assert mock_destroy.called

def test_onToolSelected(profound_panel, mocker):
    """Verify tool selection logic and UI updates."""
    # Test switching to query
    mock_event = mocker.Mock(spec=wx.CommandEvent)
    mock_event.GetId.return_value = ID_profoundQuery

    profound_panel.onToolSelected(mock_event)
    assert profound_panel.currentTool == 'query'
    assert profound_panel.mainSizer.GetItem(2).IsShown()
    assert not profound_panel.mainSizer.GetItem(1).IsShown()

    # Test switching to pmf
    mock_event.GetId.return_value = ID_profoundPMF
    profound_panel.onToolSelected(mock_event)
    assert profound_panel.currentTool == 'pmf'
    assert profound_panel.mainSizer.GetItem(1).IsShown()
    assert not profound_panel.mainSizer.GetItem(2).IsShown()

def test_onModificationSelected(profound_panel):
    """Verify modification count labels update."""
    profound_panel.paramFixedMods_listbox.Set(['Mod1', 'Mod2'])
    profound_panel.paramFixedMods_listbox.Select(0)
    
    profound_panel.paramVariableMods_listbox.Set(['Mod3', 'Mod4'])
    profound_panel.paramVariableMods_listbox.Select(0)
    profound_panel.paramVariableMods_listbox.Select(1)
    
    profound_panel.onModificationSelected()
    
    assert "Fixed modifications: (1)" in profound_panel.paramFixedMods_label.GetLabel()
    assert "Variable modifications: (2)" in profound_panel.paramVariableMods_label.GetLabel()

def test_onGetPeaklist(profound_panel, mock_parent, mocker):
    """Verify peaklist extraction and formatting."""
    mock_peak = mocker.Mock()
    mock_peak.mz = 123.456
    mock_peak.intensity = 789.012
    mock_parent.getCurrentPeaklist.return_value = [mock_peak]

    profound_panel.filterAnnotations_check.SetValue(True)
    profound_panel.filterMatches_check.SetValue(True)
    profound_panel.filterUnselected_check.SetValue(True)
    profound_panel.filterIsotopes_check.SetValue(True)
    profound_panel.filterUnknown_check.SetValue(True)

    profound_panel.onGetPeaklist()

    mock_parent.getCurrentPeaklist.assert_called_with('AMSIX')
    assert "123.456" in profound_panel.paramQuery_value.GetValue()
    assert "789.012" in profound_panel.paramQuery_value.GetValue()

def test_onGetPeaklist_no_data(profound_panel, mock_parent, mocker):
    """Verify behavior when no peaklist is returned."""
    mock_parent.getCurrentPeaklist.return_value = None
    profound_panel.paramQuery_value.SetValue("old value")

    mock_bell = mocker.patch('wx.Bell')
    profound_panel.onGetPeaklist(evt=mocker.Mock())
    assert profound_panel.paramQuery_value.GetValue() == ""
    assert mock_bell.called

def test_onSearch_success(profound_panel, mocker):
    """Verify happy path for search execution."""
    mocker.patch.object(profound_panel, 'getParams', return_value=True)
    mocker.patch.object(profound_panel, 'checkParams', return_value=True)
    mocker.patch.object(profound_panel, 'makeSearchHTML', return_value="<html></html>")
    mocker.patch('tempfile.gettempdir', return_value='/tmp')
    mock_file = mocker.mock_open()
    mocker.patch('gui.panel_profound.file', mock_file, create=True)
    mock_open = mocker.patch('webbrowser.open')
    profound_panel.onSearch(None)
    mock_file.assert_called_with('/tmp/mmass_profound_search.html', 'w')
    mock_open.assert_called_with('file:///tmp/mmass_profound_search.html', autoraise=1)

def test_onSearch_failure(profound_panel, mocker):
    """Verify error handling in search execution."""
    mocker.patch.object(profound_panel, 'getParams', return_value=True)
    mocker.patch.object(profound_panel, 'checkParams', return_value=True)
    mocker.patch.object(profound_panel, 'makeSearchHTML', return_value="<html></html>")
    mocker.patch('gui.panel_profound.file', side_effect=IOError("Write error"), create=True)
    mock_bell = mocker.patch('wx.Bell')
    mock_dlg = mocker.patch('gui.mwx.dlgMessage')
    profound_panel.onSearch(None)
    assert mock_bell.called
    assert mock_dlg.called

def test_setData(profound_panel, mocker):
    """Verify setData updates UI from document."""
    mock_doc = mocker.Mock()
    mock_doc.title = "Test Doc"

    mock_get_pkl = mocker.patch.object(profound_panel, 'onGetPeaklist')
    profound_panel.setData(mock_doc)
    assert profound_panel.paramTitle_value.GetValue() == "Test Doc"
    assert mock_get_pkl.called

def test_setData_none(profound_panel):
    """Verify setData handles None document."""
    profound_panel.setData(None)
    assert profound_panel.paramTitle_value.GetValue() == ""
    assert profound_panel.paramQuery_value.GetValue() == ""

def test_getParams_success(profound_panel):
    """Verify parameters extraction."""
    profound_panel.paramTitle_value.SetValue("New Title")
    profound_panel.paramTaxonomy_choice.SetStringSelection("All taxa")
    profound_panel.paramDatabase_choice.SetStringSelection("NCBI nr")
    profound_panel.paramEnzyme_choice.SetStringSelection("Trypsin")
    profound_panel.paramZscore_radio.SetValue(True)
    
    profound_panel.paramProteinMassLow_value.SetValue("10")
    profound_panel.paramProteinMassHigh_value.SetValue("200")
    profound_panel.paramProteinPILow_value.SetValue("4")
    profound_panel.paramProteinPIHigh_value.SetValue("9")
    profound_panel.paramPeptideTol_value.SetValue("0.5")
    profound_panel.paramExpectation_value.SetValue("0.05")
    profound_panel.paramCandidates_value.SetValue("100")
    
    assert profound_panel.getParams() is True
    assert config.profound['title'] == "New Title"
    assert config.profound['ranking'] == 'zscore'
    assert config.profound['proteinMassLow'] == 10.0
    assert config.profound['candidates'] == 100

def test_getParams_exception(profound_panel, mocker):
    """Verify getParams handles exceptions (e.g. invalid float)."""
    profound_panel.paramProteinMassLow_value.SetValue("invalid")
    mock_bell = mocker.patch('wx.Bell')
    assert profound_panel.getParams() is False
    assert mock_bell.called

def test_checkParams(profound_panel, mocker):
    """Verify parameters validation."""
    config.profound['taxonomy'] = 'All taxa'
    config.profound['database'] = 'NCBI nr'
    config.profound['enzyme'] = 'Trypsin'
    profound_panel.paramQuery_value.SetValue("123.456 100")

    assert profound_panel.checkParams() is True

    # Test invalid
    config.profound['taxonomy'] = ''
    mock_bell = mocker.patch('wx.Bell')
    mock_dlg = mocker.patch('gui.mwx.dlgMessage')
    assert profound_panel.checkParams() is False
    assert mock_bell.called
    assert mock_dlg.called

def test_updateForm(profound_panel):
    """Verify form population from currentParams."""
    # updateForm is called in __init__
    assert 'NCBI nr' in profound_panel.paramDatabase_choice.GetStrings()
    assert 'All taxa' in profound_panel.paramTaxonomy_choice.GetStrings()
    assert 'Trypsin' in profound_panel.paramEnzyme_choice.GetStrings()

def test_makeSearchHTML(profound_panel):
    """Verify HTML generation."""
    config.profound['title'] = "Test Search"
    config.profound['massType'] = 'Average'
    profound_panel.paramQuery_value.SetValue("100.1 200.2")
    
    html = profound_panel.makeSearchHTML()
    assert "Test Search" in html
    assert "APKS" in html
    assert "100.1 200.2" in html
    
    config.profound['massType'] = 'Monoisotopic'
    html = profound_panel.makeSearchHTML()
    assert "MPKS" in html

def test_onToolSelected_no_evt(profound_panel):
    """Verify tool selection without event."""
    profound_panel.onToolSelected(tool='query')
    assert profound_panel.currentTool == 'query'
    profound_panel.onToolSelected(tool='pmf')
    assert profound_panel.currentTool == 'pmf'

def test_onModificationSelected_query_tool(profound_panel, mocker):
    """Verify modifications count doesn't update for query tool if evt is present."""
    profound_panel.currentTool = 'query'
    label_fixed = profound_panel.paramFixedMods_label.GetLabel()
    label_var = profound_panel.paramVariableMods_label.GetLabel()

    # Trigger with event
    profound_panel.onModificationSelected(evt=mocker.Mock())
    assert profound_panel.paramFixedMods_label.GetLabel() == label_fixed
    assert profound_panel.paramVariableMods_label.GetLabel() == label_var

def test_onGetPeaklist_no_evt(profound_panel, mock_parent, mocker):
    """Verify onGetPeaklist without event."""
    mock_parent.getCurrentPeaklist.return_value = None
    profound_panel.paramQuery_value.SetValue("old")
    mock_bell = mocker.patch('wx.Bell')
    profound_panel.onGetPeaklist(evt=None)
    assert profound_panel.paramQuery_value.GetValue() == ""
    assert not mock_bell.called

def test_getParams_empty_numeric(profound_panel):
    """Verify getParams handles empty numeric fields."""
    profound_panel.paramProteinMassLow_value.SetValue("")
    profound_panel.paramProteinMassHigh_value.SetValue("")
    profound_panel.paramProteinPILow_value.SetValue("")
    profound_panel.paramProteinPIHigh_value.SetValue("")
    profound_panel.paramPeptideTol_value.SetValue("")
    profound_panel.paramExpectation_value.SetValue("")
    profound_panel.paramCandidates_value.SetValue("")
    
    assert profound_panel.getParams() is True
    assert config.profound['proteinMassLow'] == ""

def test_escape(profound_panel):
    """Verify HTML escaping."""
    assert profound_panel._escape(" < > & \" ' ") == "&lt; &gt; &amp; &quot; &#39;"

