import pytest
import wx

# Workaround for missing wx.RESIZE_BOX in some wxPython versions
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = getattr(wx, "RESIZE_BORDER", 0)

import mmass.gui.config as config
import mmass.gui.panel_mass_to_formula as panel_mass_to_formula
from mmass import mspy


@pytest.fixture
def mock_parent(wx_app, mocker):
    """Create mock parent for the panel."""
    # Use a real wx.Frame to avoid TypeError in MiniFrame.__init__
    parent = wx.Frame(None)
    parent.updateMassPoints = mocker.Mock()
    parent.onToolsMassCalculator = mocker.Mock()
    yield parent
    if parent:
        parent.Destroy()


@pytest.fixture
def panel(wx_app, mock_parent):
    """Instantiate panelMassToFormula."""
    # Ensure config.massToFormula and config.main are properly initialized
    # They are initialized on import in gui.config
    p = panel_mass_to_formula.panelMassToFormula(mock_parent)
    yield p
    if p:
        p.Destroy()


def test_init_and_make_gui(panel):
    """Test that the panel builds successfully (Step 2)."""
    assert panel is not None
    assert panel.GetTitle() == "Mass To Formula"

    # Verify key UI components are created
    assert hasattr(panel, "mass_value")
    assert isinstance(panel.mass_value, wx.TextCtrl)

    assert hasattr(panel, "formulaeList")
    # sortListCtrl is a subclass of ListCtrl
    assert isinstance(panel.formulaeList, wx.ListCtrl)

    assert hasattr(panel, "gauge")
    # mwx.gauge is a custom control, but it should exist
    assert panel.gauge is not None


def test_on_close(panel, mocker):
    """Test onClose behavior (Step 2)."""
    # Case 1: self.processing is None -> Destroy called
    mock_destroy = mocker.patch.object(panel, "Destroy")
    panel.processing = None
    panel.onClose(None)
    mock_destroy.assert_called_once()

    # Case 2: self.processing is not None -> Bell called, Destroy not called
    mock_destroy = mocker.patch.object(panel, "Destroy")
    mock_bell = mocker.patch("wx.Bell")
    panel.processing = mocker.Mock()
    panel.onClose(None)
    mock_bell.assert_called_once()
    mock_destroy.assert_not_called()


def test_set_data(panel, mocker):
    """Test setData updates UI widgets (Step 3)."""
    mock_doc = mocker.Mock()
    mock_doc.spectrum.hasprofile.return_value = True

    # Test with all parameters
    panel.setData(
        document=mock_doc,
        mass=123.456,
        charge=2,
        tolerance=0.5,
        units="ppm",
        agentFormula="Na",
    )

    assert panel.currentDocument == mock_doc
    assert panel.checkPattern_check.IsEnabled()
    assert panel.mass_value.GetValue() == "123.456"
    assert panel.charge_value.GetValue() == "2"
    assert panel.tolerance_value.GetValue() == "0.5"
    assert panel.unitsPpm_radio.GetValue() is True
    assert panel.unitsDa_radio.GetValue() is False
    assert (
        panel.ionization_choice.GetStringSelection() == "Na+"
    )  # In the code choices = ['M', 'M*', 'H+', 'Na+', 'K+', 'Li+', 'NH4+']

    # Test with document=None and mass=None
    panel.setData(document=None, mass=None)
    assert panel.currentDocument is None
    assert not panel.checkPattern_check.IsEnabled()
    # mass_value should remain unchanged if mass is None
    assert panel.mass_value.GetValue() == "123.456"


def test_get_params(panel, mocker):
    """Test getParams retrieves values from UI (Step 3)."""
    panel.mass_value.SetValue("500.123")
    panel.charge_value.SetValue("1")
    panel.tolerance_value.SetValue("10.0")
    panel.unitsPpm_radio.SetValue(True)
    panel.ionization_choice.SetSelection(2)  # 'H+'
    panel.formulaMin_value.SetValue("C1")
    panel.formulaMax_value.SetValue("C100")
    panel.checkPattern_check.SetValue(True)

    mock_get_rules = mocker.patch.object(panel, "getRules")
    success = panel.getParams()
    assert success is True
    assert panel.currentMass == 500.123
    assert config.massToFormula["charge"] == 1
    assert config.massToFormula["tolerance"] == 10.0
    assert config.massToFormula["units"] == "ppm"
    assert (
        config.massToFormula["ionization"] == "H"
    )  # choices = ['', 'e', 'H', 'Na', 'K', 'Li', 'NH4']
    assert config.massToFormula["formulaMin"] == "C1"
    assert config.massToFormula["formulaMax"] == "C100"
    assert config.massToFormula["checkPattern"] is True
    mock_get_rules.assert_called_once()


def test_get_params_exception(panel, mocker):
    """Test getParams handles exceptions (Step 3)."""
    panel.mass_value.SetValue("invalid")
    mock_bell = mocker.patch("wx.Bell")
    success = panel.getParams()
    assert success is False
    mock_bell.assert_called_once()


def test_get_rules(panel):
    """Test getRules updates config based on checkboxes (Step 3)."""
    panel.ruleHC_check.SetValue(True)
    panel.ruleNOPSC_check.SetValue(False)
    panel.ruleNOPS_check.SetValue(True)
    panel.ruleRDBE_check.SetValue(False)
    panel.ruleRDBEInt_check.SetValue(True)

    panel.getRules()
    rules = config.massToFormula["rules"]
    assert "HC" in rules
    assert "NOPSC" not in rules
    assert "NOPS" in rules
    assert "RDBE" not in rules
    assert "RDBEInt" in rules


def test_on_item_selected(panel, mock_parent, mocker):
    """Test item selection updates mass points in parent (Step 4)."""
    # Current formulae: list of [formula, mass, mz, error, hc, rdbe, similarity, cmpd]
    panel.currentFormulae = [["C6H12O6", 180.0, 181.0, 0.0, None, 1.0, None, None]]
    mock_evt = mocker.Mock()
    mock_evt.GetData.return_value = 0

    panel.onItemSelected(mock_evt)
    mock_parent.updateMassPoints.assert_called_once_with([181.0])


def test_on_item_send_to_mass_calculator(panel, mock_parent, mocker):
    """Test sending formula to mass calculator (Step 4)."""
    # Current formulae: list of [formula, mass, mz, error, hc, rdbe, similarity, cmpd]
    panel.currentFormulae = [["C6H12O6", 180.0, 181.0, 0.0, None, 1.0, None, None]]

    # Configure mock list control
    mocker.patch.object(panel.formulaeList, "getSelected", return_value=[0])
    mocker.patch.object(panel.formulaeList, "GetItemData", return_value=0)
    config.massToFormula["charge"] = 1
    config.massToFormula["ionization"] = "H"

    panel.onItemSendToMassCalculator(None)

    mock_parent.onToolsMassCalculator.assert_called_once_with(
        formula="C6H12O6", charge=1, agentFormula="H", agentCharge=1
    )


def test_on_list_key(panel, mocker):
    """Test list key events, specifically Ctrl+C (Step 4)."""
    mock_evt = mocker.Mock()
    mock_evt.GetKeyCode.return_value = 67  # 'C'
    mock_evt.CmdDown.return_value = True

    mock_copy = mocker.patch.object(panel, "onListCopy")
    panel.onListKey(mock_evt)
    mock_copy.assert_called_once()


def test_on_list_rmu(panel, mocker):
    """Test list right-click menu creation (Step 4)."""
    mock_evt = mocker.Mock()
    # Mock PopupMenu to avoid actually showing it
    mock_popup = mocker.patch.object(panel, "PopupMenu")
    mock_menu = mocker.patch("wx.Menu")
    panel.onListRMU(mock_evt)
    mock_popup.assert_called_once()
    # Verify it destroys the menu after use
    mock_menu.return_value.Destroy.assert_called_once()


def test_on_item_copy_formula(panel, mocker):
    """Test copying formula to clipboard (Step 5)."""
    panel.currentFormulae = [["C6H12O6", 180.0, 181.0, 0.0, None, 1.0, None, None]]

    mocker.patch.object(panel.formulaeList, "getSelected", return_value=[0])
    mocker.patch.object(panel.formulaeList, "GetItemData", return_value=0)
    mock_clipboard = mocker.patch("wx.TheClipboard")
    mock_clipboard.Open.return_value = True
    panel.onItemCopyFormula(None)

    mock_clipboard.Open.assert_called_once()
    # Verify SetData was called with TextDataObject containing the formula
    # We can't easily check the object type in mock calls but we can check the call happened
    assert mock_clipboard.SetData.called
    mock_clipboard.Close.assert_called_once()


@pytest.mark.parametrize(
    "server_id, server_name",
    [
        (panel_mass_to_formula.ID_massToFormulaSearchPubChem, "PubChem"),
        (panel_mass_to_formula.ID_massToFormulaSearchChemSpider, "ChemSpider"),
        (panel_mass_to_formula.ID_massToFormulaSearchMETLIN, "METLIN"),
        (panel_mass_to_formula.ID_massToFormulaSearchHMDB, "HMDB"),
        (panel_mass_to_formula.ID_massToFormulaSearchLipidMaps, "Lipid MAPS"),
    ],
)
def test_on_item_search(panel, server_id, server_name, mocker):
    """Test formula search in external databases (Step 5)."""
    panel.currentFormulae = [["C6H12O6", 180.0, 181.0, 0.0, None, 1.0, None, None]]

    mock_evt = mocker.Mock()
    mock_evt.GetId.return_value = server_id

    # Configure mock list control
    mocker.patch.object(panel.formulaeList, "getSelected", return_value=[0])
    mocker.patch.object(panel.formulaeList, "GetItemData", return_value=0)
    mock_web_open = mocker.patch("webbrowser.open")
    # We need to mock the built-in 'open'
    mock_file = mocker.patch("builtins.open", mocker.mock_open())
    panel.onItemSearch(mock_evt)

    mock_file.assert_called()
    # Check if write was called with expected content
    # We don't check full HTML but verify formula and server name are present
    handle = mock_file()
    written_content = handle.write.call_args[0][0]
    if isinstance(written_content, bytes):
        written_content = written_content.decode("utf-8")
    assert server_name in written_content
    assert "C6H12O6" in written_content

    mock_web_open.assert_called()
    assert mock_web_open.call_args[0][0].startswith("file://")


def test_on_item_search_exception(panel, mocker):
    """Test exception handling in onItemSearch (Step 5)."""
    panel.currentFormulae = [["C6H12O6", 180.0, 181.0, 0.0, None, 1.0, None, None]]
    mock_evt = mocker.Mock()
    mock_evt.GetId.return_value = panel_mass_to_formula.ID_massToFormulaSearchPubChem

    mocker.patch.object(panel.formulaeList, "getSelected", return_value=[0])
    mocker.patch.object(panel.formulaeList, "GetItemData", return_value=0)
    mocker.patch("builtins.open", side_effect=OSError("Test Error"))
    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mock_bell = mocker.patch("wx.Bell")
    panel.onItemSearch(mock_evt)
    mock_bell.assert_called_once()
    mock_dlg.assert_called_once()


def test_on_generate_path1_early_exit(panel, mocker):
    """Test onGenerate path 1: getParams returns False (Step 6)."""
    mocker.patch.object(panel, "getParams", return_value=False)
    mock_update = mocker.patch.object(panel, "updateFormulaeList")
    mock_bell = mocker.patch("wx.Bell")
    panel.onGenerate()
    mock_update.assert_called_once()
    mock_bell.assert_called_once()
    assert panel.currentFormulae is None


def test_on_generate_path2_mass_limit(panel, mocker):
    """Test onGenerate path 2: checkMassLimit returns False (Step 6)."""
    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "checkMassLimit", return_value=False)
    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mock_bell = mocker.patch("wx.Bell")
    panel.onGenerate()
    mock_bell.assert_called_once()
    mock_dlg.assert_called_once()


def test_on_generate_path3_valid(panel, mocker):
    """Test onGenerate path 3: valid execution with threading (Step 6)."""
    # Set mass limit to something high
    config.massToFormula["massLimit"] = 5000.0
    config.massToFormula["countLimit"] = 100
    panel.currentMass = 180.0

    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "checkMassLimit", return_value=True)
    mock_processing = mocker.patch.object(panel, "onProcessing")
    mock_update = mocker.patch.object(panel, "updateFormulaeList")
    # Mock threading.Thread to avoid actual background execution
    mock_thread = mocker.patch("threading.Thread")
    mock_thread_instance = mock_thread.return_value
    # simulate thread finishing immediately
    mock_thread_instance.is_alive.return_value = False

    panel.onGenerate()

    mock_thread.assert_called_once_with(target=panel.runGenerator)
    mock_thread_instance.start.assert_called_once()

    # Verify onProcessing(True) and onProcessing(False) were called
    mock_processing.assert_any_call(True)
    mock_processing.assert_any_call(False)
    mock_update.assert_called_once()


def test_on_generate_limit_warning(panel, mocker):
    """Test onGenerate displays limit warning (Step 6)."""
    config.massToFormula["countLimit"] = 5

    def mock_update():
        panel.currentFormulae = [mocker.Mock()] * 5

    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "checkMassLimit", return_value=True)
    mocker.patch.object(panel, "onProcessing")
    mocker.patch.object(panel, "updateFormulaeList", side_effect=mock_update)
    mock_thread = mocker.patch("threading.Thread")
    mock_thread.return_value.is_alive.return_value = False
    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mock_bell = mocker.patch("wx.Bell")
    panel.onGenerate()
    mock_bell.assert_called_once()
    mock_dlg.assert_called_once()


def test_on_processing(panel, mocker):
    """Test onProcessing show/hide gauge."""
    mock_disabler = mocker.patch("wx.WindowDisabler")
    mocker.patch.object(panel, "Layout")
    mock_mspy_start = mocker.patch("mmass.mspy.start")
    # Show
    panel.onProcessing(True)
    mock_disabler.assert_called_with(panel)
    assert panel.mainSizer.IsShown(4)

    # Hide
    panel.onProcessing(False)
    assert not hasattr(panel, "_disabler")
    assert not panel.mainSizer.IsShown(4)
    assert panel.processing is None
    mock_mspy_start.assert_called_once()


def test_on_stop(panel, mocker):
    """Test onStop behavior."""
    # Case 1: Processing alive -> mspy.stop called
    panel.processing = mocker.Mock()
    panel.processing.is_alive.return_value = True
    mock_stop = mocker.patch("mmass.mspy.stop")
    panel.onStop(None)
    mock_stop.assert_called_once()

    # Case 2: No processing or not alive -> Bell called
    panel.processing = None
    mock_bell = mocker.patch("wx.Bell")
    panel.onStop(None)
    mock_bell.assert_called_once()


def test_run_generator(panel, mocker):
    """Test runGenerator worker (Step 7)."""
    # Configure config and panel
    config.massToFormula["ionization"] = "H"
    config.massToFormula["charge"] = 1
    config.massToFormula["autoCHNO"] = True
    config.massToFormula["formulaMin"] = "C1"
    config.massToFormula["formulaMax"] = "C10H20"
    config.massToFormula["tolerance"] = 10.0
    config.massToFormula["units"] = "ppm"
    config.massToFormula["countLimit"] = 100
    config.massToFormula["checkPattern"] = False
    panel.currentMass = 180.0

    # Mock mspy functions
    mock_mz = mocker.patch("mmass.mspy.mz", return_value=179.0)
    mock_formulator = mocker.patch("mmass.mspy.formulator", return_value=["C6H12O6"])
    mock_delta = mocker.patch("mmass.mspy.delta", side_effect=[0.1, 0.001])
    # Mock mspy.compound class
    mock_compound_class = mocker.patch("mmass.mspy.compound")
    mock_cmpd = mocker.Mock()
    mock_compound_class.return_value = mock_cmpd
    mock_cmpd.composition.return_value = {"C": 1, "H": 1}
    mock_cmpd.mass.return_value = 180.0
    mock_cmpd.mz.return_value = [181.0]
    mock_cmpd.count.side_effect = [6, 12]  # C, H
    mock_cmpd.rdbe.return_value = 1.0
    mock_cmpd.formula.return_value = "C6H12O6"

    panel.runGenerator()

    # Verify calls
    mock_mz.assert_called_once()
    mock_formulator.assert_called_once()
    mock_compound_class.assert_any_call("C6H12O6")

    # Verify results in currentFormulae
    assert len(panel.currentFormulae) == 1
    item = panel.currentFormulae[0]
    # Format: [formula, mass, mz, error, hc, rdbe, similarity, cmpd]
    assert item[0] == "C6H12O6"
    assert item[1] == 180.0
    assert item[2] == 181.0
    assert item[3] == 0.1
    assert item[4] == 12.0 / 6.0  # hc
    assert item[5] == 1.0  # rdbe
    assert item[6] is None  # similarity (checkPattern is False)
    assert item[7] == mock_cmpd


def test_run_generator_force_quit(panel, mocker):
    """Test runGenerator handles mspy.ForceQuit (Step 7)."""
    mocker.patch("mmass.mspy.mz", side_effect=mspy.ForceQuit)
    # Should return without raising exception
    panel.runGenerator()
    assert panel.currentFormulae == []


def test_compare_isotopic_pattern(panel, mocker):
    """Test isotopic pattern comparison (Step 8)."""
    # Configure mock document
    mock_doc = mocker.Mock()
    mock_doc.spectrum.hasprofile.return_value = True
    mock_doc.spectrum.profile = [(100.0, 1.0), (101.0, 0.5)]
    mock_doc.spectrum.baseline.return_value = 0.0
    panel.currentDocument = mock_doc

    mock_cmpd = mocker.Mock()
    mock_cmpd.mz.return_value = [100.0]
    mock_cmpd.pattern.return_value = [[100.0, 100.0], [101.0, 50.0]]

    mock_labelpeak = mocker.patch("mmass.mspy.labelpeak")
    mock_peak = mocker.Mock()
    mock_peak.fwhm = 0.1
    mock_labelpeak.return_value = mock_peak

    mock_matchpattern = mocker.patch("mmass.mspy.matchpattern", return_value=0.2)
    similarity = panel.compareIsotopicPattern(mock_cmpd, 1, "H", shift=0.01)

    # (1 - rms) * 100 = (1 - 0.2) * 100 = 80.0
    assert similarity == 80.0

    mock_labelpeak.assert_called_once()
    mock_matchpattern.assert_called_once()

    # Check pattern was generated with expected parameters
    mock_cmpd.pattern.assert_called_once_with(
        fwhm=0.1, threshold=0.01, charge=1, agentFormula="H", agentCharge=1, real=True
    )


def test_update_formulae_list(panel, mocker):
    """Test updateFormulaeList populates the list correctly (Step 9)."""
    # Setup config
    config.main["mzDigits"] = 4
    config.main["ppmDigits"] = 2
    config.massToFormula["units"] = "Da"

    # Mock compound
    mock_cmpd = mocker.Mock()

    # Setup currentFormulae
    # [formula, mass, mz, error, hc, rdbe, similarity, cmpd]
    panel.currentFormulae = [
        ["C6H12O6", 180.063388, 181.070664, 0.0012, 2.0, 1.0, 95.5, mock_cmpd]
    ]

    mocker.patch.object(panel, "applyRules", return_value=True)
    panel.updateFormulaeList()

    # Verify list content
    assert panel.formulaeList.GetItemCount() == 1
    assert panel.formulaeList.GetItemText(0) == "C6H12O6"
    assert panel.formulaeList.GetItem(0, 1).GetText() == "180.0634"  # mass
    assert panel.formulaeList.GetItem(0, 2).GetText() == "181.0707"  # mz
    assert panel.formulaeList.GetItem(0, 3).GetText() == "0.0012"  # error (Da)
    assert panel.formulaeList.GetItem(0, 4).GetText() == "2.0"  # hc
    assert panel.formulaeList.GetItem(0, 5).GetText() == "1.0"  # rdbe
    assert panel.formulaeList.GetItem(0, 6).GetText() == "95.5"  # similarity

    # Test with ppm units
    config.massToFormula["units"] = "ppm"
    panel.currentFormulae[0][3] = 6.63
    mocker.patch.object(panel, "applyRules", return_value=True)
    panel.updateFormulaeList()
    assert panel.formulaeList.GetItem(0, 3).GetText() == "6.63"  # error (ppm)


def test_check_mass_limit(panel, mocker):
    """Test checkMassLimit (Step 9)."""
    config.massToFormula["massLimit"] = 1000.0
    config.massToFormula["ionization"] = "H"
    config.massToFormula["charge"] = 1
    panel.currentMass = 500.0

    # Mock mspy.mz to return a value within limit
    mocker.patch("mmass.mspy.mz", return_value=500.0)
    assert panel.checkMassLimit() is True

    # Mock mspy.mz to return a value over limit
    mocker.patch("mmass.mspy.mz", return_value=1500.0)
    assert panel.checkMassLimit() is False

    # Test with ionization 'e'
    config.massToFormula["ionization"] = "e"
    mock_mz = mocker.patch("mmass.mspy.mz", return_value=500.0)
    panel.checkMassLimit()
    # Verify agentCharge was passed as -1
    assert mock_mz.call_args[1]["agentCharge"] == -1


def test_test_escape(panel):
    """Test _escape method (Step 9)."""
    assert panel._escape("  C6H12O6  ") == "C6H12O6"
    assert panel._escape("H2O & CO2") == "H2O &amp; CO2"
    assert panel._escape("x < y") == "x &lt; y"
    assert panel._escape("x > y") == "x &gt; y"
    assert panel._escape('quote "test"') == "quote &quot;test&quot;"
    assert panel._escape("single 'quote'") == "single &#39;quote&#39;"


def test_compare_isotopic_pattern_no_document(panel, mocker):
    """Test compareIsotopicPattern with no document (Step 8)."""
    panel.currentDocument = None
    similarity = panel.compareIsotopicPattern(mocker.Mock(), 1, "H")
    assert similarity is None
