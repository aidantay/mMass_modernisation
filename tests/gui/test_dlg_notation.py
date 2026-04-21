import pytest
import wx


class MockNotation:
    def __init__(self):
        self.label = "TestLabel"
        self.formula = "H2O"
        self.theoretical = 18.010565
        self.mz = 18.010565
        self.charge = 1
        self.radical = 0


@pytest.fixture
def notation():
    return MockNotation()


@pytest.fixture
def mock_deps(mocker):
    # Mock mspy and config in the module
    m_mspy = mocker.patch("mmass.gui.dlg_notation.mspy")
    m_config = mocker.patch("mmass.gui.dlg_notation.config")
    m_config.main = {"mzDigits": 4}

    # Mock wx.Bell to avoid actual sound and for assertions
    m_bell = mocker.patch("mmass.gui.dlg_notation.wx.Bell")

    return m_mspy, m_config, m_bell


def test_init(wx_app, mock_deps, notation):
    from mmass.gui.dlg_notation import dlgNotation

    dlg = dlgNotation(None, notation)
    try:
        assert dlg.notation == notation
        assert dlg.button == "Add"
        assert dlg.GetTitle() == "Notation for m/z: 18.0106"

        # Check initial values set by setData
        assert dlg.label_value.GetValue() == "TestLabel"
        assert dlg.formula_value.GetValue() == "H2O"
        assert dlg.theoreticalMZ_value.GetValue() == "18.010565"
        assert dlg.charge_value.GetValue() == "1"
        assert dlg.radical_check.GetValue() == False
        assert dlg.mzByUser_radio.GetValue() == True
    finally:
        dlg.Destroy()


def test_setData_empty(wx_app, mock_deps):
    from mmass.gui.dlg_notation import dlgNotation

    notation = MockNotation()
    notation.formula = None
    notation.theoretical = None
    notation.charge = None

    dlg = dlgNotation(None, notation)
    try:
        assert dlg.formula_value.GetValue() == ""
        assert dlg.theoreticalMZ_value.GetValue() == ""
        assert dlg.charge_value.GetValue() == ""
    finally:
        dlg.Destroy()


def test_onOK_success(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    m_mspy, m_config, m_bell = mock_deps

    dlg = dlgNotation(None, notation)
    try:
        dlg.label_value.SetValue("NewLabel")
        dlg.formula_value.SetValue("NH3")
        dlg.theoreticalMZ_value.SetValue("17.0305")
        dlg.charge_value.SetValue("1")
        dlg.radical_check.SetValue(True)

        m_mspy.compound.return_value = mocker.Mock()

        # Mock EndModal to prevent closing the dialog and for assertion
        mocker.patch.object(dlg, "EndModal")

        dlg.onOK()

        assert notation.label == "NewLabel"
        assert notation.formula == "NH3"
        assert notation.theoretical == 17.0305
        assert notation.charge == 1
        assert notation.radical == 1
        dlg.EndModal.assert_called_with(wx.ID_OK)
        assert not m_bell.called
    finally:
        dlg.Destroy()


def test_onOK_validation_failures(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    m_mspy, m_config, m_bell = mock_deps

    dlg = dlgNotation(None, notation)
    try:
        mocker.patch.object(dlg, "EndModal")

        # Fail label
        dlg.label_value.SetValue("")
        dlg.onOK()
        m_bell.assert_called()
        m_bell.reset_mock()
        assert not dlg.EndModal.called

        # Fail formula
        dlg.label_value.SetValue("Label")
        dlg.formula_value.SetValue("InvalidFormula")
        m_mspy.compound.side_effect = Exception("Invalid")
        dlg.onOK()
        m_bell.assert_called()
        m_bell.reset_mock()

        # Fail theoretical
        m_mspy.compound.side_effect = None
        dlg.formula_value.SetValue("H2O")
        dlg.theoreticalMZ_value.SetValue("invalid")
        dlg.onOK()
        m_bell.assert_called()
        m_bell.reset_mock()

        # Fail charge
        dlg.theoreticalMZ_value.SetValue("18.0")
        dlg.charge_value.SetValue("invalid")
        dlg.onOK()
        m_bell.assert_called()
        m_bell.reset_mock()
    finally:
        dlg.Destroy()


def test_onOK_empty_optional_fields(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    m_mspy, m_config, m_bell = mock_deps

    dlg = dlgNotation(None, notation)
    try:
        mocker.patch.object(dlg, "EndModal")
        dlg.label_value.SetValue("Label")
        dlg.formula_value.SetValue("")
        dlg.theoreticalMZ_value.SetValue("")
        dlg.charge_value.SetValue("")
        dlg.radical_check.SetValue(False)

        dlg.onOK()

        assert notation.formula is None
        assert notation.theoretical is None
        assert notation.charge is None
        assert notation.radical == 0
        dlg.EndModal.assert_called_with(wx.ID_OK)
    finally:
        dlg.Destroy()


def test_onMassType(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    dlg = dlgNotation(None, notation)
    try:
        # Manual mode
        dlg.mzByUser_radio.SetValue(True)
        dlg.onMassType()
        assert dlg.theoreticalMZ_value.IsEnabled() == True

        # Automatic mode (calls onFormula)
        dlg.mzByFormulaMo_radio.SetValue(True)
        mock_onFormula = mocker.patch.object(dlg, "onFormula")
        dlg.onMassType()
        assert dlg.mzByUser_radio.GetValue() == False
        assert dlg.theoreticalMZ_value.IsEnabled() == False
        mock_onFormula.assert_called_once()
    finally:
        dlg.Destroy()


def test_onFormula_manual_mode(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    dlg = dlgNotation(None, notation)
    try:
        dlg.mzByUser_radio.SetValue(True)
        dlg.formula_value.SetValue("H2O")
        # We'll spy on the internal GetValue call if we could, but let's just
        # check that theoreticalMZ_value doesn't change
        dlg.theoreticalMZ_value.SetValue("orig")
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == "orig"
    finally:
        dlg.Destroy()


def test_onFormula_empty_fields(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    dlg = dlgNotation(None, notation)
    try:
        dlg.mzByFormulaMo_radio.SetValue(True)

        # Empty formula
        dlg.formula_value.SetValue("")
        dlg.charge_value.SetValue("1")
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == ""

        # Empty charge
        dlg.formula_value.SetValue("H2O")
        dlg.charge_value.SetValue("")
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == ""
    finally:
        dlg.Destroy()


def test_onFormula_calculations(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    m_mspy, m_config, m_bell = mock_deps

    dlg = dlgNotation(None, notation)
    try:
        dlg.mzByFormulaMo_radio.SetValue(True)
        dlg.formula_value.SetValue("H2O")
        dlg.charge_value.SetValue("1")
        dlg.radical_check.SetValue(False)

        mock_compound = mocker.Mock()
        mock_compound.mz.return_value = (19.018201, 19.018701)  # Mo, Av
        m_mspy.compound.return_value = mock_compound

        # Test Monoisotopic
        dlg.mzByFormulaMo_radio.SetValue(True)
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == "19.018201"
        mock_compound.mz.assert_called_with(charge=1, agentFormula="H", agentCharge=1)

        # Test Average
        dlg.mzByFormulaMo_radio.SetValue(False)
        dlg.mzByFormulaAv_radio.SetValue(True)
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == "19.018701"

        # Test Radical
        dlg.radical_check.SetValue(True)
        dlg.onFormula()
        mock_compound.mz.assert_called_with(charge=1, agentFormula="e", agentCharge=-1)
    finally:
        dlg.Destroy()


def test_onFormula_error(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    m_mspy, m_config, m_bell = mock_deps

    dlg = dlgNotation(None, notation)
    try:
        dlg.mzByFormulaMo_radio.SetValue(True)
        dlg.formula_value.SetValue("Invalid")
        dlg.charge_value.SetValue("1")
        m_mspy.compound.side_effect = Exception("Invalid")

        dlg.theoreticalMZ_value.SetValue("some")
        dlg.onFormula()
        assert dlg.theoreticalMZ_value.GetValue() == ""
    finally:
        dlg.Destroy()


def test_onFormula_evt_skip(wx_app, mock_deps, notation, mocker):
    from mmass.gui.dlg_notation import dlgNotation

    dlg = dlgNotation(None, notation)
    try:
        evt = mocker.Mock(spec=wx.CommandEvent)
        dlg.mzByUser_radio.SetValue(True)
        dlg.onFormula(evt)
        evt.Skip.assert_called_once()
    finally:
        dlg.Destroy()
