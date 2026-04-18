import sys

import pytest
import wx


# Helper classes that don't depend on mocking framework directly
class MockThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}
        self._alive = False

    def start(self):
        self._alive = True
        if self.target:
            self.target(*self.args, **self.kwargs)
        self._alive = False

    def is_alive(self):
        return self._alive

    def is_alive(self):
        return self._alive


class MockImagesLib(dict):
    def __getitem__(self, key):
        return wx.Bitmap(10, 10)


@pytest.fixture
def mock_gui_env(mocker):
    """
    Fixture to setup the mocked environment for GUI tests.
    Returns a dictionary of all mocked modules.
    """
    modules_to_mock = ["mwx", "images", "config", "libs", "mspy", "doc", "ids"]
    mocks = {}
    for mod_name in modules_to_mock:
        m = mocker.MagicMock()
        mocks[mod_name] = m
        # Also patch sys.modules for any direct imports
        mocks["gui." + mod_name] = m
        mocker.patch("gui." + mod_name, m, create=True)

    mocks["gui.panel_match"] = mocker.MagicMock()
    mocker.patch("gui.panel_match", mocks["gui.panel_match"], create=True)

    # Setup mock_images.lib
    mocks["images"].lib = MockImagesLib()

    # Setup mock_ids
    mock_ids = mocks["ids"]
    mock_ids.ID_compoundsSearchCompounds = 1001
    mock_ids.ID_compoundsSearchFormula = 1002
    mock_ids.ID_listViewAll = 1003
    mock_ids.ID_listViewMatched = 1004
    mock_ids.ID_listViewUnmatched = 1005
    mock_ids.ID_listSendToMassCalculator = 1006
    mock_ids.ID_listCopyFormula = 1007
    mock_ids.ID_listCopy = 1008

    # Handle missing wx.RESIZE_BOX in wxPython Phoenix
    if not hasattr(wx, "RESIZE_BOX"):
        wx.RESIZE_BOX = getattr(wx, "MAXIMIZE_BOX", 0)

    # Setup mock_mwx
    mock_mwx = mocks["mwx"]
    mock_mwx.LISTCTRL_NO_SPACE = 0
    mock_mwx.TOOLBAR_HEIGHT = 30
    mock_mwx.TOOLBAR_TOOLSIZE = (24, 24)
    mock_mwx.TOOLBAR_LSPACE = 5
    mock_mwx.TOOLBAR_RSPACE = 5
    mock_mwx.BUTTON_SIZE_CORRECTION = 0
    mock_mwx.SMALL_CHOICE_HEIGHT = 20
    mock_mwx.SMALL_BUTTON_HEIGHT = 20
    mock_mwx.CONTROLBAR_HEIGHT = 30
    mock_mwx.CONTROLBAR_LSPACE = 5
    mock_mwx.CONTROLBAR_RSPACE = 5
    mock_mwx.SMALL_TEXTCTRL_HEIGHT = 20
    mock_mwx.GAUGE_SPACE = 5
    mock_mwx.LISTCTRL_STYLE_SINGLE = 0
    mock_mwx.LISTCTRL_ALTCOLOUR = wx.Colour(240, 240, 240)
    mock_mwx.SMALL_FONT_SIZE = 10

    def mock_layout(win, sizer):
        if hasattr(win, "Layout"):
            win.Layout()

    mock_mwx.layout = mock_layout

    class MockValidator(wx.Validator):
        def __init__(self, *args, **kwargs):
            wx.Validator.__init__(self)

        def Clone(self):
            return MockValidator()

        def Validate(self, win):
            return True

        def TransferToWindow(self):
            return True

        def TransferFromWindow(self):
            return True

    mock_mwx.validator = MockValidator

    class MockListCtrl(wx.Panel):
        def __init__(self, parent=None, *args, **kwargs):
            wx.Panel.__init__(self, parent, -1)
            self.SetFont = mocker.MagicMock()
            self.setSecondarySortColumn = mocker.MagicMock()
            self.setAltColour = mocker.MagicMock()
            self.InsertColumn = mocker.MagicMock()
            self.SetColumnWidth = mocker.MagicMock()
            self.DeleteAllItems = mocker.MagicMock()
            self.setDataMap = mocker.MagicMock()
            self.getSelected = mocker.MagicMock(return_value=[])
            self.GetItemData = mocker.MagicMock(return_value=0)
            self.InsertItem = mocker.MagicMock(return_value=0)
            self.SetItem = mocker.MagicMock()
            self.SetItemData = mocker.MagicMock()
            self.SetItemTextColour = mocker.MagicMock()
            self.SetItemFont = mocker.MagicMock()
            self.sort = mocker.MagicMock()
            self.EnsureVisible = mocker.MagicMock()
            self.copyToClipboard = mocker.MagicMock()
            self.GetItemCount = mocker.MagicMock(return_value=0)

    mock_mwx.sortListCtrl = lambda parent, *args, **kwargs: MockListCtrl(parent)

    class MockGauge(wx.Gauge):
        def __init__(self, parent=None, *args, **kwargs):
            wx.Gauge.__init__(self, parent, -1)

        def SetValue(self, val):
            pass

        def pulse(self):
            pass

    mock_mwx.gauge = lambda parent, *args, **kwargs: MockGauge(parent)

    def mock_bgrPanel(parent, *args, **kwargs):
        return wx.Panel(parent)

    mock_mwx.bgrPanel = mock_bgrPanel

    # Setup mock_config
    mock_config = mocks["config"]
    mock_config.compoundsSearch = {
        "massType": 0,
        "maxCharge": 1,
        "radicals": 0,
        "adducts": ["Na", "K"],
    }
    mock_config.main = {"mzDigits": 4, "ppmDigits": 1}
    mock_config.match = {"units": "ppm"}

    # Setup mock_libs
    mocks["libs"].compounds = {"Group1": {}}

    # Setup mock_mspy
    class MockForceQuit(Exception):
        pass

    mock_mspy = mocks["mspy"]
    mock_mspy.ForceQuit = MockForceQuit
    mock_mspy.CHECK_FORCE_QUIT = mocker.MagicMock()
    mocker.patch("mspy.CHECK_FORCE_QUIT", mock_mspy.CHECK_FORCE_QUIT)

    def make_mock_compound(formula):
        comp = mocker.MagicMock()
        comp.isvalid.return_value = True
        comp.mz.return_value = [100.0, 100.0]
        comp.expression = formula
        return comp

    mock_mspy.compound = mocker.MagicMock(side_effect=make_mock_compound)
    mocker.patch("mspy.compound", mock_mspy.compound)

    # Patch sys.modules
    mocker.patch.dict(sys.modules, mocks)

    # Patch threading.Thread
    mocker.patch("threading.Thread", MockThread)

    return mocks


@pytest.fixture
def panel_class(mock_gui_env):
    """
    Fixture to import the panel class after mocks are established.
    Forces a reload to ensure mocks are used.
    """
    if "gui.panel_compounds_search" in sys.modules:
        del sys.modules["gui.panel_compounds_search"]
    from gui.panel_compounds_search import panelCompoundsSearch

    return panelCompoundsSearch


@pytest.fixture
def parent_frame(wx_app, mocker):
    frame = wx.Frame(None)
    frame.updateMassPoints = mocker.MagicMock()
    frame.onDocumentChanged = mocker.MagicMock()
    yield frame
    frame.Destroy()


@pytest.fixture
def panel(panel_class, parent_frame):
    p = panel_class(parent_frame)
    yield p
    if p:
        try:
            p.Destroy()
        except:
            pass


def test_init(panel):
    assert panel.GetTitle() == "Compounds Search"
    assert panel.currentTool == "compounds"


def test_onToolSelected(panel, mock_gui_env, mocker):
    mock_ids = mock_gui_env["ids"]
    mock_evt = mocker.MagicMock()
    mock_evt.GetId.return_value = mock_ids.ID_compoundsSearchFormula
    panel.onToolSelected(mock_evt)
    assert panel.currentTool == "formula"
    assert panel.GetTitle() == "Formula Search"

    mock_evt.GetId.return_value = mock_ids.ID_compoundsSearchCompounds
    panel.onToolSelected(mock_evt)
    assert panel.currentTool == "compounds"


def test_getParams(panel, mock_gui_env, mocker):
    mock_config = mock_gui_env["config"]
    panel.massTypeAv_radio.SetValue(True)
    panel.maxCharge_value.SetValue("2")
    assert panel.getParams() is True
    assert mock_config.compoundsSearch["massType"] == 1
    assert mock_config.compoundsSearch["maxCharge"] == 2

    panel.maxCharge_value.SetValue("invalid")
    mock_bell = mocker.patch("wx.Bell")
    assert panel.getParams() is False
    mock_bell.assert_called_once()


def test_onProcessing(panel, mock_gui_env, mocker):
    mock_mspy = mock_gui_env["mspy"]
    mock_disabler = mocker.patch("wx.WindowDisabler")
    panel.onProcessing(True)
    assert panel.mainSizer.IsShown(3)
    mock_disabler.assert_called_with(panel)

    panel.onProcessing(False)
    assert not panel.mainSizer.IsShown(3)
    mock_mspy.start.assert_called_once()
    assert not hasattr(panel, "_disabler")


def test_onStop(panel, mock_gui_env, mocker):
    mock_mspy = mock_gui_env["mspy"]
    panel.processing = mocker.MagicMock()
    panel.processing.is_alive.return_value = True
    panel.onStop(None)
    mock_mspy.stop.assert_called_once()


def test_onClose(panel, mocker):
    panel.matchPanel = mocker.MagicMock()
    panel.processing = None
    mock_destroy = mocker.patch.object(panel, "Destroy")
    panel.onClose(None)
    panel.matchPanel.Close.assert_called_once()
    mock_destroy.assert_called_once()


def test_runGenerateIons(panel, mock_gui_env, mocker):
    mock_mspy = mock_gui_env["mspy"]
    mock_config = mock_gui_env["config"]

    # We need to recreate the mock compound helper because mspy is mocked
    def make_mock_compound(formula):
        comp = mocker.MagicMock()
        comp.isvalid.return_value = True
        comp.mz.return_value = [18.0, 18.0]
        comp.expression = formula
        return comp

    mock_comp = make_mock_compound("H2O")
    compounds = {"Water": mock_comp}

    mock_config.compoundsSearch = {
        "massType": 0,
        "maxCharge": 1,
        "radicals": 1,
        "adducts": ["Na"],
    }

    panel.runGenerateIons(compounds)
    assert len(panel.currentCompounds) >= 2  # [H2O, H2O_radical, H2O_Na] etc.

    assert panel.currentCompounds[0][0] == "Water"
    assert panel.currentCompounds[0][3] == None
    assert panel.currentCompounds[1][3] == "radical"


def test_runGenerateIons_force_quit(panel, mock_gui_env, mocker):
    mock_mspy = mock_gui_env["mspy"]
    mock_config = mock_gui_env["config"]

    def make_mock_compound(formula):
        comp = mocker.MagicMock()
        comp.isvalid.return_value = True
        comp.mz.return_value = [100.0, 100.0]
        comp.expression = formula
        return comp

    mock_comp = make_mock_compound("H2O")
    compounds = {"Water": mock_comp}
    mock_config.compoundsSearch = {
        "massType": 0,
        "maxCharge": 1,
        "radicals": 0,
        "adducts": [],
    }

    # ForceQuit exception
    mock_mspy.CHECK_FORCE_QUIT.side_effect = mock_mspy.ForceQuit()

    panel.runGenerateIons(compounds)
    assert panel.currentCompounds == []


def test_onGenerate(panel, mock_gui_env, mocker):
    mock_libs = mock_gui_env["libs"]
    mock_mspy = mock_gui_env["mspy"]

    def make_mock_compound(formula):
        comp = mocker.MagicMock()
        comp.isvalid.return_value = True
        comp.mz.return_value = [100.0, 100.0]
        comp.expression = formula
        return comp

    # Set up UI and config to ensure it doesn't return early
    mock_libs.compounds = {"Group1": {"Water": make_mock_compound("H2O")}}
    panel.compounds_choice.Append("Group1")
    panel.compounds_choice.SetStringSelection("Group1")
    panel.maxCharge_value.SetValue("1")
    panel.radicals_check.SetValue(False)

    # Mock updateCompoundsList and onProcessing
    mock_update = mocker.patch.object(panel, "updateCompoundsList")
    mock_proc = mocker.patch.object(panel, "onProcessing")
    panel.onGenerate(None)
    mock_proc.assert_any_call(True)
    mock_proc.assert_any_call(False)
    mock_update.assert_called()


def test_onAnnotate(panel, mocker):
    doc = mocker.MagicMock()
    doc.annotations = []
    panel.currentDocument = doc

    # 0 name, 1 m/z, 2 z, 3 adduct, 4 formula, 5 error, 6 matches
    mock_match1 = mocker.MagicMock()
    mock_match2 = mocker.MagicMock()
    mock_match3 = mocker.MagicMock()
    panel.currentCompounds = [
        ["Water", 18.0, 1, None, "H2O", 0.0, [mock_match1]],
        ["WaterRadical", 18.0, 1, "radical", "H2O", 0.0, [mock_match2]],
        ["WaterNa", 18.0, 1, "Na", "H2O", 0.0, [mock_match3]],
    ]

    panel.onAnnotate(None)
    doc.backup.assert_called_with("annotations")
    assert len(doc.annotations) == 3
    assert doc.annotations[0].label == "Water"
    assert doc.annotations[1].label == "WaterRadical (radical)"
    assert doc.annotations[1].radical == 1
    assert doc.annotations[2].label == "WaterNa (Na adduct)"
    panel.parent.onDocumentChanged.assert_called()


def test_onMatch(panel, mocker):
    panel.currentCompounds = [["Water", 18.0, 1, None, "H2O", None, []]]
    mock_match_cls = mocker.patch("gui.panel_compounds_search.panelMatch")
    mock_match_panel = mock_match_cls.return_value
    panel.matchPanel = mock_match_panel  # Ensure match=True
    panel.onMatch(mocker.MagicMock())
    assert panel.matchPanel == mock_match_panel
    mock_match_panel.setData.assert_called_with(panel.currentCompounds)
    mock_match_panel.onMatch.assert_called()


def test_setData(panel, mocker):
    doc = mocker.MagicMock()
    panel.currentCompounds = [["Water", 18.0, 1, None, "H2O", 0.0, []]]
    panel.setData(doc)
    assert panel.currentDocument == doc
    # clearMatches should clear item[5] and item[-1]
    assert panel.currentCompounds[0][5] == None
    assert panel.currentCompounds[0][-1] == []


def test_onItemSelected(panel, mocker):
    panel.currentCompounds = [["Water", 18.0, 1, None, "H2O", None, []]]
    mock_evt = mocker.MagicMock()
    mock_evt.GetData.return_value = 0
    panel.onItemSelected(mock_evt)
    panel.parent.updateMassPoints.assert_called_with([18.0])


def test_onItemSendToMassCalculator(panel, mocker):
    panel.currentCompounds = [
        ["Water", 18.0, 1, None, "H2O", None, []],
        ["WaterRadical", 18.0, 1, "radical", "H2O", None, []],
    ]
    panel.parent.onToolsMassCalculator = mocker.MagicMock()

    # Case 1: No selection
    panel.compoundsList.getSelected.return_value = []
    mock_bell = mocker.patch("wx.Bell")
    panel.onItemSendToMassCalculator(None)
    mock_bell.assert_called_once()

    # Case 2: Normal selection
    panel.compoundsList.getSelected.return_value = [0]
    panel.compoundsList.GetItemData.return_value = 0
    panel.onItemSendToMassCalculator(None)
    panel.parent.onToolsMassCalculator.assert_called_with(
        formula="H2O", charge=1, agentFormula="H", agentCharge=1
    )

    # Case 3: Radical selection
    panel.compoundsList.GetItemData.return_value = 1
    panel.onItemSendToMassCalculator(None)
    panel.parent.onToolsMassCalculator.assert_called_with(
        formula="H2O", charge=1, agentFormula="e", agentCharge=-1
    )


def test_onItemActivated(panel, mocker):
    mock_send = mocker.patch.object(panel, "onItemSendToMassCalculator")
    panel.onItemActivated(None)
    mock_send.assert_called_once()


def test_onItemCopyFormula(panel, mocker):
    panel.currentCompounds = [["Water", 18.0, 1, None, "H2O", None, []]]
    panel.compoundsList.getSelected.return_value = [0]
    panel.compoundsList.GetItemData.return_value = 0

    mock_cb = mocker.patch("wx.TheClipboard")
    mock_cb.Open.return_value = True
    panel.onItemCopyFormula(None)
    mock_cb.SetData.assert_called()
    mock_cb.Close.assert_called()


def test_onListKey(panel, mocker):
    mock_evt = mocker.MagicMock()
    mock_evt.GetKeyCode.return_value = 67  # 'C'
    mock_evt.CmdDown.return_value = True
    mock_copy = mocker.patch.object(panel, "onListCopy")
    panel.onListKey(mock_evt)
    mock_copy.assert_called_once()

    mock_evt.CmdDown.return_value = False
    panel.onListKey(mock_evt)
    mock_evt.Skip.assert_called_once()


def test_onListRMU(panel, mocker):
    panel.PopupMenu = mocker.MagicMock()
    mock_menu_cls = mocker.patch("wx.Menu")
    panel.onListRMU(None)
    mock_menu_cls.return_value.Append.assert_called()
    panel.PopupMenu.assert_called()


def test_updateCompoundsList_matched(panel):
    panel.currentCompounds = [
        ["Water", 18.0, 1, None, "H2O", 0.0, []],
        ["Other", 100.0, 1, None, "C", None, []],
    ]
    # Filter matched
    panel._compoundsFilter = 1
    panel.updateCompoundsList()
    # It should call InsertItem once
    assert panel.compoundsList.InsertItem.called

    # Filter unmatched
    panel._compoundsFilter = -1
    panel.updateCompoundsList()
    assert panel.compoundsList.InsertItem.called


def test_onListFilter(panel, mock_gui_env, mocker):
    mock_ids = mock_gui_env["ids"]
    mock_evt = mocker.MagicMock()
    mock_evt.GetId.return_value = mock_ids.ID_listViewMatched
    panel.onListFilter(mock_evt)
    assert panel._compoundsFilter == 1

    mock_evt.GetId.return_value = mock_ids.ID_listViewUnmatched
    panel.onListFilter(mock_evt)
    assert panel._compoundsFilter == -1

    mock_evt.GetId.return_value = mock_ids.ID_listViewAll
    panel.onListFilter(mock_evt)
    assert panel._compoundsFilter == 0


def test_onListCopy(panel):
    panel.onListCopy(None)
    panel.compoundsList.copyToClipboard.assert_called_once()
