import pytest
import wx
from gui.ids import *
from gui.panel_document_info import dlgPresetsName, panelDocumentInfo


@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.onDocumentChanged = mocker.Mock()
    yield parent
    if parent:
        parent.Destroy()


class MockSpectrum:
    def __init__(self):
        self.scanNumber = 123
        self.retentionTime = 45.6
        self.msLevel = 2
        self.precursorMZ = 789.0
        self.precursorCharge = 2
        self.polarity = 1
        self.profile = [1, 2, 3]
        self.peaklist = [10, 20]


class MockDocument:
    def __init__(self):
        self.title = "Test Title"
        self.date = "2023-10-27"
        self.path = "/path/to/test"
        self.operator = "Test Operator"
        self.contact = "test@example.com"
        self.institution = "Test Inst"
        self.instrument = "Test MS"
        self.notes = "Test Notes"
        self.spectrum = MockSpectrum()


@pytest.fixture
def mock_document():
    return MockDocument()


@pytest.fixture
def panel(wx_app, mocker, mock_parent):
    # Mock missing wx constants
    if not hasattr(wx, "RESIZE_BOX"):
        wx.RESIZE_BOX = 0
    if not hasattr(wx, "MAXIMIZE_BOX"):
        wx.MAXIMIZE_BOX = 0

    # Mock images.lib
    mocker.patch(
        "gui.images.lib",
        {
            "bgrToolbar": wx.Bitmap(1, 1),
            "documentInfoSummaryOff": wx.Bitmap(1, 1),
            "documentInfoSummaryOn": wx.Bitmap(1, 1),
            "documentInfoSpectrumOff": wx.Bitmap(1, 1),
            "documentInfoSpectrumOn": wx.Bitmap(1, 1),
            "documentInfoNotesOff": wx.Bitmap(1, 1),
            "documentInfoNotesOn": wx.Bitmap(1, 1),
            "toolsPresets": wx.Bitmap(1, 1),
        },
    )

    p = panelDocumentInfo(mock_parent)
    yield p
    if p:
        p.Destroy()


def test_init(panel):
    assert panel.GetTitle() == "Document Summary"
    assert panel.currentTool == "summary"
    assert panel.currentDocument is None


def test_onToolSelected(panel, mocker):
    # Select spectrum tool
    evt = mocker.Mock()
    evt.GetId.return_value = ID_documentInfoSpectrum
    panel.onToolSelected(evt)
    assert panel.currentTool == "spectrum"
    assert panel.GetTitle() == "Spectrum Info"

    # Select notes tool
    evt.GetId.return_value = ID_documentInfoNotes
    panel.onToolSelected(evt)
    assert panel.currentTool == "notes"
    assert panel.GetTitle() == "Analysis Notes"

    # Select summary tool
    evt.GetId.return_value = ID_documentInfoSummary
    panel.onToolSelected(evt)
    assert panel.currentTool == "summary"
    assert panel.GetTitle() == "Document Summary"


def test_setData(panel, mock_document):
    panel.setData(mock_document)
    assert panel.currentDocument == mock_document
    assert panel.title_value.GetValue() == "Test Title"
    assert panel.operator_value.GetValue() == "Test Operator"
    assert panel.scanNumber_value.GetValue() == "123"
    assert panel.polarity_choice.GetStringSelection() == "Positive"
    assert panel.points_value.GetValue() == "3"
    assert panel.peaklist_value.GetValue() == "2"


def test_setData_none(panel, mock_document):
    mock_document.spectrum.scanNumber = None
    mock_document.spectrum.retentionTime = None
    mock_document.spectrum.msLevel = None
    mock_document.spectrum.precursorMZ = None
    mock_document.spectrum.precursorCharge = None
    mock_document.spectrum.polarity = 0

    panel.setData(mock_document)
    assert panel.scanNumber_value.GetValue() == ""
    assert panel.polarity_choice.GetStringSelection() == "Unknown"


def test_onSave(panel, mock_document, mock_parent):
    panel.setData(mock_document)

    # Change title
    panel.title_value.SetValue("New Title")
    panel.onSave(None)
    assert mock_document.title == "New Title"
    mock_parent.onDocumentChanged.assert_called()

    # Change other fields
    panel.operator_value.SetValue("New Operator")
    panel.scanNumber_value.SetValue("456")
    panel.polarity_choice.SetStringSelection("Negative")
    panel.onSave(None)

    assert mock_document.operator == "New Operator"
    assert mock_document.spectrum.scanNumber == 456
    assert mock_document.spectrum.polarity == -1


def test_onSave_invalid_types(panel, mock_document):
    panel.setData(mock_document)

    panel.scanNumber_value.SetValue("invalid")
    panel.retentionTime_value.SetValue("invalid")
    panel.msLevel_value.SetValue("invalid")
    panel.precursorMZ_value.SetValue("invalid")
    panel.precursorCharge_value.SetValue("invalid")

    panel.onSave(None)

    assert mock_document.spectrum.scanNumber is None
    assert mock_document.spectrum.retentionTime is None
    assert mock_document.spectrum.msLevel is None
    assert mock_document.spectrum.precursorMZ is None
    assert mock_document.spectrum.precursorCharge is None


def test_onSave_no_document(panel):
    panel.currentDocument = None
    # This should just return without error (it rings the bell)
    panel.onSave(None)


def test_onPresets(panel, mocker):
    mocker.patch("gui.panel_document_info.libs.presets", {"operator": {"Preset 1": {}}})
    mocker.patch.object(panel, "PopupMenu")
    mocker.patch("wx.Menu")
    panel.onPresets(None)
    panel.PopupMenu.assert_called()


def test_onPresetsSelected(panel, mocker):
    preset_data = {
        "operator": "Op1",
        "contact": "Con1",
        "institution": "Inst1",
        "instrument": "Instr1",
    }
    panel.presets_popup = mocker.Mock()
    item = mocker.Mock()
    item.GetText.return_value = "Preset 1"
    panel.presets_popup.FindItemById.return_value = item

    evt = mocker.Mock()
    evt.GetId.return_value = 123

    mocker.patch(
        "gui.panel_document_info.libs.presets", {"operator": {"Preset 1": preset_data}}
    )
    panel.onPresetsSelected(evt)
    assert panel.operator_value.GetValue() == "Op1"
    assert panel.contact_value.GetValue() == "Con1"
    assert panel.institution_value.GetValue() == "Inst1"
    assert panel.instrument_value.GetValue() == "Instr1"


def test_onPresetsSave(panel, mocker):
    panel.operator_value.SetValue("Op1")

    mock_dlg_class = mocker.patch("gui.panel_document_info.dlgPresetsName")
    mock_presets = mocker.patch(
        "gui.panel_document_info.libs.presets", {"operator": {}}
    )
    mock_save = mocker.patch("gui.panel_document_info.libs.savePresets")

    mock_dlg = mock_dlg_class.return_value
    mock_dlg.ShowModal.return_value = wx.ID_OK
    mock_dlg.name = "New Preset"

    panel.onPresetsSave(None)

    assert "New Preset" in mock_presets["operator"]
    assert mock_presets["operator"]["New Preset"]["operator"] == "Op1"
    mock_save.assert_called_once()


def test_onPresetsSave_cancel(panel, mocker):
    mocker.patch(
        "gui.panel_document_info.dlgPresetsName"
    ).return_value.ShowModal.return_value = wx.ID_CANCEL
    mock_save = mocker.patch("gui.libs.savePresets")

    panel.onPresetsSave(None)
    mock_save.assert_not_called()


def test_dlgPresetsName(wx_app, mock_parent, mocker):
    dlg = dlgPresetsName(mock_parent)
    dlg.name_value.SetValue("Test")

    # Mock EndModal to avoid blocking
    mock_end = mocker.patch.object(dlg, "EndModal")
    dlg.onOK(None)
    assert dlg.name == "Test"
    mock_end.assert_called_with(wx.ID_OK)

    dlg.Destroy()


def test_dlgPresetsName_empty(wx_app, mock_parent, mocker):
    dlg = dlgPresetsName(mock_parent)
    dlg.name_value.SetValue("")

    mock_end = mocker.patch.object(dlg, "EndModal")
    mock_bell = mocker.patch("wx.Bell")
    dlg.onOK(None)
    mock_end.assert_not_called()
    mock_bell.assert_called_once()

    dlg.Destroy()


def test_onToolSelected_other(panel, mocker):
    # Tool not matching any ID, should default to 'summary'
    evt = mocker.Mock()
    evt.GetId.return_value = 9999
    panel.onToolSelected(evt)
    assert panel.currentTool == "summary"


def test_onPresets_empty(panel, mocker):
    mocker.patch("gui.libs.presets", {"operator": {}})
    mocker.patch.object(panel, "PopupMenu")
    mocker.patch("wx.Menu")
    panel.onPresets(None)
    panel.PopupMenu.assert_called()


def test_onSave_no_title_change(panel, mock_document, mock_parent):
    panel.setData(mock_document)
    mock_parent.onDocumentChanged.reset_mock()

    # Don't change title
    panel.onSave(None)
    # onDocumentChanged still called with 'info', but title change logic skipped
    # Actually, onDocumentChanged(items=('doctitle')) should NOT be called.
    mock_parent.onDocumentChanged.assert_any_call(items=("info"))

    # Check that it wasn't called with doctitle
    for call in mock_parent.onDocumentChanged.call_args_list:
        assert call[1].get("items") != ("doctitle")


def test_setData_null(panel):
    panel.setData(None)
    assert panel.currentDocument is None
    assert panel.title_value.GetValue() == ""


def test_onSave_polarity_unknown(panel, mock_document):
    panel.setData(mock_document)
    panel.polarity_choice.SetStringSelection("Unknown")
    panel.onSave(None)
    assert mock_document.spectrum.polarity is None


def test_onClose(panel, mocker):
    mock_destroy = mocker.patch.object(panel, "Destroy")
    panel.onClose(None)
    mock_destroy.assert_called_once()
