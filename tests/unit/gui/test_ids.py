import wx

from mmass.gui import ids


def test_ids_defined(wx_app):
    """Verify that expected IDs are defined as integers or wx.WindowID."""
    # Check common IDs
    assert isinstance(ids.ID_quit, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_about, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_preferences, (int, wx.WindowIDRef))

    # Check some generated IDs
    assert isinstance(ids.ID_documentNew, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_viewGrid, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_processingUndo, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_sequenceNew, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_toolsProcessing, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_libraryCompounds, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_linksBiomedMSTools, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_windowMaximize, (int, wx.WindowIDRef))
    assert isinstance(ids.ID_helpAbout, (int, wx.WindowIDRef))


def test_hotkeys_defined():
    """Verify that expected hotkeys are defined as strings."""
    assert isinstance(ids.HK_quit, str)
    assert ids.HK_quit.startswith("\t")

    assert isinstance(ids.HK_documentNew, str)
    assert ids.HK_documentNew.startswith("\t")

    assert isinstance(ids.HK_viewPosBars, str)
    assert ids.HK_viewPosBars.startswith("\t")

    assert isinstance(ids.HK_processingUndo, str)
    assert ids.HK_processingUndo.startswith("\t")

    assert isinstance(ids.HK_toolsCalibration, str)
    assert ids.HK_toolsCalibration.startswith("\t")

    assert isinstance(ids.HK_windowLayout1, str)
    assert ids.HK_windowLayout1.startswith("\t")

    assert isinstance(ids.HK_helpUserGuide, str)
    assert ids.HK_helpUserGuide.startswith("\t")


def test_hk_preferences_platform_logic(monkeypatch):
    """Verify HK_preferences logic based on platform.

    This test is informative and doesn't reload the module to avoid side effects.
    """
    if wx.Platform == "__WXMAC__":
        assert ids.HK_preferences == "\tCtrl+,"
    else:
        assert ids.HK_preferences == ""
