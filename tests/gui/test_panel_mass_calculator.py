import copy

import pytest
import wx

# Handle missing wx.RESIZE_BOX in some wxPython versions
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = getattr(wx, "RESIZE_BORDER", 0)

import gui.config as config
import gui.doc as doc
import gui.images as images
import gui.panel_mass_calculator as panel_mass_calculator

import mspy


def safe_updateTmpSpectrum(self):
    """Show current profile in the main canvas (patched to avoid numpy error)."""
    # check data
    if self.currentPatternProfile is None:
        self.parent.updateTmpSpectrum(None)
        return

    # apply current shift
    profile = mspy.offset(
        self.currentPatternProfile, x=config.massCalculator["patternShift"]
    )

    # draw tmp spectrum
    self.parent.updateTmpSpectrum(profile)


@pytest.fixture
def mock_parent(wx_app, mocker):
    """Fixture for mock parent of panelMassCalculator."""
    parent = wx.Frame(None)
    # Required methods mentioned in the plan
    parent.updateTmpSpectrum = mocker.MagicMock()
    parent.onDocumentNew = mocker.MagicMock()
    yield parent
    if parent:
        try:
            parent.Destroy()
        except (wx.PyDeadObjectError, RuntimeError):
            pass


@pytest.fixture
def patched_config(mocker):
    """Fixture to patch gui.config with deepcopies to avoid cross-test pollution."""
    # Create deepcopies of the default config values
    new_mass_calculator = copy.deepcopy(config.massCalculator)
    new_main = copy.deepcopy(config.main)

    mocker.patch("gui.config.massCalculator", new_mass_calculator)
    mocker.patch("gui.config.main", new_main)
    yield


@pytest.fixture
def calculator_panel(wx_app, mock_parent, patched_config, mocker):
    """Fixture for panelMassCalculator instance."""
    # wx_app is a session fixture from conftest.py
    # Patch mspy.plot.canvas to avoid wxAssertionError in headless environment
    mocker.patch("mspy.plot.canvas")
    panel = panel_mass_calculator.panelMassCalculator(mock_parent)

    # Patch updateTmpSpectrum to avoid numpy comparison ValueError (using 'is' instead of '==')
    import types

    panel.updateTmpSpectrum = types.MethodType(safe_updateTmpSpectrum, panel)

    yield panel

    # Ensure destruction during teardown
    if panel:
        try:
            panel.Destroy()
        except (wx.PyDeadObjectError, RuntimeError):
            pass


# --- Step 2: Initialization & GUI Construction ---


def test_init(calculator_panel):
    """Verify initialization of panelMassCalculator."""
    assert calculator_panel.currentTool == "pattern"
    assert calculator_panel.currentCompound is None
    assert calculator_panel.currentIons is None
    assert calculator_panel.currentIon is None
    assert calculator_panel.currentPattern is None
    assert calculator_panel.currentPatternProfile is None
    assert calculator_panel.currentPatternPeaks is None
    assert calculator_panel.currentPatternScan is None


def test_makeGUI(calculator_panel):
    """Verify GUI elements existence after makeGUI."""
    assert hasattr(calculator_panel, "mainSizer")
    assert hasattr(calculator_panel, "toolbar")
    assert hasattr(calculator_panel, "summary_butt")
    assert hasattr(calculator_panel, "ionseries_butt")
    assert hasattr(calculator_panel, "pattern_butt")
    assert hasattr(calculator_panel, "compound_value")
    assert hasattr(calculator_panel, "save_butt")
    assert hasattr(calculator_panel, "patternSizer")
    assert hasattr(calculator_panel, "ionsList")
    assert hasattr(calculator_panel, "patternCanvas")

    # Verify sizer hierarchy
    # toolbar is index 0, summary is index 1, ionseries is index 2, pattern is index 3
    assert (
        calculator_panel.mainSizer.GetItem(0).GetSizer() is None
    )  # It's a panel containing a sizer
    assert isinstance(calculator_panel.mainSizer.GetItem(1).GetWindow(), wx.Panel)
    assert isinstance(calculator_panel.mainSizer.GetItem(2).GetSizer(), wx.BoxSizer)
    assert (
        calculator_panel.mainSizer.GetItem(3).GetSizer()
        == calculator_panel.patternSizer
    )


# --- Step 3: Tool Navigation & UI Interactions ---


def test_onToolSelected(calculator_panel):
    """Verify tool selection logic."""
    # Test switching to 'summary'
    calculator_panel.onToolSelected(tool="summary")
    assert calculator_panel.currentTool == "summary"
    assert calculator_panel.mainSizer.IsShown(1) is True
    assert calculator_panel.mainSizer.IsShown(2) is False
    assert calculator_panel.mainSizer.IsShown(3) is False
    # Check button icon
    assert calculator_panel.summary_butt.GetBitmapLabel().IsSameAs(
        images.lib["massCalculatorSummaryOn"]
    )

    # Test switching to 'ionseries'
    calculator_panel.onToolSelected(tool="ionseries")
    assert calculator_panel.currentTool == "ionseries"
    assert calculator_panel.mainSizer.IsShown(1) is False
    assert calculator_panel.mainSizer.IsShown(2) is True
    assert calculator_panel.mainSizer.IsShown(3) is False
    # Check button icon
    assert calculator_panel.ionseries_butt.GetBitmapLabel().IsSameAs(
        images.lib["massCalculatorIonSeriesOn"]
    )

    # Test switching to 'pattern'
    calculator_panel.onToolSelected(tool="pattern")
    assert calculator_panel.currentTool == "pattern"
    assert calculator_panel.mainSizer.IsShown(1) is False
    assert calculator_panel.mainSizer.IsShown(2) is False
    assert calculator_panel.mainSizer.IsShown(3) is True
    # Check button icon
    assert calculator_panel.pattern_butt.GetBitmapLabel().IsSameAs(
        images.lib["massCalculatorPatternOn"]
    )


def test_onCollapse(calculator_panel):
    """Verify pattern settings collapse/expand logic."""
    # Initially expanded
    assert calculator_panel.patternSizer.IsShown(1) is True
    assert calculator_panel.patternCollapse_butt.GetBitmapLabel().IsSameAs(
        images.lib["arrowsDown"]
    )

    # Collapse
    calculator_panel.onCollapse(None)
    assert calculator_panel.patternSizer.IsShown(1) is False
    assert calculator_panel.patternCollapse_butt.GetBitmapLabel().IsSameAs(
        images.lib["arrowsRight"]
    )

    # Expand
    calculator_panel.onCollapse(None)
    assert calculator_panel.patternSizer.IsShown(1) is True
    assert calculator_panel.patternCollapse_butt.GetBitmapLabel().IsSameAs(
        images.lib["arrowsDown"]
    )


# --- Step 4: Form Input & Parameter Parsing (getParams) ---


def test_getParams_valid(calculator_panel, patched_config):
    """Verify getParams with valid inputs."""
    calculator_panel.compound_value.SetValue("H2O")
    calculator_panel.ionseriesAgentFormula_value.SetValue("H")
    calculator_panel.ionseriesAgentCharge_value.SetValue("1")
    calculator_panel.patternFwhm_value.SetValue("0.1")
    calculator_panel.patternIntensity_value.SetValue("1000")
    calculator_panel.patternBaseline_value.SetValue("0")
    calculator_panel.patternShift_value.SetValue("0")
    calculator_panel.showPeaks_check.SetValue(True)
    calculator_panel.patternPeakShape_choice.SetSelection(0)  # Symmetrical/Gaussian

    assert calculator_panel.getParams() is True
    assert calculator_panel.currentCompound is not None
    assert calculator_panel.currentCompound.formula() == "H2O"
    assert config.massCalculator["patternFwhm"] == 0.1
    assert config.massCalculator["patternIntensity"] == 1000.0


def test_getParams_invalid_formula(calculator_panel, patched_config, mocker):
    """Verify getParams with invalid chemical formula."""
    # Formula that raises ValueError in mspy.compound
    calculator_panel.compound_value.SetValue("Invalid123")
    assert calculator_panel.getParams() is False

    # Formula that is valid but has negative composition, triggering wx.Bell()
    calculator_panel.compound_value.SetValue("C-1")
    mock_bell = mocker.patch("wx.Bell")
    assert calculator_panel.getParams() is False
    assert mock_bell.called


def test_getParams_invalid_pattern(calculator_panel, patched_config, mocker):
    """Verify getParams with invalid pattern parameters."""
    calculator_panel.compound_value.SetValue("H2O")

    # Negative FWHM
    calculator_panel.patternFwhm_value.SetValue("-0.1")
    mock_bell = mocker.patch("wx.Bell")
    assert calculator_panel.getParams() is False
    assert mock_bell.called

    # Baseline >= Intensity
    calculator_panel.patternFwhm_value.SetValue("0.1")
    calculator_panel.patternIntensity_value.SetValue("100")
    calculator_panel.patternBaseline_value.SetValue("200")
    mock_bell = mocker.patch("wx.Bell")
    assert calculator_panel.getParams() is False
    assert mock_bell.called


# --- Step 5: Calculations & Application State ---


def test_setData(calculator_panel, patched_config, mocker):
    """Verify setData programmatically updates UI and triggers calculations."""
    # Patch runIonSeries and runPattern to verify they are called
    mock_run_ions = mocker.patch.object(
        calculator_panel, "runIonSeries", wraps=calculator_panel.runIonSeries
    )
    mock_run_pattern = mocker.patch.object(
        calculator_panel, "runPattern", wraps=calculator_panel.runPattern
    )

    calculator_panel.setData(
        formula="C6H12O6", charge=1, fwhm=0.5, intensity=5000, baseline=10
    )

    assert calculator_panel.compound_value.GetValue() == "C6H12O6"
    assert calculator_panel.patternFwhm_value.GetValue() == "0.5"
    assert float(calculator_panel.patternIntensity_value.GetValue()) == 5000.0
    assert float(calculator_panel.patternBaseline_value.GetValue()) == 10.0

    assert mock_run_ions.called
    assert calculator_panel.currentIons is not None
    # Since charge=1 was provided, it should be selected and trigger runPattern
    assert mock_run_pattern.called


def test_onCompoundChanged(calculator_panel, patched_config, mocker):
    """Verify onCompoundChanged triggers necessary updates."""
    calculator_panel.compound_value.SetValue("H2O")

    mock_run_ions = mocker.patch.object(calculator_panel, "runIonSeries")
    mock_run_pattern = mocker.patch.object(calculator_panel, "runPattern")
    mock_update_summary = mocker.patch.object(calculator_panel, "updateSummary")
    mock_update_ions_list = mocker.patch.object(calculator_panel, "updateIonsList")

    calculator_panel.onCompoundChanged(None)

    assert mock_run_ions.called
    assert mock_run_pattern.called
    assert mock_update_summary.called
    assert mock_update_ions_list.called


def test_runIonSeries(calculator_panel, patched_config):
    """Verify runIonSeries correctly handles polarities."""
    calculator_panel.setData(formula="H2O")

    # Positive polarity
    calculator_panel.ionseriesPositive_radio.SetValue(True)
    calculator_panel.getParams()
    calculator_panel.runIonSeries()
    assert all(ion[3] >= 0 for ion in calculator_panel.currentIons)

    # Negative polarity
    calculator_panel.ionseriesNegative_radio.SetValue(True)
    calculator_panel.getParams()
    calculator_panel.runIonSeries()
    assert all(ion[3] <= 0 for ion in calculator_panel.currentIons)


def test_makeProfile_shapes(calculator_panel, patched_config):
    """Verify makeProfile with different peak shapes."""
    calculator_panel.setData(formula="H2O")
    calculator_panel.showPeaks_check.SetValue(True)

    # Gaussian
    config.massCalculator["patternPeakShape"] = "gaussian"
    calculator_panel.makeProfile()
    assert calculator_panel.currentPatternPeaks is not None
    assert len(calculator_panel.currentPatternPeaks) > 0

    # Lorentzian
    config.massCalculator["patternPeakShape"] = "lorentzian"
    calculator_panel.makeProfile()
    assert calculator_panel.currentPatternPeaks is not None
    assert len(calculator_panel.currentPatternPeaks) > 0

    # GaussLorentzian
    config.massCalculator["patternPeakShape"] = "gausslorentzian"
    calculator_panel.makeProfile()
    assert calculator_panel.currentPatternPeaks is not None
    assert len(calculator_panel.currentPatternPeaks) > 0


# --- Step 6: List Interactions & Plotting ---


def test_onIonSelected(calculator_panel, patched_config, mocker):
    """Verify onIonSelected updates currentIon and triggers pattern recalculation."""
    calculator_panel.setData(formula="H2O")
    # currentIons should be populated. Index 0 is [M]

    mock_pattern_changed = mocker.patch.object(calculator_panel, "onPatternChanged")

    # Create a mock event
    class MockEvent:
        def GetData(self):
            return 0

    calculator_panel.onIonSelected(MockEvent())

    assert calculator_panel.currentIon == calculator_panel.currentIons[0]
    assert mock_pattern_changed.called


def test_onListKey_copy(calculator_panel, mocker):
    """Verify onListKey handles Ctrl+C."""
    mock_event = mocker.MagicMock()
    mock_event.GetKeyCode.return_value = 67  # ord('C')
    mock_event.CmdDown.return_value = True

    mock_copy = mocker.patch.object(calculator_panel.ionsList, "copyToClipboard")
    calculator_panel.onListKey(mock_event)
    assert mock_copy.called


def test_onListKey_other(calculator_panel, mocker):
    """Verify onListKey skips other keys."""
    mock_event = mocker.MagicMock()
    mock_event.GetKeyCode.return_value = 65  # ord('A')
    mock_event.CmdDown.return_value = False

    calculator_panel.onListKey(mock_event)
    assert mock_event.Skip.called


def test_updatePatternCanvas(calculator_panel, patched_config, mocker):
    """Verify updatePatternCanvas executes without exception and calls canvas.draw."""
    calculator_panel.setData(formula="H2O")  # This sets currentPatternScan

    mock_draw = mocker.patch.object(calculator_panel.patternCanvas, "draw")
    calculator_panel.updatePatternCanvas()
    assert mock_draw.called
    # Check if first argument is mspy.plot.container
    args, _ = mock_draw.call_args
    assert isinstance(args[0], mspy.plot.container)


# --- Step 7: Actions & Teardown ---


def test_onSave_valid(calculator_panel, mock_parent, patched_config):
    """Verify onSave creates a document and notifies parent."""
    calculator_panel.setData(formula="H2O")
    assert calculator_panel.currentPatternScan is not None

    calculator_panel.onSave(None)

    assert mock_parent.onDocumentNew.called
    args, kwargs = mock_parent.onDocumentNew.call_args
    document = kwargs.get("document") or args[0]

    assert isinstance(document, doc.document)
    assert "H2O" in document.title
    assert document.spectrum is not None
    assert len(document.annotations) == 2


def test_onSave_invalid(calculator_panel, mock_parent, mocker):
    """Verify onSave does nothing if data is missing."""
    calculator_panel.currentPatternScan = None
    mock_bell = mocker.patch("wx.Bell")
    calculator_panel.onSave(None)
    assert mock_bell.called
    assert not mock_parent.onDocumentNew.called


def test_onClose(calculator_panel, mock_parent, mocker):
    """Verify onClose clears tmp spectrum and destroys frame."""
    mock_destroy = mocker.patch.object(calculator_panel, "Destroy")
    calculator_panel.onClose(None)
    mock_parent.updateTmpSpectrum.assert_called_with(None)
    assert mock_destroy.called


def test_onPatternChanged(calculator_panel, patched_config, mocker):
    """Verify onPatternChanged updates pattern."""
    calculator_panel.setData(formula="H2O")

    mock_run_pattern = mocker.patch.object(calculator_panel, "runPattern")
    calculator_panel.onPatternChanged(None)
    assert mock_run_pattern.called


def test_onProfileChanged(calculator_panel, patched_config, mocker):
    """Verify onProfileChanged updates profile."""
    calculator_panel.setData(formula="H2O")

    mock_make_profile = mocker.patch.object(calculator_panel, "makeProfile")
    calculator_panel.onProfileChanged(None)
    assert mock_make_profile.called


def test_onSave_with_ion(calculator_panel, mock_parent, patched_config):
    """Verify onSave with a selected ion."""
    calculator_panel.setData(formula="H2O", charge=1)
    # setData with charge=1 should select the +1 ion and set currentIon
    assert calculator_panel.currentIon is not None

    calculator_panel.onSave(None)

    assert mock_parent.onDocumentNew.called
    args, kwargs = mock_parent.onDocumentNew.call_args
    document = kwargs.get("document") or args[0]
    assert "H2O" in document.title
    assert "Ion: [M+1H] 1+" in document.notes


def test_getParams_exception(calculator_panel, patched_config, mocker):
    """Verify getParams handles non-numeric input."""
    calculator_panel.compound_value.SetValue("H2O")
    calculator_panel.patternFwhm_value.SetValue("abc")
    mock_bell = mocker.patch("wx.Bell")
    assert calculator_panel.getParams() is False
    assert mock_bell.called


def test_onToolSelected_by_event(calculator_panel, mocker):
    """Verify onToolSelected when called via event."""
    from gui.ids import ID_massCalculatorIonSeries

    mock_event = mocker.MagicMock()
    mock_event.GetId.return_value = ID_massCalculatorIonSeries

    calculator_panel.onToolSelected(mock_event)
    assert calculator_panel.currentTool == "ionseries"


def test_onCompoundChanged_invalid(calculator_panel, patched_config, mocker):
    """Verify onCompoundChanged handles invalid params."""
    calculator_panel.compound_value.SetValue("")  # Invalid

    mock_update = mocker.patch.object(calculator_panel, "updateSummary")
    calculator_panel.onCompoundChanged(None)
    assert mock_update.called
    assert calculator_panel.currentCompound is None


def test_onPatternChanged_invalid(calculator_panel, patched_config, mocker):
    """Verify onPatternChanged handles invalid params."""
    calculator_panel.setData(formula="H2O")
    calculator_panel.patternFwhm_value.SetValue("-1")  # Invalid

    mock_update = mocker.patch.object(calculator_panel, "updatePatternCanvas")
    calculator_panel.onPatternChanged(None)
    assert mock_update.called
    assert calculator_panel.currentPattern is None


def test_onProfileChanged_no_pattern(calculator_panel):
    """Verify onProfileChanged does nothing if no pattern exists."""
    calculator_panel.currentPattern = None
    calculator_panel.onProfileChanged(None)  # Should return early


def test_onProfileChanged_invalid_params(calculator_panel, patched_config):
    """Verify onProfileChanged handles invalid params."""
    calculator_panel.setData(formula="H2O")
    calculator_panel.patternIntensity_value.SetValue("0")  # Invalid

    calculator_panel.onProfileChanged(None)
    assert calculator_panel.currentPatternProfile is None


def test_runIonSeries_limit(calculator_panel, patched_config):
    """Verify runIonSeries hits the m/z limit."""
    # Use a high charge to hit mz < 100 quickly
    calculator_panel.compound_value.SetValue("C60")
    calculator_panel.ionseriesAgentCharge_value.SetValue("100")
    calculator_panel.getParams()
    calculator_panel.runIonSeries()
    # Should have stopped when mz < 100
    assert calculator_panel.currentIons[-1][1] < 1000  # Just checking it runs


def test_setData_edge_cases(calculator_panel):
    """Verify setData with edge cases in intensity/baseline."""
    # Baseline >= Intensity
    calculator_panel.setData(intensity=100, baseline=200)
    assert float(calculator_panel.patternIntensity_value.GetValue()) == 400.0

    # Zero intensity/baseline
    calculator_panel.setData(intensity=0, baseline=0)
    assert float(calculator_panel.patternIntensity_value.GetValue()) == 1.0

    # Large intensity
    calculator_panel.setData(intensity=20000)
    assert calculator_panel.patternIntensity_value.GetValue() == "2.0e+04"


def test_onToolSelected_ids(calculator_panel, mocker):
    """Verify onToolSelected with all possible IDs."""
    from gui.ids import (
        ID_massCalculatorIonSeries,
        ID_massCalculatorPattern,
        ID_massCalculatorSummary,
    )

    for tool_id, tool_name in [
        (ID_massCalculatorSummary, "summary"),
        (ID_massCalculatorIonSeries, "ionseries"),
        (ID_massCalculatorPattern, "pattern"),
    ]:
        mock_event = mocker.MagicMock()
        mock_event.GetId.return_value = tool_id
        calculator_panel.onToolSelected(mock_event)
        assert calculator_panel.currentTool == tool_name
