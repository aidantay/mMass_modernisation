import sys
import os
import pytest
import copy
import wx

# Fixture to mock images, mwx and mspy modules needed for importing panel_spectrum
@pytest.fixture(autouse=True, scope='function')
def mock_dependencies(wx_app, mocker):
    # Mock images module
    class MockImageLib(object):
        def __getitem__(self, key):
            if 'cursor' in key.lower():
                return wx.Cursor(wx.CURSOR_ARROW)
            return wx.Bitmap(16, 16)
        def __contains__(self, key):
            return True
        def get(self, key, default=None):
            return self[key]

    mock_images = mocker.Mock()
    mock_images.lib = MockImageLib()
    
    # Mock mwx
    mock_mwx = mocker.Mock()
    mock_mwx.BOTTOMBAR_HEIGHT = 28
    mock_mwx.BOTTOMBAR_TOOLSIZE = (22, 22)
    mock_mwx.PLOTCANVAS_STYLE_PANEL = 0
    mock_mwx.GRIDBAG_VSPACE = 5
    mock_mwx.GRIDBAG_HSPACE = 5
    mock_mwx.PANEL_SPACE_MAIN = 10
    mock_mwx.BOTTOMBAR_LSPACE = 5
    mock_mwx.BOTTOMBAR_RSPACE = 5
    mock_mwx.BUTTON_SIZE_CORRECTION = 2
    mock_mwx.SLIDER_STYLE = 0
    mock_mwx.bgrPanel = lambda parent, id, bitmap, size: wx.Panel(parent, id, size=size)
    mock_mwx.validator = lambda name: wx.DefaultValidator

    # Mock mspy and mspy.plot
    mock_plot = mocker.Mock()
    def mock_canvas_class(parent, *args, **kwargs):
        p = wx.Panel(parent, -1)
        p.setProperties = mocker.Mock()
        p.setCursorImage = mocker.Mock()
        p.setMFunction = mocker.Mock()
        p.setLMBFunction = mocker.Mock()
        p.draw = mocker.Mock()
        p.refresh = mocker.Mock()
        p.getCurrentXRange = mocker.Mock(return_value=(0, 1000))
        p.getCurrentYRange = mocker.Mock(return_value=(0, 1000))
        p.getCursorPosition = mocker.Mock(return_value=(100, 100))
        p.getDistance = mocker.Mock(return_value=(0, 0))
        p.getSelectionBox = mocker.Mock(return_value=None)
        p.getIsotopes = mocker.Mock(return_value=None)
        p.getCharge = mocker.Mock(return_value=1)
        p.onMMotion = mocker.Mock()
        p.onMScroll = mocker.Mock()
        p.onLMU = mocker.Mock()
        p.setCurrentObject = mocker.Mock()
        p.highlightXPoints = mocker.Mock()
        p.SetDropTarget = mocker.Mock()
        p.zoom = mocker.Mock()
        p.getBitmap = mocker.Mock(return_value=wx.Bitmap(10, 10))
        p.getPrintout = mocker.Mock()
        p.Destroy = mocker.Mock()
        return p
    mock_plot.canvas = mock_canvas_class

    class MockContainer(list):
        def __init__(self, *args):
            super(MockContainer, self).__init__(*args)
        def append(self, item):
            super(MockContainer, self).append(item)

    mock_plot.container = mocker.Mock(side_effect=lambda x: MockContainer(x))
    mock_plot.points = mocker.Mock(side_effect=lambda *args, **kwargs: mocker.Mock(setProperties=mocker.Mock(), setNormalization=mocker.Mock()))
    mock_plot.spectrum = mocker.Mock(side_effect=lambda *args, **kwargs: mocker.Mock(setProperties=mocker.Mock(), setNormalization=mocker.Mock()))
    mock_plot.annotations = mocker.Mock(side_effect=lambda *args, **kwargs: mocker.Mock(setProperties=mocker.Mock(), setNormalization=mocker.Mock()))

    mock_mspy = mocker.Mock()
    mock_mspy.plot = mock_plot
    mock_mspy.mz = mocker.Mock(side_effect=lambda mz, charge, currentCharge: mz)
    mock_mspy.labelpeak = mocker.Mock()
    mock_mspy.labelpoint = mocker.Mock()
    mock_mspy.envmono = mocker.Mock()
    mock_mspy.envcentroid = mocker.Mock()
    mock_mspy.peak = mocker.Mock()

    # Apply the mocks to sys.modules BEFORE any other imports
    mocker.patch.dict(sys.modules, {
        'images': mock_images,
        'gui.images': mock_images,
        'mwx': mock_mwx,
        'gui.mwx': mock_mwx,
        'mspy': mock_mspy,
        'mspy.plot': mock_plot
    })

# Helper to get the panelSpectrum class, ensuring it's imported after mocks are set up
def get_panel_spectrum():
    import gui.panel_spectrum as panel_spectrum
    return panel_spectrum

class MockDocument(object):
    def __init__(self, title="Test Doc", mocker=None):
        self.title = title
        self.visible = True
        self.flipped = False
        self.offset = [0, 0]
        self.colour = (0, 0, 0)
        self.style = 'line'
        self.spectrum = mocker.Mock()
        self.spectrum.hasprofile.return_value = True
        self.spectrum.polarity = 1
        self.spectrum.normalization.return_value = 1.0
        self.spectrum.area.return_value = 0.0
        self.spectrum.baseline.return_value = []
        self.backup = mocker.Mock()

@pytest.fixture
def mock_documents(mocker):
    return [MockDocument("Doc 1", mocker), MockDocument("Doc 2", mocker)]

@pytest.fixture
def panel(wx_app, mock_documents, mocker):
    panel_spectrum = get_panel_spectrum()
    parent = wx.Frame(None)
    parent.onDocumentDropped = mocker.Mock()
    parent.onView = mocker.Mock()
    parent.onToolsSpectrum = mocker.Mock()
    parent.onViewSpectrumRuler = mocker.Mock()
    parent.onDocumentChanged = mocker.Mock()
    parent.PopupMenu = mocker.Mock()
    
    # Initialize with empty documents first
    docs = []
    p = panel_spectrum.panelSpectrum(parent, docs)
    # Populate documents and container in sync
    for doc in mock_documents:
        docs.append(doc)
        p.appendLastSpectrum(refresh=False)
    
    # Mock PopupMenu on panel instance itself because it calls self.PopupMenu
    p.PopupMenu = mocker.Mock()
    yield p
    if p:
        p.Destroy()
    parent.Destroy()

@pytest.fixture(autouse=True)
def reset_config():
    import gui.config as config
    orig_main = copy.deepcopy(config.main)
    orig_spectrum = copy.deepcopy(config.spectrum)
    yield
    config.main.clear()
    config.main.update(orig_main)
    config.spectrum.clear()
    config.spectrum.update(orig_spectrum)

def test_fileDropTarget(wx_app, mocker):
    panel_spectrum = get_panel_spectrum()
    mock_fn = mocker.Mock()
    target = panel_spectrum.fileDropTarget(mock_fn)
    paths = ['/path/to/file1', '/path/to/file2']
    target.OnDropFiles(0, 0, paths)
    mock_fn.assert_called_once_with(paths=paths)

def test_dlgSpectrumOffset(wx_app, mocker):
    panel_spectrum = get_panel_spectrum()
    mocker.patch('wx.Dialog.__init__', return_value=None)
    mock_sizer = mocker.Mock()
    mocker.patch.object(panel_spectrum.dlgSpectrumOffset, 'makeGUI', return_value=mock_sizer)
    mocker.patch.object(panel_spectrum.dlgSpectrumOffset, 'SetSizer')
    mocker.patch.object(panel_spectrum.dlgSpectrumOffset, 'SetMinSize')
    mocker.patch.object(panel_spectrum.dlgSpectrumOffset, 'GetSize', return_value=(100, 100))
    mocker.patch.object(panel_spectrum.dlgSpectrumOffset, 'Centre')
    
    offset = [0, 10.0]
    parent = wx.Frame(None)
    dlg = panel_spectrum.dlgSpectrumOffset(parent, offset)
    
    # Test onChange
    dlg.offset_value = mocker.Mock()
    dlg.offset_value.GetValue.return_value = "25.5"
    dlg.onChange(None)
    assert dlg.offset == [0, 25.5]
    
    # Test onOffset happy path
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')
    dlg.onOffset(None)
    mock_end_modal.assert_called_once_with(wx.ID_OK)
    
    # Test onChange with invalid float
    dlg.offset_value.GetValue.return_value = "invalid"
    dlg.onChange(None)
    assert dlg.offset is None
    
    # Test onOffset with invalid value
    mock_bell = mocker.patch('wx.Bell')
    dlg.onOffset(None)
    mock_bell.assert_called_once()
    
    parent.Destroy()

def test_dlgViewRange(wx_app, mocker):
    panel_spectrum = get_panel_spectrum()
    mocker.patch('wx.Dialog.__init__', return_value=None)
    mock_sizer = mocker.Mock()
    mocker.patch.object(panel_spectrum.dlgViewRange, 'makeGUI', return_value=mock_sizer)
    mocker.patch.object(panel_spectrum.dlgViewRange, 'Layout')
    mocker.patch.object(panel_spectrum.dlgViewRange, 'SetSizer')
    mocker.patch.object(panel_spectrum.dlgViewRange, 'Centre')
    
    data = (100.0, 200.0)
    parent = wx.Frame(None)
    dlg = panel_spectrum.dlgViewRange(parent, data)
    
    dlg.minX_value = mocker.Mock()
    dlg.maxX_value = mocker.Mock()
    
    # Test onOK with minX < maxX
    dlg.minX_value.GetValue.return_value = "150.0"
    dlg.maxX_value.GetValue.return_value = "250.0"
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')
    dlg.onOK(None)
    assert dlg.data == (150.0, 250.0)
    mock_end_modal.assert_called_once_with(wx.ID_OK)
    
    # Test onOK with minX >= maxX
    dlg.minX_value.GetValue.return_value = "300.0"
    dlg.maxX_value.GetValue.return_value = "200.0"
    mock_bell = mocker.patch('wx.Bell')
    dlg.onOK(None)
    mock_bell.assert_called_once()
        
    # Test onOK with invalid float
    dlg.minX_value.GetValue.return_value = "invalid"
    dlg.onOK(None)
    assert mock_bell.call_count == 2
        
    parent.Destroy()

def test_dlgCanvasProperties(wx_app, mocker):
    panel_spectrum = get_panel_spectrum()
    import gui.config as config
    mocker.patch('wx.Dialog.__init__', return_value=None)
    mock_sizer = mocker.Mock()
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'makeGUI', return_value=mock_sizer)
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'Layout')
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'SetSizer')
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'SetMinSize')
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'GetSize', return_value=(100, 100))
    mocker.patch.object(panel_spectrum.dlgCanvasProperties, 'CentreOnParent')
    
    mock_onChangeFn = mocker.Mock()
    parent = wx.Frame(None)
    dlg = panel_spectrum.dlgCanvasProperties(parent, mock_onChangeFn)
    
    dlg.mzDigits_slider = mocker.Mock()
    dlg.intDigits_slider = mocker.Mock()
    dlg.posBarSize_slider = mocker.Mock()
    dlg.gelHeight_slider = mocker.Mock()
    dlg.axisFontSize_slider = mocker.Mock()
    dlg.labelFontSize_slider = mocker.Mock()
    dlg.notationMaxLength_slider = mocker.Mock()
    
    dlg.mzDigits_slider.GetValue.return_value = 3
    dlg.intDigits_slider.GetValue.return_value = 2
    dlg.posBarSize_slider.GetValue.return_value = 10
    dlg.gelHeight_slider.GetValue.return_value = 20
    dlg.axisFontSize_slider.GetValue.return_value = 11
    dlg.labelFontSize_slider.GetValue.return_value = 12
    dlg.notationMaxLength_slider.GetValue.return_value = 50
    
    dlg.onChange(None)
    
    assert config.main['mzDigits'] == 3
    assert config.main['intDigits'] == 2
    assert config.spectrum['posBarSize'] == 10
    assert config.spectrum['gelHeight'] == 20
    assert config.spectrum['axisFontSize'] == 11
    assert config.spectrum['labelFontSize'] == 12
    assert config.spectrum['notationMaxLength'] == 50
    
    mock_onChangeFn.assert_called_once()
    
    parent.Destroy()

def test_panel_init(panel, mock_documents):
    assert panel.documents == mock_documents
    assert panel.currentDocument is None
    # 2 default objects (tmp + notation) + 2 mock documents
    assert len(panel.container) == 4

def test_setCurrentTool(panel):
    panel.setCurrentTool('labelpeak')
    assert panel.currentTool == 'labelpeak'
    panel.spectrumCanvas.setLMBFunction.assert_called_with('range')
    
    panel.setCurrentTool('ruler')
    assert panel.currentTool == 'ruler'
    panel.spectrumCanvas.setLMBFunction.assert_called_with('xDistance')

def test_makeSpectrumCanvas(panel):
    import gui.config as config
    # Verify setProperties was called multiple times during makeSpectrumCanvas
    assert panel.spectrumCanvas.setProperties.called
    
    # Check for some specific property calls
    calls = panel.spectrumCanvas.setProperties.call_args_list
    all_keys = []
    for call in calls:
        all_keys.extend(call[1].keys())
    
    assert 'xLabel' in all_keys
    assert 'yLabel' in all_keys
    assert any(c[1].get('showZero') is True for c in calls if 'showZero' in c[1])

def test_makeToolbar(panel):
    from gui.ids import ID_viewLabels
    # Buttons are created during __init__ via makeGUI -> makeToolbar
    assert isinstance(panel.showLabels_butt, wx.BitmapButton)
    assert isinstance(panel.toolsRuler_butt, wx.BitmapButton)
    assert isinstance(panel.cursorInfo, wx.StaticText)
    
    # Check if they have correct IDs
    assert panel.showLabels_butt.GetId() == ID_viewLabels

def test_onCanvasMMotion(panel, mocker):
    event = mocker.Mock()
    mock_update = mocker.patch.object(panel, 'updateCursorInfo')
    panel.onCanvasMMotion(event)
    panel.spectrumCanvas.onMMotion.assert_called_with(event)
    mock_update.assert_called_once()

def test_onCanvasMScroll(panel, mocker):
    event = mocker.Mock()
    mock_update = mocker.patch.object(panel, 'updateCursorInfo')
    panel.onCanvasMScroll(event)
    panel.spectrumCanvas.onMScroll.assert_called_with(event)
    mock_update.assert_called_once()

def test_updateCursorInfo_basic(panel):
    panel.spectrumCanvas.getCursorPosition.return_value = (100.0, 500.0)
    panel.spectrumCanvas.getDistance.return_value = None
    panel.currentDocument = None
    
    panel.updateCursorInfo()
    
    # Should show basic m/z and a.i.
    label = panel.cursorInfo.GetLabel()
    assert "m/z: 100" in label
    assert "a.i.: 500" in label

def test_updateCursorInfo_offset(panel):
    panel.currentTool = 'offset'
    panel.spectrumCanvas.getCursorPosition.return_value = (100.0, 500.0)
    panel.spectrumCanvas.getDistance.return_value = (0, 50.0)
    
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "dist: 50" in label

def test_updateCursorInfo_labelenvelope(panel, mocker):
    panel.currentTool = 'labelenvelope'
    panel.spectrumCanvas.getCursorPosition.return_value = (100.0, 500.0)
    panel.spectrumCanvas.getCharge.return_value = 2
    
    mocker.patch('mspy.mz', return_value=199.0, create=True)
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "z: 2" in label
    assert "mass: 199" in label

def test_updateCursorInfo_distance_small(panel, mocker):
    import gui.config as config
    panel.currentTool = 'ruler'
    panel.spectrumCanvas.getCursorPosition.return_value = (1000.0, 500.0)
    panel.spectrumCanvas.getDistance.return_value = (1.0, 0) # dist = 1.0 -> z = 1
    
    config.main['cursorInfo'] = ['mz', 'dist', 'z']
    
    mocker.patch('mspy.mz', return_value=1000.0, create=True)
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "m/z: 1000" in label
    assert "dist: 1.0" in label
    assert "z: 1 (1" in label

def test_updateCursorInfo_distance_large(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'ruler'
    panel.spectrumCanvas.getCursorPosition.return_value = (1000.0, 500.0)
    panel.spectrumCanvas.getDistance.return_value = (11.0, 0) # dist > 10
    
    config.main['cursorInfo'] = ['mz', 'dist', 'z', 'cmass', 'pmass']
    
    mocker.patch('mspy.mz', side_effect=[1000.0, 900.0], create=True)
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "mass (c): 1000" in label
    assert "mass (p): 900" in label

def test_updateCursorInfo_area(panel, mock_documents):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'ruler'
    panel.spectrumCanvas.getCursorPosition.return_value = (100.0, 500.0)
    panel.spectrumCanvas.getDistance.return_value = (10.0, 0)
    
    config.main['cursorInfo'] = ['area']
    mock_documents[0].spectrum.area.return_value = 1234.5
    
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "area: 1234" in label or "area: 1235" in label

def test_onCanvasLMU_labelpeak(panel, mock_documents, mocker):
    panel.currentDocument = 0
    panel.currentTool = 'labelpeak'
    panel.spectrumCanvas.getSelectionBox.return_value = (100.0, 0, 110.0, 500.0)
    
    mock_label = mocker.patch.object(panel, 'labelPeak')
    panel.onCanvasLMU(mocker.Mock())
    mock_label.assert_called_once_with((100.0, 0, 110.0, 500.0))

def test_onCanvasLMU_offset(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'offset'
    panel.spectrumCanvas.getDistance.return_value = (0, 10.0)
    config.spectrum['normalize'] = False
    
    mock_update = mocker.patch.object(panel, 'updateSpectrumProperties')
    panel.onCanvasLMU(mocker.Mock())
    assert mock_documents[0].offset[1] == 10.0
    mock_update.assert_called_once_with(0)

def test_onCanvasProperties(panel, mocker):
    mock_dlg = mocker.patch('gui.panel_spectrum.dlgCanvasProperties')
    panel.onCanvasProperties(None)
    mock_dlg.assert_called_once()
    mock_dlg.return_value.ShowModal.assert_called_once()

def test_onCursorInfoRMU(panel, mocker):
    panel.currentTool = 'ruler'
    mocker.patch('wx.Menu')
    panel.onCursorInfoRMU(mocker.Mock())
    panel.PopupMenu.assert_called_once()

def test_setSpectrumProperties(panel, mock_documents):
    panel.setSpectrumProperties(0)
    spectrum = panel.container[2]
    assert spectrum.setProperties.called
    
    # Check for specific call
    calls = spectrum.setProperties.call_args_list
    assert any(c[1].get('legend') == "Doc 1" for c in calls if 'legend' in c[1])

def test_updateCanvasProperties(panel, mock_documents, mocker):
    from gui.ids import ID_viewLabels
    import gui.config as config
    config.spectrum['showLabels'] = True
    mock_set_bitmap = mocker.patch.object(panel.showLabels_butt, 'SetBitmapLabel')
    panel.updateCanvasProperties(ID_viewLabels)
    mock_set_bitmap.assert_called_once()
    
    assert panel.spectrumCanvas.setProperties.called

def test_updateTmpSpectrum(panel, mock_documents, mocker):
    panel.currentDocument = 0
    points = [[100.0, 500.0], [200.0, 600.0]]
    # Patch points() at the module level used by panel_spectrum
    panel_spectrum = get_panel_spectrum()
    mock_pts = mocker.patch.object(panel_spectrum.mspy.plot, 'points', create=True)
    panel.updateTmpSpectrum(points)
    assert mock_pts.called

def test_updateNotationMarks(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    notations = [(100.0, 500.0, "Label")]
    config.spectrum['showNotations'] = True
    # Patch annotations() at the module level used by panel_spectrum
    panel_spectrum = get_panel_spectrum()
    mock_ann = mocker.patch.object(panel_spectrum.mspy.plot, 'annotations', create=True)
    panel.updateNotationMarks(notations)
    assert mock_ann.called

def test_updateSpectrum(panel, mock_documents):
    panel.updateSpectrum(0)
    assert len(panel.container) == 4

def test_selectSpectrum(panel, mock_documents):
    panel.selectSpectrum(0)
    assert panel.currentDocument == 0
    panel.spectrumCanvas.setCurrentObject.assert_called_with(2)

def test_appendLastSpectrum(panel, mock_documents, mocker):
    # Initial state from fixture has 4 items (2 default + 2 docs)
    # Adding one more mock document to simulate app behavior
    new_doc = MockDocument("New Doc", mocker)
    panel.documents.append(new_doc)
    panel.appendLastSpectrum()
    assert len(panel.container) == 5

def test_deleteSpectrum(panel, mock_documents):
    # Delete first doc (at index 0 -> container[2])
    panel.deleteSpectrum(0)
    assert len(panel.container) == 3 # 2 default + 1 remaining doc

def test_labelPeak(panel, mock_documents, mocker):
    panel.currentDocument = 0
    mock_documents[0].spectrum.hasprofile.return_value = True
    mock_documents[0].spectrum.profile = mocker.Mock()
    mock_documents[0].spectrum.peaklist = mocker.Mock()
    
    mock_label = mocker.patch('mspy.labelpeak', return_value=mocker.Mock(), create=True)
    panel.labelPeak((100.0, 0, 110.0, 500.0))
    mock_label.assert_called_once()
    mock_documents[0].spectrum.peaklist.append.assert_called_once()
    panel.parent.onDocumentChanged.assert_called_once()

def test_labelPoint(panel, mock_documents, mocker):
    panel.currentDocument = 0
    mock_documents[0].spectrum.hasprofile.return_value = True
    mock_documents[0].spectrum.profile = mocker.Mock()
    mock_documents[0].spectrum.peaklist = mocker.Mock()
    
    mock_label = mocker.patch('mspy.labelpoint', return_value=mocker.Mock(), create=True)
    panel.labelPoint(100.0)
    mock_label.assert_called_once()
    mock_documents[0].spectrum.peaklist.append.assert_called_once()

def test_labelEnvelope(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    mock_documents[0].spectrum.hasprofile.return_value = True
    mock_documents[0].spectrum.peaklist = mocker.Mock()
    config.processing['deisotoping']['labelEnvelope'] = '1st'
    
    peaks = [mocker.Mock(mz=100.0, ai=500.0, base=0.0, intensity=500.0, sn=10.0), 
             mocker.Mock(mz=101.0, ai=250.0, base=0.0, intensity=250.0, sn=5.0)]
    
    mocker.patch('mspy.labelpeak', side_effect=peaks, create=True)
    panel.labelEnvelope([100.0, 101.0], 1)
    mock_documents[0].spectrum.peaklist.append.assert_called_once()

def test_deleteLabel(panel, mock_documents, mocker):
    panel.currentDocument = 0
    mock_peak = mocker.Mock(mz=105.0, ai=300.0)
    
    # Create a mock peaklist that is iterable AND has delete
    mock_peaklist = mocker.Mock()
    mock_peaklist.__iter__ = mocker.Mock(return_value=iter([mock_peak]))
    mock_peaklist.delete = mocker.Mock()
    mock_documents[0].spectrum.peaklist = mock_peaklist
    
    panel.deleteLabel((100.0, 0, 110.0, 500.0))
    mock_peaklist.delete.assert_called_once_with([0])

def test_refresh(panel):
    panel.refresh()
    panel.spectrumCanvas.refresh.assert_called_once()

def test_getBitmap(panel):
    panel.getBitmap(800, 600, 1.0)
    panel.spectrumCanvas.getBitmap.assert_called_with(800, 600, 1.0)

def test_getPrintout(panel):
    panel.getPrintout(1.0, "Title")
    panel.spectrumCanvas.getPrintout.assert_called_with(1.0, "Title")

def test_getCurrentRange(panel):
    panel.getCurrentRange()
    panel.spectrumCanvas.getCurrentXRange.assert_called_once()

@pytest.mark.parametrize("id_val, config_key, config_obj", [
    (151, 'showLabels', 'spectrum'), # ID_viewLabels
    (152, 'showTicks', 'spectrum'), # ID_viewTicks
    (160, 'showNotations', 'spectrum'), # ID_viewNotations
    (156, 'labelAngle', 'spectrum'), # ID_viewLabelAngle
    (146, 'showPosBars', 'spectrum'), # ID_viewPosBars
    (147, 'showGel', 'spectrum'), # ID_viewGel
    (149, 'showTracker', 'spectrum'), # ID_viewTracker
    (164, 'autoscale', 'spectrum'), # ID_viewAutoscale
    (165, 'normalize', 'spectrum'), # ID_viewNormalize
])
def test_updateCanvasProperties_all_ids(panel, id_val, config_key, config_obj):
    import gui.config as config
    cfg = getattr(config, config_obj)
    cfg[config_key] = True
    panel.updateCanvasProperties(id_val)
    # Check if canvas setProperties was called
    assert panel.spectrumCanvas.setProperties.called

@pytest.mark.parametrize("tool", ['ruler', 'labelpeak', 'labelpoint', 'labelenvelope', 'deletelabel', 'offset'])
@pytest.mark.parametrize("tracker", [True, False])
def test_setCurrentTool_all_variants(panel, tool, tracker):
    import gui.config as config
    config.spectrum['showTracker'] = tracker
    panel.setCurrentTool(tool)
    assert panel.currentTool == tool
    assert panel.spectrumCanvas.setCursorImage.called

def test_onCanvasLMU_flipped(panel, mock_documents, mocker):
    panel.currentDocument = 0
    panel.currentTool = 'labelpeak'
    mock_documents[0].flipped = True
    # selection is (x1, y1, x2, y2)
    panel.spectrumCanvas.getSelectionBox.return_value = (100.0, 10.0, 110.0, 50.0)
    
    mock_label = mocker.patch.object(panel, 'labelPeak')
    panel.onCanvasLMU(mocker.Mock())
    # y values should be flipped: y1 = -1*50, y2 = -1*10
    mock_label.assert_called_once_with((100.0, -50.0, 110.0, -10.0))

def test_onCanvasLMU_normalize(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'labelpeak'
    config.spectrum['normalize'] = True
    mock_documents[0].spectrum.normalization.return_value = 100.0
    panel.spectrumCanvas.getSelectionBox.return_value = (100.0, 0.1, 110.0, 0.5)
    
    mock_label = mocker.patch.object(panel, 'labelPeak')
    panel.onCanvasLMU(mocker.Mock())
    # y values should be multiplied by 100
    mock_label.assert_called_once_with((100.0, 10.0, 110.0, 50.0))

def test_onCanvasLMU_offset_logic(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'labelpeak'
    config.spectrum['normalize'] = False
    mock_documents[0].offset = [10.0, 20.0]
    panel.spectrumCanvas.getSelectionBox.return_value = (110.0, 50.0, 120.0, 100.0)
    
    mock_label = mocker.patch.object(panel, 'labelPeak')
    panel.onCanvasLMU(mocker.Mock())
    # selection should be offset: x-10, y-20
    mock_label.assert_called_once_with((100.0, 30.0, 110.0, 80.0))

def test_onCanvasLMU_labelenvelope(panel, mock_documents, mocker):
    panel.currentDocument = 0
    panel.currentTool = 'labelenvelope'
    panel.spectrumCanvas.getIsotopes.return_value = [100.0, 101.0]
    panel.spectrumCanvas.getCharge.return_value = 1
    
    mock_label = mocker.patch.object(panel, 'labelEnvelope')
    panel.onCanvasLMU(mocker.Mock())
    mock_label.assert_called_once_with([100.0, 101.0], 1)

def test_onCanvasLMU_labelpoint(panel, mock_documents, mocker):
    panel.currentDocument = 0
    panel.currentTool = 'labelpoint'
    panel.spectrumCanvas.getCursorPosition.return_value = (100.0, 500.0)
    
    mock_label = mocker.patch.object(panel, 'labelPoint')
    panel.onCanvasLMU(mocker.Mock())
    mock_label.assert_called_once_with(100.0)

def test_onCanvasLMU_deletelabel(panel, mock_documents, mocker):
    panel.currentDocument = 0
    panel.currentTool = 'deletelabel'
    panel.spectrumCanvas.getSelectionBox.return_value = (100.0, 0, 110.0, 500.0)
    
    mock_label = mocker.patch.object(panel, 'deleteLabel')
    panel.onCanvasLMU(mocker.Mock())
    mock_label.assert_called_once_with((100.0, 0.0, 110.0, 500.0))

def test_onCanvasLMU_offset_tool(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    panel.currentTool = 'offset'
    panel.spectrumCanvas.getDistance.return_value = (0, 10.0)
    config.spectrum['normalize'] = False
    mock_documents[0].flipped = True
    
    mocker.patch.object(panel, 'updateSpectrumProperties')
    panel.onCanvasLMU(mocker.Mock())
    # if flipped, offset[1] -= distance[1] -> 0 - 10 = -10
    assert mock_documents[0].offset[1] == -10.0

def test_updateCursorInfo_detailed(panel, mock_documents, mocker):
    import gui.config as config
    panel.currentDocument = 0
    mock_documents[0].spectrum.polarity = -1
    
    # Test negative polarity branch (returns early)
    panel.updateCursorInfo()
    assert panel.cursorInfo.GetLabel() == ""
    
    mock_documents[0].spectrum.polarity = 1
    panel.currentTool = 'ruler'
    panel.spectrumCanvas.getCursorPosition.return_value = (1000.0, 500.0)
    
    # Test all flags
    config.main['cursorInfo'] = ['mz', 'dist', 'ppm', 'z', 'cmass', 'pmass', 'area']
    panel.spectrumCanvas.getDistance.return_value = (1.0, 0)
    
    mocker.patch('mspy.mz', return_value=123.4, create=True)
    panel.updateCursorInfo()
    label = panel.cursorInfo.GetLabel()
    assert "m/z: 1000" in label
    assert "dist: 1" in label
    assert "ppm: 1000" in label # 1e6 * 1 / 1000 = 1000
    assert "z: 1" in label
    assert "mass (c): 123" in label
    assert "mass (p): 123" in label
    assert "area:" in label

def test_updateCursorInfo_distance_ranges(panel, mocker):
    import gui.config as config
    panel.currentTool = 'ruler'
    panel.spectrumCanvas.getCursorPosition.return_value = (1000.0, 500.0)
    config.main['cursorInfo'] = ['z']
    
    # Range 1: dist <= 2
    panel.spectrumCanvas.getDistance.return_value = (1.0, 0)
    panel.updateCursorInfo()
    assert "z: 1 (1" in panel.cursorInfo.GetLabel()
    
    # Range 2: dist > 10
    panel.spectrumCanvas.getDistance.return_value = (100.0, 0)
    panel.updateCursorInfo()
    # charge = (900 - 1.00728) / 100 = 8.9899...
    # z label shows (charge+1)/charge -> 9.99/8.99
    assert "z: 9.99/8.99" in panel.cursorInfo.GetLabel()
    
    # Range 3: dist < -10
    panel.spectrumCanvas.getDistance.return_value = (-100.0, 0)
    panel.updateCursorInfo()
    # charge = abs((1000 - 1.00728) / -100) = 9.9899
    assert "z: 10.99/9.99" in panel.cursorInfo.GetLabel()

def test_onCanvasLMU_no_document(panel, mocker):
    panel.currentDocument = None
    panel.currentTool = 'labelpeak'
    event = mocker.Mock()
    mock_bell = mocker.patch('wx.Bell')
    panel.onCanvasLMU(event)
    event.Skip.assert_called_once()
    mock_bell.assert_called_once()

@pytest.mark.parametrize("mode", ['1st', 'monoisotope', 'centroid', 'isotopes'])
@pytest.mark.parametrize("intensity", ['sum', 'average'])
def test_labelEnvelope_all_modes(panel, mock_documents, mode, intensity, mocker):
    import gui.config as config
    panel.currentDocument = 0
    mock_documents[0].spectrum.hasprofile.return_value = True
    mock_documents[0].spectrum.peaklist = mocker.Mock()
    mock_documents[0].spectrum.peaklist.groupname.return_value = "Group 1"
    
    config.processing['deisotoping']['labelEnvelope'] = mode
    config.processing['deisotoping']['envelopeIntensity'] = intensity
    
    peaks = [mocker.Mock(mz=100.0, ai=500.0, base=0.0, intensity=500.0, sn=10.0), 
             mocker.Mock(mz=101.0, ai=250.0, base=0.0, intensity=250.0, sn=5.0)]
    
    mocker.patch('mspy.labelpeak', side_effect=peaks, create=True)
    mock_mono = mocker.patch('mspy.envmono', return_value=mocker.Mock(), create=True)
    mock_centroid = mocker.patch('mspy.envcentroid', return_value=mocker.Mock(), create=True)
    
    panel.labelEnvelope([100.0, 101.0], 1)
    
    if mode == 'monoisotope':
        mock_mono.assert_called_once()
    elif mode == 'centroid':
        mock_centroid.assert_called_once()
    
    assert mock_documents[0].spectrum.peaklist.append.called
