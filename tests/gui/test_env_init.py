import wx


def test_wx_app_fixture(wx_app):
    """
    Test that the wx_app fixture provides a valid wx.App instance.
    """
    # The fixture is passed by name, and should be active
    app = wx.GetApp()
    assert app is not None
    assert isinstance(app, wx.App)
    # The fixture itself should be the app
    assert wx_app is app
