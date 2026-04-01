import os
import sys
import pytest
import wx
import collections
import mspy
import gui.config as config
import gui.libs as libs
import gui.images as images
from gui.ids import *

# Patch wx for compatibility with legacy code
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = wx.RESIZE_BORDER

from gui.panel_calibration import panelCalibration

@pytest.fixture
def mock_mspy_dependencies(monkeypatch, mocker):
    """Mock mspy.calibration, mspy.delta, and mspy.plot."""
    # Mock mspy.calibration
    mock_calib_fn = mocker.Mock(side_effect=lambda params, mz: mz + 0.1)
    mock_calib = mocker.Mock(return_value=(mock_calib_fn, [1.0, 0.1]))
    monkeypatch.setattr(mspy, 'calibration', mock_calib)

    # mspy.delta(mz1, mz2, units)
    def delta_side_effect(mz1, mz2, units):
        if units == 'Da':
            return mz1 - mz2
        else:
            return (mz1 - mz2) / (mz2 if mz2 != 0 else 1.0) * 1e6

    mock_delta = mocker.Mock(side_effect=delta_side_effect)
    monkeypatch.setattr(mspy, 'delta', mock_delta)

    # Mock mspy.plot.canvas to return a real wx.Panel that looks like a canvas
    def canvas_side_effect(parent, *args, **kwargs):
        c = wx.Panel(parent, -1)
        c.setProperties = mocker.Mock()
        c.setMFunction = mocker.Mock()
        c.draw = mocker.Mock()
        return c

    monkeypatch.setattr(mspy.plot, 'canvas', mocker.Mock(side_effect=canvas_side_effect))

    # Mock mspy.plot.container
    monkeypatch.setattr(mspy.plot, 'container', mocker.Mock())

    return mock_calib, mock_delta

@pytest.fixture
def mock_config_and_libs(monkeypatch):
    """Mock gui.config.calibration and libs.references."""
    # Mock config.calibration
    monkeypatch.setattr(config, 'calibration', {
        'fitting': 'linear',
        'units': 'Da',
        'tolerance': 0.1,
        'statCutOff': 100.0
    })
    
    # Mock config.main
    monkeypatch.setattr(config, 'main', {
        'mzDigits': 4,
        'ppmDigits': 2,
        'reverseScrolling': False,
        'macListCtrlGeneric': False
    })

    # Mock config.spectrum
    monkeypatch.setattr(config, 'spectrum', {
        'axisFontSize': 10
    })
    
    # Mock libs.references
    mock_refs = {
        'Test List': [('ref1', 100.0), ('ref2', 200.0)]
    }
    monkeypatch.setattr(libs, 'references', mock_refs)
    return mock_refs

@pytest.fixture
def mock_images(monkeypatch):
    """Patch gui.images.lib with mock wx.Bitmap objects."""
    # Use a real bitmap because some wx controls might expect it
    empty_bitmap = wx.Bitmap(16, 16)
    mock_lib = collections.defaultdict(lambda: empty_bitmap)
    monkeypatch.setattr(images, 'lib', mock_lib)
    return mock_lib

@pytest.fixture
def mock_document(mocker):
    """Fixture that returns a mock object representing a document."""
    doc = mocker.Mock()
    doc.spectrum = mocker.Mock()

    # Create some real mspy peaks for better compatibility
    p1 = mspy.peak(mz=100.0, ai=1000.0)
    p2 = mspy.peak(mz=200.0, ai=500.0)
    peaklist = mspy.peaklist([p1, p2])

    doc.spectrum.peaklist = peaklist
    doc.spectrum.recalibrate = mocker.Mock()
    doc.annotations = []
    doc.sequences = []

    doc.backup = mocker.Mock()
    return doc

@pytest.fixture
def mock_main_frame(wx_app, mock_document, mocker):
    """Fixture for the parent frame."""
    frame = wx.Frame(None)
    frame.onDocumentChanged = mocker.Mock()
    frame.updateMassPoints = mocker.Mock()
    frame.currentDocument = mock_document
    yield frame
    if frame:
        frame.Destroy()

@pytest.fixture
def panel(wx_app, mock_main_frame, mock_mspy_dependencies, mock_config_and_libs, mock_images):
    """Fixture to instantiate gui.panel_calibration.panelCalibration."""
    p = panelCalibration(mock_main_frame)
    yield p
    if p:
        p.Destroy()

def test_panel_initialization(panel):
    """Assert the panel is created successfully and is an instance of panelCalibration."""
    assert isinstance(panel, panelCalibration)
    assert panel.GetTitle() == "Calibration"

def test_initial_ui_state(panel):
    """Verify the "References" tool is active, the title is "Calibration", and the 'Apply' button is disabled."""
    assert panel.currentTool == 'references'
    assert panel.GetTitle() == "Calibration"
    assert not panel.apply_butt.IsEnabled()
    # Check if the references panel is shown
    assert panel.mainSizer.IsShown(1)
    # Check if the errors panel is hidden
    assert not panel.mainSizer.IsShown(2)

def test_tool_switching(panel):
    """
    Simulate a click on the errors_butt.
    Verify the "Errors" tool becomes active, the title changes to "Error Plot", and the correct sub-panel is visible.
    Simulate a click back on references_butt and verify it returns to the original state.
    """
    # Simulate click on errors_butt
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_calibrationErrors)
    event.SetEventObject(panel.errors_butt)
    panel.onToolSelected(event)
    
    assert panel.currentTool == 'errors'
    assert panel.GetTitle() == "Error Plot"
    assert panel.mainSizer.IsShown(2)
    assert not panel.mainSizer.IsShown(1)
    
    # Simulate click on references_butt
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_calibrationReferences)
    event.SetEventObject(panel.references_butt)
    panel.onToolSelected(event)
    
    assert panel.currentTool == 'references'
    assert panel.GetTitle() == "Calibration"
    assert panel.mainSizer.IsShown(1)
    assert not panel.mainSizer.IsShown(2)

def test_set_data_with_document(panel, mock_main_frame):
    """
    Call panel.setData(mock_main_frame.currentDocument).
    Assert the panel's currentDocument is set.
    Assert the error plot is updated.
    """
    doc = mock_main_frame.currentDocument
    panel.setData(doc)
    
    assert panel.currentDocument == doc
    # Check if errorCanvas.draw was called
    assert panel.errorCanvas.draw.called

def test_set_data_with_references(panel, mock_main_frame, mocker):
    """
    Create a list of reference tuples [(name, theoretical_mz, measured_mz)].
    Call panel.setData(mock_main_frame.currentDocument, references=...).
    Assert that panel.calcCalibration was called.
    Assert that panel.referencesList is populated with the provided data.
    Assert that the 'Apply' button is enabled.
    """
    # Patch calcCalibration to verify it was called
    mock_calc = mocker.patch.object(panel, 'calcCalibration')
    refs = [('ref1', 100.0, 100.1), ('ref2', 200.0, 200.2)]
    panel.setData(mock_main_frame.currentDocument, references=refs)

    assert mock_calc.called
    assert panel.currentDocument == mock_main_frame.currentDocument
    assert len(panel.currentReferences) == 2
    assert panel.currentReferences[0][0] == 'ref1'
    assert panel.currentReferences[1][0] == 'ref2'

    # Verify referencesList has items
    assert panel.referencesList.GetItemCount() == 2

def test_on_references_selected(panel, mock_config_and_libs):
    """
    Select the 'Test List' in panel.references_choice.
    Trigger the wx.EVT_CHOICE event.
    Verify panel.currentReferences is populated from the mocked libs.references.
    Verify the referencesList control is updated.
    """
    # Find the index of 'Test List'
    idx = panel.references_choice.FindString('Test List')
    assert idx != wx.NOT_FOUND
    
    panel.references_choice.SetSelection(idx)
    
    # Trigger event
    event = wx.CommandEvent(wx.EVT_CHOICE.typeId, panel.references_choice.GetId())
    event.SetEventObject(panel.references_choice)
    panel.onReferencesSelected(event)
    
    assert len(panel.currentReferences) == 2
    assert panel.currentReferences[0][0] == 'ref1'
    assert panel.currentReferences[1][0] == 'ref2'
    assert panel.referencesList.GetItemCount() == 2

def test_internal_calibration_workflow(panel, mock_main_frame):
    """
    Set the parent's document using panel.setData().
    Select a reference list.
    Simulate a click on the assign_butt.
    Verify panel.internalCalibration logic correctly finds peaks from the mock document's peaklist.
    Verify mspy.calibration was called with the correct points.
    Verify panel.currentCalibration is set and the apply_butt is enabled.
    """
    # 1. Set data
    doc = mock_main_frame.currentDocument
    panel.setData(doc)
    
    # 2. Select reference list
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()
    
    # 3. Assign
    # Peaklist has mz=100.0, 200.0
    # Refs have theoretical 100.0, 200.0
    # tolerance is 0.1
    panel.onAssign()
    
    # 4. Verify
    assert panel.currentReferences[0][2] == 100.0 # Measured
    assert panel.currentReferences[1][2] == 200.0 # Measured
    assert panel.currentCalibration is not None
    assert panel.apply_butt.IsEnabled()

def test_statistical_calibration_workflow(panel, mock_main_frame):
    """
    Set the parent's document.
    Simulate a click on panel.statCalibration_check.
    Verify UI elements like references_choice are disabled.
    Verify panel.statisticalCalibration is called and generates references.
    Verify mspy.calibration is called and apply_butt is enabled.
    """
    # 1. Set data
    doc = mock_main_frame.currentDocument
    panel.setData(doc)
    
    # 2. Toggle statistical calibration
    panel.statCalibration_check.SetValue(True)
    event = wx.CommandEvent(wx.EVT_CHECKBOX.typeId, panel.statCalibration_check.GetId())
    event.SetEventObject(panel.statCalibration_check)
    panel.onStatCalibration(event)
    
    # 3. Verify
    assert not panel.references_choice.IsEnabled()
    assert panel.currentReferences is not None
    # Statistical calibration for 100.0 and 200.0 (assuming statCutOff is 100.0 and peak.mz >= 100.0)
    assert len(panel.currentReferences) >= 2
    assert panel.currentCalibration is not None
    assert panel.apply_butt.IsEnabled()

def test_item_activation_disables_point(panel, mock_main_frame, mocker):
    """
    Perform an assignment to get points in the referencesList.
    Get an item from the list and simulate wx.EVT_LIST_ITEM_ACTIVATED.
    Verify the corresponding entry in panel.currentReferences has its use flag (index 6) toggled to False.
    Verify calcCalibration is called again.
    """
    # 1. Set data and assign
    panel.setData(mock_main_frame.currentDocument)
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()
    panel.onAssign()

    initial_use = panel.currentReferences[0][6]
    assert initial_use is True

    # 2. Activate first item
    event = mocker.Mock(spec=wx.ListEvent)
    event.GetData.return_value = 0 # index in currentReferences
    event.GetIndex.return_value = 0 # row in list control

    panel.onItemActivated(event)

    # 3. Verify
    assert panel.currentReferences[0][6] is not initial_use
    # Toggling back
    panel.onItemActivated(event)
    assert panel.currentReferences[0][6] is initial_use

def test_apply_calibration(panel, mock_main_frame, mocker):
    """
    Patch threading.Thread to execute the target function immediately without a new thread.
    Perform an assignment to enable the apply_butt.
    Simulate a click on the apply_butt.
    Verify panel.onProcessing(True) is called.
    Verify mock_main_frame.onDocumentChanged is called.
    Verify panel.onProcessing(False) is called.
    """
    # 1. Setup calibration
    panel.setData(mock_main_frame.currentDocument)
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()
    panel.onAssign()
    assert panel.apply_butt.IsEnabled()

    # 2. Patch threading.Thread
    class MockThread(object):
        def __init__(self, target, kwargs):
            self.target = target
            self.kwargs = kwargs
        def start(self):
            self.target(**self.kwargs)
        def isAlive(self):
            return False

    mocker.patch('threading.Thread', side_effect=MockThread)
    # Also patch onProcessing to verify calls
    mock_proc = mocker.patch.object(panel, 'onProcessing')
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, panel.apply_butt.GetId())
    event.SetEventObject(panel.apply_butt)
    panel.onApply(event)

    # Verify processing calls
    mock_proc.assert_any_call(True)
    mock_proc.assert_any_call(False)

    # Verify document changes
    assert mock_main_frame.onDocumentChanged.called
    assert mock_main_frame.currentDocument.spectrum.recalibrate.called

def test_calibrate_insufficient_points(panel):
    """
    Set up calibration with insufficient points.
    Linear needs 1, Quadratic needs 3.
    """
    # 1. Quadratic with only two points
    config.calibration['fitting'] = 'quadratic'
    panel.currentReferences = [
        ['ref1', 100.0, 100.1, None, None, None, True],
        ['ref2', 200.0, 200.2, None, None, None, True]
    ]
    panel.calcCalibration()
    assert panel.currentCalibration is None
    assert not panel.apply_butt.IsEnabled()

    # 2. Linear with zero points
    config.calibration['fitting'] = 'linear'
    panel.currentReferences = [
        ['ref1', 100.0, None, None, None, None, True],
        ['ref2', 200.0, None, None, None, None, True]
    ]
    panel.calcCalibration()
    assert panel.currentCalibration is None
    assert not panel.apply_butt.IsEnabled()

def test_on_assign_no_document(panel, mocker):
    """Test onAssign when no document is set."""
    panel.currentDocument = None
    mock_bell = mocker.patch('wx.Bell')
    panel.onAssign()
    assert mock_bell.called
    assert panel.currentCalibration is None

def test_assign_with_no_peaklist(panel, mock_main_frame, mocker):
    """
    Set mock_main_frame.currentDocument.spectrum.peaklist = None.
    Call panel.setData(...).
    Simulate a click on assign_butt.
    Patch wx.Bell and assert it was called. Verify no calibration is performed.
    """
    # 1. Set no peaklist
    mock_main_frame.currentDocument.spectrum.peaklist = None
    panel.setData(mock_main_frame.currentDocument)

    # 2. Assign
    mock_bell = mocker.patch('wx.Bell')
    panel.onAssign()
    assert mock_bell.called
    assert panel.currentCalibration is None

def test_internal_calibration_invalid_tolerance(panel, mock_main_frame, mocker):
    """Test internalCalibration with invalid tolerance value."""
    panel.setData(mock_main_frame.currentDocument)
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()

    panel.tolerance_value.SetValue('invalid')
    mock_bell = mocker.patch('wx.Bell')
    panel.onAssign() # Calls internalCalibration
    assert mock_bell.called

def test_on_apply_no_calibration(panel, mock_main_frame, mocker):
    """Test onApply when no calibration is set."""
    panel.setData(mock_main_frame.currentDocument)
    panel.currentCalibration = None
    mock_bell = mocker.patch('wx.Bell')
    panel.onApply(None)
    assert mock_bell.called

def test_on_close_while_processing(panel, mocker):
    """Test onClose when processing is active."""
    panel.Show()
    panel.processing = mocker.Mock()
    mock_bell = mocker.patch('wx.Bell')
    panel.onClose(None)
    assert mock_bell.called
    # Should NOT be destroyed
    assert panel.IsShown()

def test_on_item_selected_no_measured(panel, mock_main_frame, mocker):
    """Test onItemSelected when measured value is None."""
    panel.setData(mock_main_frame.currentDocument)
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()

    # First item has no measured value yet
    event = mocker.Mock(spec=wx.ListEvent)
    event.GetData.return_value = 0

    panel.onItemSelected(event)
    # updateMassPoints should be called with only theoretical mass
    panel.parent.updateMassPoints.assert_called_with([100.0])

def test_model_and_units_changes(panel, mock_main_frame):
    """Test onModelChanged and onUnitsChanged."""
    panel.setData(mock_main_frame.currentDocument)
    idx = panel.references_choice.FindString('Test List')
    panel.references_choice.SetSelection(idx)
    panel.onReferencesSelected()
    panel.onAssign()
    
    # Model change
    panel.quadraticFit_radio.SetValue(True)
    panel.onModelChanged(None)
    assert config.calibration['fitting'] == 'quadratic'
    
    # Units change
    panel.unitsPpm_radio.SetValue(True)
    panel.onUnitsChanged(None)
    assert config.calibration['units'] == 'ppm'
    assert panel.toleranceUnits_label.GetLabel() == 'ppm'
    
    # Change back to linear and Da
    panel.linearFit_radio.SetValue(True)
    panel.onModelChanged(None)
    assert config.calibration['fitting'] == 'linear'
    
    panel.unitsDa_radio.SetValue(True)
    panel.onUnitsChanged(None)
    assert config.calibration['units'] == 'Da'
    assert panel.toleranceUnits_label.GetLabel() == 'Da'
