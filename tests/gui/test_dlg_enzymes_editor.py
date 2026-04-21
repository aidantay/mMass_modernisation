import pytest
import wx

from mmass.gui.dlg_enzymes_editor import dlgEnzymesEditor


@pytest.fixture
def dialog(wx_app, mocker):
    """
    Fixture for dlgEnzymesEditor.
    """
    # Mock global enzymes and enzyme class
    mocker.patch("mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={})
    # Also mock formulaCtrl because it might need more setup or might be slow
    # But for now, let's see if it works with original.
    # Actually, the plan says mock mspy.enzyme too.

    dlg = dlgEnzymesEditor(None)
    yield dlg
    dlg.Destroy()


def test_initialization(dialog):
    """
    Test dialog initialization.
    """
    assert dialog.GetTitle() == "Enzymes Library"
    assert hasattr(dialog, "itemsList")
    assert hasattr(dialog, "itemName_value")
    assert hasattr(dialog, "itemExpression_value")
    assert hasattr(dialog, "itemCTerm_value")
    assert hasattr(dialog, "itemNTerm_value")
    assert hasattr(dialog, "itemModsBefore_check")
    assert hasattr(dialog, "itemModsAfter_check")


def test_get_item_data_success(dialog, mocker):
    """
    Test getItemData with valid inputs.
    """
    dialog.itemName_value.SetValue("Trypsin")
    dialog.itemExpression_value.SetValue("[KR](?!P)")
    dialog.itemCTerm_value.SetValue("OH")
    dialog.itemNTerm_value.SetValue("H")
    dialog.itemModsBefore_check.SetValue(False)
    dialog.itemModsAfter_check.SetValue(True)

    # Mock mspy.enzyme to avoid side effects of its constructor (like formula validation)
    mock_enzyme_class = mocker.patch("mmass.gui.dlg_enzymes_editor.mspy.enzyme")
    mock_enzyme_instance = mocker.Mock()
    mock_enzyme_class.return_value = mock_enzyme_instance

    result = dialog.getItemData()

    assert result == mock_enzyme_instance
    mock_enzyme_class.assert_called_with(
        name="Trypsin",
        expression="[KR](?!P)",
        cTermFormula="OH",
        nTermFormula="H",
        modsBefore=0,
        modsAfter=1,
    )


@pytest.mark.parametrize(
    "name, expression, cTerm, nTerm",
    [
        ("", "[KR](?!P)", "OH", "H"),
        ("Trypsin", "", "OH", "H"),
        ("Trypsin", "[KR](?!P)", "", "H"),
        ("Trypsin", "[KR](?!P)", "OH", ""),
    ],
)
def test_get_item_data_empty_fields(dialog, mocker, name, expression, cTerm, nTerm):
    """
    Test getItemData with empty required fields.
    """
    dialog.itemName_value.SetValue(name)
    dialog.itemExpression_value.SetValue(expression)
    dialog.itemCTerm_value.SetValue(cTerm)
    dialog.itemNTerm_value.SetValue(nTerm)

    mock_bell = mocker.patch("wx.Bell")

    result = dialog.getItemData()

    assert result is False
    mock_bell.assert_called_once()


def test_get_item_data_invalid_regex(dialog, mocker):
    """
    Test getItemData with invalid regex.
    """
    dialog.itemName_value.SetValue("Invalid")
    dialog.itemExpression_value.SetValue("[invalid")
    dialog.itemCTerm_value.SetValue("OH")
    dialog.itemNTerm_value.SetValue("H")

    mock_bell = mocker.patch("wx.Bell")

    result = dialog.getItemData()

    assert result is False
    mock_bell.assert_called_once()


def test_get_item_data_enzyme_creation_failure(dialog, mocker):
    """
    Test getItemData with enzyme creation failure.
    """
    dialog.itemName_value.SetValue("Fail")
    dialog.itemExpression_value.SetValue("expression")
    dialog.itemCTerm_value.SetValue("OH")
    dialog.itemNTerm_value.SetValue("H")

    mocker.patch("mmass.gui.dlg_enzymes_editor.mspy.enzyme", side_effect=Exception)
    mock_bell = mocker.patch("wx.Bell")

    result = dialog.getItemData()

    assert result is False
    mock_bell.assert_called_once()


def test_update_items_list(dialog, mocker):
    """
    Test updateItemsList.
    """
    mock_enzyme1 = mocker.Mock()
    mock_enzyme1.name = "Enzyme1"
    mock_enzyme1.expression = "Expr1"
    mock_enzyme1.cTermFormula = "CT1"
    mock_enzyme1.nTermFormula = "NT1"
    mock_enzyme1.modsBefore = True
    mock_enzyme1.modsAfter = False

    mock_enzyme2 = mocker.Mock()
    mock_enzyme2.name = "Enzyme2"
    mock_enzyme2.expression = "Expr2"
    mock_enzyme2.cTermFormula = "CT2"
    mock_enzyme2.nTermFormula = "NT2"
    mock_enzyme2.modsBefore = False
    mock_enzyme2.modsAfter = True

    mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes",
        new={"Enzyme1": mock_enzyme1, "Enzyme2": mock_enzyme2},
    )

    dialog.updateItemsList()

    assert dialog.itemsList.GetItemCount() == 2
    # Verify values in list (might be sorted)
    # Enzyme1: modsBefore=True -> "allowed", modsAfter=False -> "not allowed"
    # Enzyme2: modsBefore=False -> "not allowed", modsAfter=True -> "allowed"

    # We can check itemsMap which is sorted
    assert dialog.itemsMap[0][0] == "Enzyme1"
    assert dialog.itemsMap[0][4] is True
    assert dialog.itemsMap[0][5] is False

    assert dialog.itemsMap[1][0] == "Enzyme2"
    assert dialog.itemsMap[1][4] is False
    assert dialog.itemsMap[1][5] is True


def test_clear_editor(dialog):
    """
    Test clearEditor.
    """
    dialog.itemName_value.SetValue("Value")
    dialog.itemExpression_value.SetValue("Value")
    dialog.itemCTerm_value.SetValue("Value")
    dialog.itemNTerm_value.SetValue("Value")
    dialog.itemModsBefore_check.SetValue(True)
    dialog.itemModsAfter_check.SetValue(True)

    dialog.clearEditor()

    assert dialog.itemName_value.GetValue() == ""
    assert dialog.itemExpression_value.GetValue() == ""
    assert dialog.itemCTerm_value.GetValue() == ""
    assert dialog.itemNTerm_value.GetValue() == ""
    assert dialog.itemModsBefore_check.GetValue() is False
    assert dialog.itemModsAfter_check.GetValue() is False


def test_on_item_selected(dialog, mocker):
    """
    Test onItemSelected.
    """
    mock_enzyme = mocker.Mock()
    mock_enzyme.expression = "Expr"
    mock_enzyme.cTermFormula = "CT"
    mock_enzyme.nTermFormula = "NT"
    mock_enzyme.modsBefore = True
    mock_enzyme.modsAfter = False

    mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={"MockEnzyme": mock_enzyme}
    )

    evt = mocker.Mock()
    evt.GetText.return_value = "MockEnzyme"

    dialog.onItemSelected(evt)

    assert dialog.itemName_value.GetValue() == "MockEnzyme"
    assert dialog.itemExpression_value.GetValue() == "Expr"
    assert dialog.itemCTerm_value.GetValue() == "CT"
    assert dialog.itemNTerm_value.GetValue() == "NT"
    assert dialog.itemModsBefore_check.GetValue() is True
    assert dialog.itemModsAfter_check.GetValue() is False


def test_on_add_item_new(dialog, mocker):
    """
    Test onAddItem with a new enzyme.
    """
    mock_item_data = mocker.Mock()
    mock_item_data.name = "NewEnzyme"

    mocker.patch.object(dialog, "getItemData", return_value=mock_item_data)
    mock_enzymes = mocker.patch("mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={})
    mock_update = mocker.patch.object(dialog, "updateItemsList")
    mock_clear = mocker.patch.object(dialog, "clearEditor")

    dialog.onAddItem(None)

    assert mock_enzymes["NewEnzyme"] == mock_item_data
    mock_update.assert_called_once()
    mock_clear.assert_called_once()


def test_on_add_item_invalid(dialog, mocker):
    """
    Test onAddItem with invalid data.
    """
    mocker.patch.object(dialog, "getItemData", return_value=None)
    mock_enzymes = mocker.patch("mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={})

    dialog.onAddItem(None)

    assert len(mock_enzymes) == 0


def test_on_add_item_existing_replace(dialog, mocker):
    """
    Test onAddItem with an existing enzyme and user chooses Replace.
    """
    mock_item_data = mocker.Mock()
    mock_item_data.name = "Existing"

    mocker.patch.object(dialog, "getItemData", return_value=mock_item_data)
    mock_enzymes = mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={"Existing": "Old"}
    )

    mock_dlg_message = mocker.patch("mmass.gui.dlg_enzymes_editor.mwx.dlgMessage")
    mock_dlg_instance = mock_dlg_message.return_value
    mock_dlg_instance.ShowModal.return_value = wx.ID_OK

    mock_update = mocker.patch.object(dialog, "updateItemsList")
    mock_clear = mocker.patch.object(dialog, "clearEditor")

    dialog.onAddItem(None)

    assert mock_enzymes["Existing"] == mock_item_data
    mock_update.assert_called_once()
    mock_clear.assert_called_once()
    mock_dlg_instance.Destroy.assert_called_once()


def test_on_add_item_existing_cancel(dialog, mocker):
    """
    Test onAddItem with an existing enzyme and user chooses Cancel.
    """
    mock_item_data = mocker.Mock()
    mock_item_data.name = "Existing"

    mocker.patch.object(dialog, "getItemData", return_value=mock_item_data)
    mock_enzymes = mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes", new={"Existing": "Old"}
    )

    mock_dlg_message = mocker.patch("mmass.gui.dlg_enzymes_editor.mwx.dlgMessage")
    mock_dlg_instance = mock_dlg_message.return_value
    mock_dlg_instance.ShowModal.return_value = wx.ID_CANCEL

    dialog.onAddItem(None)

    assert mock_enzymes["Existing"] == "Old"
    mock_dlg_instance.Destroy.assert_called_once()


def test_on_delete_item_confirm(dialog, mocker):
    """
    Test onDeleteItem with confirmation.
    """
    mock_enzymes = mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes",
        new={"Enzyme1": "E1", "Enzyme2": "E2"},
    )
    dialog.itemsMap = [("Enzyme1",), ("Enzyme2",)]

    mock_dlg_message = mocker.patch("mmass.gui.dlg_enzymes_editor.mwx.dlgMessage")
    mock_dlg_instance = mock_dlg_message.return_value
    mock_dlg_instance.ShowModal.return_value = wx.ID_OK

    mocker.patch.object(dialog.itemsList, "getSelected", return_value=[0])
    mocker.patch.object(dialog.itemsList, "GetItemData", return_value=0)

    mock_update = mocker.patch.object(dialog, "updateItemsList")
    mock_clear = mocker.patch.object(dialog, "clearEditor")

    dialog.onDeleteItem(None)

    assert "Enzyme1" not in mock_enzymes
    assert "Enzyme2" in mock_enzymes
    mock_update.assert_called_once()
    mock_clear.assert_called_once()
    mock_dlg_instance.Destroy.assert_called_once()


def test_on_delete_item_cancel(dialog, mocker):
    """
    Test onDeleteItem with cancellation.
    """
    mock_enzymes = mocker.patch(
        "mmass.gui.dlg_enzymes_editor.mspy.enzymes",
        new={"Enzyme1": "E1", "Enzyme2": "E2"},
    )

    mock_dlg_message = mocker.patch("mmass.gui.dlg_enzymes_editor.mwx.dlgMessage")
    mock_dlg_instance = mock_dlg_message.return_value
    mock_dlg_instance.ShowModal.return_value = wx.ID_CANCEL

    dialog.onDeleteItem(None)

    assert len(mock_enzymes) == 2
    mock_dlg_instance.Destroy.assert_called_once()
