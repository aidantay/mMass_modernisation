import pytest
import wx


@pytest.fixture(scope="session")
def wx_app():
    """
    Session-scoped fixture to provide a wx.App instance for GUI tests.
    """
    app = wx.App(False)

    # Initialize images
    from gui import images

    try:
        # Patch wx.Image.SetOptionInt if it's missing (happens in some wx versions)
        if not hasattr(wx.Image, "SetOptionInt"):
            wx.Image.SetOptionInt = lambda self, name, value: self.SetOption(
                name, str(value)
            )
        images.loadImages()
    except Exception:
        # Fallback: populate images.lib with dummy bitmaps so tests don't fail on KeyError
        dummy_bitmap = wx.Bitmap(16, 16)
        keys = [
            "bulletsDocument",
            "bulletsAnnotationsOn",
            "bulletsAnnotationsOff",
            "bulletsSequenceOn",
            "bulletsSequenceOff",
            "bulletsNotationOn",
            "bulletsNotationOff",
            "documentsAdd",
            "documentsDelete",
            "bgrBottombar",
        ]
        for key in keys:
            if key not in images.lib:
                images.lib[key] = dummy_bitmap

    yield app
    # wx.App objects are cleaned up by the Python garbage collector
    # and don't typically require explicit termination in unit tests.


@pytest.fixture(autouse=True)
def mock_wx_yield(mocker):
    """
    Globally mock wx.Yield to prevent crashes and hangs in headless test environments.
    """
    return mocker.patch("wx.Yield", return_value=True)
