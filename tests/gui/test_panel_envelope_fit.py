import pytest
import wx
import os
import sys

# Handle missing wx.RESIZE_BOX in some wxPython versions
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = getattr(wx, 'RESIZE_BORDER', 0)

from gui.panel_envelope_fit import panelEnvelopeFit
from gui import images
import gui.config as config
import mspy

@pytest.fixture
def mock_images(mocker):
    """Fixture to mock images.lib."""
    # Create some dummy bitmaps and cursors
    dummy_bitmap = wx.Bitmap(1, 1)
    dummy_cursor = wx.Cursor(wx.CURSOR_ARROW)
    
    mock_lib = {
        'bgrToolbar': dummy_bitmap,
        'arrowsDown': dummy_bitmap,
        'arrowsRight': dummy_bitmap,
        'bgrControlbar': dummy_bitmap,
        'stopper': dummy_bitmap,
        'cursorsCrossMeasure': dummy_cursor,
        'iconDlg': dummy_bitmap,
    }
    
    mocker.patch.dict(images.lib, mock_lib, clear=True)
    yield images.lib

@pytest.fixture
def mock_parent(wx_app, mocker):
    """Fixture providing a real wx.Frame mimicking the main frame."""
    parent = wx.Frame(None)
    # Add the required method
    parent.updateTmpSpectrum = mocker.Mock()
    yield parent
    if parent:
        parent.Destroy()

@pytest.fixture
def mock_document(mocker):
    """Fixture mimicking an mMass document."""
    doc = mocker.Mock()
    doc.spectrum = mocker.Mock()
    doc.spectrum.hasprofile = mocker.Mock(return_value=True)
    doc.spectrum.haspeaks = mocker.Mock(return_value=True)
    doc.spectrum.peaklist = []
    doc.spectrum.profile = []
    doc.spectrum.baseline = mocker.Mock(return_value=[])
    return doc

@pytest.fixture
def mock_config(mocker):
    """Fixture to isolate gui.config dictionaries."""
    mocker.patch.dict(config.envelopeFit, {
        'loss': 'H',
        'gain': 'H{2}',
        'fit': 'spectrum',
        'scaleMin': 0,
        'scaleMax': 10,
        'charge': 1,
        'fwhm': 0.01,
        'forceFwhm': 0,
        'peakShape': 'gaussian',
        'autoAlign': 1,
        'relThreshold': 0.05,
    }, clear=True)
    mocker.patch.dict(config.spectrum, {
        'xLabel': 'm/z',
        'yLabel': 'a.i.',
        'showGrid': 1,
        'showMinorTicks': 1,
        'posBarSize': 7,
        'axisFontSize': 10,
        'showTracker': 1,
    }, clear=True)
    mocker.patch.dict(config.main, {
        'mzDigits': 4,
        'intDigits': 0,
        'reverseScrolling': 0,
    }, clear=True)
    mocker.patch.dict(config.processing, {
        'baseline': {'precision': 15, 'offset': 0.25},
        'peakpicking': {'baseline': 1, 'pickingHeight': 0.75},
        'baseline': {'precision': 15, 'offset': 0.25},
    }, clear=False) # Don't clear processing as it has sub-dicts
    yield config

@pytest.fixture
def panel(wx_app, mock_parent, mock_config, mock_images, mocker):
    """Fixture that instantiates panelEnvelopeFit."""
    # Mock mspy.plot.canvas and container to avoid actual plotting during init
    mock_canvas = mocker.patch('mspy.plot.canvas')
    mock_container = mocker.patch('mspy.plot.container')
    
    def canvas_side_effect(parent, *args, **kwargs):
        canvas = wx.Window(parent)
        canvas.setProperties = mocker.Mock()
        canvas.setLMBFunction = mocker.Mock()
        canvas.draw = mocker.Mock()
        canvas.refresh = mocker.Mock()
        canvas.setCursorImage = mocker.Mock()
        canvas.setMFunction = mocker.Mock()
        return canvas
        
    mock_canvas.side_effect = canvas_side_effect
    
    container_instance = mocker.Mock()
    container_instance.empty = mocker.Mock()
    container_instance.append = mocker.Mock()
    mock_container.return_value = container_instance
    
    p = panelEnvelopeFit(mock_parent)
    yield p
    if p:
        p.Destroy()

def test_init_and_make_gui(panel):
    """Verify core initialization of the panel."""
    assert panel.GetTitle() == "Envelope Fit"
    
    # Verify mainSizer contains exactly 4 elements
    children = panel.mainSizer.GetChildren()
    assert len(children) == 4
    
    # Index 0: Toolbar
    # Index 1: Controlbar
    # Index 2: Results panel
    # Index 3: Gauge panel
    
    # Ensure gauge is initially hidden
    assert not panel.mainSizer.IsShown(3)

# Step 3: UI Interaction Logic Tests

def test_on_close(panel, mocker):
    """Verify onClose behavior."""
    mock_destroy = mocker.patch.object(panel, 'Destroy')
    # Case 1: Not processing
    panel.processing = None
    evt = mocker.Mock()
    panel.onClose(evt)
    panel.parent.updateTmpSpectrum.assert_called_with(None)
    mock_destroy.assert_called_once()
    
    # Case 2: Processing active
    mock_destroy.reset_mock()
    panel.parent.updateTmpSpectrum.reset_mock()
    panel.processing = mocker.Mock()
    mock_bell = mocker.patch('wx.Bell')
    panel.onClose(evt)
    mock_bell.assert_called_once()
    mock_destroy.assert_not_called()
    panel.parent.updateTmpSpectrum.assert_not_called()

def test_on_collapse(panel, mocker):
    """Verify toggling visibility of the results panel."""
    # Initially results panel (index 2) is shown
    assert panel.mainSizer.IsShown(2)
    
    mock_set_bitmap = mocker.patch.object(panel.collapse_butt, 'SetBitmapLabel')
    # Collapse
    evt = mocker.Mock()
    panel.onCollapse(evt)
    assert not panel.mainSizer.IsShown(2)
    mock_set_bitmap.assert_called_with(images.lib['arrowsRight'])
    
    # Expand
    mock_set_bitmap.reset_mock()
    panel.onCollapse(evt)
    assert panel.mainSizer.IsShown(2)
    mock_set_bitmap.assert_called_with(images.lib['arrowsDown'])

def test_on_stop(panel, mocker):
    """Verify onStop behavior."""
    mock_stop = mocker.patch('mspy.stop')
    mock_bell = mocker.patch('wx.Bell')
    
    # Case 1: Processing active and alive
    panel.processing = mocker.Mock()
    panel.processing.isAlive.return_value = True
    panel.onStop(None)
    mock_stop.assert_called_once()
    mock_bell.assert_not_called()
    
    # Case 2: Not processing
    mock_stop.reset_mock()
    panel.processing = None
    panel.onStop(None)
    mock_bell.assert_called_once()
    mock_stop.assert_not_called()

    # Case 3: Processing exists but is not alive
    mock_stop.reset_mock()
    mock_bell.reset_mock()
    panel.processing = mocker.Mock()
    panel.processing.isAlive.return_value = False
    panel.onStop(None)
    mock_bell.assert_called_once()
    mock_stop.assert_not_called()

def test_on_list_key(panel, mocker):
    """Verify list key events (Ctrl+C, Ctrl+A)."""
    mock_copy = mocker.patch.object(panel.resultsList, 'copyToClipboard')
    mock_set_state = mocker.patch.object(panel.resultsList, 'SetItemState')
    mocker.patch.object(panel.resultsList, 'GetItemCount', return_value=2)
    
    # Ctrl+C
    evt = mocker.Mock()
    evt.GetKeyCode.return_value = ord('C')
    evt.CmdDown.return_value = True
    panel.onListKey(evt)
    mock_copy.assert_called_once()
    
    # Ctrl+A
    evt.GetKeyCode.return_value = ord('A')
    panel.onListKey(evt)
    assert mock_set_state.call_count == 2
    mock_set_state.assert_has_calls([
        mocker.call(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED),
        mocker.call(1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
    ])
    
    # Other key
    evt.GetKeyCode.return_value = ord('X')
    panel.onListKey(evt)
    evt.Skip.assert_called_once()

# Step 4: Data Update and Parameters Logic Tests

def test_set_data_profile_only(panel, mocker):
    """Verify setData with profile data only."""
    doc = mocker.Mock()
    doc.spectrum.hasprofile.return_value = True
    doc.spectrum.haspeaks.return_value = False
    
    panel.setData(document=doc)
    
    assert panel.fitToSpectrum_radio.GetValue()
    assert not panel.fitToPeaklist_radio.IsEnabled()
    assert panel.fitToSpectrum_radio.IsEnabled()

def test_set_data_peaks_only(panel, mocker):
    """Verify setData with peak data only."""
    doc = mocker.Mock()
    doc.spectrum.hasprofile.return_value = False
    doc.spectrum.haspeaks.return_value = True
    
    panel.setData(document=doc)
    
    assert panel.fitToPeaklist_radio.GetValue()
    assert not panel.fitToSpectrum_radio.IsEnabled()
    assert panel.fitToPeaklist_radio.IsEnabled()

def test_get_params_success(panel, mock_config, mocker):
    """Verify successful parameter retrieval."""
    panel.formula_value.SetValue("C6H12O6")
    panel.exchangeLoss_value.SetValue("H")
    panel.exchangeGain_value.SetValue("D")
    panel.charge_value.SetValue("2")
    panel.scaleMin_value.SetValue("0")
    panel.scaleMax_value.SetValue("5")
    panel.fwhm_value.SetValue("0.02")
    panel.forceFwhm_check.SetValue(True)
    panel.autoAlign_check.SetValue(False)
    panel.relThreshold_value.SetValue("1.0")
    panel.fitToSpectrum_radio.SetValue(True)
    
    mocker.patch('mspy.compound')
    assert panel.getParams() is True
    
    assert config.envelopeFit['loss'] == "H"
    assert config.envelopeFit['gain'] == "D"
    assert config.envelopeFit['fit'] == 'spectrum'
    assert config.envelopeFit['charge'] == 2
    assert config.envelopeFit['scaleMin'] == 0
    assert config.envelopeFit['scaleMax'] == 5
    assert config.envelopeFit['fwhm'] == 0.02
    assert config.envelopeFit['forceFwhm'] is True
    assert config.envelopeFit['autoAlign'] is False
    assert config.envelopeFit['relThreshold'] == 0.01

def test_get_params_failure(panel, mocker):
    """Verify parameter retrieval failure on invalid input."""
    panel.formula_value.SetValue("") # Empty formula
    mock_bell = mocker.patch('wx.Bell')
    assert panel.getParams() is False
    mock_bell.assert_called_once()

def test_update_average_label(panel, mocker):
    """Verify average label updates."""
    # Case 1: No current fit
    panel.currentFit = None
    panel.updateAverageLabel()
    assert panel.average_label.GetLabel() == "Average X: "
    
    # Case 2: With fit
    panel.currentFit = mocker.Mock()
    panel.currentFit.average = 150.5
    panel.updateAverageLabel()
    assert panel.average_label.GetLabel() == "Average X: 150.5"

# Step 5: Visual Update Logic Tests

def test_update_spectrum_canvas(panel, mocker):
    """Verify updateSpectrumCanvas behavior."""
    # Case 1: currentFit is None
    panel.currentFit = None
    mock_draw = mocker.patch.object(panel.spectrumCanvas, 'draw')
    panel.updateSpectrumCanvas()
    mock_draw.assert_called_once()
    panel.parent.updateTmpSpectrum.assert_called_with(None)

    # Case 2: currentFit has data
    panel.currentFit = mocker.Mock()
    panel.currentFit.spectrum = [1, 2, 3]
    panel.currentFit.data = [4, 5, 6]
    panel.currentFit.model = [7, 8, 9]
    panel.currentFit.envelope.return_value = [10, 11, 12]
    
    mocker.patch('mspy.plot.points')
    mock_append = mocker.patch.object(panel.spectrumContainer, 'append')
    mock_draw.reset_mock()
    
    panel.updateSpectrumCanvas()
    assert mock_append.call_count == 4
    mock_draw.assert_called_once()
    panel.parent.updateTmpSpectrum.assert_called_with([10, 11, 12])

def test_update_results_list(panel, mocker):
    """Verify updateResultsList behavior."""
    # Case 1: currentFit is None
    panel.currentFit = None
    mock_delete = mocker.patch.object(panel.resultsList, 'DeleteAllItems')
    panel.updateResultsList()
    mock_delete.assert_called_once()

    # Case 2: currentFit has data
    panel.currentFit = mocker.Mock()
    panel.currentFit.ncomposition.items.return_value = [(1, 0.5), (2, 0.3)]
    
    mock_insert = mocker.patch.object(panel.resultsList, 'InsertItem')
    mock_set = mocker.patch.object(panel.resultsList, 'SetItem')
    mock_set_data = mocker.patch.object(panel.resultsList, 'SetItemData')
    mocker.patch.object(panel.resultsList, 'setDataMap')
    mocker.patch.object(panel.resultsList, 'sort')
    mocker.patch.object(panel.resultsList, 'EnsureVisible')
    mocker.patch.object(panel.resultsList, 'GetItemCount', return_value=2)
    
    panel.updateResultsList()
    assert mock_insert.call_count == 2
    assert mock_set.call_count == 2
    assert mock_set_data.call_count == 2
    mock_insert.assert_any_call(0, "1")
    mock_set.assert_any_call(0, 1, "50.0")

# Step 6: Threading & Processing Logic Tests

def test_on_processing(panel, mocker):
    """Verify onProcessing behavior."""
    panel.MakeModal = mocker.Mock()
    mock_show = mocker.patch.object(panel.mainSizer, 'Show')
    mock_hide = mocker.patch.object(panel.mainSizer, 'Hide')
    mocker.patch.object(panel, 'Layout')
    mock_mspy_start = mocker.patch('mspy.start')
    
    # Status True
    panel.onProcessing(True)
    panel.MakeModal.assert_called_with(True)
    mock_show.assert_called_with(3)
    
    # Status False
    panel.onProcessing(False)
    panel.MakeModal.assert_called_with(False)
    mock_hide.assert_called_with(3)
    mock_mspy_start.assert_called_once()
    assert panel.processing is None

def test_on_calculate_no_document(panel, mocker):
    """Verify onCalculate when no document is set."""
    panel.currentDocument = None
    mock_bell = mocker.patch('wx.Bell')
    panel.onCalculate(None)
    mock_bell.assert_called_once()

def test_on_calculate_already_processing(panel, mocker):
    """Verify onCalculate when already processing."""
    panel.processing = mocker.Mock()
    mock_get_params = mocker.patch.object(panel, 'getParams')
    panel.onCalculate(None)
    mock_get_params.assert_not_called()

def test_on_calculate_get_params_failure(panel, mocker):
    """Verify onCalculate when getParams fails."""
    panel.currentDocument = mocker.Mock()
    panel.currentDocument.spectrum.hasprofile.return_value = True
    
    mocker.patch.object(panel, 'getParams', return_value=False)
    mock_avg = mocker.patch.object(panel, 'updateAverageLabel')
    panel.onCalculate(None)
    mock_avg.assert_called_once()

def test_on_calculate_success(panel, mocker):
    """Verify onCalculate successful flow."""
    panel.currentDocument = mocker.Mock()
    panel.currentDocument.spectrum.hasprofile.return_value = True
    
    mock_on_proc = mocker.patch.object(panel, 'onProcessing')
    mock_thread = mocker.patch('threading.Thread')
    mock_avg = mocker.patch.object(panel, 'updateAverageLabel')
    mock_canvas = mocker.patch.object(panel, 'updateSpectrumCanvas')
    mock_results = mocker.patch.object(panel, 'updateResultsList')
    mocker.patch.object(panel.calculate_butt, 'Enable')
    mocker.patch.object(panel, 'getParams', return_value=True)
    
    # Mock thread to be finished immediately
    thread_instance = mock_thread.return_value
    thread_instance.isAlive.return_value = False
    
    panel.currentFit = mocker.Mock()
    
    panel.onCalculate(None)
    
    mock_on_proc.assert_has_calls([mocker.call(True), mocker.call(False)])
    mock_thread.assert_called_once()
    mock_avg.assert_called()
    mock_canvas.assert_called()
    mock_results.assert_called()

def test_run_envelope_fit_peaklist(panel, mock_config, mocker):
    """Verify runEnvelopeFit for peaklist fitting."""
    config.envelopeFit['fit'] = 'peaklist'
    panel.currentCompound = mocker.Mock()
    panel.currentCompound.formula.return_value = "C6H12O6"
    panel.currentDocument = mocker.Mock()
    
    mock_envfit_class = mocker.patch('mspy.envfit')
    fit_instance = mock_envfit_class.return_value
    fit_instance.topeaklist.return_value = True
    
    panel.runEnvelopeFit()
    
    mock_envfit_class.assert_called_once()
    fit_instance.topeaklist.assert_called_once()

def test_run_envelope_fit_spectrum(panel, mock_config, mocker):
    """Verify runEnvelopeFit for spectrum fitting."""
    config.envelopeFit['fit'] = 'spectrum'
    panel.currentCompound = mocker.Mock()
    panel.currentCompound.formula.return_value = "C6H12O6"
    panel.currentDocument = mocker.Mock()
    panel.currentDocument.spectrum.baseline.return_value = [0, 0, 0]
    panel.currentDocument.spectrum.profile = [1, 2, 3]
    
    mock_envfit_class = mocker.patch('mspy.envfit')
    fit_instance = mock_envfit_class.return_value
    fit_instance.tospectrum.return_value = True
    
    panel.runEnvelopeFit()
    
    mock_envfit_class.assert_called_once()
    fit_instance.tospectrum.assert_called_once()

def test_run_envelope_fit_force_quit(panel, mock_config, mocker):
    """Verify runEnvelopeFit handling mspy.ForceQuit."""
    panel.currentCompound = mocker.Mock()
    panel.currentCompound.formula.return_value = "C6H12O6"
    
    mocker.patch('mspy.envfit', side_effect=mspy.ForceQuit)
    panel.runEnvelopeFit()
    assert panel.currentFit is None

def test_run_envelope_fit_failure(panel, mock_config, mocker):
    """Verify runEnvelopeFit when fitting fails."""
    config.envelopeFit['fit'] = 'peaklist'
    panel.currentCompound = mocker.Mock()
    panel.currentCompound.formula.return_value = "C6H12O6"
    panel.currentDocument = mocker.Mock()
    
    mock_envfit_class = mocker.patch('mspy.envfit')
    fit_instance = mock_envfit_class.return_value
    fit_instance.topeaklist.return_value = False
    
    panel.runEnvelopeFit()
    
    assert panel.currentFit is False
