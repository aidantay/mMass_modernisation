import contextlib
import importlib

import pytest
import wx

from mmass.gui import config, images, panel_about


@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.onLibraryLink = mocker.Mock()
    yield parent
    parent.Destroy()


@pytest.fixture
def about_frame(wx_app, mock_parent, mocker):
    # Mocking images.lib to provide 'iconAbout' bitmap
    mocker.patch.dict(images.lib, {"iconAbout": wx.Bitmap(1, 1)})
    mocker.patch("wx.RESIZE_BOX", 0, create=True)
    frame_inst = panel_about.PanelAbout(mock_parent)
    yield frame_inst
    if frame_inst:
        with contextlib.suppress(RuntimeError):
            frame_inst.Destroy()


def test_initialization(about_frame):
    """Test that PanelAbout is initialized correctly."""
    assert isinstance(about_frame, panel_about.PanelAbout)


def test_frame_type_and_title(mocker):
    """Test platform-dependent frame type and title."""
    # We need to reload the module to see the effect of wx.Platform change
    # because these are defined at module level.

    mocker.patch("wx.Platform", "__WXMAC__")
    # Use top-level panel_about import

    importlib.reload(panel_about)
    assert panel_about.frame == wx.Frame
    assert panel_about.frameTitle == ""
    mocker.stopall()

    mocker.patch("wx.Platform", "__WXMSW__")
    # Use top-level panel_about import

    importlib.reload(panel_about)
    assert panel_about.frame == wx.Frame
    assert panel_about.frameTitle == "About mMass"
    mocker.stopall()

    # Reload again to restore original state for other tests
    importlib.reload(panel_about)


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
    mocker.patch("mmass.gui.config.nightbuild", False)
    mocker.patch("mmass.gui.config.version", "5.5.0")
    mocker.patch.dict(images.lib, {"iconAbout": wx.Bitmap(1, 1)})
    mocker.patch("wx.RESIZE_BOX", 0, create=True)
    frame_inst = panel_about.PanelAbout(mock_parent)
    panel = next(c for c in frame_inst.GetChildren() if isinstance(c, wx.Panel))
    texts = [c.GetLabel() for c in panel.GetChildren() if isinstance(c, wx.StaticText)]
    assert "Version 5.5.0" in texts
    frame_inst.Destroy()


def test_version_label_nightly(wx_app, mock_parent, mocker):
    """Test version label when nightbuild is set."""
    mocker.patch("mmass.gui.config.nightbuild", "20240101")
    mocker.patch("mmass.gui.config.version", "5.5.0")
    mocker.patch.dict(images.lib, {"iconAbout": wx.Bitmap(1, 1)})
    mocker.patch("wx.RESIZE_BOX", 0, create=True)
    frame_inst = panel_about.PanelAbout(mock_parent)
    panel = next(c for c in frame_inst.GetChildren() if isinstance(c, wx.Panel))
    texts = [c.GetLabel() for c in panel.GetChildren() if isinstance(c, wx.StaticText)]
    expected = "Version 5.5.0 (20240101)\nFor testing only!"
    assert expected in texts
    frame_inst.Destroy()


def test_button_events(about_frame, mock_parent):
    """Test that button clicks call parent.onLibraryLink."""
    panel = next(c for c in about_frame.GetChildren() if isinstance(c, wx.Panel))
    buttons = [c for c in panel.GetChildren() if isinstance(c, wx.Button)]

    for button in buttons:
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, button.GetId())
        button.GetEventHandler().ProcessEvent(event)
        assert mock_parent.onLibraryLink.called
        mock_parent.onLibraryLink.reset_mock()


def test_on_close(about_frame, mocker):
    """Test that onClose calls Destroy."""
    mock_destroy = mocker.patch.object(
        about_frame, "Destroy", wraps=about_frame.Destroy
    )
    about_frame.onClose(None)
    assert mock_destroy.called
