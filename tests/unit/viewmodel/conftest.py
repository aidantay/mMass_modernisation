import pytest
import wx


@pytest.fixture(scope="session", autouse=True)
def wx_app():
    """Session-scoped fixture to provide a wx.App instance for tests."""
    app = wx.App(False)
    return app


@pytest.fixture(autouse=True)
def mock_wx_yield(mocker):
    """Globally mock wx.Yield to prevent crashes and hangs in headless test environments."""
    return mocker.patch("wx.Yield", return_value=True)
