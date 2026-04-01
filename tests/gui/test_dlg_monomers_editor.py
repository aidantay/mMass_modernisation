import pytest
import wx
import re
import gui.dlg_monomers_editor as dlg_editor
import mspy
import gui.mwx as mwx
import gui.config as config

class MockMonomer(object):
    def __init__(self, abbr, formula, losses=None, name='', category=''):
        if formula == "Invalid":
            raise ValueError("Invalid formula")
        self.abbr = abbr
        self.name = name
        self.formula = formula
        self.losses = losses or []
        self.category = category
        self.mass = (100.0, 100.1)

class MockCompound(object):
    def __init__(self, formula):
        if formula == "Invalid":
            raise ValueError("Invalid formula")
        self.formula = formula
    def mass(self):
        if self.formula == "H2O":
            return (18.01056, 18.01528)
        elif self.formula == "CH4":
            return (16.0313, 16.0425)
        return (0.0, 0.0)

@pytest.fixture
def mock_mspy(mocker):
    """Mock mspy.monomers dictionary and mspy classes."""
    initial_monomers = {
        'Gly': MockMonomer('Gly', 'C2H3NO', [], name='Glycine', category='_InternalAA'),
        'TestMon': MockMonomer('TestMon', 'H2O', [], name='Test Monomer', category='Test'),
        'UsedMon': MockMonomer('UsedMon', 'CH4', [], name='Used Monomer', category='Used')
    }
    mocker.patch('mspy.monomers', initial_monomers)
    mocked_monomer_class = mocker.patch('mspy.monomer', side_effect=MockMonomer)
    mocked_compound_class = mocker.patch('mspy.compound', side_effect=MockCompound)
    yield mocker.Mock(monomers=initial_monomers, monomer=mocked_monomer_class, compound=mocked_compound_class)

@pytest.fixture
def mock_config(mocker):
    """Mock config.main['mzDigits']."""
    mocker.patch('gui.config.main', {'mzDigits': 4})
    yield config.main

@pytest.fixture
def mock_mwx(mocker):
    """Mock mwx components."""
    mocked_dlg = mocker.patch('gui.mwx.dlgMessage')
    yield mocked_dlg

@pytest.fixture
def dialog(wx_app, mock_mspy, mock_config, mock_mwx, mocker):
    """Fixture for dlgMonomersEditor instance."""
    parent = wx.Frame(None)
    parent.getUsedMonomers = mocker.Mock(return_value=['UsedMon'])

    dlg = dlg_editor.dlgMonomersEditor(parent)
    yield dlg
    dlg.Destroy()
    parent.Destroy()

def test_init(dialog):
    """Test dialog initialization."""
    assert dialog.GetTitle() == "Monomers Library"
    assert "UsedMon" in dialog.used
    assert "Gly" in dialog._aminoacids
    assert "TestMon" not in dialog._aminoacids
    
    # Gly should be excluded from itemsMap
    items_abbrs = [item[0] for item in dialog.itemsMap]
    assert "TestMon" in items_abbrs
    assert "UsedMon" in items_abbrs
    assert "Gly" not in items_abbrs
    
    assert dialog.itemsList.GetItemCount() == 2

def test_on_item_selected(dialog, mock_mspy, mocker):
    """Test populating editor fields on item selection."""
    evt = mocker.Mock()
    evt.GetText.return_value = "TestMon"

    dialog.onItemSelected(evt)
    
    assert dialog.itemAbbr_value.GetValue() == "TestMon"
    assert dialog.itemName_value.GetValue() == "Test Monomer"
    assert dialog.itemCategory_value.GetValue() == "Test"
    assert dialog.itemFormula_value.GetValue() == "H2O"

def test_on_add_item_new(dialog, mock_mspy):
    """Test adding a new monomer."""
    dialog.itemAbbr_value.SetValue("NewMon")
    dialog.itemName_value.SetValue("New Monomer")
    dialog.itemCategory_value.SetValue("New")
    dialog.itemFormula_value.SetValue("CH4")
    
    dialog.onAddItem(None)
    
    assert "NewMon" in mspy.monomers
    assert mspy.monomers["NewMon"].name == "New Monomer"
    # Fields should be cleared
    assert dialog.itemAbbr_value.GetValue() == ""

def test_on_add_item_replace_confirm(dialog, mock_mspy, mock_mwx):
    """Test replacing an existing monomer with confirmation."""
    mock_mwx.return_value.ShowModal.return_value = wx.ID_OK
    
    dialog.itemAbbr_value.SetValue("TestMon")
    dialog.itemName_value.SetValue("Updated Test Monomer")
    dialog.itemCategory_value.SetValue("Test")
    dialog.itemFormula_value.SetValue("H2O")
    
    dialog.onAddItem(None)
    
    assert mspy.monomers["TestMon"].name == "Updated Test Monomer"
    mock_mwx.assert_called()

def test_on_add_item_replace_cancel(dialog, mock_mspy, mock_mwx):
    """Test cancelling replacement of an existing monomer."""
    mock_mwx.return_value.ShowModal.return_value = wx.ID_CANCEL
    
    dialog.itemAbbr_value.SetValue("TestMon")
    dialog.itemName_value.SetValue("Updated Test Monomer")
    dialog.itemCategory_value.SetValue("Test")
    dialog.itemFormula_value.SetValue("H2O")
    
    dialog.onAddItem(None)
    
    # Name should remain unchanged
    assert mspy.monomers["TestMon"].name == "Test Monomer"

def test_on_add_item_reserved_abbr(dialog, mock_mspy, mock_mwx, mocker):
    """Test adding a monomer with a reserved abbreviation."""
    dialog.itemAbbr_value.SetValue("Gly")
    dialog.itemFormula_value.SetValue("H2O")

    mock_bell = mocker.patch('wx.Bell')
    dialog.onAddItem(None)
    mock_bell.assert_called_once()

    mock_mwx.assert_called()
    assert mspy.monomers["Gly"].formula == "C2H3NO" # Unchanged

def test_on_add_item_invalid_data(dialog, mock_mspy, mocker):
    """Test adding a monomer with invalid data."""
    # Empty abbreviation
    dialog.itemAbbr_value.SetValue("")
    dialog.itemFormula_value.SetValue("H2O")

    mock_bell = mocker.patch('wx.Bell')
    dialog.onAddItem(None)
    mock_bell.assert_called_once()

    # Invalid abbreviation format
    dialog.itemAbbr_value.SetValue("Invalid@Abbr")
    mock_bell.reset_mock()
    dialog.onAddItem(None)
    mock_bell.assert_called_once()

def test_on_delete_item_success(dialog, mock_mspy, mock_mwx, mocker):
    """Test deleting selected monomers."""
    mock_mwx.return_value.ShowModal.return_value = wx.ID_OK

    # Selected index 0 corresponds to TestMon in our sorted list
    mocker.patch.object(dialog.itemsList, 'getSelected', return_value=[0])
    # Mock GetItemData to return the index into itemsMap
    mocker.patch.object(dialog.itemsList, 'GetItemData', return_value=0)
    dialog.onDeleteItem(None)

    assert "TestMon" not in mspy.monomers
    assert "UsedMon" in mspy.monomers

def test_on_delete_item_used(dialog, mock_mspy, mock_mwx, mocker):
    """Test deleting an in-use monomer."""
    mock_mwx.return_value.ShowModal.return_value = wx.ID_OK

    # Assuming UsedMon is at index 1 in itemsMap
    mocker.patch.object(dialog.itemsList, 'getSelected', return_value=[0])
    mocker.patch.object(dialog.itemsList, 'GetItemData', return_value=1)
    mock_bell = mocker.patch('wx.Bell')
    dialog.onDeleteItem(None)
    mock_bell.assert_called()

    assert "UsedMon" in mspy.monomers

def test_on_search(dialog):
    """Test searching monomers."""
    dialog.itemSearch_value.SetValue("test")
    dialog.onSearch(None)
    
    items_abbrs = [item[0] for item in dialog.itemsMap]
    assert "TestMon" in items_abbrs
    assert "UsedMon" not in items_abbrs
    
    dialog.itemSearch_value.SetValue("used")
    dialog.onSearch(None)
    items_abbrs = [item[0] for item in dialog.itemsMap]
    assert "TestMon" not in items_abbrs
    assert "UsedMon" in items_abbrs

def test_update_formula_mass(dialog):
    """Test mass calculation for formula."""
    dialog.itemFormula_value.SetValue("H2O")
    dialog.updateFormulaMass()
    
    assert dialog.itemMoMass_value.GetValue() == "18.01056"
    assert dialog.itemAvMass_value.GetValue() == "18.01528"
    
    # Invalid formula
    dialog.itemFormula_value.SetValue("Invalid")
    dialog.updateFormulaMass()
    assert dialog.itemMoMass_value.GetValue() == ""

def test_update_loss_formula_mass(dialog, mocker):
    """Test mass calculation for loss formula."""
    # Mock FindFocus to return the first loss field
    mocker.patch.object(dialog, 'FindFocus', return_value=dialog.itemLosses_values[0])
    dialog.itemLosses_values[0].SetValue("H2O")
    dialog.updateLossFormulaMass()
    assert dialog.itemLossMoMass_value.GetValue() == "18.01056"

def test_on_formula_edited(dialog, mocker):
    """Test onFormulaEdited event handler."""
    mock_call_after = mocker.patch('wx.CallAfter')
    evt = mocker.Mock()
    dialog.onFormulaEdited(evt)
    evt.Skip.assert_called_once()
    mock_call_after.assert_called_once_with(dialog.updateFormulaMass)

def test_on_loss_formula(dialog, mocker):
    """Test onLossFormula event handler."""
    mock_call_after = mocker.patch('wx.CallAfter')
    evt = mocker.Mock()
    dialog.onLossFormula(evt)
    evt.Skip.assert_called_once()
    mock_call_after.assert_called_once_with(dialog.updateLossFormulaMass)
