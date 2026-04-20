import pytest
import wx
from gui.panel_peaklist import dlgCopy, dlgThreshold, fileDropTarget, panelPeaklist


@pytest.fixture
def mock_config(mocker):
    mock_conf = mocker.patch('gui.panel_peaklist.config')
    mock_conf.main = {
        'peaklistColumns': ['mz', 'ai', 'sn', 'z'],
        'mzDigits': 4,
        'intDigits': 0
    }
    mock_conf.export = {
        'peaklistColumns': ['mz', 'ai']
    }
    return mock_conf

@pytest.fixture
def mock_images(mocker):
    mock_img = mocker.patch('gui.panel_peaklist.images')
    mock_img.lib = {
        'bgrBottombar': wx.Bitmap(1, 1),
        'peaklistAdd': wx.Bitmap(1, 1),
        'peaklistDelete': wx.Bitmap(1, 1),
        'peaklistAnnotate': wx.Bitmap(1, 1),
        'peaklistEditorOff': wx.Bitmap(1, 1),
        'peaklistEditorOn': wx.Bitmap(1, 1),
        'bgrPeakEditor': wx.Bitmap(1, 1),
    }
    return mock_img

@pytest.fixture
def mock_mspy(mocker):
    return mocker.patch('gui.panel_peaklist.mspy')

@pytest.fixture
def mock_doc(mocker):
    return mocker.patch('gui.panel_peaklist.doc')

@pytest.fixture
def mock_document(mocker):
    document = mocker.Mock()
    document.spectrum.peaklist = []
    document.annotations = []
    return document

@pytest.fixture
def mock_parent(mocker):
    parent = mocker.Mock(spec=wx.Window)
    parent.onDocumentDropped = mocker.Mock()
    parent.updateMassPoints = mocker.Mock()
    parent.onDocumentChanged = mocker.Mock()
    parent.onViewPeaklistColumns = mocker.Mock()
    parent.onToolsMassToFormula = mocker.Mock()
    return parent

@pytest.fixture
def real_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.onDocumentDropped = mocker.Mock()
    parent.updateMassPoints = mocker.Mock()
    parent.onDocumentChanged = mocker.Mock()
    parent.onViewPeaklistColumns = mocker.Mock()
    parent.onToolsMassToFormula = mocker.Mock()
    yield parent
    parent.Destroy()

def test_fileDropTarget_onDropFiles(mocker):
    # Mock callback
    mock_callback = mocker.Mock()

    # Instantiate fileDropTarget
    target = fileDropTarget(mock_callback)

    # Test paths
    paths = ['/path/to/file1.mzML', '/path/to/file2.mzML']

    # Invoke OnDropFiles
    target.OnDropFiles(0, 0, paths)

    # Verify callback invoked with proper arguments
    mock_callback.assert_called_once_with(paths=paths)

# --- dlgThreshold Tests ---

def test_dlgThreshold_init(real_parent):
    dlg = dlgThreshold(real_parent)
    assert dlg.GetTitle() == "Delete by Threshold"
    dlg.Destroy()

def test_dlgThreshold_onChange(real_parent):
    dlg = dlgThreshold(real_parent)

    # Initial state
    assert dlg.threshold is None

    # Change to valid float
    dlg.threshold_value.SetValue("10.5")
    assert dlg.threshold == 10.5

    # Change to invalid float
    dlg.threshold_value.SetValue("invalid")
    assert dlg.threshold is None

    dlg.Destroy()

def test_dlgThreshold_onDelete_valid(real_parent, mocker):
    dlg = dlgThreshold(real_parent)
    dlg.threshold = 10.5
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')

    dlg.onDelete(None)
    mock_end_modal.assert_called_once_with(wx.ID_OK)
    dlg.Destroy()

def test_dlgThreshold_onDelete_invalid(real_parent, mocker):
    dlg = dlgThreshold(real_parent)
    dlg.threshold = None
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    mock_end_modal = mocker.patch.object(dlg, 'EndModal')

    dlg.onDelete(None)
    mock_bell.assert_called_once()
    mock_end_modal.assert_not_called()
    dlg.Destroy()

def test_dlgThreshold_getData(real_parent):
    dlg = dlgThreshold(real_parent)
    dlg.threshold = 123.456
    dlg.thresholdType_choice.SetSelection(1) # 'a.i.'

    threshold, threshold_type = dlg.getData()
    assert threshold == 123.456
    assert threshold_type == 'a.i.'
    dlg.Destroy()

# --- dlgCopy Tests ---

def test_dlgCopy_init(real_parent, mock_config):
    dlg = dlgCopy(real_parent)
    assert dlg.GetTitle() == "Select Columns to Copy"
    dlg.Destroy()

def test_dlgCopy_getData(real_parent, mock_config):
    dlg = dlgCopy(real_parent)

    # Initially some should be checked based on mock_config.export
    # mock_config.export = {'peaklistColumns': ['mz', 'ai']}
    assert dlg.peaklistColumnMz_check.IsChecked()
    assert dlg.peaklistColumnAi_check.IsChecked()
    assert not dlg.peaklistColumnBase_check.IsChecked()

    # Toggle some checkboxes
    dlg.peaklistColumnMz_check.SetValue(False)
    dlg.peaklistColumnBase_check.SetValue(True)

    dlg.getData()

    # Verify config.export was updated
    assert 'mz' not in mock_config.export['peaklistColumns']
    assert 'ai' in mock_config.export['peaklistColumns']
    assert 'base' in mock_config.export['peaklistColumns']

    dlg.Destroy()

# --- panelPeaklist Tests ---

def test_panelPeaklist_init(real_parent, mock_config, mock_images):
    panel = panelPeaklist(real_parent)
    assert panel.currentDocument is None
    assert panel.peakListMap is None
    assert panel.selectedPeak is None

    # Check if UI components are created
    assert hasattr(panel, 'peakList')
    assert hasattr(panel, 'addPeak_butt')
    assert hasattr(panel, 'deletePeak_butt')
    assert hasattr(panel, 'annotatePeak_butt')
    assert hasattr(panel, 'editPeak_butt')
    assert hasattr(panel, 'peaksCount')

    # Check editor components
    assert hasattr(panel, 'peakMz_value')
    assert hasattr(panel, 'peakAi_value')
    assert hasattr(panel, 'peakBase_value')
    assert hasattr(panel, 'peakSN_value')
    assert hasattr(panel, 'peakCharge_value')
    assert hasattr(panel, 'peakFwhm_value')
    assert hasattr(panel, 'peakGroup_value')
    assert hasattr(panel, 'peakMonoisotopic_check')
    assert hasattr(panel, 'peakAdd_butt')
    assert hasattr(panel, 'peakReplace_butt')

    panel.Destroy()

def test_panelPeaklist_setData(real_parent, mock_config, mock_images, mock_document, mocker):
    panel = panelPeaklist(real_parent)

    # Mock updatePeakList to verify it's called
    mock_update = mocker.patch.object(panel, 'updatePeakList')
    panel.setData(mock_document)
    assert panel.currentDocument == mock_document
    mock_update.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_updatePeakList(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Setup mock document with peaks
    mock_document = mocker.Mock()
    peak1 = mocker.Mock()
    peak1.mz = 100.123456
    peak1.ai = 1000.123
    peak1.intensity = 1100.456
    peak1.base = 100.789
    peak1.ri = 0.5
    peak1.sn = 10.123
    peak1.charge = 1
    peak1.mass.return_value = 101.123456
    peak1.fwhm = 0.123456
    peak1.resolution = 1000.456
    peak1.group = "G1"

    mock_document.spectrum.peaklist = [peak1]

    # Set all columns in config
    mock_config.main['peaklistColumns'] = ['mz', 'ai', 'int', 'base', 'rel', 'sn', 'z', 'mass', 'fwhm', 'resol', 'group']
    mock_config.main['mzDigits'] = 4
    mock_config.main['intDigits'] = 0

    # Update columns
    panel.updatePeaklistColumns()

    panel.setData(mock_document)

    # Verify peakListMap
    assert len(panel.peakListMap) == 1
    row = panel.peakListMap[0]
    assert row[0] == 100.123456 # mz
    assert row[1] == 1000.123   # ai
    assert row[2] == 1100.456   # int
    assert row[3] == 100.789    # base
    assert row[4] == 50.0       # rel (ri*100)
    assert row[5] == 10.123     # sn
    assert row[6] == 1          # z
    assert row[7] == 101.123456 # mass
    assert row[8] == 0.123456   # fwhm
    assert row[9] == 1000.456   # resol
    assert row[10] == "G1"      # group

    # Verify list items (formatted)
    # mzFormat = '%0.' + `config.main['mzDigits']` + 'f' -> %0.4f -> 100.1235 (rounded)
    # intFormat = '%0.' + `config.main['intDigits']` + 'f' -> %0.0f -> 1000 (rounded)
    # fwhmFormat = '%0.' + `max(config.main['mzDigits'],3)` + 'f' -> %0.4f -> 0.1235

    assert panel.peakList.GetItemText(0, 0) == "100.1235"
    assert panel.peakList.GetItemText(0, 1) == "1000"
    assert panel.peakList.GetItemText(0, 2) == "1100"
    assert panel.peakList.GetItemText(0, 3) == "101"
    assert panel.peakList.GetItemText(0, 4) == "50.00"
    assert panel.peakList.GetItemText(0, 5) == "10.1"
    assert panel.peakList.GetItemText(0, 6) == "1"
    assert panel.peakList.GetItemText(0, 7) == "101.1235"
    assert panel.peakList.GetItemText(0, 8) == "0.1235"
    assert panel.peakList.GetItemText(0, 9) == "1000"
    assert panel.peakList.GetItemText(0, 10) == "G1"

    panel.Destroy()

def test_panelPeaklist_updatePeakListItem_edge_cases(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Setup mock document with a peak having None values
    mock_document = mocker.Mock()
    peak1 = mocker.Mock()
    peak1.mz = 100.0
    peak1.ai = 1000.0
    peak1.intensity = 1000.0
    peak1.base = 0.0
    peak1.ri = 0.0 # Will result in empty 'rel' if item[x] is 0
    peak1.sn = None
    peak1.charge = None
    peak1.mass.return_value = None
    peak1.fwhm = None
    peak1.resolution = None
    peak1.group = None

    mock_document.spectrum.peaklist = [peak1]
    mock_config.main['peaklistColumns'] = ['mz', 'ai', 'int', 'base', 'rel', 'sn', 'z', 'mass', 'fwhm', 'resol', 'group']

    # Update columns to match config
    panel.updatePeaklistColumns()

    panel.setData(mock_document)

    # Verify empty strings for None/0 values where applicable in updatePeakListItem
    assert panel.peakList.GetItemText(0, 4) == "" # rel (item[x] is 0)
    assert panel.peakList.GetItemText(0, 5) == "" # sn (None)
    assert panel.peakList.GetItemText(0, 6) == "" # z (None)
    assert panel.peakList.GetItemText(0, 7) == "" # mass (None)
    assert panel.peakList.GetItemText(0, 8) == "" # fwhm (None)
    assert panel.peakList.GetItemText(0, 9) == "" # resol (None)
    assert panel.peakList.GetItemText(0, 10) == "" # group (None)

    panel.Destroy()

# --- Step 7: Test UI Selection & Keyboard Events ---

def test_panelPeaklist_onItemSelected(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Setup mock document
    mock_doc = mocker.Mock()
    peak = mocker.Mock()
    peak.mz = 123.456
    peak.ai = 1000.0
    peak.base = 0.0
    peak.sn = 10.0
    peak.charge = 1
    peak.fwhm = 0.1
    peak.group = "G1"
    peak.isotope = 0
    mock_doc.spectrum.peaklist = [peak]
    panel.currentDocument = mock_doc

    # Mock event
    mock_evt = mocker.Mock()
    mock_evt.GetData.return_value = 0 # First peak

    # Mock panel.peakList.getSelected
    mocker.patch.object(panel.peakList, 'getSelected', return_value=[0])

    # Mock updatePeakEditor
    mock_update_editor = mocker.patch.object(panel, 'updatePeakEditor')

    panel.onItemSelected(mock_evt)

    assert panel.selectedPeak == 0
    real_parent.updateMassPoints.assert_called_once_with([123.456])
    mock_update_editor.assert_called_once_with(peak)
    mock_evt.Skip.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onListKey_selectAll(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Mock peakList.GetItemCount
    mocker.patch.object(panel.peakList, 'GetItemCount', return_value=3)
    mock_set_item_state = mocker.patch.object(panel.peakList, 'SetItemState')

    # Mock event for Cmd+A (Select All)
    # On Mac Cmd is CmdDown, on others it might be CtrlDown depending on wx implementation of CmdDown
    mock_evt = mocker.Mock()
    mock_evt.GetKeyCode.return_value = 65 # 'A'
    mock_evt.CmdDown.return_value = True

    panel.onListKey(mock_evt)

    assert mock_set_item_state.call_count == 3
    for x in range(3):
        mock_set_item_state.assert_any_call(x, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

    panel.Destroy()

def test_panelPeaklist_onListKey_copy(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    mock_copy = mocker.patch.object(panel, 'copyToClipboard')

    # Mock event for Cmd+C
    mock_evt = mocker.Mock()
    mock_evt.GetKeyCode.return_value = 67 # 'C'
    mock_evt.CmdDown.return_value = True

    panel.onListKey(mock_evt)
    mock_copy.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onListKey_delete(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    mock_delete = mocker.patch.object(panel, 'onDeleteSelected')

    # Mock event for Delete key
    mock_evt = mocker.Mock()
    mock_evt.GetKeyCode.return_value = wx.WXK_DELETE
    mock_evt.CmdDown.return_value = False

    panel.onListKey(mock_evt)
    mock_delete.assert_called_once()

    # Mock event for Cmd+Back
    mock_delete.reset_mock()
    mock_evt.GetKeyCode.return_value = wx.WXK_BACK
    mock_evt.CmdDown.return_value = True

    panel.onListKey(mock_evt)
    mock_delete.assert_called_once()

    panel.Destroy()

# --- Step 8: Test Toolbar Interactions (onAdd, onEdit, onDelete) ---

def test_panelPeaklist_onAdd(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Test with no document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onAdd(None)
    mock_bell.assert_called_once()

    # Test with document
    panel.currentDocument = mocker.Mock()
    mock_update_editor = mocker.patch.object(panel, 'updatePeakEditor')

    # Initially hidden
    assert not panel.mainSizer.IsShown(1)

    panel.onAdd(None)
    mock_update_editor.assert_called_once_with(None)
    assert panel.mainSizer.IsShown(1)

    panel.Destroy()

def test_panelPeaklist_onEdit(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Initially hidden
    assert not panel.mainSizer.IsShown(1)

    # Show it
    panel.onEdit(None)
    assert panel.mainSizer.IsShown(1)

    # Hide it
    panel.onEdit(None)
    assert not panel.mainSizer.IsShown(1)

    panel.Destroy()

def test_panelPeaklist_onDeleteSelected(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Test with no document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onDeleteSelected(None)
    mock_bell.assert_called_once()

    # Test with document and selection
    mock_document = mocker.Mock()
    panel.currentDocument = mock_document

    mocker.patch.object(panel.peakList, 'getSelected', return_value=[0, 2])
    mocker.patch.object(panel.peakList, 'GetItemData', side_effect=[10, 12]) # Indices in peaklist

    panel.onDeleteSelected(None)

    mock_document.backup.assert_called_once_with('spectrum')
    mock_document.spectrum.peaklist.delete.assert_called_once_with([10, 12])
    real_parent.onDocumentChanged.assert_called_once_with(items=('spectrum'))

    panel.Destroy()

def test_panelPeaklist_onDeleteAll(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Test with no document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onDeleteAll(None)
    mock_bell.assert_called_once()

    # Test with document
    mock_document = mocker.Mock()
    panel.currentDocument = mock_document

    panel.onDeleteAll(None)

    mock_document.backup.assert_called_once_with('spectrum')
    mock_document.spectrum.peaklist.empty.assert_called_once()
    real_parent.onDocumentChanged.assert_called_once_with(items=('spectrum'))

    panel.Destroy()

def test_panelPeaklist_onDeleteByThreshold(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Test with no document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onDeleteByThreshold(None)
    mock_bell.assert_called_once()

    # Test with document
    mock_document = mocker.Mock()
    peak1 = mocker.Mock(); peak1.mz = 100.0; peak1.ai = 1000.0; peak1.intensity = 1100.0; peak1.ri = 0.1; peak1.sn = 5.0
    peak2 = mocker.Mock(); peak2.mz = 200.0; peak2.ai = 2000.0; peak2.intensity = 2100.0; peak2.ri = 0.5; peak2.sn = 15.0
    peak3 = mocker.Mock(); peak3.mz = 300.0; peak3.ai = 3000.0; peak3.intensity = 3100.0; peak3.ri = 1.0; peak3.sn = 25.0

    mock_peaklist = mocker.MagicMock()
    mock_peaklist.__iter__.side_effect = lambda: iter([peak1, peak2, peak3])
    mock_peaklist.__len__.return_value = 3

    mock_document.spectrum.peaklist = mock_peaklist
    panel.currentDocument = mock_document

    # Mock dlgThreshold
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgThreshold')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_OK

    # Test m/z threshold
    mock_dlg.getData.return_value = (250.0, 'm/z')
    panel.onDeleteByThreshold(None)
    mock_peaklist.delete.assert_called_with([0, 1])

    # Test a.i. threshold
    mock_peaklist.delete.reset_mock()
    mock_dlg.getData.return_value = (2500.0, 'a.i.')
    panel.onDeleteByThreshold(None)
    mock_peaklist.delete.assert_called_with([0, 1])

    # Test Intensity threshold
    mock_peaklist.delete.reset_mock()
    mock_dlg.getData.return_value = (2500.0, 'Intensity')
    panel.onDeleteByThreshold(None)
    mock_peaklist.delete.assert_called_with([0, 1])

    # Test Relative Intensity threshold (input is 0-100, logic divides by 100)
    mock_peaklist.delete.reset_mock()
    mock_dlg.getData.return_value = (60.0, 'Relative Intensity') # 0.6 threshold
    panel.onDeleteByThreshold(None)
    mock_peaklist.delete.assert_called_with([0, 1])

    # Test s/n threshold
    mock_peaklist.delete.reset_mock()
    mock_dlg.getData.return_value = (20.0, 's/n')
    panel.onDeleteByThreshold(None)
    mock_peaklist.delete.assert_called_with([0, 1])

    panel.Destroy()

# --- Step 9: Test Editor Operations ---

def test_panelPeaklist_getPeakEditorData_valid(real_parent, mock_config, mock_images, mock_mspy):
    panel = panelPeaklist(real_parent)

    panel.peakMz_value.SetValue("123.456")
    panel.peakAi_value.SetValue("1000")
    panel.peakBase_value.SetValue("100")
    panel.peakSN_value.SetValue("10")
    panel.peakCharge_value.SetValue("2")
    panel.peakFwhm_value.SetValue("0.1")
    panel.peakGroup_value.SetValue("G1")
    panel.peakMonoisotopic_check.SetValue(True)

    peak = panel.getPeakEditorData()

    assert peak is not False
    mock_mspy.peak.assert_called_with(
        mz=123.456, ai=1000.0, base=100.0, sn=10.0,
        charge=2, isotope=0, fwhm=0.1, group="G1"
    )

    panel.Destroy()

def test_panelPeaklist_getPeakEditorData_invalid(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')

    # Non-float in mz
    panel.peakMz_value.SetValue("invalid")
    assert panel.getPeakEditorData() is False
    assert mock_bell.call_count == 1

    # ai is 0
    mock_bell.reset_mock()
    panel.peakMz_value.SetValue("123.456")
    panel.peakAi_value.SetValue("0")
    assert panel.getPeakEditorData() is False
    assert mock_bell.call_count == 1

    panel.Destroy()

def test_panelPeaklist_onAddPeak(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # No document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onAddPeak(None)
    mock_bell.assert_called_once()

    # Valid document and valid data
    mock_document = mocker.Mock()
    mock_peaklist = mocker.MagicMock()
    mock_document.spectrum.peaklist = mock_peaklist
    panel.currentDocument = mock_document

    mock_peak = mocker.Mock()
    mocker.patch.object(panel, 'getPeakEditorData', return_value=mock_peak)

    panel.onAddPeak(None)

    mock_document.backup.assert_called_once_with('spectrum')
    mock_peaklist.append.assert_called_once_with(mock_peak)
    real_parent.onDocumentChanged.assert_called_once_with(items=('spectrum'))

    panel.Destroy()

def test_panelPeaklist_onReplacePeak(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # No selection
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onReplacePeak(None)
    mock_bell.assert_called_once()

    # Valid selection and valid data
    mock_document = mocker.Mock()
    mock_peaklist = mocker.MagicMock()
    mock_document.spectrum.peaklist = mock_peaklist
    panel.currentDocument = mock_document
    panel.selectedPeak = 0

    mock_peak = mocker.Mock()
    mocker.patch.object(panel, 'getPeakEditorData', return_value=mock_peak)

    panel.onReplacePeak(None)

    mock_document.backup.assert_called_once_with('spectrum')
    mock_peaklist.__setitem__.assert_called_once_with(0, mock_peak)
    real_parent.onDocumentChanged.assert_called_once_with(items=('spectrum'))

    panel.Destroy()

# --- Step 10: Test Context Menus & Tools ---

def test_panelPeaklist_onAnnotate(real_parent, mock_config, mock_images, mock_doc, mocker):
    panel = panelPeaklist(real_parent)

    # No document or selection
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onAnnotate()
    mock_bell.assert_called_once()

    # Valid document and selection
    mock_document = mocker.Mock()
    peak = mocker.Mock()
    peak.mz = 123.456; peak.ai = 1000.0; peak.base = 0.0; peak.charge = 1
    mock_document.spectrum.peaklist = [peak]
    panel.currentDocument = mock_document
    panel.selectedPeak = 0

    # Mock dlgNotation
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgNotation')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_OK

    # Mock annotation object
    mock_annot = mocker.Mock()
    mock_doc.annotation.return_value = mock_annot

    panel.onAnnotate()

    mock_doc.annotation.assert_called_once_with(label='', mz=peak.mz, ai=peak.ai, base=peak.base, charge=peak.charge)
    mock_document.annotations.append.assert_called_once_with(mock_annot)
    mock_document.sortAnnotations.assert_called_once()
    real_parent.onDocumentChanged.assert_called_once_with(items=('annotations'))

    panel.Destroy()

def test_panelPeaklist_onItemRMU(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # Return early if no document/selection
    panel.onItemRMU(mocker.Mock())

    # Set document and selection
    panel.currentDocument = mocker.Mock()
    panel.selectedPeak = 0

    mock_menu_cls = mocker.patch('gui.panel_peaklist.wx.Menu')
    mock_popup = mocker.patch.object(panel, 'PopupMenu')

    panel.onItemRMU(mocker.Mock())

    mock_menu_cls.assert_called_once()
    mock_popup.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onColumnRMU(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    mock_menu_cls = mocker.patch('gui.panel_peaklist.wx.Menu')
    mock_popup = mocker.patch.object(panel, 'PopupMenu')

    panel.onColumnRMU(mocker.Mock())

    mock_menu_cls.assert_called_once()
    mock_popup.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onSendToMassToFormula(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # No document or selection
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onSendToMassToFormula()
    mock_bell.assert_called_once()

    # Set document and selection
    mock_document = mocker.Mock()
    peak = mocker.Mock()
    peak.mz = 123.456; peak.charge = 1
    mock_document.spectrum.peaklist = [peak]
    panel.currentDocument = mock_document
    panel.selectedPeak = 0

    panel.onSendToMassToFormula()

    real_parent.onToolsMassToFormula.assert_called_once_with(mass=123.456, charge=1)

    panel.Destroy()

def test_panelPeaklist_copyToClipboard(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # No selection
    mocker.patch.object(panel.peakList, 'getSelected', return_value=[])
    panel.copyToClipboard()

    # Selection
    mocker.patch.object(panel.peakList, 'getSelected', return_value=[0])
    mocker.patch.object(panel.peakList, 'GetItemData', return_value=10)

    mock_document = mocker.Mock()
    peak = mocker.Mock()
    peak.mz = 123.456; peak.ai = 1000.0; peak.base = 0.0; peak.intensity = 1100.0; peak.ri = 0.5; peak.sn = 10.0; peak.charge = 1
    peak.mass.return_value = 124.456; peak.fwhm = 0.1; peak.resolution = 1234.0; peak.group = "G1"
    mock_document.spectrum.peaklist = {10: peak} # Dict-like mock for indexing
    panel.currentDocument = mock_document

    # Mock dlgCopy
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgCopy')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_OK

    # Mock config.export['peaklistColumns'] - ensure all are tested
    mock_config.export['peaklistColumns'] = ['mz', 'ai', 'base', 'int', 'rel', 'sn', 'z', 'mass', 'fwhm', 'resol', 'group']

    # Mock Clipboard
    mock_clipboard = mocker.patch('gui.panel_peaklist.wx.TheClipboard')
    mock_clipboard.Open.return_value = True

    mock_data_obj_cls = mocker.patch('gui.panel_peaklist.wx.TextDataObject')
    mock_data_obj = mock_data_obj_cls.return_value

    panel.copyToClipboard()

    # Verify buffer content
    # Order: mz, ai, base, int, rel, sn, z, mass, fwhm, resol, group
    expected_buff = "123.456\t1000.0\t0.0\t1100.0\t50.0\t10.0\t1\t124.456\t0.1\t1234.0\tG1"
    mock_data_obj.SetText.assert_called_once_with(expected_buff)

    mock_clipboard.SetData.assert_called_once_with(mock_data_obj)
    mock_clipboard.Close.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onAddPeak_invalid_data(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    panel.currentDocument = mocker.Mock()
    mocker.patch.object(panel, 'getPeakEditorData', return_value=False)

    panel.onAddPeak(None)

    panel.currentDocument.backup.assert_not_called()
    panel.Destroy()

def test_panelPeaklist_onReplacePeak_invalid_data(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    panel.currentDocument = mocker.Mock()
    panel.selectedPeak = 0
    mocker.patch.object(panel, 'getPeakEditorData', return_value=False)

    panel.onReplacePeak(None)

    panel.currentDocument.backup.assert_not_called()
    panel.Destroy()

def test_panelPeaklist_onAnnotate_cancel(real_parent, mock_config, mock_images, mock_doc, mocker):
    panel = panelPeaklist(real_parent)
    mock_document = mocker.Mock()
    peak = mocker.Mock()
    peak.mz = 123.456; peak.ai = 1000.0; peak.base = 0.0; peak.charge = 1
    mock_document.spectrum.peaklist = [peak]
    panel.currentDocument = mock_document
    panel.selectedPeak = 0

    # Mock dlgNotation
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgNotation')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_CANCEL

    panel.onAnnotate()

    mock_document.annotations.append.assert_not_called()
    panel.Destroy()

def test_panelPeaklist_onDeleteByThreshold_cancel(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    panel.currentDocument = mocker.Mock()

    # Mock dlgThreshold
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgThreshold')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_CANCEL

    panel.onDeleteByThreshold(None)

    panel.currentDocument.backup.assert_not_called()
    panel.Destroy()

def test_panelPeaklist_copyToClipboard_cancel(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    mocker.patch.object(panel.peakList, 'getSelected', return_value=[0])

    # Mock dlgCopy
    mock_dlg_cls = mocker.patch('gui.panel_peaklist.dlgCopy')
    mock_dlg = mock_dlg_cls.return_value
    mock_dlg.ShowModal.return_value = wx.ID_CANCEL

    # Mock Clipboard to ensure it is not opened
    mock_clipboard = mocker.patch('gui.panel_peaklist.wx.TheClipboard')

    panel.copyToClipboard()

    mock_clipboard.Open.assert_not_called()
    panel.Destroy()

def test_panelPeaklist_getSelectedPeaks(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    mock_document = mocker.Mock()
    peak1 = mocker.Mock()
    peak2 = mocker.Mock()
    mock_document.spectrum.peaklist = {10: peak1, 12: peak2}
    panel.currentDocument = mock_document

    mocker.patch.object(panel.peakList, 'getSelected', return_value=[0, 1])
    mocker.patch.object(panel.peakList, 'GetItemData', side_effect=[10, 12])

    peaks = panel.getSelectedPeaks()
    assert peaks == [peak1, peak2]

    panel.Destroy()

def test_panelPeaklist_onDelete(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)

    # No document
    mock_bell = mocker.patch('gui.panel_peaklist.wx.Bell')
    panel.onDelete(None)
    mock_bell.assert_called_once()

    # With document
    panel.currentDocument = mocker.Mock()
    mock_menu_cls = mocker.patch('gui.panel_peaklist.wx.Menu')
    mock_popup = mocker.patch.object(panel, 'PopupMenu')

    panel.onDelete(None)

    mock_menu_cls.assert_called_once()
    mock_popup.assert_called_once()

    panel.Destroy()

def test_panelPeaklist_onItemActivated(real_parent, mock_config, mock_images, mocker):
    panel = panelPeaklist(real_parent)
    mock_on_annotate = mocker.patch.object(panel, 'onAnnotate')

    panel.onItemActivated(None)
    mock_on_annotate.assert_called_once()

    panel.Destroy()
