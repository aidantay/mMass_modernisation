import numpy
import pytest
import wx

# Monkeypatch wx.RESIZE_BOX before importing gui.panel_processing
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = 0

from gui.ids import *
from gui.panel_processing import dlgPresetsName, panelProcessing

import mspy
from gui import config, doc, libs


@pytest.fixture
def mock_config(mocker):
    """Mock config.processing."""
    mock_processing = {
        "crop": {"lowMass": 0.0, "highMass": 1000.0},
        "baseline": {"precision": 20, "offset": 0.1},
        "smoothing": {"method": "MA", "windowSize": 0.5, "cycles": 1},
        "peakpicking": {
            "snThreshold": 3.0,
            "absIntThreshold": 100.0,
            "relIntThreshold": 0.01,
            "pickingHeight": 0.8,
            "baseline": True,
            "smoothing": True,
            "deisotoping": True,
            "removeShoulders": False,
        },
        "deisotoping": {
            "maxCharge": 1,
            "massTolerance": 0.1,
            "intTolerance": 0.5,
            "isotopeShift": 0.0,
            "removeIsotopes": False,
            "removeUnknown": False,
            "setAsMonoisotopic": True,
            "labelEnvelope": "monoisotope",
            "envelopeIntensity": "maximum",
        },
        "deconvolution": {
            "massType": 0,
            "groupWindow": 0.5,
            "groupPeaks": True,
            "forceGroupWindow": False,
        },
        "batch": {
            "swap": False,
            "math": False,
            "crop": False,
            "baseline": False,
            "smoothing": False,
            "peakpicking": False,
            "deisotoping": False,
            "deconvolution": False,
        },
        "math": {"operation": "normalize", "multiplier": 1.0},
    }
    mocker.patch.dict(config.processing, mock_processing, clear=True)
    return config.processing


@pytest.fixture
def mock_images(mocker):
    """Mock images.lib."""
    mock_lib = mocker.MagicMock()
    mock_lib.__getitem__.return_value = wx.Bitmap(1, 1)
    # Patch in multiple places to ensure coverage
    mocker.patch("gui.images.lib", mock_lib)
    from gui import images as img_mod

    img_mod.lib = mock_lib
    return mock_lib


@pytest.fixture
def mock_parent(wx_app, mocker):
    """Mock parent frame."""
    # Use a real wx.Frame so it's accepted by wx.MiniFrame
    parent = wx.Frame(None)
    parent.documents = []
    parent.onDocumentNew = mocker.Mock()
    parent.onDocumentChanged = mocker.Mock()
    parent.onDocumentChangedMulti = mocker.Mock()
    parent.updateTmpSpectrum = mocker.Mock()

    parent.spectrumPanel = mocker.Mock()
    parent.spectrumPanel.spectrumCanvas = mocker.Mock()
    parent.spectrumPanel.spectrumCanvas.setProperties = mocker.Mock()

    yield parent
    if parent:
        parent.Destroy()


@pytest.fixture
def panel(mock_parent, mock_config, mock_images, mocker):
    """Fixture for panelProcessing."""
    # Mock Slider.SetTickFreq because it might have incompatible signature in some wx versions
    mocker.patch("wx.Slider.SetTickFreq")

    mocker.patch("mspy.start")
    mocker.patch("mspy.stop")
    p = panelProcessing(mock_parent)
    yield p
    if p:
        p.Destroy()


def test_init(panel):
    """Test initialization."""
    assert panel.GetTitle() == "Peak Picking"
    assert panel.currentTool == "peakpicking"
    assert panel.currentDocument is None


def test_onToolSelected(panel, mock_images):
    """Test switching between tools."""
    tools = [
        (ID_processingMath, "Math Operations"),
        (ID_processingCrop, "Crop"),
        (ID_processingBaseline, "Baseline Correction"),
        (ID_processingSmoothing, "Smoothing"),
        (ID_processingPeakpicking, "Peak Picking"),
        (ID_processingDeisotoping, "Deisotoping"),
        (ID_processingDeconvolution, "Deconvolution"),
        (ID_processingBatch, "Batch Processing"),
    ]

    for tool_id, expected_title in tools:
        evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, tool_id)
        panel.onToolSelected(evt)
        assert panel.GetTitle() == expected_title


def test_onClose(panel, mocker):
    """Test closing the panel."""
    # Mock Destroy to verify it's called
    destroy_mock = mocker.patch.object(panel, "Destroy")

    # Test closing when not processing
    panel.processing = None
    panel.onClose(None)
    destroy_mock.assert_called_once()

    # Test closing when processing
    destroy_mock.reset_mock()
    panel.processing = mocker.Mock()
    bell_mock = mocker.patch("wx.Bell")
    panel.onClose(None)
    bell_mock.assert_called_once()
    destroy_mock.assert_not_called()


def test_setData(panel, mocker):
    """Test setting current document."""
    doc_obj = mocker.MagicMock()
    doc_obj.title = "Test Doc"
    doc_obj.colour = (0, 0, 0)
    # Ensure spectrum.profile is a numpy array to avoid TypeError in basepeak
    doc_obj.spectrum.profile = numpy.array([[100, 10], [200, 20]])
    panel.parent.documents = [doc_obj]

    # Mock makeThresholdLine to avoid deep calls
    mocker.patch.object(panel, "makeThresholdLine", return_value=[])

    panel.setData(doc_obj)
    assert panel.currentDocument == doc_obj
    # Verify Spectrum A choice updated
    assert panel.mathSpectrumA_choice.GetString(0) == "#1: Test Doc"


def test_updateAvailableDocuments(panel, mocker):
    """Test updating available documents."""
    doc1 = mocker.MagicMock()
    doc1.title = "Doc 1"
    doc1.colour = (255, 0, 0)

    doc2 = mocker.MagicMock()
    doc2.title = "Doc 2"
    doc2.colour = (0, 255, 0)

    panel.parent.documents = [doc1, doc2]
    panel.updateAvailableDocuments()

    # Check Math Spectrum B choice
    assert panel.mathSpectrumB_choice.GetCount() == 3  # None, Doc 1, Doc 2
    assert panel.mathSpectrumB_choice.GetString(1) == "#1: Doc 1"
    assert panel.mathSpectrumB_choice.GetString(2) == "#2: Doc 2"

    # Check Batch Documents List
    assert panel.batchDocumentsList.GetItemCount() == 2
    assert panel.batchDocumentsList.GetItemText(0) == "Doc 1"
    assert panel.batchDocumentsList.GetItemText(1) == "Doc 2"


def test_getParams_success(panel, mock_config):
    """Test getting parameters from UI."""
    # Set some values in UI
    panel.cropLowMass_value.SetValue("100.5")
    panel.cropHighMass_value.SetValue("2000.0")
    panel.baselinePrecision_slider.SetValue(50)
    panel.baselineOffset_slider.SetValue(20)  # 20%

    assert panel.getParams() is True

    assert mock_config["crop"]["lowMass"] == 100.5
    assert mock_config["crop"]["highMass"] == 2000.0
    assert mock_config["baseline"]["precision"] == 50.0
    assert mock_config["baseline"]["offset"] == 0.2


def test_getParams_branches(panel, mock_config):
    """Test getParams branches for various controls."""
    # Math operations
    math_ops = [
        (panel.mathOperationAverageAll_radio, "averageall"),
        (panel.mathOperationCombineAll_radio, "combineall"),
        (panel.mathOperationOverlayAll_radio, "overlayall"),
        (panel.mathOperationNorm_radio, "normalize"),
        (panel.mathOperationCombine_radio, "combine"),
        (panel.mathOperationOverlay_radio, "overlay"),
        (panel.mathOperationSubtract_radio, "subtract"),
        (panel.mathOperationMultiply_radio, "multiply"),
    ]
    for radio, expected in math_ops:
        radio.SetValue(True)
        panel.getParams()
        assert mock_config["math"]["operation"] == expected

    # Smoothing methods
    smoothing_methods = [
        ("Moving Average", "MA"),
        ("Gaussian", "GA"),
        ("Savitzky-Golay", "SG"),
    ]
    for selection, expected in smoothing_methods:
        panel.smoothingMethod_choice.SetStringSelection(selection)
        panel.getParams()
        assert mock_config["smoothing"]["method"] == expected

    # Label envelopes
    envelopes = [
        ("1st Selected", "1st"),
        ("Monoisotopic Mass", "monoisotope"),
        ("Envelope Centroid", "centroid"),
        ("All Isotopes", "isotopes"),
    ]
    for selection, expected in envelopes:
        panel.deisotopingLabelEnvelopeTool_choice.SetStringSelection(selection)
        panel.getParams()
        assert mock_config["deisotoping"]["labelEnvelope"] == expected

    # Envelope intensity
    intensities = [
        ("Envelope Maximum", "maximum"),
        ("Summed Isotopes", "sum"),
        ("Averaged Isotopes", "average"),
    ]
    for selection, expected in intensities:
        panel.deisotopingEnvelopeIntensity_choice.SetStringSelection(selection)
        panel.getParams()
        assert mock_config["deisotoping"]["envelopeIntensity"] == expected


def test_getParams_failure(panel, mocker):
    """Test getting parameters failure (invalid input)."""
    # mathMultiply_value has floatPos validator but we can force text
    panel.mathMultiply_value.SetValue("abc")

    bell_mock = mocker.patch("wx.Bell")
    assert panel.getParams() is False
    bell_mock.assert_called_once()


def test_onPresets(panel, mocker):
    """Test showing presets menu."""
    mocker.patch.dict(libs.presets, {"processing": {"Preset1": {}}}, clear=True)

    # Mock Menu and PopupMenu
    mock_menu = mocker.patch("wx.Menu", autospec=True)
    mock_popup = mocker.patch.object(panel, "PopupMenu")

    panel.onPresets(None)

    # Verify Preset1 was added
    mock_menu.return_value.Append.assert_any_call(-1, "Preset1")
    mock_popup.assert_called_once()


def test_onPresetsSelected(panel, mocker):
    """Test loading presets."""
    presets_data = {
        "crop": {"lowMass": 10, "highMass": 500},
        "baseline": {"precision": 10, "offset": 0.05},
        "smoothing": {"method": "GA", "windowSize": 0.1, "cycles": 2},
        "peakpicking": {
            "snThreshold": 5,
            "absIntThreshold": 10,
            "relIntThreshold": 0.05,
            "pickingHeight": 0.5,
            "baseline": False,
            "smoothing": False,
            "deisotoping": False,
            "removeShoulders": True,
        },
        "deisotoping": {
            "maxCharge": 5,
            "massTolerance": 0.05,
            "intTolerance": 0.1,
            "isotopeShift": 0.01,
            "removeIsotopes": True,
            "removeUnknown": True,
            "setAsMonoisotopic": False,
            "labelEnvelope": "centroid",
            "envelopeIntensity": "sum",
        },
        "deconvolution": {
            "massType": 1,
            "groupWindow": 0.1,
            "groupPeaks": False,
            "forceGroupWindow": True,
        },
        "batch": {
            "swap": True,
            "math": True,
            "crop": True,
            "baseline": True,
            "smoothing": True,
            "peakpicking": True,
            "deisotoping": True,
            "deconvolution": True,
        },
    }
    mocker.patch.dict(libs.presets["processing"], {"MyPreset": presets_data})

    panel.presets_popup = mocker.Mock()
    panel.presets_popup.FindItemById.return_value.GetText.return_value = "MyPreset"

    evt = mocker.Mock()
    panel.onPresetsSelected(evt)

    assert panel.cropLowMass_value.GetValue() == "10"
    assert panel.smoothingMethod_choice.GetSelection() == 1  # Gaussian
    assert (
        panel.deisotopingLabelEnvelopeTool_choice.GetSelection() == 2
    )  # Envelope Centroid
    assert (
        panel.deisotopingEnvelopeIntensity_choice.GetSelection() == 1
    )  # Summed Isotopes


def test_onPresetsSave(panel, mocker):
    """Test saving presets."""
    # Mock dlgPresetsName
    mock_dlg = mocker.patch("gui.panel_processing.dlgPresetsName")
    mock_dlg.return_value.ShowModal.return_value = wx.ID_OK
    mock_dlg.return_value.name = "NewPreset"

    save_mock = mocker.patch("gui.libs.savePresets")

    # Ensure getParams returns True
    mocker.patch.object(panel, "getParams", return_value=True)

    panel.onPresetsSave(None)

    assert "NewPreset" in libs.presets["processing"]
    save_mock.assert_called_once()


def test_dlgPresetsName(wx_app, mock_parent, mocker):
    """Test dlgPresetsName dialog."""
    dlg = dlgPresetsName(mock_parent)
    dlg.name_value.SetValue("MyPreset")

    # Mock EndModal
    end_modal_mock = mocker.patch.object(dlg, "EndModal")
    # Trigger onOK
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, wx.ID_OK)
    dlg.onOK(evt)
    assert dlg.name == "MyPreset"
    end_modal_mock.assert_called_with(wx.ID_OK)

    dlg.Destroy()


def test_dlgPresetsName_empty(wx_app, mock_parent, mocker):
    """Test dlgPresetsName with empty name."""
    dlg = dlgPresetsName(mock_parent)
    dlg.name_value.SetValue("")

    bell_mock = mocker.patch("wx.Bell")
    mocker.patch.object(dlg, "EndModal")
    evt = wx.CommandEvent(wx.EVT_BUTTON.typeId, wx.ID_OK)
    dlg.onOK(evt)
    bell_mock.assert_called_once()

    dlg.Destroy()


def test_onMathChanged(panel):
    """Test math panel UI changes."""
    # Group operations
    panel.mathOperationAverageAll_radio.SetValue(True)
    panel.onMathChanged()
    assert not panel.mathSpectrumB_choice.IsEnabled()
    assert not panel.mathMultiply_value.IsEnabled()
    assert not panel.batchMath_check.IsEnabled()

    # Single operations
    panel.mathOperationCombine_radio.SetValue(True)
    panel.onMathChanged()
    assert panel.mathSpectrumB_choice.IsEnabled()
    assert not panel.mathMultiply_value.IsEnabled()

    panel.mathOperationMultiply_radio.SetValue(True)
    panel.onMathChanged()
    assert not panel.mathSpectrumB_choice.IsEnabled()
    assert panel.mathMultiply_value.IsEnabled()


def test_onBaselineChanged(panel, mocker):
    """Test baseline preview calculation."""
    panel.onToolSelected(tool="baseline")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    doc_obj.spectrum.baseline.return_value = numpy.array([[100, 5], [200, 5]])
    panel.currentDocument = doc_obj

    panel.onBaselineChanged()

    panel.parent.updateTmpSpectrum.assert_called()
    assert panel.previewData == [[100, 5], [200, 5]]


def test_onPeakpickingChanged(panel, mocker):
    """Test peakpicking preview (threshold line)."""
    panel.onToolSelected(tool="peakpicking")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    panel.currentDocument = doc_obj

    # Mock makeThresholdLine
    mocker.patch.object(panel, "makeThresholdLine", return_value=[[0, 10], [1000, 10]])

    panel.onPeakpickingChanged()

    panel.parent.updateTmpSpectrum.assert_called_with([[0, 10], [1000, 10]])


def test_onPreview_baseline(panel, mocker, sync_thread):
    """Test preview for baseline subtraction."""
    panel.onToolSelected(tool="baseline")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    doc_obj.spectrum.profile = numpy.array([[100, 10], [200, 20]])
    doc_obj.spectrum.baseline.return_value = numpy.array([[100, 5], [200, 5]])
    panel.currentDocument = doc_obj

    mocker.patch("mspy.subbase", return_value=numpy.array([[100, 5], [200, 15]]))

    panel.onPreview(None)

    assert panel.previewData is not None
    panel.parent.updateTmpSpectrum.assert_called()


def test_onPreview_smoothing(panel, mocker, sync_thread):
    """Test preview for smoothing."""
    panel.onToolSelected(tool="smoothing")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    doc_obj.spectrum.profile = numpy.array([[100, 10], [200, 20]])
    panel.currentDocument = doc_obj

    mocker.patch("mspy.smooth", return_value=numpy.array([[100, 11], [200, 19]]))

    panel.onPreview(None)

    assert panel.previewData is not None
    panel.parent.updateTmpSpectrum.assert_called()


def test_onBatchChanged(panel):
    """Test batch processing conflicts."""
    panel.batchPeakpicking_check.SetValue(True)
    panel.peakpickingBaseline_check.SetValue(True)

    panel.onBatchChanged()

    assert not panel.batchBaseline_check.IsEnabled()
    assert not panel.batchBaseline_check.GetValue()


@pytest.fixture
def sync_thread(mocker):
    """Patch threading.Thread to run target synchronously."""

    def mock_init(
        self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None
    ):
        self._target = target
        self._args = args
        self._kwargs = kwargs if kwargs is not None else {}

    def mock_start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)

    mocker.patch("threading.Thread.__init__", mock_init)
    mocker.patch("threading.Thread.start", mock_start)
    mocker.patch("threading.Thread.is_alive", return_value=False)


def test_onPreview_math(panel, mocker, sync_thread):
    """Test preview for math operations."""
    panel.onToolSelected(tool="math")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.profile = numpy.array([[100, 10], [200, 20]])
    panel.currentDocument = doc_obj

    mocker.patch("mspy.normalize", return_value=numpy.array([[100, 0.1], [200, 0.2]]))
    mocker.patch("mspy.multiply", return_value=numpy.array([[100, 10], [200, 20]]))

    panel.onPreview(None)

    assert panel.previewData is not None
    panel.parent.updateTmpSpectrum.assert_called()


def test_onApply_crop(panel, mocker, sync_thread):
    """Test applying crop."""
    panel.onToolSelected(tool="crop")

    doc_obj = mocker.MagicMock()
    doc_obj.annotations = []
    doc_obj.sequences = []
    panel.currentDocument = doc_obj

    panel.cropLowMass_value.SetValue("100")
    panel.cropHighMass_value.SetValue("500")

    panel.onApply(None)

    doc_obj.spectrum.crop.assert_called_with(100.0, 500.0)
    panel.parent.onDocumentChanged.assert_called()


def test_onApply_baseline(panel, mocker, sync_thread):
    """Test applying baseline subtraction."""
    panel.onToolSelected(tool="baseline")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    panel.currentDocument = doc_obj

    panel.onApply(None)

    doc_obj.spectrum.subbase.assert_called()
    panel.parent.onDocumentChanged.assert_called()


def test_onApply_smoothing(panel, mocker, sync_thread):
    """Test applying smoothing."""
    panel.onToolSelected(tool="smoothing")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    panel.currentDocument = doc_obj

    panel.onApply(None)

    doc_obj.spectrum.smooth.assert_called()
    panel.parent.onDocumentChanged.assert_called()


def test_onApply_peakpicking(panel, mocker, sync_thread):
    """Test applying peak picking."""
    panel.onToolSelected(tool="peakpicking")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.hasprofile.return_value = True
    doc_obj.spectrum.profile = numpy.array([[100, 10], [200, 20]], dtype=numpy.float64)
    doc_obj.annotations = []
    doc_obj.sequences = []
    panel.currentDocument = doc_obj

    panel.onApply(None)

    doc_obj.spectrum.labelscan.assert_called()
    panel.parent.onDocumentChanged.assert_called()


def test_runApplyMath_forcequit(panel, mocker):
    """Test ForceQuit exception in runApplyMath."""
    panel.onToolSelected(tool="math")
    panel.mathOperationNorm_radio.SetValue(True)
    panel.currentDocument = mocker.Mock()

    # Mock backup to raise ForceQuit
    panel.currentDocument.backup.side_effect = mspy.ForceQuit()

    # runApplyMath should catch ForceQuit and return
    panel.runApplyMath()

    # Verify no bell on cancel
    # Actually runApplyMath doesn't ring bell on ForceQuit


def test_runPreviewMath_no_doc(panel, mocker):
    """Test runPreviewMath with no current document."""
    panel.onToolSelected(tool="math")
    panel.mathOperationNorm_radio.SetValue(True)
    panel.currentDocument = None

    bell_mock = mocker.patch("wx.Bell")
    panel.runPreviewMath()
    bell_mock.assert_called_once()


def test_runApplyMath_no_doc(panel, mocker):
    """Test runApplyMath with no current document."""
    panel.onToolSelected(tool="math")
    panel.mathOperationNorm_radio.SetValue(True)
    panel.currentDocument = None

    bell_mock = mocker.patch("wx.Bell")
    panel.runApplyMath()
    bell_mock.assert_called_once()


def test_onApply_deisotoping(panel, mocker, sync_thread):
    """Test applying deisotoping."""
    panel.onToolSelected(tool="deisotoping")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.haspeaks.return_value = True
    doc_obj.annotations = []
    doc_obj.sequences = []
    panel.currentDocument = doc_obj

    panel.onApply(None)

    doc_obj.spectrum.deisotope.assert_called()
    panel.parent.onDocumentChanged.assert_called()


def test_onApply_math_averageall(panel, mocker, sync_thread):
    """Test applying average all math."""
    panel.onToolSelected(tool="math")
    panel.mathOperationAverageAll_radio.SetValue(True)

    doc1 = mocker.MagicMock()
    doc1.visible = True
    doc1.title = "Doc1"
    panel.parent.documents = [doc1]

    # Mock doc.document()
    mock_new_doc = mocker.MagicMock()
    mocker.patch.object(doc, "document", return_value=mock_new_doc)

    panel.onApply(None)

    panel.parent.onDocumentNew.assert_called()
    mock_new_doc.spectrum.combine.assert_called()
    mock_new_doc.spectrum.multiply.assert_called()


def test_onApply_math_single(panel, mocker, sync_thread):
    """Test applying single spectrum math operations."""
    panel.onToolSelected(tool="math")

    doc1 = mocker.MagicMock()
    doc1.title = "Doc1"
    doc1.colour = (255, 0, 0)
    doc2 = mocker.MagicMock()
    doc2.title = "Doc2"
    doc2.colour = (0, 255, 0)
    panel.parent.documents = [doc1, doc2]
    panel.currentDocument = doc1

    # Mock updateAvailableDocuments to populate choices
    panel.updateAvailableDocuments()

    # Normalize
    panel.mathOperationNorm_radio.SetValue(True)
    panel.onApply(None)
    doc1.spectrum.normalize.assert_called()

    # Combine
    panel.mathOperationCombine_radio.SetValue(True)
    panel.mathSpectrumB_choice.Select(2)  # Select Doc2 (#2: Doc2)
    panel.onApply(None)
    # The actual call might pass the spectrum profile depending on some internal mspy logic but gui says it passes spectrum object
    doc1.spectrum.combine.assert_called()

    # Overlay
    panel.mathOperationOverlay_radio.SetValue(True)
    panel.onApply(None)
    doc1.spectrum.overlay.assert_called()

    # Subtract
    panel.mathOperationSubtract_radio.SetValue(True)
    panel.onApply(None)
    doc1.spectrum.subtract.assert_called()

    # Multiply
    panel.mathOperationMultiply_radio.SetValue(True)
    panel.mathMultiply_value.SetValue("2.5")
    panel.onApply(None)
    doc1.spectrum.multiply.assert_called_with(y=2.5)


def test_onApply_deconvolution(panel, mocker, sync_thread):
    """Test applying deconvolution."""
    panel.onToolSelected(tool="deconvolution")

    doc_obj = mocker.MagicMock()
    doc_obj.spectrum.haspeaks.return_value = True
    # Ensure at least one peak has charge to pass checkChargedPeaks
    peak = mocker.MagicMock()
    peak.charge = 1
    doc_obj.spectrum.peaklist = [peak]
    panel.currentDocument = doc_obj

    # Mock copy.deepcopy in the module it is used
    mocker.patch("gui.panel_processing.copy.deepcopy", return_value=doc_obj)

    panel.onApply(None)

    doc_obj.spectrum.deconvolute.assert_called()
    panel.parent.onDocumentNew.assert_called()


def test_runApplyBatch(panel, mocker, sync_thread):
    """Test batch processing execution."""
    panel.onToolSelected(tool="batch")

    doc1 = mocker.MagicMock()
    doc1.title = "Doc1"
    panel.parent.documents = [doc1]

    # Setup mock documents list with one item
    panel.batchDocumentsList.DeleteAllItems()
    panel.batchDocumentsList.InsertItem(0, "Doc1")
    panel.batchDocumentsList.SetItemData(0, 0)

    # Select the item
    panel.batchDocumentsList.SetItemState(
        0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
    )

    panel.batchCrop_check.SetValue(True)

    # Mock runApplyCrop to avoid real logic
    mock_run_crop = mocker.patch.object(panel, "runApplyCrop")

    panel.onApply(None)

    mock_run_crop.assert_called_with(batch=True)
    panel.parent.onDocumentChangedMulti.assert_called()


def test_runApplyBatch_all_ops(panel, mocker, sync_thread):
    """Test batch processing with all checkboxes enabled."""
    panel.onToolSelected(tool="batch")

    doc1 = mocker.MagicMock()
    doc1.title = "Doc1"
    panel.parent.documents = [doc1]

    panel.batchDocumentsList.DeleteAllItems()
    panel.batchDocumentsList.InsertItem(0, "Doc1")
    panel.batchDocumentsList.SetItemData(0, 0)
    panel.batchDocumentsList.SetItemState(
        0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED
    )

    panel.batchSwap_check.SetValue(True)
    panel.batchMath_check.SetValue(True)
    panel.batchCrop_check.SetValue(True)
    panel.batchBaseline_check.SetValue(True)
    panel.batchSmoothing_check.SetValue(True)
    panel.batchPeakpicking_check.SetValue(True)
    panel.batchDeisotoping_check.SetValue(True)
    panel.batchDeconvolution_check.SetValue(True)

    # Mock all runApply methods
    mocker.patch.object(panel, "runApplySwap")
    mocker.patch.object(panel, "runApplyMath")
    mocker.patch.object(panel, "runApplyCrop")
    mocker.patch.object(panel, "runApplyBaseline")
    mocker.patch.object(panel, "runApplySmoothing")
    mocker.patch.object(panel, "runApplyPeakpicking")
    mocker.patch.object(panel, "runApplyDeisotoping")
    mocker.patch.object(panel, "runApplyDeconvolution")

    panel.onApply(None)

    panel.runApplySwap.assert_called_with(batch=True)
    panel.runApplyMath.assert_called_with(batch=True)
    panel.runApplyCrop.assert_called_with(batch=True)
    panel.runApplyBaseline.assert_called_with(batch=True)
    panel.runApplySmoothing.assert_called_with(batch=True)
    panel.runApplyPeakpicking.assert_called_with(batch=True)
    panel.runApplyDeisotoping.assert_called_with(batch=True)
    panel.runApplyDeconvolution.assert_called_with(batch=True)


def test_onStop(panel, mocker):
    """Test stopping processing."""
    panel.processing = mocker.Mock()
    panel.processing.is_alive.return_value = True

    stop_mock = mocker.patch("mspy.stop")
    panel.onStop(None)
    stop_mock.assert_called_once()


def test_checkIsotopeMassTolerance(panel, mocker):
    """Test isotope mass tolerance validation."""
    # Update config directly as checkIsotopeMassTolerance reads from it
    config.processing["deisotoping"]["maxCharge"] = 10
    config.processing["deisotoping"]["massTolerance"] = 0.5

    # 0.5 * 10 = 5.0 > 1.0 (limit)
    dlg_mock = mocker.patch("gui.panel_processing.mwx.dlgMessage")
    dlg_mock.return_value.ShowModal.return_value = wx.ID_NO
    assert panel.checkIsotopeMassTolerance() is False
    dlg_mock.assert_called()


def test_checkChargedPeaks(panel, mocker):
    """Test charged peaks validation."""
    doc_obj = mocker.MagicMock()
    peak = mocker.MagicMock()
    peak.charge = 0  # uncharged
    doc_obj.spectrum.peaklist = [peak]
    panel.currentDocument = doc_obj

    dlg_mock = mocker.patch("gui.panel_processing.mwx.dlgMessage")
    dlg_mock.return_value.ShowModal.return_value = wx.ID_OK
    assert panel.checkChargedPeaks() is False  # returns False because no charged peaks
    dlg_mock.assert_called()
