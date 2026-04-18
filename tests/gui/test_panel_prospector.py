import copy

import gui.config
import gui.images
import gui.mwx
import gui.panel_prospector
import pytest
import wx
from gui.ids import *


# Fixture to patch missing wx constants
@pytest.fixture(autouse=True)
def patch_wx_constants():
    if not hasattr(wx, "RESIZE_BORDER"):
        wx.RESIZE_BORDER = 0
    if not hasattr(wx, "RESIZE_BOX"):
        wx.RESIZE_BOX = 0
    if not hasattr(wx, "MAXIMIZE_BOX"):
        wx.MAXIMIZE_BOX = 0


# Fixture to mock and restore config.prospector
@pytest.fixture
def mock_config():
    original_prospector = copy.deepcopy(gui.config.prospector)
    yield gui.config.prospector
    gui.config.prospector.clear()
    gui.config.prospector.update(original_prospector)


# Fixture for mock parent
@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.getCurrentPeaklist = mocker.MagicMock(return_value=[])
    yield parent
    if parent:
        parent.Destroy()


# Fixture to mock and restore images.lib
@pytest.fixture(autouse=True)
def mock_images_lib(mocker):
    """Mock images.lib to avoid loading real images which fails in this environment."""
    blank_bitmap = wx.Bitmap(16, 16)

    class MockLib(dict):
        def __getitem__(self, key):
            return blank_bitmap

    mocker.patch("gui.images.lib", MockLib())
    mocker.patch("gui.images.loadImages")


def test_init(wx_app, mock_parent, mock_config):
    """Test initialization of panelProspector."""
    panel = gui.panel_prospector.panelProspector(mock_parent)
    assert panel.GetTitle() == "Protein Prospector - MS-Fit"
    assert panel.currentTool == "msfit"
    assert panel.parent == mock_parent
    panel.Destroy()

    # Test with explicit tool
    panel = gui.panel_prospector.panelProspector(mock_parent, tool="mstag")
    assert panel.GetTitle() == "Protein Prospector - MS-Tag"
    assert panel.currentTool == "mstag"
    panel.Destroy()


def test_make_gui(wx_app, mock_parent, mock_config):
    """Test GUI construction."""
    panel = gui.panel_prospector.panelProspector(mock_parent)
    assert hasattr(panel, "msFit_butt")
    assert hasattr(panel, "msTag_butt")
    assert hasattr(panel, "query_butt")
    assert hasattr(panel, "search_butt")
    assert hasattr(panel, "mainSizer")
    panel.Destroy()


def test_on_tool_selected(wx_app, mock_parent, mock_config, mocker):
    """Test tool selection logic."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # Select MS-Tag via event
    evt = mocker.MagicMock()
    evt.GetId.return_value = ID_prospectorMSTag
    panel.onToolSelected(evt)
    assert panel.currentTool == "mstag"
    assert panel.GetTitle() == "Protein Prospector - MS-Tag"
    assert panel.search_butt.IsEnabled()
    assert gui.config.prospector["common"]["searchType"] == "mstag"

    # Select Query via event
    evt.GetId.return_value = ID_prospectorQuery
    panel.onToolSelected(evt)
    assert panel.currentTool == "query"
    assert panel.GetTitle() == "Protein Prospector - Peak List"
    assert not panel.search_butt.IsEnabled()

    # Select MS-Fit via event
    evt.GetId.return_value = ID_prospectorMSFit
    panel.onToolSelected(evt)
    assert panel.currentTool == "msfit"
    assert panel.GetTitle() == "Protein Prospector - MS-Fit"
    assert panel.search_butt.IsEnabled()
    assert gui.config.prospector["common"]["searchType"] == "msfit"

    # Test passing tool name directly
    panel.onToolSelected(tool="mstag")
    assert panel.currentTool == "mstag"

    panel.Destroy()


def test_set_data(wx_app, mock_parent, mock_config, mocker):
    """Test setting document data."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    mock_doc = mocker.MagicMock()
    mock_doc.title = "Test Document"
    mock_doc.spectrum.precursorMZ = 1234.5678

    # Mock onGetPeaklist to avoid side effects
    mock_get_pkl = mocker.patch.object(panel, "onGetPeaklist")
    panel.setData(mock_doc)
    assert panel.paramMSFitTitle_value.GetValue() == "Test Document"
    assert panel.paramMSTagTitle_value.GetValue() == "Test Document"
    assert panel.paramMSTagPeptideMass_value.GetValue() == "1234.5678"
    mock_get_pkl.assert_called_once()

    # Test with precursorMZ = None
    mock_doc.spectrum.precursorMZ = None
    panel.setData(mock_doc)
    assert panel.paramMSTagPeptideMass_value.GetValue() == ""

    # Test with None document
    panel.setData(None)
    assert panel.paramMSFitTitle_value.GetValue() == ""
    assert panel.paramMSTagTitle_value.GetValue() == ""
    assert panel.paramQuery_value.GetValue() == ""

    panel.Destroy()


def test_on_get_peaklist(wx_app, mock_parent, mock_config, mocker):
    """Test getting and formatting peak list."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    peak1 = mocker.MagicMock()
    peak1.mz = 100.1
    peak1.intensity = 1000.0
    peak2 = mocker.MagicMock()
    peak2.mz = 200.2
    peak2.intensity = 2000.0

    mock_parent.getCurrentPeaklist.return_value = [peak1, peak2]

    # Toggle all filters
    panel.filterAnnotations_check.SetValue(True)
    panel.filterMatches_check.SetValue(True)
    panel.filterUnselected_check.SetValue(True)
    panel.filterIsotopes_check.SetValue(True)
    panel.filterUnknown_check.SetValue(True)

    panel.onGetPeaklist()

    mock_parent.getCurrentPeaklist.assert_called_with("AMSIX")
    expected_query = "100.100000\t1000.000000\n200.200000\t2000.000000\n"
    assert panel.paramQuery_value.GetValue() == expected_query

    # Test empty peaklist with event (bell should trigger)
    mock_parent.getCurrentPeaklist.return_value = []
    mock_bell = mocker.patch("wx.Bell")
    panel.onGetPeaklist(evt=mocker.MagicMock())
    assert panel.paramQuery_value.GetValue() == ""
    mock_bell.assert_called_once()

    panel.Destroy()


def test_on_modification_selected(wx_app, mock_parent, mock_config):
    """Test updating modification count labels."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # Mock MS-Fit selections
    panel.paramMSFitFixedMods_listbox.Clear()
    for s in ["Mod1", "Mod2", "Mod3"]:
        panel.paramMSFitFixedMods_listbox.Append(s)
    panel.paramMSFitFixedMods_listbox.Select(0)
    panel.paramMSFitFixedMods_listbox.Select(1)

    panel.paramMSFitVariableMods_listbox.Clear()
    panel.paramMSFitVariableMods_listbox.Append("VMod1")
    panel.paramMSFitVariableMods_listbox.Select(0)

    # Mock MS-Tag selections
    panel.paramMSTagFixedMods_listbox.Clear()
    panel.paramMSTagFixedMods_listbox.Append("Mod1")
    panel.paramMSTagFixedMods_listbox.Select(0)

    panel.onModificationSelected()

    assert "Fixed modifications: (2)" in panel.paramMSFitFixedMods_label.GetLabel()
    assert (
        "Variable modifications: (1)" in panel.paramMSFitVariableMods_label.GetLabel()
    )
    assert "Fixed modifications: (1)" in panel.paramMSTagFixedMods_label.GetLabel()

    panel.Destroy()


def test_get_params_msfit(wx_app, mock_parent, mock_config):
    """Test parameter extraction for MS-Fit."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # Switch to MS-Fit
    panel.onToolSelected(tool="msfit")

    # Set values in UI
    panel.paramMSFitTitle_value.SetValue("MSFit Title")
    panel.paramMSFitDatabase_choice.SetStringSelection("SwissProt")
    panel.paramMSFitTaxonomy_choice.SetStringSelection("All")
    panel.paramMSFitEnzyme_choice.SetStringSelection("Trypsin")
    panel.paramMSFitMiscleavages_choice.SetStringSelection("1")
    panel.paramMSFitProteinMassLow_value.SetValue("10")
    panel.paramMSFitProteinMassHigh_value.SetValue("200")
    panel.paramMSFitProteinPILow_value.SetValue("3")
    panel.paramMSFitProteinPIHigh_value.SetValue("10")
    panel.paramMSFitPeptideTol_value.SetValue("0.5")
    panel.paramMSFitPeptideTolUnits_choice.SetStringSelection("ppm")
    panel.paramMSFitMassType_choice.SetStringSelection("Average")
    panel.paramMSFitInstrument_choice.SetStringSelection("ESI-Q-TOF")
    panel.paramMSFitMinMatches_choice.SetStringSelection("5")
    panel.paramMSFitMaxMods_choice.SetStringSelection("2")
    panel.paramMSFitReport_choice.SetStringSelection("10")

    panel.paramMSFitFixedMods_listbox.Clear()
    panel.paramMSFitFixedMods_listbox.Append("Fixed1")
    panel.paramMSFitFixedMods_listbox.Append("Fixed2")
    panel.paramMSFitFixedMods_listbox.Select(0)

    panel.paramMSFitVariableMods_listbox.Clear()
    panel.paramMSFitVariableMods_listbox.Append("Var1")
    panel.paramMSFitVariableMods_listbox.Append("Var2")
    panel.paramMSFitVariableMods_listbox.Select(1)

    assert panel.getParams() is True

    cfg = gui.config.prospector["msfit"]
    assert cfg["title"] == "MSFit Title"
    assert cfg["database"] == "SwissProt"
    assert cfg["taxonomy"] == "All"
    assert cfg["proteinMassLow"] == 10.0
    assert cfg["proteinMassHigh"] == 200.0
    assert cfg["proteinPILow"] == 3.0
    assert cfg["proteinPIHigh"] == 10.0
    assert cfg["peptideTol"] == 0.5
    assert cfg["peptideTolUnits"] == "ppm"
    assert cfg["massType"] == "Average"
    assert cfg["instrument"] == "ESI-Q-TOF"
    assert cfg["minMatches"] == "5"
    assert cfg["maxMods"] == "2"
    assert cfg["report"] == "10"
    assert cfg["fixedMods"] == ["Fixed1"]
    assert cfg["variableMods"] == ["Var2"]

    panel.Destroy()


def test_get_params_mstag(wx_app, mock_parent, mock_config):
    """Test parameter extraction for MS-Tag."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # Switch to MS-Tag
    panel.onToolSelected(tool="mstag")

    # Set values in UI
    panel.paramMSTagTitle_value.SetValue("MSTag Title")
    panel.paramMSTagPeptideMass_value.SetValue("1234.5")
    panel.paramMSTagPeptideTol_value.SetValue("0.1")
    panel.paramMSTagMSMSTol_value.SetValue("0.2")
    panel.paramMSTagPeptideCharge_choice.SetStringSelection("2")

    panel.paramMSTagFixedMods_listbox.Clear()
    panel.paramMSTagFixedMods_listbox.Append("Fixed1")
    panel.paramMSTagFixedMods_listbox.Select(0)

    panel.paramMSTagVariableMods_listbox.Clear()
    panel.paramMSTagVariableMods_listbox.Append("Var1")
    panel.paramMSTagVariableMods_listbox.Select(0)

    assert panel.getParams() is True

    cfg = gui.config.prospector["mstag"]
    assert cfg["title"] == "MSTag Title"
    assert cfg["peptideMass"] == 1234.5
    assert cfg["peptideTol"] == 0.1
    assert cfg["msmsTol"] == 0.2
    assert cfg["peptideCharge"] == "2"
    assert cfg["fixedMods"] == ["Fixed1"]
    assert cfg["variableMods"] == ["Var1"]

    panel.Destroy()


def test_check_params(wx_app, mock_parent, mock_config, mocker):
    """Test parameter validation rules."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # Set up valid state for MS-Fit
    panel.onToolSelected(tool="msfit")
    gui.config.prospector["msfit"]["taxonomy"] = "All"
    gui.config.prospector["msfit"]["database"] = "SwissProt"
    gui.config.prospector["msfit"]["enzyme"] = "Trypsin"
    gui.config.prospector["msfit"]["instrument"] = "ESI-Q-TOF"
    gui.config.prospector["msfit"]["peptideTol"] = 0.1
    gui.config.prospector["msfit"]["variableMods"] = ["Mod1"]
    panel.paramQuery_value.SetValue("100.1\t1000.0")

    assert panel.checkParams() is True

    # Invalid - missing taxonomy
    gui.config.prospector["msfit"]["taxonomy"] = ""
    mock_dlg = mocker.patch("gui.mwx.dlgMessage")
    assert panel.checkParams() is False
    mock_dlg.assert_called()

    panel.Destroy()


def test_make_search_html(wx_app, mock_parent, mock_config):
    """Test HTML generation for both search types."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    # MS-Fit
    panel.onToolSelected(tool="msfit")
    gui.config.prospector["msfit"]["title"] = "MSFit & Title"
    gui.config.prospector["msfit"]["massType"] = "Monoisotopic"
    gui.config.prospector["msfit"]["proteinMassLow"] = 10.0
    gui.config.prospector["msfit"]["proteinMassHigh"] = 200.0
    gui.config.prospector["msfit"]["fixedMods"] = ["Fixed1"]
    gui.config.prospector["msfit"]["variableMods"] = ["Var1"]
    gui.config.prospector["msfit"]["database"] = "SwissProt"
    gui.config.prospector["msfit"]["taxonomy"] = "All"
    gui.config.prospector["msfit"]["enzyme"] = "Trypsin"
    gui.config.prospector["msfit"]["miscleavages"] = "1"
    gui.config.prospector["msfit"]["instrument"] = "MALDI-TOFTOF"
    gui.config.prospector["msfit"]["pfactor"] = "0.4"
    gui.config.prospector["msfit"]["minMatches"] = "4"
    gui.config.prospector["msfit"]["peptideTol"] = "0.1"
    gui.config.prospector["msfit"]["peptideTolUnits"] = "Da"
    gui.config.prospector["msfit"]["maxMods"] = "1"
    gui.config.prospector["msfit"]["report"] = "5"

    panel.paramQuery_value.SetValue("100.1\t1000.0")

    html = panel.makeSearchHTML()
    assert "MSFit &amp; Title" in html
    assert 'name="ms_prot_low_mass" value="10000.0"' in html

    panel.Destroy()


def test_on_search(wx_app, mock_parent, mock_config, mocker):
    """Test triggering the search."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "checkParams", return_value=True)
    mocker.patch.object(panel, "makeSearchHTML", return_value="<html>Test</html>")
    mock_open_browser = mocker.patch("webbrowser.open")
    mocker.patch("tempfile.gettempdir", return_value="/tmp")
    mock_open_file = mocker.patch("gui.panel_prospector.open", create=True)

    mock_f = mocker.MagicMock()
    mock_open_file.return_value = mock_f

    panel.onSearch(None)

    mock_open_browser.assert_called_with(
        "file:///tmp/mmass_prospector_search.html", autoraise=1
    )
    mock_f.write.assert_called_with(b"<html>Test</html>")

    # Test error during file write
    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "checkParams", return_value=True)
    mocker.patch.object(panel, "makeSearchHTML", return_value="<html>Test</html>")
    mocker.patch("gui.panel_prospector.open", side_effect=IOError)
    mock_bell = mocker.patch("wx.Bell")
    mock_dlg = mocker.patch("gui.mwx.dlgMessage")

    panel.onSearch(None)
    mock_bell.assert_called_once()
    mock_dlg.assert_called()

    panel.Destroy()


def test_on_close(wx_app, mock_parent, mock_config, mocker):
    """Test cleanup on close."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    mock_unlink = mocker.patch("os.unlink")
    mocker.patch("tempfile.gettempdir", return_value="/tmp")
    mock_destroy = mocker.patch.object(panel, "Destroy")

    panel.onClose(None)
    mock_unlink.assert_called_with("/tmp/mmass_prospector_search.html")
    mock_destroy.assert_called_once()

    # Test when file doesn't exist
    panel = gui.panel_prospector.panelProspector(mock_parent)
    mocker.patch("os.unlink", side_effect=OSError)
    mock_destroy = mocker.patch.object(panel, "Destroy")
    panel.onClose(None)
    mock_destroy.assert_called_once()


def test_escape(wx_app, mock_parent):
    """Test character escaping."""
    panel = gui.panel_prospector.panelProspector(mock_parent)
    assert panel._escape("  & \" ' < >  ") == "&amp; &quot; &#39; &lt; &gt;"
    panel.Destroy()


def test_update_form(wx_app, mock_parent, mock_config):
    """Test population of form elements from config."""
    panel = gui.panel_prospector.panelProspector(mock_parent)

    gui.config.prospector["msfit"]["database"] = "NCBInr"
    gui.config.prospector["msfit"]["taxonomy"] = "HUMAN MOUSE"
    gui.config.prospector["msfit"]["enzyme"] = "Trypsin"
    gui.config.prospector["msfit"]["instrument"] = "ESI-Q-TOF"
    gui.config.prospector["msfit"]["fixedMods"] = ["Carbamidomethyl (C)"]
    gui.config.prospector["msfit"]["variableMods"] = ["Oxidation (M)"]

    panel.updateForm()

    assert panel.paramMSFitDatabase_choice.GetStringSelection() == "NCBInr"
    assert panel.paramMSFitTaxonomy_choice.GetStringSelection() == "HUMAN MOUSE"

    # Check selections
    selections = panel.paramMSFitFixedMods_listbox.GetSelections()
    expected_index = panel.paramMSFitFixedMods_listbox.FindString("Carbamidomethyl (C)")
    assert expected_index in selections

    panel.Destroy()
