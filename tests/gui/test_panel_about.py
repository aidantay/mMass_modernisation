import pytest
import wx
import gui.panel_about
from gui.ids import ID_helpHomepage, ID_helpDonate, ID_helpCite
import gui.config as config
import gui.images as images

@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.onLibraryLink = mocker.Mock()
    yield parent
    parent.Destroy()

@pytest.fixture
def about_frame(wx_app, mock_parent, mocker):
    # Mocking images.lib to provide 'iconAbout' bitmap
    mocker.patch.dict(images.lib, {'iconAbout': wx.Bitmap(1, 1)})
    mocker.patch('wx.RESIZE_BOX', 0, create=True)
    frame_inst = gui.panel_about.panelAbout(mock_parent)
    yield frame_inst
    if frame_inst:
        try:
            frame_inst.Destroy()
        except wx.PyDeadObjectError:
            pass

def test_initialization(about_frame):
    """Test that panelAbout is initialized correctly."""
    assert isinstance(about_frame, gui.panel_about.panelAbout)

def test_frame_type_and_title(mocker):
    """Test platform-dependent frame type and title."""
    # We need to reload the module to see the effect of wx.Platform change
    # because these are defined at module level.

    mocker.patch('wx.Platform', '__WXMAC__')
    import gui.panel_about as pa
    reload(pa)
    assert pa.frame == wx.Frame
    assert pa.frameTitle == ''
    mocker.stopall()

    mocker.patch('wx.Platform', '__WXMSW__')
    import gui.panel_about as pa
    reload(pa)
    assert pa.frame == wx.MiniFrame
    assert pa.frameTitle == 'About mMass'
    mocker.stopall()

    # Reload again to restore original state for other tests
    reload(gui.panel_about)

def test_gui_elements_exist(about_frame):
    """Verify that all expected GUI elements are created."""
    panel = None
    for child in about_frame.GetChildren():
        if isinstance(child, wx.Panel):
            panel = child
            break
    
    assert panel is not None
    
    children = panel.GetChildren()
    
    # Check for StaticBitmap
    bitmaps = [c for c in children if isinstance(c, wx.StaticBitmap)]
    assert len(bitmaps) == 1
    
    # Check for StaticTexts
    texts = [c for c in children if isinstance(c, wx.StaticText)]
    # Title, Version, Copyright
    assert len(texts) >= 3
    
    labels = [t.GetLabel() for t in texts]
    assert "mMass" in labels
    assert "(c) 2005-2013 Martin Strohalm" in labels
    
    # Check for Buttons
    buttons = [c for c in children if isinstance(c, wx.Button)]
    assert len(buttons) == 3
    
    button_labels = [b.GetLabel() for b in buttons]
    assert "Homepage" in button_labels
    assert "Make a Donation" in button_labels
    assert "How to Cite" in button_labels

def test_version_label_regular(wx_app, mock_parent, mocker):
    """Test version label when nightbuild is False."""
    mocker.patch('gui.config.nightbuild', False)
    mocker.patch('gui.config.version', '5.5.0')
    mocker.patch.dict(images.lib, {'iconAbout': wx.Bitmap(1, 1)})
    mocker.patch('wx.RESIZE_BOX', 0, create=True)
    frame_inst = gui.panel_about.panelAbout(mock_parent)
    panel = [c for c in frame_inst.GetChildren() if isinstance(c, wx.Panel)][0]
    texts = [c.GetLabel() for c in panel.GetChildren() if isinstance(c, wx.StaticText)]
    assert 'Version 5.5.0' in texts
    frame_inst.Destroy()

def test_version_label_nightly(wx_app, mock_parent, mocker):
    """Test version label when nightbuild is set."""
    mocker.patch('gui.config.nightbuild', '20240101')
    mocker.patch('gui.config.version', '5.5.0')
    mocker.patch.dict(images.lib, {'iconAbout': wx.Bitmap(1, 1)})
    mocker.patch('wx.RESIZE_BOX', 0, create=True)
    frame_inst = gui.panel_about.panelAbout(mock_parent)
    panel = [c for c in frame_inst.GetChildren() if isinstance(c, wx.Panel)][0]
    texts = [c.GetLabel() for c in panel.GetChildren() if isinstance(c, wx.StaticText)]
    expected = 'Version 5.5.0 (20240101)\nFor testing only!'
    assert expected in texts
    frame_inst.Destroy()

def test_button_events(about_frame, mock_parent):
    """Test that button clicks call parent.onLibraryLink."""
    panel = [c for c in about_frame.GetChildren() if isinstance(c, wx.Panel)][0]
    buttons = [c for c in panel.GetChildren() if isinstance(c, wx.Button)]
    
    for button in buttons:
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
        button.GetEventHandler().ProcessEvent(event)
        assert mock_parent.onLibraryLink.called
        mock_parent.onLibraryLink.reset_mock()

def test_on_close(about_frame, mocker):
    """Test that onClose calls Destroy."""
    mock_destroy = mocker.patch.object(about_frame, 'Destroy', wraps=about_frame.Destroy)
    about_frame.onClose(None)
    assert mock_destroy.called
