import pytest
import wx

from mmass.gui import images

# Monkeypatch wx for missing constants in wxPython 4
if not hasattr(wx, "RESIZE_BOX"):
    wx.RESIZE_BOX = 0

import contextlib

from mmass.gui import panel_periodic_table
from mmass.mspy import blocks


@pytest.fixture
def mock_parent(wx_app, mocker):
    parent = wx.Frame(None)
    parent.onToolsMassCalculator = mocker.Mock()
    yield parent
    if parent:
        parent.Destroy()


@pytest.fixture
def periodic_table(wx_app, mocker, mock_parent):
    # Mock images.lib to avoid loading real images

    mocker.patch.dict(images.lib, {}, clear=True)
    # We need to fill it with something that can be used as a bitmap
    dummy_bitmap = wx.Bitmap(10, 10)

    # Get elements from PanelPeriodicTable to know which images to mock
    elements = [
        "H",
        "He",
        "Li",
        "Be",
        "B",
        "C",
        "N",
        "O",
        "F",
        "Ne",
        "Na",
        "Mg",
        "Al",
        "Si",
        "P",
        "S",
        "Cl",
        "Ar",
        "K",
        "Ca",
        "Sc",
        "Ti",
        "V",
        "Cr",
        "Mn",
        "Fe",
        "Co",
        "Ni",
        "Cu",
        "Zn",
        "Ga",
        "Ge",
        "As",
        "Se",
        "Br",
        "Kr",
        "Rb",
        "Sr",
        "Y",
        "Zr",
        "Nb",
        "Mo",
        "Tc",
        "Ru",
        "Rh",
        "Pd",
        "Ag",
        "Cd",
        "In",
        "Sn",
        "Sb",
        "Te",
        "I",
        "Xe",
        "Cs",
        "Ba",
        "La",
        "Hf",
        "Ta",
        "W",
        "Re",
        "Os",
        "Ir",
        "Pt",
        "Au",
        "Hg",
        "Tl",
        "Pb",
        "Bi",
        "Po",
        "At",
        "Rn",
        "Fr",
        "Ra",
        "Ac",
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
        "Th",
        "Pa",
        "U",
        "Np",
        "Pu",
        "Am",
        "Cm",
        "Bk",
        "Cf",
        "Es",
        "Fm",
        "Md",
        "No",
        "Lr",
    ]

    for el in elements:
        images.lib["periodicTable" + el + "Off"] = dummy_bitmap
        images.lib["periodicTable" + el + "On"] = dummy_bitmap
        images.lib["periodicTable" + el + "Sel"] = dummy_bitmap

    images.lib["periodicTableConnection"] = dummy_bitmap
    images.lib["bgrToolbar"] = dummy_bitmap

    panel = panel_periodic_table.PanelPeriodicTable(mock_parent)
    yield panel
    if panel:
        with contextlib.suppress(BaseException):
            panel.Destroy()


def test_init(periodic_table):
    assert periodic_table.currentElement is None
    assert periodic_table.currentGroup is None
    assert periodic_table.highlight_choice.GetSelection() == 0
    assert periodic_table.isotopes_butt.IsEnabled() is False
    assert periodic_table.photos_butt.IsEnabled() is False


def test_on_close(periodic_table, mocker):
    mocked_destroy = mocker.patch.object(periodic_table, "Destroy")
    periodic_table.onClose(None)
    mocked_destroy.assert_called_once()


def test_on_highlight_group(periodic_table, mocker):
    # Test valid group
    periodic_table.highlight_choice.SetStringSelection("Alkali Metals")
    periodic_table.onHighlightGroup()
    assert periodic_table.currentGroup == "Alkali Metals"

    # Check if buttons are updated
    mocked_set_bitmap = mocker.patch.object(wx.BitmapButton, "SetBitmapLabel")
    periodic_table.onHighlightGroup()
    assert mocked_set_bitmap.called

    # Test 'None'
    periodic_table.highlight_choice.SetStringSelection("None")
    periodic_table.onHighlightGroup()
    assert periodic_table.currentGroup is None

    # Test invalid group
    periodic_table.highlight_choice.SetStringSelection("---")
    periodic_table.onHighlightGroup()
    assert periodic_table.currentGroup is None
    assert periodic_table.highlight_choice.GetStringSelection() == "None"


def test_on_element_selected(periodic_table, mocker):
    # Test None event
    periodic_table.onElementSelected(None)
    assert periodic_table.currentElement is None
    assert periodic_table.elementName.GetLabel() == ""
    assert periodic_table.elementMass.GetLabel() == ""
    assert periodic_table.isotopes_butt.IsEnabled() is False
    assert periodic_table.photos_butt.IsEnabled() is False

    # Test valid element selection
    button_id = None
    for bid, el in list(periodic_table.elementsIDs.items()):
        if el == "C":
            button_id = bid
            break

    assert button_id is not None

    mock_event = mocker.Mock()
    mock_event.GetId.return_value = button_id

    # Ensure blocks.elements has data
    if "C" not in blocks.elements:
        blocks.elements["C"] = mocker.Mock()
        blocks.elements["C"].name = "Carbon"
        blocks.elements["C"].atomicNumber = 6
        blocks.elements["C"].mass = (12.0, 12.011)

    periodic_table.onElementSelected(mock_event)
    assert periodic_table.currentElement == "C"
    assert "Carbon" in periodic_table.elementName.GetLabel()
    assert "C" in periodic_table.elementName.GetLabel()
    assert "6" in periodic_table.elementName.GetLabel()
    assert "12.0" in periodic_table.elementMass.GetLabel()
    assert periodic_table.isotopes_butt.IsEnabled() is True
    assert periodic_table.photos_butt.IsEnabled() is True


def test_on_isotopes(periodic_table, mock_parent, mocker):
    # Without selection
    periodic_table.currentElement = None
    mocked_bell = mocker.patch("wx.Bell")
    periodic_table.onIsotopes()
    mocked_bell.assert_called_once()
    mock_parent.onToolsMassCalculator.assert_not_called()

    # With selection
    periodic_table.currentElement = "C"
    periodic_table.onIsotopes()
    mock_parent.onToolsMassCalculator.assert_called_with(formula="C")


def test_on_wiki(periodic_table, mocker):
    mocked_open = mocker.patch("webbrowser.open")
    # With element
    periodic_table.currentElement = "C"
    if "C" not in blocks.elements:
        blocks.elements["C"] = mocker.Mock()
        blocks.elements["C"].name = "Carbon"
    periodic_table.onWiki(None)
    mocked_open.assert_called_with("http://en.wikipedia.org/wiki/Carbon", autoraise=1)

    # Without element, with group
    periodic_table.currentElement = None
    periodic_table.currentGroup = "Alkali Metals"
    periodic_table.onWiki(None)
    mocked_open.assert_called_with(
        "http://en.wikipedia.org/wiki/Alkali_metal", autoraise=1
    )

    # Without element, without group
    periodic_table.currentGroup = None
    periodic_table.onWiki(None)
    mocked_open.assert_called_with(
        "http://en.wikipedia.org/wiki/Periodic_table", autoraise=1
    )

    # Test exception handling
    mocked_open.side_effect = Exception("Browser error")
    periodic_table.onWiki(None)


def test_on_photos(periodic_table, mocker):
    mocked_open = mocker.patch("webbrowser.open")
    mocked_bell = mocker.patch("wx.Bell")
    # With element
    periodic_table.currentElement = "C"
    if "C" not in blocks.elements:
        blocks.elements["C"] = mocker.Mock()
        blocks.elements["C"].atomicNumber = 6
    periodic_table.onPhotos(None)
    mocked_open.assert_called_with(
        "http://www.periodictable.com/Elements/006/index.html", autoraise=1
    )

    # Without element
    periodic_table.currentElement = None
    periodic_table.onPhotos(None)
    mocked_bell.assert_called_once()

    # Test exception handling
    periodic_table.currentElement = "C"
    mocked_open.side_effect = Exception("Browser error")
    periodic_table.onPhotos(None)


def test_on_element_selected_complex(periodic_table, mocker):
    # Setup: select an element first
    bid_c = None
    bid_h = None
    for bid, el in list(periodic_table.elementsIDs.items()):
        if el == "C":
            bid_c = bid
        if el == "H":
            bid_h = bid

    if "C" not in blocks.elements:
        blocks.elements["C"] = mocker.Mock(
            name="Carbon", atomicNumber=6, mass=(12.0, 12.011)
        )
    if "H" not in blocks.elements:
        blocks.elements["H"] = mocker.Mock(
            name="Hydrogen", atomicNumber=1, mass=(1.0, 1.008)
        )

    mock_event_c = mocker.Mock()
    mock_event_c.GetId.return_value = bid_c
    periodic_table.onElementSelected(mock_event_c)
    assert periodic_table.currentElement == "C"

    # Now set a group manually to avoid clearing currentElement
    periodic_table.currentGroup = "Nonmetals"

    mock_event_h = mocker.Mock()
    mock_event_h.GetId.return_value = bid_h

    # 'C' is in 'Nonmetals', so line 225 should be hit when selecting 'H'
    periodic_table.onElementSelected(mock_event_h)
    assert periodic_table.currentElement == "H"

    # Select again without group
    periodic_table.currentGroup = None
    periodic_table.onElementSelected(mock_event_c)
    assert periodic_table.currentElement == "C"


def test_on_wiki_empty_link(periodic_table, mocker):
    mocked_open = mocker.patch("webbrowser.open")
    periodic_table.currentElement = None
    periodic_table.currentGroup = "Other Nonmetals"
    # 'Other Nonmetals' maps to empty string, so link is the base wiki URL
    periodic_table.onWiki(None)
    mocked_open.assert_called_with("http://en.wikipedia.org/wiki/", autoraise=1)


def test_on_element_selected_clear(periodic_table, mocker):
    # Select then clear
    bid_c = None
    for bid, el in list(periodic_table.elementsIDs.items()):
        if el == "C":
            bid_c = bid
            break

    if "C" not in blocks.elements:
        blocks.elements["C"] = mocker.Mock(
            name="Carbon", atomicNumber=6, mass=(12.0, 12.011)
        )

    mock_event = mocker.Mock()
    mock_event.GetId.return_value = bid_c
    periodic_table.onElementSelected(mock_event)
    assert periodic_table.currentElement == "C"

    # Clear
    periodic_table.onElementSelected(None)
    assert periodic_table.currentElement is None
