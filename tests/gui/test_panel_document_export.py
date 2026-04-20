import pytest
import wx
import os

# Workaround for missing RESIZE_BOX in some wxPython versions
if not hasattr(wx, 'RESIZE_BOX'):
    wx.RESIZE_BOX = getattr(wx, 'RESIZE_BORDER', 0)

# Workaround for missing constants in some wxPython versions (e.g., wxPython 4)
if not hasattr(wx, 'SAVE'):
    wx.SAVE = getattr(wx, 'FD_SAVE', 0x0001)
if not hasattr(wx, 'OVERWRITE_PROMPT'):
    wx.OVERWRITE_PROMPT = getattr(wx, 'FD_OVERWRITE_PROMPT', 0x0002)

from gui.panel_document_export import panelDocumentExport
from gui.ids import ID_documentExportImage, ID_documentExportPeaklist, ID_documentExportSpectrum
import gui.config as config
import gui.images as images

class MockParentFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None)
    
    def getSpectrumBitmap(self, width, height, printerScale):
        return wx.Bitmap(int(width), int(height))
    
    def getCurrentPeaklist(self, filters):
        return []
    
    def getCurrentSpectrumPoints(self, currentView=False):
        return []

class DummyPeak(object):
    def __init__(self, mz, intensity, ai=100.0, base=10.0, ri=0.5, sn=10.0, charge=1, fwhm=0.1, resolution=1000.0, group=1):
        self.mz = mz
        self.intensity = intensity
        self.ai = ai
        self.base = base
        self.ri = ri
        self.sn = sn
        self.charge = charge
        self.fwhm = fwhm
        self.resolution = resolution
        self.group = group
    
    def mass(self):
        return self.mz * abs(self.charge or 1)

@pytest.fixture
def mock_parent(wx_app):
    frame = MockParentFrame()
    yield frame
    if frame:
        frame.Destroy()

@pytest.fixture
def mock_images(mocker):
    """Mock required images in images.lib."""
    required = [
        'bgrToolbar',
        'documentExportImageOff',
        'documentExportPeaklistOff',
        'documentExportSpectrumOff',
        'documentExportImageOn',
        'documentExportPeaklistOn',
        'documentExportSpectrumOn'
    ]
    for img in required:
        mocker.patch.dict(images.lib, {img: wx.Bitmap(1, 1)})

@pytest.fixture
def monkeypatch_config(monkeypatch):
    # Isolate config.export and config.main
    mock_export = {
        'imageWidth': 750,
        'imageHeight': 500,
        'imageUnits': 'px',
        'imageResolution': 72,
        'imageFontsScale': 1,
        'imageDrawingsScale': 1,
        'imageFormat': 'PNG',
        'peaklistColumns': ['mz','int'],
        'peaklistFormat': 'ASCII',
        'peaklistSeparator': 'tab',
        'spectrumSeparator': 'tab',
    }
    mock_main = {
        'lastDir': '',
    }
    monkeypatch.setattr(config, 'export', mock_export)
    monkeypatch.setattr(config, 'main', mock_main)
    return mock_export, mock_main

@pytest.fixture
def export_panel(wx_app, mock_parent, mock_images, monkeypatch_config, mocker):
    # Mock Slider.SetTickFreq because it might have incompatible signature in some wx versions
    mocker.patch('wx.Slider.SetTickFreq')
    # Mock WindowDisabler as it's used instead of MakeModal
    mocker.patch('wx.WindowDisabler')
    
    panel = panelDocumentExport(mock_parent)
    # Mock gauge.pulse to avoid wx.Yield issues in headless environments
    mocker.patch.object(panel.gauge, 'pulse')
    yield panel
    if panel:
        panel.Destroy()

def test_init_default_tool(export_panel):
    """Verify default tool is 'image' and corresponding panel is shown."""
    assert export_panel.currentTool == 'image'
    assert export_panel.GetTitle() == "Export Spectrum Image"
    # mainSizer indices: 0:toolbar, 1:image, 2:peaklist, 3:spectrum, 4:gauge
    assert export_panel.mainSizer.IsShown(1)
    assert not export_panel.mainSizer.IsShown(2)
    assert not export_panel.mainSizer.IsShown(3)

def test_init_specific_tool(mock_parent, mock_images, monkeypatch_config, mocker):
    """Verify instantiating with specific tools works."""
    # Mock Slider.SetTickFreq because it might have incompatible signature in some wx versions
    mocker.patch('wx.Slider.SetTickFreq')
    # Mock WindowDisabler
    mocker.patch('wx.WindowDisabler')

    # Test peaklist
    panel = panelDocumentExport(mock_parent, tool='peaklist')
    assert panel.currentTool == 'peaklist'
    assert panel.GetTitle() == "Export Peak List"
    assert not panel.mainSizer.IsShown(1)
    assert panel.mainSizer.IsShown(2)
    assert not panel.mainSizer.IsShown(3)
    panel.Destroy()

    # Test spectrum
    panel = panelDocumentExport(mock_parent, tool='spectrum')
    assert panel.currentTool == 'spectrum'
    assert panel.GetTitle() == "Export Spectrum Data"
    assert not panel.mainSizer.IsShown(1)
    assert not panel.mainSizer.IsShown(2)
    assert panel.mainSizer.IsShown(3)
    panel.Destroy()

def test_onToolSelected(export_panel, mocker):
    """Verify that clicking toolbar buttons updates UI state correctly."""
    # Test switching to peaklist
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_documentExportPeaklist)
    export_panel.onToolSelected(event)
    assert export_panel.currentTool == 'peaklist'
    assert export_panel.GetTitle() == "Export Peak List"
    assert export_panel.mainSizer.IsShown(2)
    assert not export_panel.mainSizer.IsShown(1)

    # Test switching to spectrum
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_documentExportSpectrum)
    export_panel.onToolSelected(event)
    assert export_panel.currentTool == 'spectrum'
    assert export_panel.GetTitle() == "Export Spectrum Data"
    assert export_panel.mainSizer.IsShown(3)
    assert not export_panel.mainSizer.IsShown(2)

    # Test switching to image
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_documentExportImage)
    export_panel.onToolSelected(event)
    assert export_panel.currentTool == 'image'
    assert export_panel.GetTitle() == "Export Spectrum Image"
    assert export_panel.mainSizer.IsShown(1)
    assert not export_panel.mainSizer.IsShown(3)

    # Test processing abort
    mock_bell = mocker.patch('wx.Bell')
    export_panel.processing = True
    export_panel.currentTool = 'image'
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId, ID_documentExportPeaklist)
    export_panel.onToolSelected(event)
    mock_bell.assert_called_once()
    assert export_panel.currentTool == 'image' # Should not have changed

def test_onClose(export_panel, mocker):
    """Verify frame destruction and processing check."""
    mock_bell = mocker.patch('wx.Bell')
    mock_destroy = mocker.patch.object(export_panel, 'Destroy')
    
    # Test closing while processing
    export_panel.processing = True
    export_panel.onClose(None)
    mock_bell.assert_called_once()
    mock_destroy.assert_not_called()
    
    # Test normal closing
    export_panel.processing = None
    export_panel.onClose(None)
    mock_destroy.assert_called_once()

def test_onImageResolutionChanged(export_panel):
    """Verify font and line scales are updated based on resolution."""
    # resolution = 72
    export_panel.imageResolution_choice.SetStringSelection('72')
    export_panel.onImageResolutionChanged()
    assert export_panel.imageFontsScale_slider.GetValue() == 1
    assert export_panel.imageDrawingsScale_slider.GetValue() == 1

    # resolution = 150
    export_panel.imageResolution_choice.SetStringSelection('150')
    export_panel.onImageResolutionChanged()
    assert export_panel.imageFontsScale_slider.GetValue() == 2
    assert export_panel.imageDrawingsScale_slider.GetValue() == 2

    # resolution = 200
    export_panel.imageResolution_choice.SetStringSelection('200')
    export_panel.onImageResolutionChanged()
    assert export_panel.imageFontsScale_slider.GetValue() == 2
    assert export_panel.imageDrawingsScale_slider.GetValue() == 2

    # resolution = 300
    export_panel.imageResolution_choice.SetStringSelection('300')
    export_panel.onImageResolutionChanged()
    assert export_panel.imageFontsScale_slider.GetValue() == 2
    assert export_panel.imageDrawingsScale_slider.GetValue() == 3

    # resolution = 600
    export_panel.imageResolution_choice.SetStringSelection('600')
    export_panel.onImageResolutionChanged()
    assert export_panel.imageFontsScale_slider.GetValue() == 4
    assert export_panel.imageDrawingsScale_slider.GetValue() == 5

def test_init_invalid_resolution(wx_app, mock_parent, mock_images, monkeypatch_config, mocker):
    """Verify initialization when config resolution is not in choices."""
    mocker.patch('wx.Slider.SetTickFreq')
    mocker.patch('wx.WindowDisabler')
    
    mock_export, _ = monkeypatch_config
    mock_export['imageResolution'] = 999 # Not in ['72', '150', '200', '300', '600']
    
    panel = panelDocumentExport(mock_parent)
    # Should not crash and should select default (index 0)
    assert panel.imageResolution_choice.GetSelection() == 0
    panel.Destroy()

def test_onPeaklistFormatChanged(export_panel):
    """Verify that UI elements are enabled/disabled based on format."""
    # ASCII - everything enabled
    export_panel.peaklistFormat_choice.SetStringSelection('ASCII')
    export_panel.onPeaklistFormatChanged()
    assert export_panel.peaklistColumnMz_check.IsEnabled()
    assert export_panel.peaklistSeparator_choice.IsEnabled()
    assert config.export['peaklistFormat'] == 'ASCII'

    # MGF - elements disabled
    export_panel.peaklistFormat_choice.SetStringSelection('MGF')
    export_panel.onPeaklistFormatChanged()
    assert not export_panel.peaklistColumnMz_check.IsEnabled()
    assert not export_panel.peaklistSeparator_choice.IsEnabled()
    assert config.export['peaklistFormat'] == 'MGF'

def test_getParams_success(export_panel):
    """Verify that getParams updates config.export with UI values."""
    # Set image values
    export_panel.imageWidth_value.SetValue('10.5')
    export_panel.imageHeight_value.SetValue('8.2')
    export_panel.imageUnits_choice.SetStringSelection('cm')
    export_panel.imageFormat_choice.SetStringSelection('JPEG')
    export_panel.imageResolution_choice.SetStringSelection('300')
    export_panel.imageFontsScale_slider.SetValue(3)
    export_panel.imageDrawingsScale_slider.SetValue(4)

    # Set peaklist values
    export_panel.peaklistColumnMz_check.SetValue(True)
    export_panel.peaklistColumnAi_check.SetValue(False)
    export_panel.peaklistColumnBase_check.SetValue(True)
    export_panel.peaklistColumnInt_check.SetValue(False)
    export_panel.peaklistColumnRel_check.SetValue(True)
    export_panel.peaklistColumnZ_check.SetValue(False)
    export_panel.peaklistColumnMass_check.SetValue(True)
    export_panel.peaklistColumnSn_check.SetValue(False)
    export_panel.peaklistColumnFwhm_check.SetValue(True)
    export_panel.peaklistColumnResol_check.SetValue(False)
    export_panel.peaklistColumnGroup_check.SetValue(True)
    export_panel.peaklistSeparator_choice.SetStringSelection('Semicolon')

    # Set spectrum values
    export_panel.spectrumSeparator_choice.SetStringSelection('Comma')

    # Call getParams
    assert export_panel.getParams() is True

    # Verify config.export updates
    assert config.export['imageWidth'] == 10.5
    assert config.export['imageHeight'] == 8.2
    assert config.export['imageUnits'] == 'cm'
    assert config.export['imageFormat'] == 'JPEG'
    assert config.export['imageResolution'] == 300
    assert config.export['imageFontsScale'] == 3
    assert config.export['imageDrawingsScale'] == 4
    
    expected_cols = ['mz', 'base', 'rel', 'mass', 'fwhm', 'group']
    assert set(config.export['peaklistColumns']) == set(expected_cols)
    assert config.export['peaklistSeparator'] == ';'
    assert config.export['spectrumSeparator'] == ','

def test_getParams_failure(export_panel, mocker):
    """Verify that getParams returns False and rings bell on invalid input."""
    mock_bell = mocker.patch('wx.Bell')
    
    # Set invalid value (not a float)
    export_panel.imageWidth_value.SetValue('invalid')
    
    # Call getParams
    assert export_panel.getParams() is False
    
    # Verify bell was rung
    mock_bell.assert_called_once()

def test_onExport_delegation(export_panel, mocker):
    """Verify that onExport calls the correct sub-handler based on currentTool."""
    mock_getParams = mocker.patch.object(export_panel, 'getParams', return_value=True)
    mock_exportImage = mocker.patch.object(export_panel, 'onExportImage')
    mock_exportPeaklist = mocker.patch.object(export_panel, 'onExportPeaklist')
    mock_exportSpectrum = mocker.patch.object(export_panel, 'onExportSpectrum')
    mock_bell = mocker.patch('wx.Bell')

    # Test Image delegation
    export_panel.currentTool = 'image'
    export_panel.onExport(None)
    mock_exportImage.assert_called_once()
    mock_exportPeaklist.assert_not_called()
    mock_exportSpectrum.assert_not_called()

    # Reset mocks
    mock_exportImage.reset_mock()

    # Test Peaklist delegation
    export_panel.currentTool = 'peaklist'
    export_panel.onExport(None)
    mock_exportPeaklist.assert_called_once()
    mock_exportImage.assert_not_called()
    mock_exportSpectrum.assert_not_called()

    # Reset mocks
    mock_exportPeaklist.reset_mock()

    # Test Spectrum delegation
    export_panel.currentTool = 'spectrum'
    export_panel.onExport(None)
    mock_exportSpectrum.assert_called_once()
    mock_exportImage.assert_not_called()
    mock_exportPeaklist.assert_not_called()

    # Reset mocks
    mock_exportSpectrum.reset_mock()

    # Test getParams failure
    mock_getParams.return_value = False
    export_panel.onExport(None)
    mock_exportImage.assert_not_called()
    mock_exportPeaklist.assert_not_called()
    mock_exportSpectrum.assert_not_called()

    # Test processing active
    mock_getParams.return_value = True
    export_panel.processing = True # Simulate active processing
    export_panel.onExport(None)
    mock_exportImage.assert_not_called()
    mock_exportPeaklist.assert_not_called()
    mock_exportSpectrum.assert_not_called()
    # Note: onExport does NOT ring bell if processing, it just returns. 
    # This is different from onToolSelected and onClose.

def test_onExportImage_success(export_panel, mocker):
    """Verify onExportImage opens dialog, updates config and calls runExportImage."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_OK
    instance.GetPath.return_value = os.path.join('/tmp', 'test_spectrum.png')
    
    mock_run = mocker.patch.object(export_panel, 'runExportImage')
    mock_on_processing = mocker.patch.object(export_panel, 'onProcessing')
    
    config.export['imageFormat'] = 'PNG'
    export_panel.onExportImage()
    
    assert config.main['lastDir'] == '/tmp'
    mock_run.assert_called_once_with(os.path.join('/tmp', 'test_spectrum.png'))
    assert mock_on_processing.call_count == 2 # True then False

def test_onExportImage_cancel(export_panel, mocker):
    """Verify onExportImage returns on cancel."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_CANCEL
    
    mock_run = mocker.patch.object(export_panel, 'runExportImage')
    
    export_panel.onExportImage()
    
    mock_run.assert_not_called()

def test_onExportPeaklist_success(export_panel, mocker):
    """Verify onExportPeaklist opens dialog, updates config and starts thread."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_OK
    instance.GetPath.return_value = os.path.join('/tmp', 'test_peaklist.txt')
    
    # Mock threading.Thread
    mock_thread = mocker.patch('threading.Thread')
    thread_instance = mock_thread.return_value
    thread_instance.is_alive.side_effect = [True, False] # To exit the while loop
    
    mock_on_processing = mocker.patch.object(export_panel, 'onProcessing')
    
    config.export['peaklistFormat'] = 'ASCII'
    export_panel.onExportPeaklist()
    
    assert config.main['lastDir'] == '/tmp'
    mock_thread.assert_called_once()
    assert mock_thread.call_args[1]['target'] == export_panel.runExportPeaklist
    assert mock_thread.call_args[1]['kwargs'] == {'path': os.path.join('/tmp', 'test_peaklist.txt')}
    thread_instance.start.assert_called_once()
    assert mock_on_processing.call_count == 2

def test_onExportPeaklist_cancel(export_panel, mocker):
    """Verify onExportPeaklist returns on cancel."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_CANCEL
    
    mock_thread = mocker.patch('threading.Thread')
    
    export_panel.onExportPeaklist()
    
    mock_thread.assert_not_called()

def test_onExportSpectrum_success(export_panel, mocker):
    """Verify onExportSpectrum opens dialog, updates config and starts thread."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_OK
    instance.GetPath.return_value = os.path.join('/tmp', 'test_spectrum.txt')
    
    # Mock threading.Thread
    mock_thread = mocker.patch('threading.Thread')
    thread_instance = mock_thread.return_value
    thread_instance.is_alive.side_effect = [True, False]
    
    mock_on_processing = mocker.patch.object(export_panel, 'onProcessing')
    
    export_panel.onExportSpectrum()
    
    assert config.main['lastDir'] == '/tmp'
    mock_thread.assert_called_once()
    assert mock_thread.call_args[1]['target'] == export_panel.runExportSpectrum
    assert mock_thread.call_args[1]['kwargs'] == {'path': os.path.join('/tmp', 'test_spectrum.txt')}
    thread_instance.start.assert_called_once()
    assert mock_on_processing.call_count == 2

def test_onExportSpectrum_cancel(export_panel, mocker):
    """Verify onExportSpectrum returns on cancel."""
    mock_file_dlg = mocker.patch('wx.FileDialog')
    instance = mock_file_dlg.return_value
    instance.ShowModal.return_value = wx.ID_CANCEL
    
    mock_thread = mocker.patch('threading.Thread')
    
    export_panel.onExportSpectrum()
    
    mock_thread.assert_not_called()

def test_runExportImage_success(export_panel, mock_parent, tmp_path):
    """Verify that runExportImage successfully saves an image file."""
    path = str(tmp_path / "test_spectrum.png")
    # Setup config
    config.export['imageFormat'] = 'PNG'
    config.export['imageWidth'] = 100
    config.export['imageHeight'] = 100
    config.export['imageUnits'] = 'px'
    config.export['imageResolution'] = 72
    config.export['imageDrawingsScale'] = 1
    config.export['imageFontsScale'] = 1
    
    # Run export
    export_panel.runExportImage(path)
    
    # Check if file exists
    assert os.path.exists(path)

@pytest.mark.parametrize("fmt, expected_type", [
    ('PNG', wx.BITMAP_TYPE_PNG),
    ('TIFF', wx.BITMAP_TYPE_TIF),
    ('JPEG', wx.BITMAP_TYPE_JPEG)
])
def test_runExportImage_formats(export_panel, mock_parent, mocker, fmt, expected_type):
    """Verify that runExportImage uses correct wx.BITMAP_TYPE for each format."""
    mock_bitmap = mocker.Mock(spec=wx.Bitmap)
    mock_image = mocker.Mock(spec=wx.Image)
    mock_bitmap.ConvertToImage.return_value = mock_image
    mocker.patch.object(mock_parent, 'getSpectrumBitmap', return_value=mock_bitmap)
    
    config.export['imageFormat'] = fmt
    config.export['imageWidth'] = 100
    config.export['imageHeight'] = 100
    config.export['imageUnits'] = 'px'
    config.export['imageResolution'] = 72
    
    export_panel.runExportImage("dummy_path")
    
    mock_image.SaveFile.assert_called_once_with("dummy_path", expected_type)

def test_runExportImage_units_conversion(export_panel, mock_parent, mocker):
    """Verify unit conversions ('in', 'cm') for image dimensions."""
    # Mock bitmap and image to avoid real file IO and GUI overhead
    mock_bitmap = mocker.Mock(spec=wx.Bitmap)
    mock_image = mocker.Mock(spec=wx.Image)
    mock_bitmap.ConvertToImage.return_value = mock_image
    
    mock_get_bitmap = mocker.patch.object(mock_parent, 'getSpectrumBitmap', return_value=mock_bitmap)
    
    path = "dummy_path"
    
    # Test 'in'
    config.export['imageWidth'] = 2.0
    config.export['imageHeight'] = 3.0
    config.export['imageUnits'] = 'in'
    config.export['imageResolution'] = 100
    config.export['imageDrawingsScale'] = 2
    config.export['imageFontsScale'] = 3
    
    export_panel.runExportImage(path)
    # width = 2.0 * 100 = 200, height = 3.0 * 100 = 300
    mock_get_bitmap.assert_called_with(200.0, 300.0, {'drawings': 2, 'fonts': 3})
    
    # Test 'cm'
    config.export['imageWidth'] = 10.0
    config.export['imageHeight'] = 20.0
    config.export['imageUnits'] = 'cm'
    config.export['imageResolution'] = 100
    
    export_panel.runExportImage(path)
    # width = 10.0 * 100 * 0.3937 = 393.7
    # height = 20.0 * 100 * 0.3937 = 787.4
    mock_get_bitmap.assert_called_with(pytest.approx(393.7), pytest.approx(787.4), {'drawings': 2, 'fonts': 3})

def test_runExportImage_no_bitmap(export_panel, mock_parent, mocker):
    """Verify that runExportImage rings bell if no bitmap is returned."""
    mocker.patch.object(mock_parent, 'getSpectrumBitmap', return_value=None)
    mock_bell = mocker.patch('wx.Bell')
    
    export_panel.runExportImage("dummy_path")
    
    mock_bell.assert_called_once()

def test_runExportImage_save_failure(export_panel, mock_parent, mocker):
    """Verify that runExportImage rings bell on SaveFile failure."""
    mock_bitmap = mocker.Mock(spec=wx.Bitmap)
    mock_image = mocker.Mock(spec=wx.Image)
    mock_bitmap.ConvertToImage.return_value = mock_image
    mock_image.SaveFile.side_effect = Exception("Save failed")
    
    mocker.patch.object(mock_parent, 'getSpectrumBitmap', return_value=mock_bitmap)
    mock_bell = mocker.patch('wx.Bell')
    
    config.export['imageFormat'] = 'PNG'
    config.export['imageWidth'] = 100
    config.export['imageHeight'] = 100
    config.export['imageUnits'] = 'px'
    config.export['imageResolution'] = 72
    
    export_panel.runExportImage("dummy_path")
    
    mock_bell.assert_called_once()

def test_runExportPeaklist_ascii(export_panel, mock_parent, tmp_path, mocker):
    """Verify runExportPeaklist generates correct ASCII file with all headers."""
    path = str(tmp_path / "peaklist.txt")
    
    # Create dummy peaks
    peaks = [
        DummyPeak(mz=100.0, intensity=500.0, ai=1000.0, base=10.0, ri=0.5, sn=50.0, charge=1, fwhm=0.01, resolution=10000.0, group=1),
    ]
    mocker.patch.object(mock_parent, 'getCurrentPeaklist', return_value=peaks)
    
    # Setup config for ALL columns
    config.export['peaklistFormat'] = 'ASCII with Headers'
    config.export['peaklistSeparator'] = ';'
    config.export['peaklistColumns'] = ['mz', 'ai', 'base', 'int', 'rel', 'sn', 'z', 'mass', 'fwhm', 'resol', 'group']
    export_panel.peaklistSelect_choice.SetStringSelection('All Peaks')
    
    # Run export
    export_panel.runExportPeaklist(path)
    
    # Verify file content
    assert os.path.exists(path)
    with open(path, 'r') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    assert len(lines) == 2
    assert lines[0] == "m/z;a.i.;base;int;r.int.;s/n;z;mass;fwhm;resol.;group"
    assert lines[1] == "100.0;1000.0;10.0;500.0;50.0;50.0;1;100.0;0.01;10000.0;1"

def test_runExportPeaklist_ascii_no_headers(export_panel, mock_parent, tmp_path, mocker):
    """Verify runExportPeaklist generates correct ASCII file without headers."""
    path = str(tmp_path / "peaklist_no_headers.txt")
    
    # Create dummy peaks
    peaks = [
        DummyPeak(mz=100.0, intensity=500.0),
    ]
    mocker.patch.object(mock_parent, 'getCurrentPeaklist', return_value=peaks)
    
    # Setup config
    config.export['peaklistFormat'] = 'ASCII'
    config.export['peaklistSeparator'] = 'tab'
    config.export['peaklistColumns'] = ['mz', 'int']
    
    # Run export
    export_panel.runExportPeaklist(path)
    
    # Verify file content
    with open(path, 'r') as f:
        content = f.read()
    
    assert content.strip() == "100.0\t500.0"

def test_runExportPeaklist_mgf(export_panel, mock_parent, tmp_path, mocker):
    """Verify runExportPeaklist generates correct MGF file."""
    path = str(tmp_path / "peaklist.mgf")
    
    # Create dummy peaks
    peaks = [
        DummyPeak(mz=100.1234, intensity=500.5678),
        DummyPeak(mz=200.5678, intensity=1000.1234)
    ]
    mocker.patch.object(mock_parent, 'getCurrentPeaklist', return_value=peaks)
    
    # Setup config
    config.export['peaklistFormat'] = 'MGF'
    export_panel.peaklistSelect_choice.SetStringSelection('All Peaks')
    
    # Run export
    export_panel.runExportPeaklist(path)
    
    # Verify file content
    assert os.path.exists(path)
    with open(path, 'r') as f:
        content = f.read()
    
    assert content.startswith("BEGIN IONS\n")
    assert content.endswith("\nEND IONS")
    assert "100.123400 500.567800" in content
    assert "200.567800 1000.123400" in content

def test_runExportPeaklist_no_peaks(export_panel, mock_parent, mocker):
    """Verify runExportPeaklist rings bell if no peaks are returned."""
    mocker.patch.object(mock_parent, 'getCurrentPeaklist', return_value=[])
    mock_bell = mocker.patch('wx.Bell')
    
    export_panel.runExportPeaklist("dummy_path")
    
    mock_bell.assert_called_once()

def test_runExportSpectrum_success(export_panel, mock_parent, tmp_path, mocker):
    """Verify runExportSpectrum successfully exports spectrum points to a file."""
    path = str(tmp_path / "spectrum.txt")
    
    # Mock spectrum data
    spectrum_data = [(100.0, 500.0), (101.0, 600.0)]
    mock_get_points = mocker.patch.object(mock_parent, 'getCurrentSpectrumPoints', return_value=spectrum_data)
    
    # --- Test Full Spectrum branch ---
    export_panel.spectrumRange_choice.SetStringSelection('Full Spectrum')
    config.export['spectrumSeparator'] = ','
    
    export_panel.runExportSpectrum(path)
    
    mock_get_points.assert_called_with()
    assert os.path.exists(path)
    with open(path, 'r') as f:
        content = f.read()
    assert content == "100.000000,500.000000\n101.000000,600.000000\n"
    
    # --- Test Current View branch and Tab separator ---
    path_tab = str(tmp_path / "spectrum_tab.txt")
    export_panel.spectrumRange_choice.SetStringSelection('Current View')
    config.export['spectrumSeparator'] = 'tab'
    
    export_panel.runExportSpectrum(path_tab)
    
    mock_get_points.assert_called_with(currentView=True)
    assert os.path.exists(path_tab)
    with open(path_tab, 'r') as f:
        content = f.read()
    assert content == "100.000000\t500.000000\n101.000000\t600.000000\n"

def test_runExportSpectrum_no_data(export_panel, mock_parent, mocker):
    """Verify runExportSpectrum rings bell if getCurrentSpectrumPoints returns None."""
    mocker.patch.object(mock_parent, 'getCurrentSpectrumPoints', return_value=None)
    mock_bell = mocker.patch('wx.Bell')
    
    export_panel.spectrumRange_choice.SetStringSelection('Full Spectrum')
    export_panel.runExportSpectrum("dummy_path")
    
    mock_bell.assert_called_once()
