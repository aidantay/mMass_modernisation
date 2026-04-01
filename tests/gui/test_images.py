import pytest
import wx
import sys
import os
from gui import images

# wxPython 4 (Phoenix) removed SetOptionInt in favor of SetOption
if not hasattr(wx.Image, 'SetOptionInt'):
    wx.Image.SetOptionInt = lambda self, *args, **kwargs: self.SetOption(*args, **kwargs)

@pytest.fixture
def clean_images_lib():
    """Fixture to clear images.lib before and after tests."""
    images.lib = {}
    yield
    images.lib = {}

def test_loadImages_gtk(wx_app, clean_images_lib, mocker):
    """Test loadImages on GTK (default) platform."""
    mocker.patch('wx.Platform', '__WXGTK__')
    mock_lib = mocker.Mock()
    # Mocking sys.modules to intercept the import inside loadImages
    mocker.patch.dict('sys.modules', {'images_lib_gtk': mock_lib})
    _setup_mock_lib(mock_lib)
    
    images.loadImages()
    
    assert 'icon16' in images.lib
    assert 'toolsOpen' in images.lib
    assert 'toolsSave' in images.lib
    assert 'periodicTableHOn' in images.lib
    assert isinstance(images.lib['cursorsArrow'], wx.Cursor)
    assert isinstance(images.lib['arrowsUp'], wx.Bitmap)

def test_loadImages_mac(wx_app, clean_images_lib, mocker):
    """Test loadImages on Mac platform."""
    mocker.patch('wx.Platform', '__WXMAC__')
    mock_lib = mocker.Mock()
    mocker.patch.dict('sys.modules', {'images_lib_mac': mock_lib})
    _setup_mock_lib(mock_lib)
    
    images.loadImages()
    
    assert 'icon16' in images.lib
    assert 'toolsProcessing' in images.lib
    assert 'toolsOpen' not in images.lib  # Mac doesn't have toolsOpen
    assert 'toolsPresets' in images.lib
    assert isinstance(images.lib['cursorsArrow'], wx.Cursor)

def test_loadImages_msw(wx_app, clean_images_lib, mocker):
    """Test loadImages on MSW platform."""
    mocker.patch('wx.Platform', '__WXMSW__')
    mock_lib = mocker.Mock()
    mocker.patch.dict('sys.modules', {'images_lib_msw': mock_lib})
    _setup_mock_lib(mock_lib)
    
    images.loadImages()
    
    assert 'icon16' in images.lib
    assert 'toolsOpen' in images.lib
    assert isinstance(images.lib['cursorsArrow'], wx.Cursor)

def test_convertImages(mocker):
    """Test convertImages function."""
    mock_img2py = mocker.patch('gui.images.img2py.main')
    # Mock 'file' which is built-in in Python 2
    mock_file = mocker.patch('__builtin__.file', mocker.mock_open())
    images.convertImages()
    
    # Check if it tried to create files for all platforms
    assert mock_file.call_count >= 3
    # Check if img2py.main was called many times
    assert mock_img2py.call_count > 0
    
    # Verify one of the calls to img2py.main
    args, _ = mock_img2py.call_args
    assert isinstance(args[0], list)

def _setup_mock_lib(mock_lib):
    """Helper to setup mock platform library."""
    # Icons
    mock_lib.getIcon16Icon.return_value = wx.Icon()
    mock_lib.getIcon32Icon.return_value = wx.Icon()
    mock_lib.getIcon48Icon.return_value = wx.Icon()
    mock_lib.getIcon128Icon.return_value = wx.Icon()
    mock_lib.getIcon256Icon.return_value = wx.Icon()
    mock_lib.getIcon512Icon.return_value = wx.Icon()
    
    # Bitmaps
    mock_lib.getIconAboutBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getIconErrorBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getIconDlgBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getStopperBitmap.return_value = wx.Bitmap(10, 10)
    
    # Cursors sheet
    mock_cursors = wx.Bitmap(200, 200)
    mock_lib.getCursorsBitmap.return_value = mock_cursors
    
    # Arrows sheet
    mock_arrows = wx.Bitmap(200, 200)
    mock_lib.getArrowsBitmap.return_value = mock_arrows
    
    # Backgrounds
    mock_lib.getBgrToolbarBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrToolbarNoBorderBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrControlbarBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrControlbarBorderBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrControlbarDoubleBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrBottombarBitmap.return_value = wx.Bitmap(10, 10)
    mock_lib.getBgrPeakEditorBitmap.return_value = wx.Bitmap(10, 10)
    
    # Bullets
    mock_lib.getBulletsOnBitmap.return_value = wx.Bitmap(200, 200)
    mock_lib.getBulletsOffBitmap.return_value = wx.Bitmap(200, 200)
    
    # Tools
    mock_lib.getToolsBitmap.return_value = wx.Bitmap(1000, 1000)
    
    # Bottombars
    mock_lib.getBottombarsOnBitmap.return_value = wx.Bitmap(1000, 1000)
    mock_lib.getBottombarsOffBitmap.return_value = wx.Bitmap(1000, 1000)
    
    # Toolbars
    mock_lib.getToolbarsOnBitmap.return_value = wx.Bitmap(1000, 1000)
    mock_lib.getToolbarsOffBitmap.return_value = wx.Bitmap(1000, 1000)
    
    # Periodic Table
    mock_lib.getPtableOnBitmap.return_value = wx.Bitmap(1000, 1000)
    mock_lib.getPtableOffBitmap.return_value = wx.Bitmap(1000, 1000)
    mock_lib.getPtableSelBitmap.return_value = wx.Bitmap(1000, 1000)
