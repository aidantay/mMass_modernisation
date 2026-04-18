import copy
import sys

import pytest
import wx

# Constants for GUI layout that might be needed early
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = 0
if not hasattr(wx, "MAXIMIZE_BOX"):
    wx.MAXIMIZE_BOX = 0


# Fixture to mock images, mwx and mspy.plot modules needed for importing panelSpectrumGenerator
@pytest.fixture(autouse=True)
def mock_dependencies(mocker):
    class MockImageLib:
        def __getitem__(self, key):
            if "cursor" in key.lower():
                return wx.Cursor(wx.CURSOR_ARROW)
            return wx.Bitmap(16, 16)

        def __contains__(self, key):
            return True

        def get(self, key, default=None):
            return self[key]

    mock_images = mocker.Mock()
    mock_images.lib = MockImageLib()

    mock_mwx = mocker.Mock()
    mock_mwx.TOOLBAR_HEIGHT = 36
    mock_mwx.CHOICE_HEIGHT = 25
    mock_mwx.SMALL_BUTTON_HEIGHT = 25
    mock_mwx.CONTROLBAR_HEIGHT = 25
    mock_mwx.CONTROLBAR_LSPACE = 5
    mock_mwx.CONTROLBAR_RSPACE = 5
    mock_mwx.GAUGE_SPACE = 5
    mock_mwx.TOOLBAR_TOOLSIZE = (22, 22)
    mock_mwx.PLOTCANVAS_STYLE_PANEL = 0
    mock_mwx.bgrPanel = lambda parent, id, bitmap, size: wx.Panel(parent, id, size=size)
    mock_mwx.validator = lambda name: wx.DefaultValidator
    mock_mwx.layout = lambda parent, sizer: None
    mock_mwx.gauge = lambda parent, id: wx.Gauge(parent, id)

    mock_plot = mocker.Mock()

    def mock_canvas_class(parent, *args, **kwargs):
        p = wx.Panel(parent, -1)
        p.setProperties = mocker.Mock()
        p.setCursorImage = mocker.Mock()
        p.setMFunction = mocker.Mock()
        p.setLMBFunction = mocker.Mock()
        p.draw = mocker.Mock()
        p.refresh = mocker.Mock()
        p.getCurrentXRange = mocker.Mock(return_value=(0, 1000))
        p.getCurrentYRange = mocker.Mock(return_value=(0, 1000))
        return p

    mock_plot.canvas = mock_canvas_class
    mock_container_inst = mocker.Mock()
    mock_container_inst.__len__ = mocker.Mock(return_value=0)
    mock_plot.container.return_value = mock_container_inst

    mock_mspy = mocker.Mock()
    mock_mspy.plot = mock_plot

    mocker.patch.dict(
        sys.modules,
        {
            "images": mock_images,
            "gui.images": mock_images,
            "mwx": mock_mwx,
            "gui.mwx": mock_mwx,
            "mspy": mock_mspy,
            "mspy.plot": mock_plot,
        },
    )
    yield


@pytest.fixture
def panel(wx_app, mocker):
    import gui.config as config
    from gui.panel_spectrum_generator import panelSpectrumGenerator

    config.spectrumGenerator.update(
        {
            "fwhm": 0.1,
            "points": 10,
            "noise": 0.1,
            "forceFwhm": False,
            "peakShape": "gaussian",
            "showPeaks": True,
            "showOverlay": False,
            "showFlipped": False,
        }
    )

    parent = wx.Frame(None)
    parent.updateTmpSpectrum = mocker.Mock()
    parent.onDocumentChanged = mocker.Mock()

    p = panelSpectrumGenerator(parent)
    yield p
    if p:
        p.Destroy()
    parent.Destroy()


class MockDocument:
    def __init__(self, mocker):
        self.spectrum = mocker.Mock()
        self.spectrum.peaklist = []
        self.spectrum._has_profile = False
        self.spectrum.hasprofile = lambda: self.spectrum._has_profile

        def setprofile(points):
            self.spectrum._has_profile = True

        self.spectrum.setprofile = setprofile
        self.backup = mocker.Mock()


@pytest.fixture(autouse=True)
def reset_config_dict():
    from gui import config

    orig_sg = copy.deepcopy(config.spectrumGenerator)
    orig_s = copy.deepcopy(config.spectrum)
    orig_m = copy.deepcopy(config.main)
    yield
    config.spectrumGenerator.clear()
    config.spectrumGenerator.update(orig_sg)
    config.spectrum.clear()
    config.spectrum.update(orig_s)
    config.main.clear()
    config.main.update(orig_m)


def test_init(panel):
    assert panel.GetTitle() == "Spectrum Generator"
    assert panel.processing is None


def test_onClose_idle(panel):
    panel.onClose(None)
    panel.parent.updateTmpSpectrum.assert_called_with(None)


def test_onClose_processing(panel, mocker):
    panel.processing = mocker.Mock()
    mock_bell = mocker.patch("wx.Bell")
    panel.onClose(None)
    mock_bell.assert_called_once()


def test_onStop_idle(panel, mocker):
    mock_bell = mocker.patch("wx.Bell")
    panel.onStop(None)
    mock_bell.assert_called_once()


def test_onStop_processing(panel, mocker):
    panel.processing = mocker.Mock()
    panel.processing.is_alive.return_value = True
    mock_stop = mocker.patch("mspy.stop")
    panel.onStop(None)
    mock_stop.assert_called_once()


def test_getParams_happy(panel, mocker):
    mocker.patch.object(panel.fwhm_value, "GetValue", return_value="0.5")
    mocker.patch.object(panel.points_value, "GetValue", return_value="20")
    mocker.patch.object(panel.noise_value, "GetValue", return_value="0.123")
    mocker.patch.object(panel.forceFwhm_check, "GetValue", return_value=True)
    mocker.patch.object(
        panel.peakShape_choice, "GetStringSelection", return_value="Symmetrical"
    )

    from gui import config

    assert panel.getParams() is True
    assert abs(config.spectrumGenerator["fwhm"] - 0.5) < 1e-6
    assert config.spectrumGenerator["points"] == 20
    assert abs(config.spectrumGenerator["noise"] - 0.123) < 1e-6
    assert config.spectrumGenerator["forceFwhm"] == True
    assert config.spectrumGenerator["peakShape"] == "gaussian"


def test_getParams_asymmetrical(panel, mocker):
    mocker.patch.object(
        panel.peakShape_choice, "GetStringSelection", return_value="Asymmetrical"
    )
    from gui import config

    assert panel.getParams() is True
    assert config.spectrumGenerator["peakShape"] == "gausslorentzian"


def test_onShowPeaks(panel, mocker):
    mocker.patch.object(panel, "updateSpectrumCanvas")
    mocker.patch.object(panel.showPeaks_check, "GetValue", return_value=True)
    from gui import config

    panel.onShowPeaks(None)
    assert config.spectrumGenerator["showPeaks"] == True


def test_onShowOverlay(panel, mocker):
    mocker.patch.object(panel, "updateSpectrumOverlay")
    mocker.patch.object(panel.showOverlay_check, "GetValue", return_value=True)
    from gui import config

    panel.onShowOverlay(None)
    assert config.spectrumGenerator["showOverlay"] == True


def test_onShowFlipped(panel, mocker):
    mocker.patch.object(panel, "updateSpectrumOverlay")
    mocker.patch.object(panel.showFlipped_check, "GetValue", return_value=True)
    from gui import config

    panel.onShowFlipped(None)
    assert config.spectrumGenerator["showFlipped"] == True


def test_onCollapse(panel):
    assert panel.mainSizer.IsShown(2)
    panel.onCollapse(None)
    assert not panel.mainSizer.IsShown(2)


def test_setData(panel, mocker):
    doc = MockDocument(mocker)
    panel.setData(doc)
    assert panel.currentDocument == doc
    panel.parent.updateTmpSpectrum.assert_called_with(None)


def test_onApply_happy_no_profile(panel, mocker):
    doc = MockDocument(mocker)
    panel.currentDocument = doc
    panel.currentProfile = [1, 2, 3]
    panel.onApply(None)
    doc.backup.assert_called_with("spectrum")
    assert doc.spectrum.hasprofile()


def test_onApply_with_profile_cancel(panel, mocker):
    doc = MockDocument(mocker)
    doc.spectrum._has_profile = True
    panel.currentDocument = doc
    panel.currentProfile = [1, 2, 3]
    mock_dlg = mocker.patch("mwx.dlgMessage")
    mock_dlg_inst = mock_dlg.return_value
    mock_dlg_inst.ShowModal.return_value = wx.ID_CANCEL
    panel.onApply(None)
    doc.backup.assert_not_called()


def test_updateSpectrumOverlay(panel, mocker):
    from gui import config

    panel.currentProfile = [1, 2, 3]
    config.spectrumGenerator["showOverlay"] = True
    config.spectrumGenerator["showFlipped"] = False
    panel.updateSpectrumOverlay()
    panel.parent.updateTmpSpectrum.assert_called_with([1, 2, 3], flipped=False)


def test_runSpectrumGenerator_gaussian(panel, mocker):
    from gui import config

    doc = MockDocument(mocker)
    peak = mocker.Mock()
    peak.mz = 100.0
    peak.base = 0.0
    peak.ai = 1000.0
    peak.fwhm = 0.5
    doc.spectrum.peaklist = [peak]
    panel.currentDocument = doc

    config.spectrumGenerator["peakShape"] = "gaussian"
    config.spectrumGenerator["forceFwhm"] = False

    mock_profile = mocker.patch("mspy.profile", return_value=[1, 2, 3])
    mock_gaussian = mocker.patch("mspy.gaussian", return_value=[4, 5, 6])
    panel.runSpectrumGenerator()
    mock_gaussian.assert_called_once()


def test_runSpectrumGenerator_lorentzian(panel, mocker):
    from gui import config

    doc = MockDocument(mocker)
    peak = mocker.Mock()
    peak.mz = 100.0
    peak.base = 0.0
    peak.ai = 1000.0
    peak.fwhm = 0.5
    doc.spectrum.peaklist = [peak]
    panel.currentDocument = doc

    config.spectrumGenerator["peakShape"] = "lorentzian"
    config.spectrumGenerator["forceFwhm"] = True
    config.spectrumGenerator["fwhm"] = 0.1

    mocker.patch("mspy.profile")
    mock_lorentzian = mocker.patch("mspy.lorentzian")
    panel.runSpectrumGenerator()
    mock_lorentzian.assert_called_with(x=100.0, minY=0.0, maxY=1000.0, fwhm=0.1)


def test_onGenerate_happy(panel, mocker):
    doc = MockDocument(mocker)
    doc.spectrum.peaklist = [[100.0, 1000.0]]
    panel.currentDocument = doc

    mocker.patch.object(panel, "getParams", return_value=True)
    mocker.patch.object(panel, "onProcessing")
    mock_thread = mocker.patch("threading.Thread")

    mock_thread_inst = mock_thread.return_value
    mock_thread_inst.is_alive.return_value = False
    panel.onGenerate(None)
    mock_thread_inst.start.assert_called_once()


def test_onProcessing(panel, mocker):
    mock_disabler = mocker.patch("wx.WindowDisabler")
    mock_show = mocker.patch.object(panel.mainSizer, "Show")
    mock_hide = mocker.patch.object(panel.mainSizer, "Hide")

    panel.onProcessing(True)
    mock_disabler.assert_called_with(panel)
    assert hasattr(panel, "_disabler")

    panel.onProcessing(False)
    assert not hasattr(panel, "_disabler")
