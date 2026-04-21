import pytest
import wx

from mmass.gui import config
from mmass.gui.dlg_preferences import dlgPreferences


@pytest.fixture
def mock_config(mocker):
    """Mock config.main dictionary."""
    default_config = {
        "updatesEnabled": 0,
        "compassMode": "Profile",
        "compassFormat": "mzXML",
        "compassDeleteFile": 0,
    }
    mocker.patch.dict(config.main, default_config, clear=True)
    return config.main


@pytest.fixture
def pref_dialog(wx_app, mock_config, mocker):
    """Fixture for dlgPreferences."""
    parent = wx.Frame(None)
    parent.onHelpUpdate = mocker.MagicMock()
    dialog = dlgPreferences(parent)
    yield dialog
    dialog.Destroy()
    parent.Destroy()


def test_initialization(pref_dialog):
    """Test dialog initialization and basic properties."""
    assert pref_dialog.GetTitle() == "Preferences"
    assert isinstance(pref_dialog.notebook, wx.Notebook)


def test_platform_specific_ui(wx_app, mock_config, mocker):
    """Test UI creation based on platform."""
    parent = wx.Frame(None)

    # Test Windows platform
    mocker.patch("wx.Platform", "__WXMSW__")
    dialog = dlgPreferences(parent)
    # Check if CompassXport page is added
    found = False
    for i in range(dialog.notebook.GetPageCount()):
        if dialog.notebook.GetPageText(i) == "CompassXport":
            found = True
            break
    assert found, "CompassXport page should be present on Windows"
    dialog.Destroy()

    # Test Non-Windows platform
    mocker.patch("wx.Platform", "__WXGTK__")
    dialog = dlgPreferences(parent)
    # Check if CompassXport page is NOT added
    found = False
    for i in range(dialog.notebook.GetPageCount()):
        if dialog.notebook.GetPageText(i) == "CompassXport":
            found = True
            break
    assert not found, "CompassXport page should NOT be present on non-Windows"
    dialog.Destroy()

    parent.Destroy()


def test_on_updates(pref_dialog, mock_config):
    """Test onUpdates event handler."""
    # Toggle checkbox
    pref_dialog.updatesEnabled_check.SetValue(True)

    # Manually call handler (simulating event)
    pref_dialog.onUpdates(None)

    assert mock_config["updatesEnabled"] == 1

    pref_dialog.updatesEnabled_check.SetValue(False)
    pref_dialog.onUpdates(None)
    assert mock_config["updatesEnabled"] == 0


def test_on_update_now(pref_dialog):
    """Test onUpdateNow event handler."""
    pref_dialog.onUpdateNow(None)
    pref_dialog.parent.onHelpUpdate.assert_called_once()


def test_on_compass(wx_app, mock_config, mocker):
    """Test onCompass event handler (Windows only)."""
    parent = wx.Frame(None)

    mocker.patch("wx.Platform", "__WXMSW__")
    dialog = dlgPreferences(parent)

    # Change values
    dialog.compassMode_choice.SetStringSelection("Line")
    dialog.compassFormat_choice.SetStringSelection("mzML")
    dialog.compassDeleteFile_check.SetValue(True)

    # Manually call handler
    dialog.onCompass(None)

    assert mock_config["compassMode"] == "Line"
    assert mock_config["compassFormat"] == "mzML"
    assert mock_config["compassDeleteFile"] == 1

    dialog.Destroy()
    parent.Destroy()
