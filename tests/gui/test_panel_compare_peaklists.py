import sys

import gui.config as config
import gui.images as images
import pytest
import wx

import mspy

# Force sys.modules to use these for 'images' and 'config' to avoid duplicates
# because gui/ modules use 'import images' whereas tests might use 'from gui import images'
sys.modules["images"] = images
sys.modules["config"] = config

from gui.panel_compare_peaklists import panelComparePeaklists


# Populate images.lib
@pytest.fixture
def setup_images(wx_app):
    """Fixture to populate images.lib after wx.App is created."""
    original_lib = images.lib.copy()
    if "bgrToolbarNoBorder" not in images.lib:
        images.lib["bgrToolbarNoBorder"] = wx.Bitmap(1, 1)
    if "stopper" not in images.lib:
        images.lib["stopper"] = wx.Bitmap(1, 1)
    if "icon16" not in images.lib:
        images.lib["icon16"] = wx.Bitmap(1, 1)
    yield
    images.lib.clear()
    images.lib.update(original_lib)


@pytest.fixture
def mock_parent(wx_app, mocker):
    """Fixture to provide a parent frame."""
    parent = wx.Frame(None)
    parent.updateMassPoints = mocker.Mock()
    yield parent
    if parent:
        parent.Destroy()


@pytest.fixture
def mock_document(mocker):
    """Fixture to provide a mocked document."""
    doc = mocker.Mock()
    doc.visible = True
    doc.colour = wx.Colour(255, 0, 0)
    doc.annotations = []
    doc.sequences = []
    doc.spectrum = mocker.Mock()
    doc.spectrum.peaklist = []
    return doc


@pytest.fixture
def panel(wx_app, mock_parent, setup_images):
    """Fixture to provide an instance of panelComparePeaklists."""
    p = panelComparePeaklists(mock_parent)
    yield p
    if p:
        p.Destroy()


def test_init(panel):
    """Test __init__ and makeGUI successfully instantiate all required wx controls."""
    assert isinstance(panel, panelComparePeaklists)
    assert panel.parent is not None
    assert hasattr(panel, "compare_choice")
    assert hasattr(panel, "tolerance_value")
    assert hasattr(panel, "unitsDa_radio")
    assert hasattr(panel, "unitsPpm_radio")
    assert hasattr(panel, "ignoreCharge_check")
    assert hasattr(panel, "ratioCheck_check")
    assert hasattr(panel, "ratioDirection_choice")
    assert hasattr(panel, "ratioThreshold_value")
    assert hasattr(panel, "compare_butt")
    assert hasattr(panel, "documentsGrid")
    assert hasattr(panel, "peaklistGrid")
    assert hasattr(panel, "matchesGrid")
    assert hasattr(panel, "gauge")


def test_getParams_success(panel):
    """Test getParams() with valid inputs."""
    panel.tolerance_value.SetValue("0.1")
    panel.unitsDa_radio.SetValue(True)
    panel.ignoreCharge_check.SetValue(True)
    panel.ratioCheck_check.SetValue(True)
    panel.ratioDirection_choice.SetSelection(0)  # 'Above'
    panel.ratioThreshold_value.SetValue("2.0")

    assert panel.getParams() is True
    assert config.comparePeaklists["tolerance"] == 0.1
    assert config.comparePeaklists["units"] == "Da"
    assert config.comparePeaklists["ignoreCharge"] == 1
    assert config.comparePeaklists["ratioCheck"] == 1
    assert config.comparePeaklists["ratioDirection"] == 1
    assert config.comparePeaklists["ratioThreshold"] == 2.0


def test_getParams_failure(panel, mocker):
    """Test getParams() failure with invalid input."""
    mocker.patch("wx.Bell")
    panel.tolerance_value.SetValue("invalid")

    assert panel.getParams() is False
    wx.Bell.assert_called_once()


def test_onRatioCheckChanged(panel):
    """Test onRatioCheckChanged enables/disables ratio controls."""
    panel.ratioCheck_check.SetValue(True)
    panel.onRatioCheckChanged()
    assert panel.ratioDirection_choice.IsEnabled() is True
    assert panel.ratioThreshold_value.IsEnabled() is True

    panel.ratioCheck_check.SetValue(False)
    panel.onRatioCheckChanged()
    assert panel.ratioDirection_choice.IsEnabled() is False
    assert panel.ratioThreshold_value.IsEnabled() is False


def test_onClose(panel, mocker):
    """Test onClose behavior."""
    mocker.patch.object(panel, "Destroy")
    mocker.patch("wx.Bell")

    # No processing
    panel.processing = None
    panel.onClose(None)
    panel.Destroy.assert_called_once()

    # With processing
    panel.Destroy.reset_mock()
    panel.processing = mocker.Mock()
    panel.onClose(None)
    wx.Bell.assert_called_once()
    panel.Destroy.assert_not_called()


def test_onStop(panel, mocker):
    """Test onStop behavior."""
    mocker.patch("mspy.stop")
    mocker.patch("wx.Bell")

    # Active thread
    panel.processing = mocker.Mock()
    panel.processing.is_alive.return_value = True
    panel.onStop(None)
    mspy.stop.assert_called_once()

    # No active thread
    mspy.stop.reset_mock()
    panel.processing = None
    panel.onStop(None)
    wx.Bell.assert_called_once()


def test_onProcessing(panel, mocker):
    """Test onProcessing behavior."""
    mock_disabler = mocker.patch("wx.WindowDisabler")
    mspy_start = mocker.patch("mspy.start")
    mocker.patch.object(panel, "Layout")

    # Start processing
    panel.onProcessing(True)
    mock_disabler.assert_called_with(panel)
    assert panel.mainSizer.IsShown(2) is True

    # Stop processing
    panel.onProcessing(False)
    assert panel.mainSizer.IsShown(2) is False
    mspy_start.assert_called_once()
    assert panel.processing is None
    assert not hasattr(panel, "_disabler")


def test_runGetPeaklists_peaklists(panel, mock_document, mocker):
    """Test runGetPeaklists with 'peaklists' mode."""
    config.comparePeaklists["compare"] = "peaklists"

    # Mock items
    item1 = mocker.Mock()
    item1.mz = 100.1234567
    item1.charge = 1
    item1.ai = 1000
    item1.base = 100

    mock_document.spectrum.peaklist = [item1]
    panel.currentDocuments = [mock_document]

    panel.runGetPeaklists()

    assert len(panel.currentPeaklist) == 1
    assert panel.currentPeaklist[0][0] == round(100.1234567, 6)
    assert panel.currentPeaklist[0][1] == 0  # docIndex
    assert panel.currentPeaklist[0][2] == 1  # charge
    assert panel.currentPeaklist[0][3] == 900  # ai - base
    assert panel.currentPeaklist[0][4] == [True]  # matches_array
    assert panel._maxSize == 1


def test_runGetPeaklists_measured(panel, mock_document, mocker):
    """Test runGetPeaklists with 'measured' mode (annotations and sequences)."""
    config.comparePeaklists["compare"] = "measured"

    # Mock annotation
    ann1 = mocker.Mock()
    ann1.mz = 200.0
    ann1.charge = 2
    ann1.ai = 2000
    ann1.base = 200

    # Mock sequence match
    seq_match = mocker.Mock()
    seq_match.mz = 300.0
    seq_match.charge = 3
    seq_match.ai = 3000
    seq_match.base = 300

    sequence = mocker.Mock()
    sequence.matches = [seq_match]

    mock_document.annotations = [ann1]
    mock_document.sequences = [sequence]
    panel.currentDocuments = [mock_document]

    panel.runGetPeaklists()

    assert len(panel.currentPeaklist) == 2
    # Sorted by mz
    assert panel.currentPeaklist[0][0] == 200.0
    assert panel.currentPeaklist[1][0] == 300.0
    assert panel._maxSize == 2


def test_runGetPeaklists_theoretical(panel, mock_document, mocker):
    """Test runGetPeaklists with 'theoretical' mode."""
    config.comparePeaklists["compare"] = "theoretical"

    # Mock annotation with theoretical
    ann1 = mocker.Mock()
    ann1.theoretical = 200.1
    ann1.charge = 2
    ann1.ai = 2000
    ann1.base = 200

    # Mock annotation without theoretical (should be skipped)
    ann2 = mocker.Mock()
    ann2.theoretical = None

    mock_document.annotations = [ann1, ann2]
    panel.currentDocuments = [mock_document]

    panel.runGetPeaklists()

    assert len(panel.currentPeaklist) == 1
    assert panel.currentPeaklist[0][0] == 200.1


def test_runGetPeaklists_force_quit(panel, mock_document, mocker):
    """Test runGetPeaklists handles ForceQuit."""
    mock_document.spectrum.peaklist = [mocker.Mock()]
    mock_docs = mocker.MagicMock()
    mock_docs.__len__.return_value = 1
    mock_docs.__iter__.side_effect = mspy.ForceQuit
    panel.currentDocuments = mock_docs

    panel.runGetPeaklists()
    assert panel.currentPeaklist == []
    assert panel._maxSize == 0


def test_runCompare(panel, mock_document, mocker):
    """Test runCompare logic."""
    panel.currentDocuments = [mock_document, mock_document]
    # [mz, docIndex, charge, intensity, [matches]]
    panel.currentPeaklist = [
        [100.0, 0, 1, 1000.0, [True, False]],
        [100.01, 1, 1, 1000.0, [False, True]],
        [200.0, 0, 2, 500.0, [True, False]],
    ]

    config.comparePeaklists["tolerance"] = 0.05
    config.comparePeaklists["units"] = "Da"
    config.comparePeaklists["ignoreCharge"] = 0  # False
    config.comparePeaklists["ratioCheck"] = 0  # False

    panel.runCompare()

    # 100.0 and 100.01 should match (diff 0.01 <= 0.05)
    assert panel.currentPeaklist[0][-1] == [True, True]
    assert panel.currentPeaklist[1][-1] == [True, True]
    # 200.0 should not match anything else
    assert panel.currentPeaklist[2][-1] == [True, False]


def test_runCompare_ignoreCharge(panel, mock_document, mocker):
    """Test runCompare with ignoreCharge=True."""
    panel.currentDocuments = [mock_document, mock_document]
    panel.currentPeaklist = [
        [100.0, 0, 1, 1000.0, [True, False]],
        [100.01, 1, 2, 1000.0, [False, True]],
    ]

    config.comparePeaklists["tolerance"] = 0.05
    config.comparePeaklists["units"] = "Da"
    config.comparePeaklists["ignoreCharge"] = 1  # True
    config.comparePeaklists["ratioCheck"] = 0  # False

    panel.runCompare()

    # Should match despite different charges
    assert panel.currentPeaklist[0][-1] == [True, True]
    assert panel.currentPeaklist[1][-1] == [True, True]


def test_runCompare_ratioCheck(panel, mock_document, mocker):
    """Test runCompare with ratioCheck."""
    panel.currentDocuments = [mock_document, mock_document]
    panel.currentPeaklist = [
        [100.0, 0, 1, 1000.0, [True, False]],
        [100.0, 1, 1, 100.0, [False, True]],  # Ratio 10.0
    ]

    config.comparePeaklists["tolerance"] = 0.05
    config.comparePeaklists["units"] = "Da"
    config.comparePeaklists["ignoreCharge"] = 1  # True
    config.comparePeaklists["ratioCheck"] = 1  # True
    config.comparePeaklists["ratioThreshold"] = 5.0
    config.comparePeaklists["ratioDirection"] = 1  # Above

    # Case: Ratio 10.0 >= Threshold 5.0 (Direction Above) -> Matched
    panel.runCompare()
    assert panel.currentPeaklist[0][-1] == [True, True]

    # Case: Ratio 10.0 > Threshold 15.0 (Direction Above) -> Not matched
    config.comparePeaklists["ratioThreshold"] = 15.0
    panel.runCompare()
    assert panel.currentPeaklist[0][-1] == [True, False]


def test_runCompare_force_quit(panel, mocker):
    """Test runCompare handles ForceQuit."""
    panel.currentPeaklist = mocker.MagicMock()
    panel.currentPeaklist.__iter__.side_effect = mspy.ForceQuit

    panel.runCompare()
    # It just returns, currentMatches remains []
    assert panel.currentMatches == []


def test_compareSelected(panel, mock_document, mocker):
    """Test compareSelected populates currentMatches."""
    # Ensure config is reset to avoid side effects from other tests
    config.comparePeaklists["tolerance"] = 0.05
    config.comparePeaklists["units"] = "Da"
    config.comparePeaklists["ignoreCharge"] = 0
    config.main["mzDigits"] = 2

    doc0 = mocker.Mock()
    doc0.colour = wx.Colour(255, 0, 0)
    doc1 = mocker.Mock()
    doc1.colour = wx.Colour(0, 255, 0)
    panel.currentDocuments = [doc0, doc1]

    # [mz, docIndex, charge, intensity, [matches]]
    panel.currentPeaklist = [
        [100.0, 0, 1, 1000.0, [True, False]],  # pkIndex 0
        [100.01, 1, 1, 500.0, [False, True]],  # match
        [200.0, 0, 1, 1000.0, [True, False]],  # no match
    ]

    panel.compareSelected(0)

    # Expected matches: p1 vs p1 (100.0 vs 100.0) and p1 vs p2 (100.0 vs 100.01)
    # They should both be in currentMatches because diff is 0.01 <= 0.05
    assert len(panel.currentMatches) == 2


def test_onCompare_threaded(panel, mocker):
    """Test onCompare using synchronously executed thread."""

    class MockThread:
        def __init__(self, target, *args, **kwargs):
            self.target = target

        def start(self):
            self.target()

        def is_alive(self):
            return False

    mocker.patch("threading.Thread", side_effect=MockThread)
    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "onProcessing")
    mocker.patch.object(panel, "runCompare")
    mocker.patch.object(panel, "updateDocumentsGrid")
    mocker.patch.object(panel, "updatePeaklistGrid")
    mocker.patch.object(panel, "updateMatchesGrid")

    panel.currentDocuments = [mocker.Mock()]
    panel.onCompare(None)

    panel.runCompare.assert_called_once()
    panel.updateDocumentsGrid.assert_called_once()
    panel.updatePeaklistGrid.assert_called_once()
    panel.updateMatchesGrid.assert_called_once()


def test_onUpdatePeaklist_threaded(panel, mocker):
    """Test onUpdatePeaklist using synchronously executed thread."""

    class MockThread:
        def __init__(self, target, *args, **kwargs):
            self.target = target

        def start(self):
            self.target()

        def is_alive(self):
            return False

    mocker.patch("threading.Thread", side_effect=MockThread)
    mocker.patch.object(panel, "onProcessing")
    mocker.patch.object(panel, "runGetPeaklists")
    mocker.patch.object(panel, "updateDocumentsGrid")
    mocker.patch.object(panel, "updatePeaklistGrid")
    mocker.patch.object(panel, "updateMatchesGrid")

    panel.currentDocuments = [mocker.Mock()]
    panel.onUpdatePeaklist(None)

    panel.runGetPeaklists.assert_called_once()
    panel.updateDocumentsGrid.assert_called_once()
    panel.updatePeaklistGrid.assert_called_once()
    panel.updateMatchesGrid.assert_called_once()


def test_updateDocumentsGrid(panel, mock_document, mocker):
    """Test updateDocumentsGrid populates grid correctly."""
    config.main["mzDigits"] = 4
    panel.currentDocuments = [mock_document]
    # [mz, docIndex, charge, intensity, [matches]]
    panel.currentPeaklist = [[123.45678, 0, 1, 1000.0, [True]]]
    panel._maxSize = 1

    panel.updateDocumentsGrid(recreate=True)

    # 1 document -> count = 1
    # Number of columns: count**2 + count = 1 + 1 = 2
    # Column 0: m/z, Column 1: *
    assert panel.documentsGrid.GetNumberCols() == 2
    assert panel.documentsGrid.GetNumberRows() == 1
    assert panel.documentsGrid.GetCellValue(0, 0) == "123.4568"
    assert panel.documentsGrid.GetCellValue(0, 1) == "*"
    assert panel.documentsGrid.GetCellBackgroundColour(0, 1) == mock_document.colour


def test_updatePeaklistGrid(panel, mock_document, mocker):
    """Test updatePeaklistGrid populates grid correctly."""
    config.main["mzDigits"] = 4
    panel.currentDocuments = [mock_document]
    panel.currentPeaklist = [[123.45678, 0, 1, 1000.0, [True]]]

    panel.updatePeaklistGrid(recreate=True)

    # 1 document -> count = 1
    # Number of columns: count + 1 = 2
    # Column 0: m/z, Column 1: *
    assert panel.peaklistGrid.GetNumberCols() == 2
    assert panel.peaklistGrid.GetNumberRows() == 1
    assert panel.peaklistGrid.GetCellValue(0, 0) == "123.4568"
    assert panel.peaklistGrid.GetCellValue(0, 1) == "*"
    assert panel.peaklistGrid.GetCellBackgroundColour(0, 1) == mock_document.colour


def test_updateMatchesGrid(panel, mock_document, mocker):
    """Test updateMatchesGrid populates grid correctly."""
    config.main["mzDigits"] = 4
    config.main["ppmDigits"] = 2
    config.comparePeaklists["units"] = "ppm"
    panel.currentDocuments = [mock_document]
    # [docIndex, mz, error, ratio1, ratio2, is_same_doc]
    panel.currentMatches = [[0, 100.1234, 1.23, 2.0, 0.5, True]]

    panel.updateMatchesGrid()

    # 5 columns: *, m/z, error, a/b, b/a
    assert panel.matchesGrid.GetNumberCols() == 5
    assert panel.matchesGrid.GetNumberRows() == 1
    assert panel.matchesGrid.GetCellValue(0, 0) == "*"
    assert panel.matchesGrid.GetCellValue(0, 1) == "100.1234"
    assert panel.matchesGrid.GetCellValue(0, 2) == "1.23"
    assert panel.matchesGrid.GetCellValue(0, 3) == "2.00"
    assert panel.matchesGrid.GetCellValue(0, 4) == "0.50"
    assert panel.matchesGrid.GetCellBackgroundColour(0, 0) == mock_document.colour


def test_onDocumentsCellSelected(panel, mock_document, mocker):
    """Test onDocumentsCellSelected behavior."""
    panel.currentDocuments = [mock_document]
    # [mz, docIndex, charge, intensity, [matches]]
    panel.currentPeaklist = [[123.4, 0, 1, 1000.0, [True]]]

    mock_event = mocker.Mock(spec=wx.grid.GridEvent)
    mock_event.GetCol.return_value = 0
    mock_event.GetRow.return_value = 0

    mocker.patch.object(panel, "compareSelected")
    mocker.patch.object(panel, "updateMatchesGrid")

    panel.onDocumentsCellSelected(mock_event)

    mock_event.Skip.assert_called_once()
    panel.parent.updateMassPoints.assert_called_with([123.4])
    panel.compareSelected.assert_called_with(0)
    panel.updateMatchesGrid.assert_called_once()


def test_onPeaklistCellSelected(panel, mock_document, mocker):
    """Test onPeaklistCellSelected behavior."""
    panel.currentDocuments = [mock_document]
    panel.currentPeaklist = [[123.4, 0, 1, 1000.0, [True]]]

    mock_event = mocker.Mock(spec=wx.grid.GridEvent)
    mock_event.GetRow.return_value = 0

    mocker.patch.object(panel, "compareSelected")
    mocker.patch.object(panel, "updateMatchesGrid")

    panel.onPeaklistCellSelected(mock_event)

    mock_event.Skip.assert_called_once()
    panel.parent.updateMassPoints.assert_called_with([123.4])
    panel.compareSelected.assert_called_with(0)
    panel.updateMatchesGrid.assert_called_once()


def test_onKeys_skip(panel, mocker):
    """Test grid key handlers skip on standard keys."""
    for method_name in ["onDocumentsKey", "onPeaklistKey", "onMatchesKey"]:
        method = getattr(panel, method_name)
        mock_event = mocker.Mock(spec=wx.KeyEvent)
        mock_event.GetKeyCode.return_value = wx.WXK_RETURN
        mock_event.CmdDown.return_value = False

        method(mock_event)
        mock_event.Skip.assert_called_once()


def test_onKeys_copy(panel, mocker):
    """Test grid key handlers trigger copy on Cmd+C."""
    mocker.patch.object(panel, "copyDocuments")
    mocker.patch.object(panel, "copyPeaklist")
    mocker.patch.object(panel, "copyMatches")

    # Cmd+C (key 67)
    for method_name, copy_name in [
        ("onDocumentsKey", "copyDocuments"),
        ("onPeaklistKey", "copyPeaklist"),
        ("onMatchesKey", "copyMatches"),
    ]:
        method = getattr(panel, method_name)
        copy_method = getattr(panel, copy_name)

        mock_event = mocker.Mock(spec=wx.KeyEvent)
        mock_event.GetKeyCode.return_value = 67
        mock_event.CmdDown.return_value = True

        method(mock_event)
        copy_method.assert_called_once()
        mock_event.Skip.assert_not_called()


def test_copyDocuments(panel, mock_document, mocker):
    """Test copyDocuments behavior."""
    config.main["mzDigits"] = 2
    panel.currentDocuments = [mock_document]
    panel.currentPeaklist = [[123.4, 0, 1, 1000.0, [True]]]
    panel._maxSize = 1
    panel.updateDocumentsGrid(recreate=True)

    mock_data_obj = mocker.patch("wx.TextDataObject")
    mock_clipboard = mocker.patch("wx.TheClipboard")
    mock_clipboard.Open.return_value = True

    panel.copyDocuments()

    # Grid cell (0,0) is "123.40", cell (0,1) is "*"
    # buff = "123.40\t*\n"
    expected_text = "123.40\t*"
    mock_data_obj.return_value.SetText.assert_called_with(expected_text)
    mock_clipboard.Open.assert_called_once()
    mock_clipboard.SetData.assert_called_once()
    mock_clipboard.Close.assert_called_once()


def test_copyPeaklist(panel, mock_document, mocker):
    """Test copyPeaklist behavior."""
    config.main["mzDigits"] = 2
    panel.currentDocuments = [mock_document]
    panel.currentPeaklist = [[123.4, 0, 1, 1000.0, [True]]]
    panel.updatePeaklistGrid(recreate=True)

    mock_data_obj = mocker.patch("wx.TextDataObject")
    mock_clipboard = mocker.patch("wx.TheClipboard")
    mock_clipboard.Open.return_value = True

    panel.copyPeaklist()

    # Grid cell (0,0) is "123.40", cell (0,1) is "*"
    expected_text = "123.40\t*"
    mock_data_obj.return_value.SetText.assert_called_with(expected_text)
    mock_clipboard.Open.assert_called_once()
    mock_clipboard.SetData.assert_called_once()
    mock_clipboard.Close.assert_called_once()


def test_copyMatches(panel, mock_document, mocker):
    """Test copyMatches behavior."""
    config.main["mzDigits"] = 2
    config.main["ppmDigits"] = 2
    config.comparePeaklists["units"] = "ppm"
    panel.currentDocuments = [mock_document]
    panel.currentMatches = [[0, 100.12, 1.23, 2.0, 0.5, True]]
    panel.updateMatchesGrid()

    mock_data_obj = mocker.patch("wx.TextDataObject")
    mock_clipboard = mocker.patch("wx.TheClipboard")
    mock_clipboard.Open.return_value = True

    panel.copyMatches()

    # Columns 1 to 4: m/z, error, a/b, b/a
    # buff = "100.12\t1.23\t2.00\t0.50\n"
    expected_text = "100.12\t1.23\t2.00\t0.50"
    mock_data_obj.return_value.SetText.assert_called_with(expected_text)
    mock_clipboard.Open.assert_called_once()
    mock_clipboard.SetData.assert_called_once()
    mock_clipboard.Close.assert_called_once()
