import pytest
import wx

import gui.config as config
from gui.panel_mass_defect_plot import panelMassDefectPlot
import mspy.plot

@pytest.fixture
def mock_parent(wx_app):
    """Fixture to provide a real parent for the panel."""
    parent = wx.Frame(None)
    yield parent
    if parent:
        parent.Destroy()

@pytest.fixture
def panel(wx_app, mock_parent, mocker):
    """Fixture to provide a panelMassDefectPlot instance."""
    # Mock canvas methods that cause issues in headless/unrealized state
    mocker.patch('mspy.plot_canvas.canvas.onSize', return_value=None)
    mocker.patch('mspy.plot_canvas.canvas.draw', return_value=None)
    p = panelMassDefectPlot(mock_parent)
    # Ensure plotBuffer exists because canvas expects it
    p.plotCanvas.plotBuffer = wx.Bitmap(1, 1)
    p.plotCanvas.lastDraw = None
    yield p
    if p:
        try:
            p.Destroy()
        except:
            pass

def test_initialization(panel):
    """Test that the panel and its components are initialized correctly."""
    assert isinstance(panel, panelMassDefectPlot)
    assert panel.GetTitle() == 'Mass Defect Plot'
    
    # Check that main components are created
    assert hasattr(panel, 'yAxis_choice')
    assert hasattr(panel, 'nominalMass_choice')
    assert hasattr(panel, 'kendrickFormula_value')
    assert hasattr(panel, 'plot_butt')
    assert hasattr(panel, 'relIntCutoff_value')
    assert hasattr(panel, 'removeIsotopes_check')
    assert hasattr(panel, 'ignoreCharge_check')
    assert hasattr(panel, 'showNotations_check')
    assert hasattr(panel, 'showAllDocuments_check')
    assert hasattr(panel, 'plotCanvas')
    
    # Check default config values are populated
    # yAxis
    expected_y_axis = config.massDefectPlot['yAxis']
    choices = ['fraction', 'standard', 'relative', 'kendrick']
    if expected_y_axis in choices:
        assert panel.yAxis_choice.GetSelection() == choices.index(expected_y_axis)
    
    # nominalMass
    expected_nominal = config.massDefectPlot['nominalMass'].title()
    assert panel.nominalMass_choice.GetStringSelection() == expected_nominal
    
    # kendrickFormula
    assert panel.kendrickFormula_value.GetValue() == config.massDefectPlot['kendrickFormula']
    
    # relIntCutoff
    expected_cutoff = str(config.massDefectPlot['relIntCutoff'] * 100)
    assert panel.relIntCutoff_value.GetValue() == expected_cutoff
    
    # checkboxes
    assert panel.removeIsotopes_check.GetValue() == bool(config.massDefectPlot['removeIsotopes'])
    assert panel.ignoreCharge_check.GetValue() == bool(config.massDefectPlot['ignoreCharge'])
    assert panel.showNotations_check.GetValue() == bool(config.massDefectPlot['showNotations'])
    assert panel.showAllDocuments_check.GetValue() == False # Hardcoded to False in makeControlbar

def test_on_axis_changed(panel):
    """Test that onAxisChanged enables/disables the Kendrick formula field."""
    # Select Kendrick
    panel.yAxis_choice.SetStringSelection('Kendrick Mass Defect')
    panel.onAxisChanged()
    assert panel.kendrickFormula_value.IsEnabled() is True
    
    # Select something else
    panel.yAxis_choice.SetStringSelection('Mass Defect')
    panel.onAxisChanged()
    assert panel.kendrickFormula_value.IsEnabled() is False

def test_on_close(panel, mocker):
    """Test that onClose calls Destroy."""
    mocked_destroy = mocker.patch.object(panel, 'Destroy')
    panel.onClose(None)
    mocked_destroy.assert_called_once()

def test_get_params_success(panel):
    """Test getParams with valid inputs."""
    # Set valid values in UI
    panel.yAxis_choice.SetSelection(2) # relative
    panel.nominalMass_choice.SetStringSelection('Floor')
    panel.relIntCutoff_value.SetValue('10.5')
    panel.removeIsotopes_check.SetValue(True)
    panel.ignoreCharge_check.SetValue(True)
    panel.showNotations_check.SetValue(True)
    panel.showAllDocuments_check.SetValue(True)
    panel.kendrickFormula_value.SetValue('CH2')
    
    assert panel.getParams() is True
    
    assert config.massDefectPlot['yAxis'] == 'relative'
    assert config.massDefectPlot['nominalMass'] == 'floor'
    assert config.massDefectPlot['relIntCutoff'] == 0.105
    assert config.massDefectPlot['removeIsotopes'] is True
    assert config.massDefectPlot['ignoreCharge'] is True
    assert config.massDefectPlot['showNotations'] is True
    assert config.massDefectPlot['showAllDocuments'] is True
    assert config.massDefectPlot['kendrickFormula'] == 'CH2'

def test_get_params_invalid_float(panel, mocker):
    """Test getParams with invalid float for intensity cutoff."""
    panel.relIntCutoff_value.SetValue('not a float')
    mocked_bell = mocker.patch('wx.Bell')
    assert panel.getParams() is False
    mocked_bell.assert_called_once()

def test_get_params_invalid_kendrick(panel, mocker):
    """Test getParams with invalid Kendrick formula when yAxis is kendrick."""
    panel.yAxis_choice.SetSelection(3) # kendrick
    panel.kendrickFormula_value.SetValue('') # Empty formula should have 0 mass
    mocked_bell = mocker.patch('wx.Bell')
    assert panel.getParams() is False
    mocked_bell.assert_called_once()

def test_on_show_notations(panel, mocker):
    """Test onShowNotations handler."""
    panel.showNotations_check.SetValue(True)
    mocked_on_plot = mocker.patch.object(panel, 'onPlot')
    panel.onShowNotations(None)
    assert config.massDefectPlot['showNotations'] is True
    mocked_on_plot.assert_called_once()

def test_on_show_all_documents(panel, mocker):
    """Test onShowAllDocuments handler."""
    panel.showAllDocuments_check.SetValue(True)
    mocked_on_plot = mocker.patch.object(panel, 'onPlot')
    panel.onShowAllDocuments(None)
    assert config.massDefectPlot['showAllDocuments'] is True
    mocked_on_plot.assert_called_once()

def test_update_documents(panel, mocker):
    """Test updateDocuments method."""
    config.massDefectPlot['showAllDocuments'] = True
    mocked_on_plot = mocker.patch.object(panel, 'onPlot')
    panel.updateDocuments()
    mocked_on_plot.assert_called_once()
        
    config.massDefectPlot['showAllDocuments'] = False
    mocked_on_plot = mocker.patch.object(panel, 'onPlot')
    panel.updateDocuments()
    assert not mocked_on_plot.called

def test_set_data(panel, mocker):
    """Test setData method."""
    mock_doc = mocker.Mock()
    mocked_on_plot = mocker.patch.object(panel, 'onPlot')
    panel.setData(mock_doc)
    assert panel.currentDocument == mock_doc
    mocked_on_plot.assert_called_once()

def test_calc_data_points(panel):
    """Test calcDataPoints calculation logic."""
    # Setup config
    config.massDefectPlot['yAxis'] = 'standard'
    config.massDefectPlot['nominalMass'] = 'round'
    config.massDefectPlot['xAxis'] = 'mz'
    config.massDefectPlot['ignoreCharge'] = True
    config.massDefectPlot['kendrickFormula'] = 'CH2'
    
    # Mock peak: (mz, charge)
    peaks = [(100.1, 1), (200.2, 2)]
    
    # mspy.md(mass=100.1, mdType='standard', rounding='round')
    # mass defect = 100.1 - round(100.1) = 100.1 - 100 = 0.1
    # mspy.md(mass=200.2, mdType='standard', rounding='round')
    # mass defect = 200.2 - round(200.2) = 200.2 - 200 = 0.2
    
    points = panel.calcDataPoints(peaks)
    assert len(points) == 2
    assert points[0][0] == 100.1
    assert pytest.approx(points[0][1]) == 0.1
    assert points[1][0] == 200.2
    assert pytest.approx(points[1][1]) == 0.2

def test_calc_data_points_kendrick(panel):
    """Test calcDataPoints with Kendrick mass defect."""
    config.massDefectPlot['yAxis'] = 'kendrick'
    config.massDefectPlot['xAxis'] = 'kendrick'
    config.massDefectPlot['nominalMass'] = 'round'
    config.massDefectPlot['ignoreCharge'] = True
    config.massDefectPlot['kendrickFormula'] = 'CH2'
    
    peaks = [(100.1, 1)]
    points = panel.calcDataPoints(peaks)
    
    # In calcDataPoints:
    # mass = mspy.nominalmass(peak[0] * kendrickFormula.nominalmass()/kendrickFormula.mass(0))
    # It uses default rounding='floor' because it's not passed.
    # CH2 factor is approx 0.99888
    # 100.1 * 0.99888 = 99.988...
    # floor(99.988...) = 99.0
    
    assert len(points) == 1
    assert points[0][0] == 99.0
    
    # Check y-axis (Kendrick Mass Defect)
    # km = 100.1 * 0.99888 = 99.988226
    # md = nominalmass(km, 'round') - km = 100.0 - 99.988226 = 0.011774
    assert points[0][1] == pytest.approx(0.011774, abs=1e-5)

def test_calc_data_points_with_charge(panel):
    """Test calcDataPoints when ignoreCharge is False."""
    config.massDefectPlot['ignoreCharge'] = False
    config.massDefectPlot['yAxis'] = 'standard'
    config.massDefectPlot['nominalMass'] = 'round'
    config.massDefectPlot['xAxis'] = 'mz'
    
    # Peak: (mz=100.1, charge=2), polarity=1
    # mspy.mz(100.1, 1, 2) = (100.1 * 2 - 1.007825) = 199.192...
    # Wait, mspy.mz(mz, charge, currentCharge)
    # If currentCharge is 2, it first calculates mass = mz * 2 - agentMass * 2
    # Then it returns mass for charge 1?
    # No, panel calls it as:
    # mspy.mz(peak[0], 1*polarity, peak[1], agentFormula='H', agentCharge=1)
    # mz(100.1, 1, 2, 'H', 1)
    
    peaks = [(100.1, 2)]
    points = panel.calcDataPoints(peaks, polarity=1)
    
    # Let's just verify it's different from mz=100.1
    assert points[0][0] == 100.1
    assert points[0][1] != pytest.approx(0.1) # 100.1 - 100

def test_make_data_points_no_polarity(panel, mocker):
    """Test makeDataPoints when polarity is None or 0."""
    config.massDefectPlot['removeIsotopes'] = False
    config.massDefectPlot['relIntCutoff'] = 0.0
    
    class MockPeak:
        def __init__(self, mz, ri, isotope, charge=1):
            self.mz = mz
            self.ri = ri
            self.isotope = isotope
            self.charge = charge
            
    peaks = [MockPeak(100.1, 0.5, 0)]
    
    mocked_calc = mocker.patch.object(panel, 'calcDataPoints', return_value=[(1,2)])
    panel.makeDataPoints(peaks, polarity=None)
    mocked_calc.assert_called_with(mocker.ANY, 1) # polarity defaults to 1

def test_on_plot_notations_complex(panel, mocker):
    """Test onPlot with annotations and sequences."""
    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = []
    mock_doc.spectrum.polarity = 1
    mock_doc.annotations = [mocker.Mock(mz=100.1, charge=1)]
    
    mock_match = mocker.Mock(mz=200.1, charge=2)
    mock_sequence = mocker.Mock()
    mock_sequence.matches = [mock_match]
    mock_doc.sequences = [mock_sequence]
    
    panel.currentDocument = mock_doc
    
    config.massDefectPlot['showAllDocuments'] = False
    config.massDefectPlot['showNotations'] = True
    
    mocker.patch.object(panel, 'getParams', return_value=True)
    mocked_make = mocker.patch.object(panel, 'makeDataPoints', return_value=[])
    mocker.patch.object(panel.plotCanvas, 'draw')
    panel.onPlot()
    # Check what was passed to makeDataPoints for notations
    # It should be a peaklist with 2 items
    notations_call = mocked_make.call_args_list[0]
    passed_peaklist = notations_call[0][0]
    assert len(passed_peaklist) == 2

def test_make_data_points(panel, mocker):
    """Test makeDataPoints filtering logic."""
    config.massDefectPlot['removeIsotopes'] = True
    config.massDefectPlot['relIntCutoff'] = 0.1 # 10%
    
    class MockPeak:
        def __init__(self, mz, ri, isotope, charge=1):
            self.mz = mz
            self.ri = ri
            self.isotope = isotope
            self.charge = charge
            
    peaks = [
        MockPeak(100.1, 0.5, 0),    # Keep
        MockPeak(100.2, 0.05, 0),   # Remove (low RI)
        MockPeak(101.1, 0.2, 1),    # Remove (isotope)
        MockPeak(200.1, 0.8, None)  # Keep (None isotope treated as 0)
    ]
    
    mocked_calc = mocker.patch.object(panel, 'calcDataPoints', return_value=[(1,2), (3,4)])
    points = panel.makeDataPoints(peaks)
    assert len(points) == 2
    mocked_calc.assert_called_once()
    # Check that only 100.1 and 200.1 were passed to calcDataPoints
    args = mocked_calc.call_args[0][0]
    assert len(args) == 2
    assert args[0] == [100.1, 1]
    assert args[1] == [200.1, 1]

def test_on_plot_current_doc(panel, mocker):
    """Test onPlot with current document."""
    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = []
    mock_doc.spectrum.polarity = 1
    panel.currentDocument = mock_doc
    
    config.massDefectPlot['showAllDocuments'] = False
    config.massDefectPlot['showNotations'] = False
    
    mocker.patch.object(panel, 'getParams', return_value=True)
    mocked_make = mocker.patch.object(panel, 'makeDataPoints', return_value=[])
    mocked_draw = mocker.patch.object(panel.plotCanvas, 'draw')
    panel.onPlot()
    mocked_make.assert_called_once()
    mocked_draw.assert_called_once()

def test_on_plot_all_docs(panel, mocker):
    """Test onPlot with all documents."""
    panel.currentDocument = None
    config.massDefectPlot['showAllDocuments'] = True
    config.massDefectPlot['showNotations'] = False
    
    doc1 = mocker.Mock()
    doc1.visible = True
    doc1.spectrum.peaklist = []
    doc1.spectrum.polarity = 1
    doc1.colour = (255, 0, 0)
    
    doc2 = mocker.Mock()
    doc2.visible = False
    
    panel.parent.documents = [doc1, doc2]
    
    mocker.patch.object(panel, 'getParams', return_value=True)
    mocked_make = mocker.patch.object(panel, 'makeDataPoints', return_value=[])
    mocked_draw = mocker.patch.object(panel.plotCanvas, 'draw')
    panel.onPlot()
    assert mocked_make.call_count == 1 # Only for doc1
    mocked_draw.assert_called_once()

def test_on_plot_notations(panel, mocker):
    """Test onPlot with notations."""
    mock_doc = mocker.Mock()
    mock_doc.spectrum.peaklist = []
    mock_doc.spectrum.polarity = 1
    mock_doc.annotations = [mocker.Mock(mz=100.1, charge=1)]
    mock_doc.sequences = []
    panel.currentDocument = mock_doc
    
    config.massDefectPlot['showAllDocuments'] = False
    config.massDefectPlot['showNotations'] = True
    
    mocker.patch.object(panel, 'getParams', return_value=True)
    mocked_make = mocker.patch.object(panel, 'makeDataPoints', return_value=[])
    mocker.patch.object(panel.plotCanvas, 'draw')
    panel.onPlot()
    # Once for notations, once for spectrum
    assert mocked_make.call_count == 2

def test_on_plot_get_params_fail(panel, mocker):
    """Test onPlot when getParams fails."""
    mocker.patch.object(panel, 'getParams', return_value=False)
    mocked_refresh = mocker.patch.object(panel.plotCanvas, 'refresh')
    mocked_bell = mocker.patch('wx.Bell')
    panel.onPlot()
    mocked_refresh.assert_called_once()
    mocked_bell.assert_called_once()

def test_on_plot_canvas_lmu(panel, mocker):
    """Test onPlotCanvasLMU interaction."""
    mock_evt = mocker.Mock()
    panel.currentDocument = mocker.Mock()
    
    # Mock position and distance
    # distance[0] == 0 means we clicked on a point
    panel.plotCanvas.getCursorPosition = mocker.Mock(return_value=(100.1, 0.1))
    panel.plotCanvas.getDistance = mocker.Mock(return_value=(0, 0))
    panel.plotCanvas.onLMU = mocker.Mock()
    panel.parent.updateMassPoints = mocker.Mock()
    
    panel.onPlotCanvasLMU(mock_evt)
    
    panel.parent.updateMassPoints.assert_called_once_with([100.1])
    mock_evt.Skip.assert_called_once()

def test_on_plot_canvas_lmu_no_doc(panel, mocker):
    """Test onPlotCanvasLMU when no document is active."""
    mock_evt = mocker.Mock()
    panel.currentDocument = None
    
    panel.onPlotCanvasLMU(mock_evt)
    mock_evt.Skip.assert_called_once()
    assert not hasattr(panel.parent, 'updateMassPoints') or not panel.parent.updateMassPoints.called

def test_update_plot_canvas_labels(panel, mocker):
    """Test updatePlotCanvasLabels for different axis configurations."""
    config.massDefectPlot['xAxis'] = 'nominal'
    config.massDefectPlot['yAxis'] = 'relative'
    
    mocked_set = mocker.patch.object(panel.plotCanvas, 'setProperties')
    panel.updatePlotCanvasLabels()
    # It should be called twice, once for xLabel, once for yLabel
    # Actually setProperties can be called with multiple kwargs
    # Let's check the calls
    calls = [mocker.call(xLabel='nominal mass'), mocker.call(yLabel='relative mass defect')]
    mocked_set.assert_has_calls(calls, any_order=True)

    config.massDefectPlot['xAxis'] = 'kendrick'
    config.massDefectPlot['yAxis'] = 'kendrick'
    mocked_set = mocker.patch.object(panel.plotCanvas, 'setProperties')
    panel.updatePlotCanvasLabels()
    calls = [mocker.call(xLabel='kendrick mass'), mocker.call(yLabel='kendrick mass defect')]
    mocked_set.assert_has_calls(calls, any_order=True)

    config.massDefectPlot['xAxis'] = 'mz'
    config.massDefectPlot['yAxis'] = 'fraction'
    mocked_set = mocker.patch.object(panel.plotCanvas, 'setProperties')
    panel.updatePlotCanvasLabels()
    calls = [mocker.call(xLabel='m/z'), mocker.call(yLabel='fractional mass')]
    mocked_set.assert_has_calls(calls, any_order=True)

def test_calc_data_points_various_axes(panel):
    """Test calcDataPoints with different xAxis and yAxis options."""
    # Test xAxis = 'nominal'
    config.massDefectPlot['xAxis'] = 'nominal'
    config.massDefectPlot['nominalMass'] = 'floor'
    config.massDefectPlot['yAxis'] = 'standard'
    config.massDefectPlot['ignoreCharge'] = True
    
    peaks = [(100.1, 1)]
    points = panel.calcDataPoints(peaks)
    assert points[0][0] == 100.0
    
    # Test xAxis = 'unknown' (else path)
    config.massDefectPlot['xAxis'] = 'unknown'
    points = panel.calcDataPoints(peaks)
    assert points[0][0] == 100.1
    
    # Test yAxis options
    config.massDefectPlot['yAxis'] = 'fraction'
    points = panel.calcDataPoints(peaks)
    assert points[0][1] == pytest.approx(0.1) # 100.1 - 100.0

    config.massDefectPlot['yAxis'] = 'relative'
    points = panel.calcDataPoints(peaks)
    # 1e6 * (100.1 - 100.0) / 100.1 = 1e6 * 0.1 / 100.1 approx 999.0
    assert points[0][1] == pytest.approx(999.0, abs=1.0)

def test_on_axis_changed_reset_formula(panel):
    """Test onAxisChanged resets formula if empty."""
    panel.yAxis_choice.SetStringSelection('Mass Defect')
    panel.kendrickFormula_value.SetValue('')
    panel.onAxisChanged()
    assert panel.kendrickFormula_value.GetValue() == 'CH2'
