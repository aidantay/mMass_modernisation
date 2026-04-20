import pytest
import wx

# Monkeypatch wx.RESIZE_BOX for compatibility with wxPython 4.0
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = getattr(wx, 'RESIZE_BORDER', 0)

from gui.panel_match import panelMatch
from gui import config
from gui import images
from gui import doc
import mspy
import mspy.plot

@pytest.fixture
def mock_mainFrame(mocker):
    """Mock mainFrame with getCurrentPeaklist."""
    frame = mocker.Mock()
    frame.getCurrentPeaklist = mocker.Mock(return_value=None)
    return frame

@pytest.fixture
def mock_parentTool(wx_app):
    """Fixture for parentTool, which must be a wx.Window/Frame."""
    frame = wx.Frame(None)
    yield frame
    if frame:
        frame.Destroy()

@pytest.fixture
def panel(wx_app, mock_parentTool, mock_mainFrame, mocker):
    """Fixture to instantiate panelMatch with necessary mocks."""
    
    # Mock methods on mock_parentTool
    mock_parentTool.updateMatches = mocker.Mock()
    mock_parentTool.calibrateByMatches = mocker.Mock()
    
    # Mock config dictionaries
    mock_config_match = {
        'tolerance': 0.2,
        'units': 'Da',
        'ignoreCharge': 0,
        'filterAnnotations': 0,
        'filterMatches': 0,
        'filterUnselected': 0,
        'filterIsotopes': 1,
        'filterUnknown': 0,
    }
    mock_config_main = {
        'mzDigits': 4,
        'reverseScrolling': 0,
    }
    mock_config_spectrum = {
        'axisFontSize': 10,
    }
    
    # Mock images library
    dummy_bitmap = wx.Bitmap(16, 16)
    mock_images_lib = {
        'bgrToolbar': dummy_bitmap,
        'matchErrorsOff': dummy_bitmap,
        'matchSummaryOff': dummy_bitmap,
        'matchErrorsOn': dummy_bitmap,
        'matchSummaryOn': dummy_bitmap,
        'bgrControlbar': dummy_bitmap,
        'stopper': dummy_bitmap,
    }
    
    def create_mock_canvas(parent, *args, **kwargs):
        """Create a mock canvas that is a real wx.Panel with expected methods."""
        p = wx.Panel(parent)
        p.draw = mocker.Mock()
        p.setProperties = mocker.Mock()
        p.setMFunction = mocker.Mock()
        return p

    # Patch dependencies
    mocker.patch.dict(config.match, mock_config_match, clear=True)
    mocker.patch.dict(config.main, mock_config_main, clear=True)
    mocker.patch.dict(config.spectrum, mock_config_spectrum, clear=True)
    mocker.patch.dict(images.lib, mock_images_lib, clear=True)
    mocker.patch('mspy.plot.canvas', side_effect=create_mock_canvas)
    mocker.patch('mspy.plot.container')
    mocker.patch('mspy.plot.points')
    mocker.patch('mspy.plot.spectrum')
        
    # Instantiate panel
    p = panelMatch(mock_parentTool, mock_mainFrame, 'massfilter')
    yield p
        
    # Cleanup
    if p:
        p.Destroy()

def test_init(wx_app, mock_mainFrame, mocker):
    """Test initialization and title for different modules."""
    
    parent = wx.Frame(None)
    modules = {
        'massfilter': 'Match References',
        'digest': 'Match Peptides',
        'fragment': 'Match Fragments',
        'compounds': 'Match Compounds',
        'unknown': 'Match Data'
    }
    
    # Mock config and images as in the panel fixture
    dummy_bitmap = wx.Bitmap(16, 16)
    mock_images_lib = {
        'bgrToolbar': dummy_bitmap,
        'matchErrorsOff': dummy_bitmap,
        'matchSummaryOff': dummy_bitmap,
        'matchErrorsOn': dummy_bitmap,
        'matchSummaryOn': dummy_bitmap,
        'bgrControlbar': dummy_bitmap,
        'stopper': dummy_bitmap,
    }
    
    def create_mock_canvas(parent, *args, **kwargs):
        """Create a mock canvas that is a real wx.Panel with expected methods."""
        p = wx.Panel(parent)
        p.draw = mocker.Mock()
        p.setProperties = mocker.Mock()
        p.setMFunction = mocker.Mock()
        return p

    mocker.patch.dict(images.lib, mock_images_lib, clear=True)
    mocker.patch('mspy.plot.canvas', side_effect=create_mock_canvas)
        
    for module, expected_title in modules.items():
        p = panelMatch(parent, mock_mainFrame, module)
        assert p.GetTitle() == expected_title
        p.Destroy()
    
    parent.Destroy()

def test_onToolSelected(panel, mocker):
    """Verify swapping between 'errors' and 'summary' updates UI visibility."""
    
    # Actually IDs are imported from ids.py
    from gui.ids import ID_matchErrors, ID_matchSummary
    
    # Case 1: Select summary
    mock_event = mocker.Mock()
    mock_event.GetId.return_value = ID_matchSummary
    panel.onToolSelected(evt=mock_event)
    assert panel.currentTool == 'summary'
    assert panel.mainSizer.IsShown(panel.errorCanvas) is False
    assert panel.mainSizer.IsShown(panel.summaryList) is True
    
    # Case 2: Select errors
    mock_event.GetId.return_value = ID_matchErrors
    panel.onToolSelected(evt=mock_event)
    assert panel.currentTool == 'errors'
    assert panel.mainSizer.IsShown(panel.errorCanvas) is True
    assert panel.mainSizer.IsShown(panel.summaryList) is False

def test_onClose(panel, mocker):
    """Test closing logic, including wx.Bell when self.processing is set."""
    
    # Case 1: Normal close
    mock_destroy = mocker.patch.object(panel, 'Destroy')
    panel.onClose(None)
    mock_destroy.assert_called_once()
    
    # Case 2: Close while processing
    panel.processing = mocker.Mock() # Simulate active processing
    mock_bell = mocker.patch('wx.Bell')
    mock_destroy = mocker.patch.object(panel, 'Destroy')
    panel.onClose(None)
    mock_bell.assert_called_once()
    mock_destroy.assert_not_called()

def test_onUnitsChanged(panel, mocker):
    """Test unit conversion in onUnitsChanged."""
    # Set initial error: 1000 m/z, 1.0 Da error
    panel.currentErrors = [[1000.0, 1.0]]
    
    # Toggle to ppm
    panel.unitsDa_radio.SetValue(False)
    panel.unitsPpm_radio.SetValue(True)
    
    mocker.patch.object(panel, 'updateErrorCanvas')
    panel.onUnitsChanged()
    assert config.match['units'] == 'ppm'
    # 1.0 / (1000.0 / 1000000) = 1000.0 ppm
    assert pytest.approx(panel.currentErrors[0][1]) == 1000.0
        
    # Toggle back to Da
    panel.unitsDa_radio.SetValue(True)
    panel.unitsPpm_radio.SetValue(False)
    panel.onUnitsChanged()
    assert config.match['units'] == 'Da'
    # 1000.0 * (1000.0 / 1000000) = 1.0 Da
    assert pytest.approx(panel.currentErrors[0][1]) == 1.0

def test_getParams(panel, mocker):
    """Test getting parameters from UI to config."""
    # Test valid tolerance
    panel.tolerance_value.SetValue("0.5")
    assert panel.getParams() is True
    assert config.match['tolerance'] == 0.5
    
    # Test invalid tolerance
    panel.tolerance_value.SetValue("abc")
    mock_bell = mocker.patch('wx.Bell')
    assert panel.getParams() is False
    mock_bell.assert_called_once()
    
    # Test checkboxes update config
    panel.tolerance_value.SetValue("0.2")
    panel.ignoreCharge_check.SetValue(True)
    panel.filterAnnotations_check.SetValue(True)
    panel.filterMatches_check.SetValue(True)
    panel.filterUnselected_check.SetValue(True)
    panel.filterIsotopes_check.SetValue(False)
    panel.filterUnknown_check.SetValue(True)
    
    panel.getParams()
    assert config.match['ignoreCharge'] == 1
    assert config.match['filterAnnotations'] == 1
    assert config.match['filterMatches'] == 1
    assert config.match['filterUnselected'] == 1
    assert config.match['filterIsotopes'] == 0
    assert config.match['filterUnknown'] == 1

def test_onFilter(panel, mocker):
    """Test onFilter updates config and refreshes data."""
    panel.filterAnnotations_check.SetValue(True)
    panel.filterMatches_check.SetValue(False)
    
    mock_getPeaklist = mocker.patch.object(panel, 'getPeaklist')
    mock_updateErrorCanvas = mocker.patch.object(panel, 'updateErrorCanvas')
    mock_updateMatchSummary = mocker.patch.object(panel, 'updateMatchSummary')
        
    panel.onFilter(None)
        
    assert config.match['filterAnnotations'] == 1
    assert config.match['filterMatches'] == 0
        
    # Verify clearing of values
    assert panel.currentPeaklist is None
    assert panel.currentSummary is None
    assert panel.currentErrors == []
    assert panel.currentCalibrationPoints == []
        
    # Verify refresh calls
    mock_getPeaklist.assert_called_once()
    mock_updateErrorCanvas.assert_called_once()
    mock_updateMatchSummary.assert_called_once()

def test_onMatch(panel, mocker):
    """Test background matching process."""
    
    panel.currentData = []
    
    # Mocking behaviors
    mock_thread = mocker.patch('threading.Thread')
    mocker.patch.object(panel, 'getParams', return_value=True)
    mock_getPeaklist = mocker.patch.object(panel, 'getPeaklist')
    mock_onProcessing = mocker.patch.object(panel, 'onProcessing')
    mocker.patch.object(panel, 'updateErrorCanvas')
    mocker.patch.object(panel, 'updateMatchSummary')
        
    # Ensure currentPeaklist is set by the mock_getPeaklist call (simulated)
    def side_effect():
        panel.currentPeaklist = mocker.Mock()
    mock_getPeaklist.side_effect = side_effect
        
    # mock_thread returns an instance
    mock_thread_instance = mock_thread.return_value
    mock_thread_instance.isAlive.return_value = False # Stop the while loop immediately
        
    panel.onMatch()
        
    # Assertions
    mock_thread.assert_called_with(target=panel.runMatch)
    mock_thread_instance.start.assert_called_once()
        
    # onProcessing called with True, then False
    assert mock_onProcessing.call_count == 2
    mock_onProcessing.assert_has_calls([mocker.call(True), mocker.call(False)])
        
    panel.parentTool.updateMatches.assert_called_with(panel.currentModule)

def test_onStop(panel, mocker):
    """Test stopping the background processing."""
    
    # Case 1: Processing is alive
    panel.processing = mocker.Mock()
    panel.processing.isAlive.return_value = True
    
    mock_stop = mocker.patch('mspy.stop')
    panel.onStop(None)
    mock_stop.assert_called_once()
    
    # Case 2: Processing is NOT alive
    panel.processing.isAlive.return_value = False
    mock_bell = mocker.patch('wx.Bell')
    panel.onStop(None)
    mock_bell.assert_called_once()

def test_getPeaklist(panel, mock_mainFrame):
    """Test constructing the filter string for getPeaklist."""
    
    # Case 1: All filters enabled
    config.match['filterAnnotations'] = 1
    config.match['filterMatches'] = 1
    config.match['filterUnselected'] = 1
    config.match['filterIsotopes'] = 1
    config.match['filterUnknown'] = 1
    
    panel.getPeaklist()
    mock_mainFrame.getCurrentPeaklist.assert_called_with('AMSIX')
    
    # Case 2: Only 'A' and 'M'
    config.match['filterAnnotations'] = 1
    config.match['filterMatches'] = 1
    config.match['filterUnselected'] = 0
    config.match['filterIsotopes'] = 0
    config.match['filterUnknown'] = 0
    
    panel.getPeaklist()
    mock_mainFrame.getCurrentPeaklist.assert_called_with('AM')
    
    # Case 3: None
    config.match['filterAnnotations'] = 0
    config.match['filterMatches'] = 0
    config.match['filterUnselected'] = 0
    config.match['filterIsotopes'] = 0
    config.match['filterUnknown'] = 0
    
    panel.getPeaklist()
    mock_mainFrame.getCurrentPeaklist.assert_called_with('')

def test_runMatch_massfilter(panel, mocker):
    """Test runMatch for massfilter module."""
    panel.currentModule = 'massfilter'
    
    # Mock peaklist with one peak
    peak = mspy.peak(mz=100.1, ai=1000)
    panel.currentPeaklist = [peak]
    
    # Set currentData: [label, mass, error, match_list]
    panel.currentData = [['label', 100.0, None, []]]
    
    # Set config params
    config.match['tolerance'] = 0.2
    config.match['units'] = 'Da'
    
    # We need to mock makeMatchSummary because it uses more data
    mocker.patch.object(panel, 'makeMatchSummary')
    panel.runMatch()
    
    # Assertions
    # error is 100.1 - 100.0 = 0.1
    assert pytest.approx(panel.currentData[0][2]) == 0.1
    assert len(panel.currentData[0][-1]) == 1
    assert isinstance(panel.currentData[0][-1][0], doc.annotation)
    
    # currentErrors: [[peak.mz, error]]
    assert len(panel.currentErrors) == 1
    assert pytest.approx(panel.currentErrors[0][0]) == 100.1
    assert pytest.approx(panel.currentErrors[0][1]) == 0.1
    
    # currentCalibrationPoints: [[label, theoretical, measured]]
    assert len(panel.currentCalibrationPoints) == 1
    assert panel.currentCalibrationPoints[0][0].startswith('Peak 100.1000')
    assert pytest.approx(panel.currentCalibrationPoints[0][1]) == 100.0
    assert pytest.approx(panel.currentCalibrationPoints[0][2]) == 100.1

def test_runMatch_digest(panel, mocker):
    """Test runMatch for digest module."""
    panel.currentModule = 'digest'
    
    # Mock peaklist with one peak
    peak = mspy.peak(mz=100.1, ai=1000)
    peak.charge = 1
    panel.currentPeaklist = [peak]
    
    # Set currentData: ['', '', mass, charge, '', error, peptide_obj, match_list]
    # index 2 is mass, index 3 is charge, index 5 is error, index 6 is peptide object, last index is match list
    peptide = mocker.Mock()
    panel.currentData = [['', '', 100.0, 1, '', None, peptide, []]]
    
    # Set config params
    config.match['tolerance'] = 0.2
    config.match['units'] = 'Da'
    config.match['ignoreCharge'] = 0
    
    mocker.patch.object(panel, 'makeMatchSummary')
    panel.runMatch()
    
    # Assertions
    assert pytest.approx(panel.currentData[0][5]) == 0.1
    assert len(panel.currentData[0][-1]) == 1
    assert isinstance(panel.currentData[0][-1][0], doc.match)

def test_runMatch_force_quit(panel, mocker):
    """Test runMatch when mspy.CHECK_FORCE_QUIT raises ForceQuit."""
    panel.currentModule = 'massfilter'
    panel.currentData = [['label', 100.0, 0.1, [mocker.Mock()]]]
    panel.currentPeaklist = [mspy.peak(mz=100.1, ai=1000)]
    
    mocker.patch('mspy.CHECK_FORCE_QUIT', side_effect=mspy.ForceQuit)
    panel.runMatch()
    
    # Assertions
    assert panel.currentErrors == []
    assert panel.currentCalibrationPoints == []
    assert panel.currentSummary == []
    # Error for index 2
    assert panel.currentData[0][2] is None
    # match_list for last index
    assert panel.currentData[0][-1] == []

def test_makeMatchSummary_digest(panel, mocker):
    """Test makeMatchSummary for digest module."""
    panel.currentModule = 'digest'
    
    # Mock peaklist
    peak = mspy.peak(mz=100.1, ai=1000)
    panel.currentPeaklist = [peak]
    
    # Mock peptide object with history
    peptide = mocker.Mock()
    # history entry: (type, start, stop)
    # To get 60% coverage on length 10, we need 6 residues.
    # range(0, 6) is 6 residues.
    # panel_match.py uses [history[-1][1]+1, history[-1][2]]
    # so [1, 6] -> mspy.coverage([1, 6], 10, human=True) -> range(0, 6) -> 60%
    peptide.history = [['normal', 0, 6]]
    
    # Set currentData: ['', '', mass, charge, '', error, peptide_obj, match_list]
    match_obj = mocker.Mock()
    match_obj.mz = 100.1
    panel.currentData = [['', '', 100.0, 1, '', 0.1, peptide, [match_obj]]]
    
    # Set summary data
    panel.currentSummaryData = {'sequenceLength': 10}
    
    panel.makeMatchSummary()
    
    # Verify summary contents
    summary_dict = dict(panel.currentSummary)
    assert summary_dict['Number of peaks searched'] == 1
    assert summary_dict['Number of peptides searched'] == '1'
    assert summary_dict['Number of peptides matched'] == 1
    assert summary_dict['Intensity matched'] == '100 %'
    assert summary_dict['Sequence length'] == 10
    assert summary_dict['Sequence coverage'] == '60 %'

def test_makeMatchSummary_fragment(panel, mocker):
    """Test makeMatchSummary for fragment module."""
    panel.currentModule = 'fragment'
    
    # Mock peaklist
    panel.currentPeaklist = [mspy.peak(mz=100.1, ai=1000)]
    
    # Create fragment mocks
    # frag1: y1 matched
    frag1 = mocker.Mock()
    frag1.fragmentSerie = 'y'
    frag1.fragmentLosses = []
    frag1.fragmentGains = []
    frag1.fragmentIndex = 1
    frag1.history = [['normal', 0, 1]]
    
    # frag2: b1 NOT matched
    frag2 = mocker.Mock()
    frag2.fragmentSerie = 'b'
    frag2.fragmentLosses = []
    frag2.fragmentGains = []
    frag2.fragmentIndex = 1
    frag2.history = [['normal', 0, 1]]
    
    # frag3: b2 -H2O matched
    frag3 = mocker.Mock()
    frag3.fragmentSerie = 'b'
    frag3.fragmentLosses = ['H2O']
    frag3.fragmentGains = []
    frag3.fragmentIndex = 2
    frag3.history = [['normal', 0, 2]]
    
    # Set currentData
    match_obj = mocker.Mock()
    match_obj.mz = 100.1
    panel.currentData = [
        ['', '', 100.0, 1, '', 0.1, frag1, [match_obj]],
        ['', '', 110.0, 1, '', None, frag2, []],
        ['', '', 120.0, 1, '', 0.1, frag3, [match_obj]],
    ]
    
    panel.currentSummaryData = {'sequenceLength': 10}
    
    panel.makeMatchSummary()
    
    summary_dict = dict(panel.currentSummary)
    assert summary_dict['Sequence length'] == 10
    assert summary_dict['Ion serie matches for "y"'] == '1'
    assert summary_dict['Ion serie matches for "b"'] == ''
    assert summary_dict['Ion serie matches for "b -H2O"'] == '2'

def test_setData(panel, mocker):
    """Test setData method."""
    matchData = [['test', 100.0, None, []]]
    summaryData = {'key': 'value'}
    
    mock_getPeaklist = mocker.patch.object(panel, 'getPeaklist')
    mock_updateErrorCanvas = mocker.patch.object(panel, 'updateErrorCanvas')
    mock_updateMatchSummary = mocker.patch.object(panel, 'updateMatchSummary')
        
    panel.setData(matchData, summaryData)
        
    assert panel.currentData == matchData
    assert panel.currentSummaryData == summaryData
    assert panel.currentPeaklist is None
    assert panel.currentSummary is None
    assert panel.currentErrors == []
    assert panel.currentCalibrationPoints == []
        
    mock_getPeaklist.assert_called_once()
    mock_updateErrorCanvas.assert_called_once()
    mock_updateMatchSummary.assert_called_once()

def test_clear(panel, mocker):
    """Test clear method."""
    panel.currentData = [['test']]
    panel.currentSummaryData = {'key': 'value'}
    
    mock_updateErrorCanvas = mocker.patch.object(panel, 'updateErrorCanvas')
    mock_updateMatchSummary = mocker.patch.object(panel, 'updateMatchSummary')
        
    panel.clear()
        
    assert panel.currentData is None
    assert panel.currentSummaryData is None
    assert panel.currentPeaklist is None
    assert panel.currentSummary is None
    assert panel.currentErrors == []
    assert panel.currentCalibrationPoints == []
        
    mock_updateErrorCanvas.assert_called_once()
    mock_updateMatchSummary.assert_called_once()

def test_updateErrorCanvas(panel, mocker):
    """Test updateErrorCanvas calls canvas draw with correct container."""
    panel.currentErrors = [[100.0, 0.1], [200.0, 0.2]]
    panel.currentPeaklist = [mspy.peak(mz=100.0, ai=1000)]
    
    mock_container = mocker.patch('mspy.plot.container')
    mock_points = mocker.patch('mspy.plot.points')
    mock_spectrum = mocker.patch('mspy.plot.spectrum')
    mocker.patch.object(panel, 'makeCurrentPeaklist', return_value=[])
        
    # Reset mock to ignore calls during setup
    panel.errorCanvas.draw.reset_mock()
        
    panel.updateErrorCanvas()
        
    # Verify container was built
    assert mock_container.call_count == 1
    assert mock_points.call_count == 1
    assert mock_spectrum.call_count == 1
        
    # Verify canvas draw called
    panel.errorCanvas.draw.assert_called_once()

def test_updateMatchSummary(panel, mocker):
    """Test updateMatchSummary updates the list control."""
    panel.currentSummary = [('Param1', 'Value1'), ('Param2', 123)]
    
    # We need to mock summaryList methods if it's not fully functional in test env
    # summaryList is a sortListCtrl which inherits from wx.ListCtrl
    mock_delete = mocker.patch.object(panel.summaryList, 'DeleteAllItems')
    mock_set_map = mocker.patch.object(panel.summaryList, 'setDataMap')
    mock_insert = mocker.patch.object(panel.summaryList, 'InsertItem')
    mock_set_string = mocker.patch.object(panel.summaryList, 'SetItem')
    mock_set_data = mocker.patch.object(panel.summaryList, 'SetItemData')
    mock_visible = mocker.patch.object(panel.summaryList, 'EnsureVisible')
    mocker.patch.object(panel.summaryList, 'updateItemsBackground')
        
    panel.updateMatchSummary()
        
    mock_delete.assert_called_once()
    mock_set_map.assert_called_with(panel.currentSummary)
    assert mock_insert.call_count == 2
    assert mock_set_string.call_count == 2
    assert mock_set_data.call_count == 2
    mock_visible.assert_called_with(0)

def test_makeCurrentPeaklist(panel):
    """Test makeCurrentPeaklist scaling logic."""
    # Peaklist with basepeak 1000
    p1 = mspy.peak(mz=100.0, ai=1000)
    p2 = mspy.peak(mz=200.0, ai=500)
    panel.currentPeaklist = mspy.peaklist([p1, p2])
    
    # Error range: 0.1 to 0.5 -> diff = 0.4
    panel.currentErrors = [[100.0, 0.1], [200.0, 0.5]]
    
    # minY = 0.1, maxY = 0.5
    # diff = 0.4
    # margin = 0.05 * 0.4 = 0.02
    # minY_adj = 0.1 - 0.02 = 0.08
    # f = (0.5 - 0.08) / 1000 = 0.00042
    # p1 new intensity = (1000 * 0.00042) + 0.08 = 0.50
    # p2 new intensity = (500 * 0.00042) + 0.08 = 0.21 + 0.08 = 0.29
    
    res = panel.makeCurrentPeaklist()
    assert isinstance(res, mspy.peaklist)
    assert len(res) == 2
    
    mz100 = [p for p in res if p.mz == 100.0][0]
    mz200 = [p for p in res if p.mz == 200.0][0]
    
    assert pytest.approx(mz100.ai) == 0.50
    assert pytest.approx(mz200.ai) == 0.29
    assert pytest.approx(mz100.base) == 0.08

def test_tooltips(panel):
    """Test tooltips for buttons."""
    # Check if tooltips are set correctly
    assert panel.errors_butt.GetToolTipText() == "Error plot"
    assert panel.summary_butt.GetToolTipText() == "Match summary"

def test_onProcessing(panel, mocker):
    """Test onProcessing for modal behavior."""
    # Mock wx.WindowDisabler
    mock_disabler = mocker.patch('wx.WindowDisabler', autospec=True)
    
    # Enable processing
    panel.onProcessing(True)
    assert hasattr(panel, '_window_disabler')
    mock_disabler.assert_called_once()
    
    # Disable processing
    panel.onProcessing(False)
    assert not hasattr(panel, '_window_disabler')

