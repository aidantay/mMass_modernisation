import pytest
import wx


@pytest.fixture(autouse=True)
def mock_gui_deps(mocker):
    """Mock images.lib and config.version for all tests in this module."""
    # Create a dummy bitmap for the icon
    bmp = wx.Bitmap(16, 16)

    # Patch images.lib in the dlg_error module
    # Note: we patch where it's USED
    mocker.patch("gui.dlg_error.images.lib", {"iconError": bmp})

    # Patch config.version in the dlg_error module
    mocker.patch("gui.dlg_error.config.version", "5.0.0")


def test_dlg_error_initialization(wx_app):
    """Test initialization with different exception strings."""
    from gui.dlg_error import dlgError

    # Test with normal exception
    dlg = dlgError(None, "Test Exception")
    try:
        assert "Test Exception" in dlg.exception
        assert "mMass: 5.0.0" in dlg.exception
        assert "-------------------------" in dlg.exception
        assert "Python:" in dlg.exception
        assert "wxPython:" in dlg.exception
    finally:
        dlg.Destroy()

    # Test with empty exception
    dlg = dlgError(None, "")
    try:
        assert "-------------------------" in dlg.exception
        assert "mMass: 5.0.0" in dlg.exception
    finally:
        dlg.Destroy()


def test_dlg_error_ui_elements(wx_app):
    """Test presence and properties of UI elements."""
    from gui.dlg_error import dlgError

    dlg = dlgError(None, "Test UI")
    try:
        # Check text control
        assert hasattr(dlg, "exception_value")
        assert isinstance(dlg.exception_value, wx.TextCtrl)
        assert dlg.exception_value.GetValue() == dlg.exception

        # Check labels and buttons (using children)
        children = dlg.GetChildren()

        # Find the buttons
        quit_butt = None
        cancel_butt = None
        message_label = None
        icon_bitmap = None

        for child in children:
            if isinstance(child, wx.Button):
                if child.GetLabel() == "Quit mMass":
                    quit_butt = child
                elif child.GetId() == wx.ID_CANCEL:
                    cancel_butt = child
            elif isinstance(child, wx.StaticText):
                if "Uups, another one..." in child.GetLabel():
                    message_label = child
            elif isinstance(child, wx.StaticBitmap):
                icon_bitmap = child

        assert quit_butt is not None
        assert cancel_butt is not None
        assert cancel_butt.GetLabel() == "Try to Continue"
        assert message_label is not None
        assert icon_bitmap is not None

        # Check font
        assert message_label.GetFont().GetPointSize() <= wx.SMALL_FONT.GetPointSize()

    finally:
        dlg.Destroy()


def test_dlg_error_on_quit(wx_app, mocker):
    """Test the onQuit event handler."""
    from gui.dlg_error import dlgError

    # We must patch sys.exit in the module where it is used
    mock_exit = mocker.patch("gui.dlg_error.sys.exit")

    dlg = dlgError(None, "Test Quit")
    try:
        # Directly call onQuit
        dlg.onQuit(None)
        mock_exit.assert_called_once()

        # Reset mock and try via button event
        mock_exit.reset_mock()

        # Find quit button
        quit_butt = None
        for child in dlg.GetChildren():
            if isinstance(child, wx.Button) and child.GetLabel() == "Quit mMass":
                quit_butt = child
                break

        assert quit_butt is not None

        # Simulate button click
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, quit_butt.GetId())
        event.SetEventObject(quit_butt)
        quit_butt.GetEventHandler().ProcessEvent(event)

        mock_exit.assert_called_once()
    finally:
        dlg.Destroy()


def test_dlg_error_layout(wx_app):
    """Test if layout methods are called during initialization."""
    from gui.dlg_error import dlgError

    dlg = dlgError(None, "Test Layout")
    try:
        assert dlg.GetSizer() is not None
        assert dlg.GetMinSize().GetWidth() > 0
        assert dlg.GetMinSize().GetHeight() > 0
    finally:
        dlg.Destroy()
