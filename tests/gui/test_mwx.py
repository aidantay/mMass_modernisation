import pytest
import wx
import gui.mwx as mwx
import mspy

@pytest.fixture
def frame(wx_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()

@pytest.fixture
def mock_images(mocker):
    mock_lib = {'iconDlg': wx.Bitmap(16, 16)}
    mocker.patch('gui.images.lib', mock_lib)
    return mock_lib

def test_appInit_mac(mocker):
    # Backup SCROLL_DIRECTION
    old_direction = mwx.SCROLL_DIRECTION
    try:
        mocker.patch('wx.Platform', '__WXMAC__')
        mocker.patch('gui.config.main', {'macListCtrlGeneric': True, 'reverseScrolling': True})
        mocker.patch('wx.SystemOptions.SetOptionInt', create=True)
        mocker.patch('wx.ToolTip.SetDelay')
        
        mwx.appInit()
        
        wx.SystemOptions.SetOptionInt.assert_called_with("mac.listctrl.always_use_generic", True)
        wx.ToolTip.SetDelay.assert_called_with(1500)
        assert mwx.SCROLL_DIRECTION == -1
    finally:
        mwx.SCROLL_DIRECTION = old_direction

def test_appInit_msw(mocker):
    mocker.patch('wx.Platform', '__WXMSW__')
    mock_set_size = mocker.patch('wx.SMALL_FONT.SetPointSize')
    mwx.appInit()
    mock_set_size.assert_called_with(mwx.SMALL_FONT_SIZE)

def test_appInit_gtk(mocker):
    mocker.patch('wx.Platform', '__WXGTK__')
    mock_set_size = mocker.patch('wx.SMALL_FONT.SetPointSize')
    mwx.appInit()
    mock_set_size.assert_called_with(mwx.SMALL_FONT_SIZE)

def test_bgrPanel(mocker, frame):
    mock_image = mocker.MagicMock()
    mock_image.GetWidth.return_value = 100
    
    panel = mwx.bgrPanel(frame, -1, mock_image, size=(200, 50))
    
    # Mock PaintDC to avoid actual drawing issues in headless env
    mock_dc_class = mocker.patch('wx.PaintDC')
    mock_dc = mock_dc_class.return_value
    panel._onPaint()
    # 200 / 100 = 2 iterations
    assert mock_dc.DrawBitmap.call_count == 2

def test_sortListCtrl_sorting(mocker, frame):
    list_ctrl = mwx.sortListCtrl(frame)
    data = [[2, 'B'], [1, 'C'], [3, 'A']]
    list_ctrl.setDataMap(data)
    list_ctrl.InsertColumn(0, 'Col 0')
    list_ctrl.InsertColumn(1, 'Col 1')
    
    # Mock IsVirtual to use the simpler sorting logic
    mocker.patch.object(list_ctrl, 'IsVirtual', return_value=True)
    mocker.patch.object(list_ctrl, 'Refresh')
    
    # Test OnGetItemText and OnGetItemImage
    assert list_ctrl.OnGetItemText(0, 0) == '2'
    assert list_ctrl.OnGetItemImage(0) == -1
    
    # Sort by col 1 (alphabetical)
    evt = mocker.MagicMock(spec=wx.ListEvent)
    evt.GetColumn.return_value = 1
    list_ctrl._onColClick(evt)
    
    # Should be A, B, C
    assert list_ctrl._data[0][1] == 'A'
    assert list_ctrl._data[1][1] == 'B'
    assert list_ctrl._data[2][1] == 'C'
    
    # Reverse sort
    list_ctrl._onColClick(evt)
    assert list_ctrl._data[0][1] == 'C'
    assert list_ctrl._data[1][1] == 'B'
    assert list_ctrl._data[2][1] == 'A'
    
    # Test sort() method
    list_ctrl.sort(1)
    # Since it was reversed, calling sort(1) should reverse it back if current column is 1
    # Actually sort(col) logic:
    # if self._currentColumn != col: direction = LISTCTRL_SORT (1)
    # else: use self._currentDirection
    list_ctrl.sort(0)
    assert list_ctrl._currentColumn == 0

def test_sortListCtrl_secondary_sort(mocker, frame):
    list_ctrl = mwx.sortListCtrl(frame)
    data = [[1, 'B'], [1, 'A'], [2, 'A']]
    list_ctrl.setDataMap(data)
    list_ctrl.InsertColumn(0, 'Col 0')
    list_ctrl.InsertColumn(1, 'Col 1')
    list_ctrl.setSecondarySortColumn(1)
    
    # Mock IsVirtual
    mocker.patch.object(list_ctrl, 'IsVirtual', return_value=True)
    mocker.patch.object(list_ctrl, 'Refresh')
    
    # Sort by col 0
    list_ctrl._sort(0, 1)
    
    # Should be [1, 'A'], [1, 'B'], [2, 'A']
    assert list_ctrl._data[0] == [1, 'A']
    assert list_ctrl._data[1] == [1, 'B']
    assert list_ctrl._data[2] == [2, 'A']
    
    # Test _columnSorter (used for non-virtual sorting)
    list_ctrl._currentColumn = 0
    list_ctrl._currentDirection = 1
    assert list_ctrl._columnSorter(0, 1) == -1 # 'A' vs 'B'

def test_sortListCtrl_attributes(frame):
    list_ctrl = mwx.sortListCtrl(frame)
    list_ctrl.setAltColour(wx.Colour(200, 200, 200))
    
    # Row 0 (even)
    attr = list_ctrl.OnGetItemAttr(0)
    assert attr.GetBackgroundColour() == list_ctrl._altColour
    
    # Row 1 (odd)
    attr = list_ctrl.OnGetItemAttr(1)
    assert attr.GetBackgroundColour() == list_ctrl._defaultColour

    # Custom attributes
    def get_attr(row):
        a = wx.ItemAttr()
        a.SetBackgroundColour(wx.RED)
        a.SetTextColour(wx.BLUE)
        a.SetFont(wx.ITALIC_FONT)
        return a
    
    list_ctrl.setItemAttrFn(get_attr)
    attr = list_ctrl.OnGetItemAttr(0)
    assert attr.GetBackgroundColour() == wx.RED
    assert attr.GetTextColour() == wx.BLUE

def test_sortListCtrl_utils(mocker, frame):
    list_ctrl = mwx.sortListCtrl(frame)
    list_ctrl.InsertColumn(0, 'Col 0')
    list_ctrl.InsertColumn(1, 'Col 1')
    
    # deleteColumns
    list_ctrl.deleteColumns()
    assert list_ctrl.GetColumnCount() == 0
    
    # unselectAll
    list_ctrl.InsertColumn(0, 'Col 0')
    list_ctrl.InsertItem(0, 'Item 0')
    mocker.patch.object(list_ctrl, 'GetNextItem', side_effect=[0, -1])
    mock_set_state = mocker.patch.object(list_ctrl, 'SetItemState')
    list_ctrl.unselectAll()
    mock_set_state.assert_any_call(0, 0, wx.LIST_STATE_SELECTED)
    
    # updateItemsBackground
    list_ctrl.setAltColour(wx.Colour(200, 200, 200))
    mocker.patch.object(list_ctrl, 'GetItemCount', return_value=2)
    mock_set_bg = mocker.patch.object(list_ctrl, 'SetItemBackgroundColour')
    list_ctrl.updateItemsBackground()
    assert mock_set_bg.call_count == 2

def test_sortListCtrl_selection_and_clipboard(mocker, frame):
    list_ctrl = mwx.sortListCtrl(frame)
    list_ctrl.InsertColumn(0, 'Col 0')
    list_ctrl.InsertItem(0, 'Item 0')
    list_ctrl.InsertItem(1, 'Item 1')
    
    # Mock GetNextItem and GetItemState for getSelected
    mocker.patch.object(list_ctrl, 'GetNextItem', side_effect=[1, -1])
    selected = list_ctrl.getSelected()
    assert selected == [1]

    # Mock clipboard
    mocker.patch('wx.TheClipboard.Open', return_value=True)
    mock_set = mocker.patch('wx.TheClipboard.SetData')
    mocker.patch('wx.TheClipboard.Close')
    list_ctrl.copyToClipboard(selected=False)
    assert mock_set.called

def test_scrollTextCtrl_setters(frame):
    ctrl = mwx.scrollTextCtrl(frame)
    ctrl.setScrollStep(5)
    assert ctrl._scrollStep == 5
    ctrl.setScrollMultiplier(0.5)
    assert ctrl._scrollMultiplier == 0.5
    ctrl.setMin(0)
    assert ctrl._min == 0
    ctrl.setMax(100)
    assert ctrl._max == 100
    ctrl.setDigits(2)
    assert ctrl._digits == 2

def test_scrollTextCtrl_keys(mocker, frame):
    ctrl = mwx.scrollTextCtrl(frame, value="10", step=1, digits=1)

    # Up key
    evt = mocker.MagicMock(spec=wx.KeyEvent)
    evt.GetKeyCode.return_value = wx.WXK_UP
    evt.AltDown.return_value = False
    ctrl._onKey(evt)
    assert ctrl.GetValue() == "11.0"
    
    # Down key
    evt.GetKeyCode.return_value = wx.WXK_DOWN
    ctrl._onKey(evt)
    assert ctrl.GetValue() == "10.0"

    # Scientific notation
    ctrl.SetValue("10000")
    ctrl._onKey(evt) # Decrement to 9999
    assert ctrl.GetValue() == "9999.0"
    
    evt.GetKeyCode.return_value = wx.WXK_UP
    ctrl._onKey(evt) # 10000.0
    ctrl._onKey(evt) # 10001.0 -> 1.0e+04
    assert ctrl.GetValue() == "1.0e+04"

def test_scrollTextCtrl_multiplier(mocker, frame):
    ctrl = mwx.scrollTextCtrl(frame, value="100", multiplier=0.1, digits=0)

    evt = mocker.MagicMock(spec=wx.KeyEvent)
    evt.GetKeyCode.return_value = wx.WXK_UP
    evt.AltDown.return_value = False
    
    # 100 + 100 * 0.1 = 110
    ctrl._onKey(evt)
    assert ctrl.GetValue() == "110"
    
    # Precise (0.1 * multiplier)
    evt.AltDown.return_value = True
    # 110 + 110 * 0.1 * 0.1 = 110 + 1.1 = 111.1 -> "111"
    ctrl._onKey(evt)
    assert ctrl.GetValue() == "111"

def test_scrollTextCtrl_limits(mocker, frame):
    ctrl = mwx.scrollTextCtrl(frame, value="10", step=1, limits=(5, 15))

    evt = mocker.MagicMock(spec=wx.KeyEvent)
    evt.AltDown.return_value = False
    
    # Max limit
    ctrl.SetValue("15")
    evt.GetKeyCode.return_value = wx.WXK_UP
    ctrl._onKey(evt)
    assert float(ctrl.GetValue()) == 15
    
    # Min limit
    ctrl.SetValue("5")
    evt.GetKeyCode.return_value = wx.WXK_DOWN
    ctrl._onKey(evt)
    assert float(ctrl.GetValue()) == 5

def test_scrollTextCtrl_invalid_value(mocker, frame):
    ctrl = mwx.scrollTextCtrl(frame, value="abc", step=1)
    evt = mocker.MagicMock(spec=wx.KeyEvent)
    evt.GetKeyCode.return_value = wx.WXK_UP
    
    mock_bell = mocker.patch('wx.Bell')
    ctrl._onKey(evt)
    mock_bell.assert_called()

def test_scrollTextCtrl_scroll(mocker, frame):
    mocker.patch('wx.Platform', '__WXMAC__')
    ctrl = mwx.scrollTextCtrl(frame, value="10", step=1)

    evt = mocker.MagicMock(spec=wx.MouseEvent)
    evt.GetWheelRotation.return_value = 120
    evt.AltDown.return_value = False
    
    # SCROLL_DIRECTION is 1 by default
    ctrl._onScroll(evt)
    assert float(ctrl.GetValue()) == 10 + 120

def test_formulaCtrl(mocker, frame):
    mock_compound = mocker.patch('gui.mwx.mspy.compound')
    ctrl = mwx.formulaCtrl(frame, value="H2O")

    # Success
    mock_compound.return_value = mocker.Mock()
    ctrl._checkFormula()
    # Check that it's NOT the error color
    assert ctrl.GetBackgroundColour() != wx.Colour(250, 100, 100)

    # Failure
    mock_compound.side_effect = Exception("Invalid")
    ctrl._checkFormula()
    assert ctrl.GetBackgroundColour() == wx.Colour(250, 100, 100)

    # Test _onText
    evt = mocker.MagicMock(spec=wx.CommandEvent)
    mock_call_after = mocker.patch('wx.CallAfter')
    ctrl._onText(evt)
    mock_call_after.assert_called()

def test_gauge(mocker, frame):
    g = mwx.gauge(frame)
    mocker.patch('wx.Yield')
    mocker.patch('time.sleep')
    g.pulse()
    # Should not crash

def test_gaugePanel(mocker, frame):
    mocker.patch('wx.Yield')
    mocker.patch('time.sleep')
    gp = mwx.gaugePanel(frame, "Processing...")
    
    # In Phoenix, self.label might be tricky due to property overlap,
    # but we can check the StaticText label if we find it.
    static_text = None
    for child in gp.GetChildren():
        if isinstance(child, wx.Panel):
            for c in child.GetChildren():
                if isinstance(c, wx.StaticText):
                    static_text = c
                    break
    
    gp.setLabel("New Label")
    if static_text:
        assert static_text.GetLabel() == "New Label"
    
    gp.pulse()
    
    mocker.patch.object(gp, 'MakeModal', create=True)
    mocker.patch.object(gp, 'Show')
    gp.show()
    
    mocker.patch.object(gp, 'Destroy')
    mocker.patch.object(gp, 'MakeModal', create=True)
    gp.close()

def test_validator(mocker, frame):
    # Test 'int'
    val = mwx.validator('int')
    ctrl = wx.TextCtrl(frame)
    mocker.patch.object(val, 'GetWindow', return_value=ctrl)

    evt = mocker.MagicMock(spec=wx.KeyEvent)
    evt.CmdDown.return_value = False
    
    # Valid digit
    evt.GetKeyCode.return_value = ord('1')
    val.OnChar(evt)
    evt.Skip.assert_called()
    
    # Valid negative sign
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = ord('-')
    val.OnChar(evt)
    evt.Skip.assert_called()

    # Invalid character
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = ord('a')
    mock_bell = mocker.patch('wx.Bell')
    val.OnChar(evt)
    mock_bell.assert_called()
    assert not evt.Skip.called

    # Test 'intPos'
    val_pos = mwx.validator('intPos')
    mocker.patch.object(val_pos, 'GetWindow', return_value=ctrl)
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = ord('-')
    mock_bell_pos = mocker.patch('wx.Bell')
    val_pos.OnChar(evt)
    mock_bell_pos.assert_called()
    assert not evt.Skip.called

    # Test 'float'
    val_float = mwx.validator('float')
    mocker.patch.object(val_float, 'GetWindow', return_value=ctrl)
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = ord('.')
    val_float.OnChar(evt)
    evt.Skip.assert_called()

    # Test 'floatPos'
    val_float_pos = mwx.validator('floatPos')
    mocker.patch.object(val_float_pos, 'GetWindow', return_value=ctrl)
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = ord('.')
    val_float_pos.OnChar(evt)
    evt.Skip.assert_called()

    # Test Navigation Keys
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = wx.WXK_LEFT
    val.OnChar(evt)
    evt.Skip.assert_called()
    
    # Test Copy (Ctrl+C / Cmd+C)
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = 99
    evt.CmdDown.return_value = True
    val.OnChar(evt)
    evt.Skip.assert_called()

    # Test Paste (Ctrl+V / Cmd+V)
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = 118
    evt.CmdDown.return_value = True
    val.OnChar(evt)
    evt.Skip.assert_called()
    
    # Test illegal > 255
    evt.Skip.reset_mock()
    evt.GetKeyCode.return_value = 300
    val.OnChar(evt)
    assert not evt.Skip.called

    # Test Transfer
    assert val.TransferToWindow() == True
    assert val.TransferFromWindow() == True

def test_dlgMessage(mocker, mock_images, frame):
    dlg = mwx.dlgMessage(frame, "Title", "Message")
    assert dlg.title == "Title"
    assert dlg.message == "Message"

    evt = mocker.MagicMock(spec=wx.CommandEvent)
    evt.GetId.return_value = wx.ID_OK
    mock_end = mocker.patch.object(dlg, 'EndModal')
    dlg.onButton(evt)
    mock_end.assert_called_with(wx.ID_OK)

def test_layout(frame):
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel = wx.Panel(frame)
    panel.SetSizer(sizer)
    mwx.layout(panel, sizer)
    # Should not crash
