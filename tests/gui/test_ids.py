import pytest
import wx
import gui.ids
from importlib import reload

def test_ids_defined(wx_app):
    """
    Verify that expected IDs are defined as integers or wx.WindowID.
    """
    # Check common IDs
    assert isinstance(gui.ids.ID_quit, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_about, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_preferences, (int, wx.WindowIDRef))
    
    # Check some generated IDs
    assert isinstance(gui.ids.ID_documentNew, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_viewGrid, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_processingUndo, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_sequenceNew, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_toolsProcessing, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_libraryCompounds, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_linksBiomedMSTools, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_windowMaximize, (int, wx.WindowIDRef))
    assert isinstance(gui.ids.ID_helpAbout, (int, wx.WindowIDRef))

def test_hotkeys_defined():
    """
    Verify that expected hotkeys are defined as strings.
    """
    assert isinstance(gui.ids.HK_quit, str)
    assert gui.ids.HK_quit.startswith('\t')
    
    assert isinstance(gui.ids.HK_documentNew, str)
    assert gui.ids.HK_documentNew.startswith('\t')
    
    assert isinstance(gui.ids.HK_viewPosBars, str)
    assert gui.ids.HK_viewPosBars.startswith('\t')
    
    assert isinstance(gui.ids.HK_processingUndo, str)
    assert gui.ids.HK_processingUndo.startswith('\t')
    
    assert isinstance(gui.ids.HK_toolsCalibration, str)
    assert gui.ids.HK_toolsCalibration.startswith('\t')
    
    assert isinstance(gui.ids.HK_windowLayout1, str)
    assert gui.ids.HK_windowLayout1.startswith('\t')
    
    assert isinstance(gui.ids.HK_helpUserGuide, str)
    assert gui.ids.HK_helpUserGuide.startswith('\t')

def test_hk_preferences_platform_logic(monkeypatch):
    """
    Verify HK_preferences logic based on platform.
    """
    # Test for __WXMAC__
    monkeypatch.setattr(wx, 'Platform', '__WXMAC__')
    reload(gui.ids)
    assert gui.ids.HK_preferences == '\tCtrl+,'
    
    # Test for other platforms (e.g., __WXMSW__)
    monkeypatch.setattr(wx, 'Platform', '__WXMSW__')
    reload(gui.ids)
    assert gui.ids.HK_preferences == ''
    
    # Cleanup: restore to actual platform and reload
    monkeypatch.undo()
    reload(gui.ids)
