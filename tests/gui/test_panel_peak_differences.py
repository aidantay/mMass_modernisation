import pytest
import wx

import mmass.gui.config as config
from mmass import mspy
from mmass.gui.panel_peak_differences import panelPeakDifferences


@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.updateMassPoints = mocker.Mock()
    parent.onToolsMassToFormula = mocker.Mock()
    yield parent
    parent.Destroy()


@pytest.fixture
def mock_monomers(mocker):
    m1 = mocker.Mock()
    m1.category = "_InternalAA"
    m1.mass = (10.0, 11.0)  # (mono, av)

    m2 = mocker.Mock()
    m2.category = "_InternalAA"
    m2.mass = (20.0, 22.0)

    monomers = {"A": m1, "B": m2, "X": mocker.Mock(category="other")}
    mocker.patch("mmass.mspy.monomers", monomers)
    yield monomers


@pytest.fixture
def panel(wx_app, mock_parent, mock_monomers, mocker):
    mock_lib = {
        "bgrToolbarNoBorder": wx.Bitmap(1, 1),
        "stopper": wx.Bitmap(1, 1),
    }
    mocker.patch("mmass.gui.images.lib", mock_lib)
    p = panelPeakDifferences(mock_parent)
    yield p
    if p:
        p.Destroy()


def test_init(panel):
    assert panel.GetTitle() == "Peak Differences"
    assert panel.parent is not None
    assert "A" in panel._aaMasses
    assert "B" in panel._aaMasses
    assert "X" not in panel._aaMasses
    assert "AA" in panel._dipMasses
    assert "AB/BA" in panel._dipMasses
    assert "BB" in panel._dipMasses


def test_make_gui(panel):
    assert isinstance(panel.difference_value, wx.TextCtrl)
    assert isinstance(panel.aminoacids_check, wx.CheckBox)
    assert isinstance(panel.dipeptides_check, wx.CheckBox)
    assert isinstance(panel.massTypeMo_radio, wx.RadioButton)
    assert isinstance(panel.massTypeAv_radio, wx.RadioButton)
    assert isinstance(panel.tolerance_value, wx.TextCtrl)
    assert isinstance(panel.consolidate_check, wx.CheckBox)
    assert isinstance(panel.search_butt, wx.Button)
    assert isinstance(panel.differencesGrid, wx.grid.Grid)
    assert isinstance(panel.matchesGrid, wx.grid.Grid)
    assert isinstance(panel.gauge, wx.Gauge)


def test_get_params_success(panel):
    panel.difference_value.SetValue("100.5")
    panel.aminoacids_check.SetValue(True)
    panel.dipeptides_check.SetValue(False)
    panel.tolerance_value.SetValue("0.1")
    panel.massTypeAv_radio.SetValue(True)
    panel.consolidate_check.SetValue(True)

    assert panel.getParams() is True
    assert panel.currentDifference == 100.5
    assert config.peakDifferences["aminoacids"] == 1
    assert config.peakDifferences["dipeptides"] == 0
    assert config.peakDifferences["tolerance"] == 0.1
    assert config.peakDifferences["massType"] == 1
    assert config.peakDifferences["consolidate"] == 1


def test_get_params_empty_diff(panel):
    panel.difference_value.SetValue("")
    assert panel.getParams() is True
    assert panel.currentDifference is None


def test_get_params_failure(panel, mocker):
    panel.tolerance_value.SetValue("invalid")
    mock_bell = mocker.patch("wx.Bell")
    assert panel.getParams() is False
    mock_bell.assert_called_once()


def test_set_data(panel, mocker):
    mock_doc = mocker.Mock()
    panel.currentDifferences = [1, 2, 3]
    panel.currentMatches = [4, 5]

    panel.setData(mock_doc)
    assert panel.currentDocument == mock_doc
    assert panel.currentDifferences is None
    assert panel.currentMatches is None


def test_on_processing(panel, mocker):
    mock_disabler = mocker.patch("wx.WindowDisabler", autospec=True)
    mock_start = mocker.patch("mmass.mspy.start")

    # Test status=True
    panel.onProcessing(True)
    mock_disabler.assert_called_with(panel)
    assert hasattr(panel, "_disabler")
    assert panel.mainSizer.IsShown(2)

    # Test status=False
    panel.onProcessing(False)
    assert not hasattr(panel, "_disabler")
    assert not panel.mainSizer.IsShown(2)
    mock_start.assert_called_once()


def test_on_stop(panel, mocker):
    panel.processing = mocker.Mock()
    panel.processing.is_alive.return_value = True
    mock_stop = mocker.patch("mmass.mspy.stop")
    panel.onStop(None)
    mock_stop.assert_called_once()

    panel.processing.is_alive.return_value = False
    mock_bell = mocker.patch("wx.Bell")
    panel.onStop(None)
    mock_bell.assert_called_once()


def test_on_cell_selected(panel, mocker):
    panel.currentDifferences = [
        [(100.0, 0), (0.0, False)],
        [(200.0, 1), (100.0, False), (0.0, False)],
    ]
    evt = mocker.Mock()
    evt.GetCol.return_value = 0
    evt.GetRow.return_value = 1

    mock_search = mocker.patch.object(panel, "searchSelected")
    mock_update = mocker.patch.object(panel, "updateMatchesGrid")
    panel.onCellSelected(evt)
    panel.parent.updateMassPoints.assert_called_with([100.0, 200.0])
    mock_search.assert_called_with(100.0)
    mock_update.assert_called_once()


def test_on_cell_activated(panel, mocker):
    panel.currentDifferences = [
        [(100.0, 0), (0.0, False)],
        [(200.0, 1), (100.0, False), (0.0, False)],
    ]
    config.peakDifferences["tolerance"] = 0.5
    evt = mocker.Mock()
    evt.GetCol.return_value = 0
    evt.GetRow.return_value = 1

    panel.onCellActivated(evt)
    panel.parent.updateMassPoints.assert_called_with([100.0, 200.0])
    panel.parent.onToolsMassToFormula.assert_called_with(
        mass=100.0, charge=0, tolerance=0.5, units="Da", agentFormula=""
    )


def test_on_search_no_doc(panel, mocker):
    panel.currentDocument = None
    mock_bell = mocker.patch("wx.Bell")
    panel.onSearch(None)
    mock_bell.assert_called_once()


def test_on_search_params_fail(panel, mocker):
    panel.currentDocument = mocker.Mock()
    mocker.patch.object(panel, "getParams", return_value=False)
    mock_bell = mocker.patch("wx.Bell")
    panel.onSearch(None)
    mock_bell.assert_called()


def test_on_search_success(panel, mocker):
    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = [mocker.Mock(mz=100.0)]
    panel.currentDocument = mock_doc

    # Mock threading.Thread to run target synchronously
    def mock_thread_init(target=None, args=(), kwargs={}):
        target(*args, **kwargs)
        return mocker.Mock(is_alive=lambda: False)

    mocker.patch("threading.Thread", side_effect=mock_thread_init)
    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "onProcessing")
    mocker.patch.object(panel, "updateDifferencesGrid")
    mocker.patch.object(panel, "updateMatchesGrid")
    panel.onSearch(None)


def test_update_differences_grid(panel):
    panel.currentDifferences = [
        [(100.0, 0), (0.0, False)],
        [(200.0, 1), (100.0, "value"), (0.0, False)],
        [(300.0, 2), (200.0, "amino"), (100.0, "dipep"), (0.0, False)],
    ]
    config.main["mzDigits"] = 2

    panel.updateDifferencesGrid()
    assert panel.differencesGrid.GetNumberRows() == 3
    assert panel.differencesGrid.GetCellValue(1, 0) == "100.00"
    assert panel.differencesGrid.GetCellValue(0, 1) == "100.00"
    assert panel.differencesGrid.GetCellValue(0, 0) == "---"

    # Check colors
    assert panel.differencesGrid.GetCellBackgroundColour(1, 0) == wx.Colour(
        100, 255, 100
    )  # value
    assert panel.differencesGrid.GetCellBackgroundColour(2, 0) == wx.Colour(
        0, 200, 255
    )  # amino
    assert panel.differencesGrid.GetCellBackgroundColour(2, 1) == wx.Colour(
        100, 255, 255
    )  # dipep


def test_update_matches_grid(panel):
    panel.currentMatches = [("A", 0.01), ("B", -0.02)]
    config.main["mzDigits"] = 2

    panel.updateMatchesGrid()
    assert panel.matchesGrid.GetNumberRows() == 2
    assert panel.matchesGrid.GetCellValue(0, 0) == "A"
    assert panel.matchesGrid.GetCellValue(0, 1) == "0.01"
    assert panel.matchesGrid.GetCellValue(1, 0) == "B"
    assert panel.matchesGrid.GetCellValue(1, 1) == "-0.02"


def test_search_selected(panel):
    panel.currentDifference = 100.0
    config.peakDifferences["tolerance"] = 0.5
    config.peakDifferences["aminoacids"] = 1
    config.peakDifferences["dipeptides"] = 1
    config.peakDifferences["massType"] = 0  # mono

    panel._aaMasses = {"A": (10.0, 11.0)}
    panel._dipMasses = {"AA": (20.0, 22.0)}

    # Match value
    panel.searchSelected(100.1)
    assert len(panel.currentMatches) == 1
    assert panel.currentMatches[0][0] == "100.0"

    # Match AA
    panel.searchSelected(10.1)
    assert any(m[0] == "A" for m in panel.currentMatches)

    # Match Dipeptide
    panel.searchSelected(20.1)
    assert any(m[0] == "AA" for m in panel.currentMatches)


def test_run_search_success(panel, mocker):
    mock_peak1 = mocker.Mock(mz=100.0)
    mock_peak2 = mocker.Mock(mz=110.0)
    mock_peak3 = mocker.Mock(mz=120.0)

    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = [mock_peak1, mock_peak2, mock_peak3]
    panel.currentDocument = mock_doc

    panel.currentDifference = 10.0
    config.peakDifferences["tolerance"] = 0.5
    config.peakDifferences["aminoacids"] = 1
    config.peakDifferences["dipeptides"] = 1
    config.peakDifferences["massType"] = 0
    config.peakDifferences["consolidate"] = 0

    panel._aaLimits = [5.0, 15.0]
    panel._aaMasses = {"A": (10.0, 11.0)}
    panel._dipLimits = [15.0, 25.0]
    panel._dipMasses = {"AA": (20.0, 22.0)}

    panel.runSearch()

    assert len(panel.currentDifferences) == 3
    # Row 0: peak1 (100.0)
    assert panel.currentDifferences[0][0] == (100.0, 0)
    # Row 1: peak2 (110.0). Diff with peak1 is 10.0. Matches value and amino.
    assert panel.currentDifferences[1][0] == (110.0, 1)
    assert panel.currentDifferences[1][1][0] == 10.0
    assert panel.currentDifferences[1][2][0] == 0.0  # self diff
    assert panel.currentDifferences[1][1][1] == "value"  # value has priority in code

    # Row 2: peak3 (120.0). Diff with peak1 is 20.0. Matches dipep.
    assert panel.currentDifferences[2][0] == (120.0, 2)
    assert panel.currentDifferences[2][1][0] == 20.0  # with peak1
    assert panel.currentDifferences[2][2][0] == 10.0  # with peak2
    assert panel.currentDifferences[2][3][0] == 0.0  # self diff
    assert panel.currentDifferences[2][1][1] == "dipep"


def test_run_search_force_quit(panel, mocker):
    panel.currentDocument = mocker.Mock()
    panel.currentDocument.spectrum.peaklist = [mocker.Mock(mz=100.0)]
    mocker.patch("mmass.mspy.CHECK_FORCE_QUIT", side_effect=mspy.ForceQuit)
    panel.runSearch()
    assert panel.currentDifferences == []


def test_consolidate_table(panel):
    # Setup data where only some peaks have matches
    # Peak 0: no matches
    # Peak 1: matches with Peak 2
    # Peak 2: matches with Peak 1
    # Peak 3: no matches
    panel.currentDifferences = [
        [(100.0, 0), (0.0, False)],
        [(110.0, 1), (10.0, False), (0.0, False)],
        [(120.0, 2), (20.0, False), (10.0, "value"), (0.0, False)],
        [(130.0, 3), (30.0, False), (20.0, False), (10.0, False), (0.0, False)],
    ]

    panel.consolidateTable()

    # Should only keep peaks 1 and 2
    assert len(panel.currentDifferences) == 2
    assert panel.currentDifferences[0][0] == (110.0, 1)
    assert panel.currentDifferences[1][0] == (120.0, 2)


def test_on_close(panel, mocker):
    panel.processing = None
    mock_destroy = mocker.patch.object(panel, "Destroy")
    panel.onClose(None)
    mock_destroy.assert_called_once()


def test_on_search_already_processing(panel, mocker):
    panel.processing = mocker.Mock()
    assert panel.onSearch(None) is None


def test_on_search_no_peaklist(panel, mocker):
    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = None
    panel.currentDocument = mock_doc

    def mock_thread_init(target=None, args=(), kwargs={}):
        target(*args, **kwargs)
        return mocker.Mock(is_alive=lambda: False)

    mocker.patch("threading.Thread", side_effect=mock_thread_init)
    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "onProcessing")
    panel.onSearch(None)
    assert panel.currentDifferences is None


def test_update_grids_twice(panel):
    # Test clearing logic in update grids
    panel.currentDifferences = [[(100.0, 0), (0.0, False)]]
    panel.updateDifferencesGrid()
    panel.updateDifferencesGrid()  # Should trigger DeleteCols/Rows

    panel.currentMatches = [("A", 0.0)]
    panel.updateMatchesGrid()
    panel.updateMatchesGrid()  # Should trigger DeleteCols/Rows


def test_on_close_processing(panel, mocker):
    panel.processing = mocker.Mock()
    mock_bell = mocker.patch("wx.Bell")
    panel.onClose(None)
    mock_bell.assert_called_once()


def test_on_processing_with_yield_fail(panel, mocker):
    mocker.patch.object(panel, "MakeModal", create=True)
    mocker.patch("wx.Yield", side_effect=Exception)
    panel.onProcessing(True)


def test_run_search_no_peaklist(panel, mocker):
    panel.currentDocument = mocker.Mock()
    panel.currentDocument.spectrum.peaklist = None
    assert panel.runSearch() is False


def test_consolidate_table_empty(panel):
    panel.currentDifferences = []
    panel.consolidateTable()
    assert panel.currentDifferences == []
