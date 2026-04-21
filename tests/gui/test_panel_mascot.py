import pytest
import wx

import mmass.gui.config as config
import mmass.gui.images as images
import mmass.gui.libs as libs
from mmass import gui
from mmass.gui.ids import *


@pytest.fixture
def mock_parent(mocker, wx_app):
    """Fixture to provide a mock wx parent Frame."""
    parent = wx.Frame(None)
    parent.getCurrentPeaklist = mocker.Mock(return_value=[])
    yield parent
    if parent:
        parent.Destroy()


@pytest.fixture
def mascot_panel(mocker, wx_app, mock_parent):
    """Fixture to initialize panelMascot with mocked dependencies."""
    # Mocking images.lib to provide required bitmaps
    mock_images = {
        "bgrToolbar": wx.Bitmap(1, 1),
        "bgrControlbar": wx.Bitmap(1, 1),
        "mascotPMFOff": wx.Bitmap(1, 1),
        "mascotMISOff": wx.Bitmap(1, 1),
        "mascotSQOff": wx.Bitmap(1, 1),
        "mascotQueryOff": wx.Bitmap(1, 1),
        "mascotPMFOn": wx.Bitmap(1, 1),
        "mascotMISOn": wx.Bitmap(1, 1),
        "mascotSQOn": wx.Bitmap(1, 1),
        "mascotQueryOn": wx.Bitmap(1, 1),
    }

    # Mocking libs.mascot to avoid issues with empty or missing config
    mock_libs_mascot = {
        "Matrix Science": {
            "url": "http://www.matrixscience.com/cgi/search_form.pl",
            "proxy": "",
            "username": "",
            "password": "",
        }
    }

    mocker.patch.dict(images.lib, mock_images)
    mocker.patch.dict(libs.mascot, mock_libs_mascot, clear=True)
    mocker.patch("wx.RESIZE_BOX", 0, create=True)
    # Ensure we don't try to actually create a real modal dialog or thread
    mocker.patch("wx.MiniFrame.Show")

    panel = gui.panel_mascot.panelMascot(mock_parent)
    yield panel
    if panel:
        try:
            panel.Destroy()
        except wx.PyDeadObjectError:
            pass


def test_initialization(mascot_panel):
    """Verify panelMascot instantiates correctly and sets currentTool."""
    assert isinstance(mascot_panel, gui.panel_mascot.panelMascot)
    assert mascot_panel.currentTool in ["pmf", "mis", "sq", "query"]


def test_gui_creation(mascot_panel):
    """Verify all child panels (toolbar, pmf, mis, sq, query, gauge) are created."""
    # The mainSizer should have 6 items added in makeGUI
    # toolbar, pmf, mis, sq, query, gauge
    assert mascot_panel.mainSizer.GetItemCount() == 6

    # Verify child attributes exist
    assert hasattr(mascot_panel, "pmf_butt")
    assert hasattr(mascot_panel, "mis_butt")
    assert hasattr(mascot_panel, "sq_butt")
    assert hasattr(mascot_panel, "query_butt")
    assert hasattr(mascot_panel, "server_choice")
    assert hasattr(mascot_panel, "search_butt")


def test_onClose_safe(mocker, mascot_panel):
    """Call onClose when self.processing is None and assert Destroy() is called."""
    mascot_panel.processing = None
    mock_destroy = mocker.patch.object(
        mascot_panel, "Destroy", wraps=mascot_panel.Destroy
    )
    # We also need to mock os.path.exists to avoid errors in temp file cleanup if it tries to access it
    mocker.patch("os.path.exists", return_value=False)
    mascot_panel.onClose(None)
    assert mock_destroy.called


def test_onClose_processing(mocker, mascot_panel):
    """Call onClose when self.processing is not None. Assert wx.Bell is called and Destroy() is NOT called."""
    mascot_panel.processing = "Some Process"
    mock_destroy = mocker.patch.object(
        mascot_panel, "Destroy", wraps=mascot_panel.Destroy
    )
    mock_bell = mocker.patch("wx.Bell")
    mascot_panel.onClose(None)
    assert mock_bell.called
    assert not mock_destroy.called


def test_onToolSelected(mocker, mascot_panel):
    """Verify tool selection logic and UI updates."""
    import mmass.gui.panel_mascot as mod

    tools = [
        (mod.ID_mascotPMF, "pmf", 1),
        (mod.ID_mascotMIS, "mis", 2),
        (mod.ID_mascotSQ, "sq", 3),
        (mod.ID_mascotQuery, "query", 4),
    ]

    for event_id, tool_name, sizer_index in tools:
        # Create a mock event with the specific ID
        mock_event = mocker.Mock(spec=wx.CommandEvent)
        mock_event.GetId.return_value = event_id

        # Call the handler
        mascot_panel.onToolSelected(mock_event)

        # Verify current tool is updated
        assert mascot_panel.currentTool == tool_name

        # Verify correct panel is shown in mainSizer
        # In makeGUI: pmf(1), mis(2), sq(3), query(4)
        assert mascot_panel.mainSizer.GetItem(sizer_index).IsShown()

        # Verify other tool panels are hidden
        for i in range(1, 5):
            if i != sizer_index:
                assert not mascot_panel.mainSizer.GetItem(i).IsShown()


def test_onModificationSelected(mascot_panel):
    """Verify modification count label updates when items are selected."""
    # Setup listboxes with some items
    items = ["Mod1", "Mod2", "Mod3"]
    mascot_panel.paramPMFFixedMods_listbox.Set(items)
    mascot_panel.paramPMFVariableMods_listbox.Set(items)

    # Select some items
    # For extended listboxes in older wx, we use Select(n) multiple times
    mascot_panel.paramPMFFixedMods_listbox.Select(0)

    mascot_panel.paramPMFVariableMods_listbox.Select(1)
    mascot_panel.paramPMFVariableMods_listbox.Select(2)

    # Call the handler
    mascot_panel.onModificationSelected(None)

    # Verify labels
    assert "Fixed modifications: (1)" in mascot_panel.paramPMFFixedMods_label.GetLabel()
    assert (
        "Variable modifications: (2)"
        in mascot_panel.paramPMFVariableMods_label.GetLabel()
    )


def test_onHiddenModifications(mocker, mascot_panel):
    """Verify hidden modifications toggle updates config and triggers update."""
    mascot_panel.currentTool = "pmf"
    mascot_panel.currentParams = {
        "MODS": [],
        "HIDDEN_MODS": [],
    }  # Required for updateModification

    mock_update = mocker.patch.object(mascot_panel, "updateModification")
    # Toggle on
    mascot_panel.paramPMFHiddenMods_check.SetValue(True)
    mascot_panel.onHiddenModifications(None)
    assert config.mascot["pmf"]["hiddenMods"] == 1
    assert mock_update.called

    mock_update.reset_mock()

    # Toggle off
    mascot_panel.paramPMFHiddenMods_check.SetValue(False)
    mascot_panel.onHiddenModifications(None)
    assert config.mascot["pmf"]["hiddenMods"] == 0
    assert mock_update.called


def test_onProcessing(mocker, mascot_panel):
    """Verify processing state UI updates."""
    mock_layout = mocker.patch.object(mascot_panel, "Layout")
    # Start processing
    mascot_panel.onProcessing(True)
    assert hasattr(mascot_panel, "_window_disabler")
    assert mascot_panel.mainSizer.GetItem(5).IsShown()  # Gauge panel is index 5
    assert mascot_panel.gauge.GetValue() == 0

    # Stop processing
    mascot_panel.processing = "some thread"
    mascot_panel.onProcessing(False)
    assert not hasattr(mascot_panel, "_window_disabler")
    assert not mascot_panel.mainSizer.GetItem(5).IsShown()
    assert mascot_panel.processing is None


def test_setData(mocker, mascot_panel):
    """Verify document metadata populates UI components."""
    # Create mock document
    mock_doc = mocker.Mock()
    mock_doc.title = "Test Document Title"
    mock_doc.spectrum.precursorMZ = 1234.5678

    # Mock onGetPeaklist to avoid side effects
    mocker.patch.object(mascot_panel, "onGetPeaklist")
    mascot_panel.setData(mock_doc)

    assert mascot_panel.currentDocument == mock_doc
    assert mascot_panel.paramPMFTitle_value.GetValue() == "Test Document Title"
    assert mascot_panel.paramMISTitle_value.GetValue() == "Test Document Title"
    assert mascot_panel.paramSQTitle_value.GetValue() == "Test Document Title"
    assert mascot_panel.paramMISPeptideMass_value.GetValue() == "1234.5678"

    # Test None document
    mascot_panel.setData(None)
    assert mascot_panel.paramPMFTitle_value.GetValue() == ""


def test_onGetPeaklist(mocker, mascot_panel, mock_parent):
    """Verify peaklist extraction and formatting."""
    # Create mock peaks
    mock_peak1 = mocker.Mock()
    mock_peak1.mz = 100.1
    mock_peak1.intensity = 500.0
    mock_peak2 = mocker.Mock()
    mock_peak2.mz = 200.2
    mock_peak2.intensity = 1000.0

    mock_parent.getCurrentPeaklist.return_value = [mock_peak1, mock_peak2]

    # Set filters
    mascot_panel.filterAnnotations_check.SetValue(True)
    mascot_panel.filterMatches_check.SetValue(False)
    mascot_panel.filterIsotopes_check.SetValue(False)
    mascot_panel.filterUnselected_check.SetValue(False)
    mascot_panel.filterUnknown_check.SetValue(False)

    # Call handler
    mascot_panel.onGetPeaklist(None)

    # Check parent call
    mock_parent.getCurrentPeaklist.assert_called_with("A")

    # Check text value
    expected = "100.100000\t500.000000\n200.200000\t1000.000000\n"
    assert mascot_panel.paramQuery_value.GetValue() == expected


def test_getParams_pmf(mascot_panel):
    """Verify PMF parameters extraction from UI."""
    # Set search type
    config.mascot["common"]["searchType"] = "pmf"

    # Set UI values
    mascot_panel.paramPMFTitle_value.SetValue("PMF Search")
    mascot_panel.paramPMFUserName_value.SetValue("User One")
    mascot_panel.paramPMFUserEmail_value.SetValue("user@test.com")
    mascot_panel.paramPMFProteinMass_value.SetValue("50.5")
    mascot_panel.paramPMFPeptideTol_value.SetValue("0.1")
    mascot_panel.paramPMFPeptideTolUnits_choice.SetStringSelection("Da")

    # Mock listbox selections
    mascot_panel.paramPMFFixedMods_listbox.Set(["FixedMod1", "FixedMod2"])
    mascot_panel.paramPMFFixedMods_listbox.Select(0)

    mascot_panel.paramPMFVariableMods_listbox.Set(["VarMod1", "VarMod2"])
    mascot_panel.paramPMFVariableMods_listbox.Select(1)

    # Call getParams
    success = mascot_panel.getParams()
    assert success

    # Verify config updates
    assert config.mascot["common"]["title"] == "PMF Search"
    assert config.mascot["pmf"]["proteinMass"] == 50.5
    assert config.mascot["pmf"]["peptideTol"] == 0.1
    assert config.mascot["pmf"]["fixedMods"] == ["FixedMod1"]
    assert config.mascot["pmf"]["variableMods"] == ["VarMod2"]


def test_checkParams_valid(mascot_panel):
    """Verify checkParams returns True for valid inputs."""
    config.mascot["common"]["searchType"] = "pmf"
    config.mascot["common"]["userName"] = "Test User"
    config.mascot["common"]["userEmail"] = "test@example.com"
    config.mascot["pmf"]["taxonomy"] = "All entries"
    config.mascot["pmf"]["database"] = "SwissProt"
    config.mascot["pmf"]["enzyme"] = "Trypsin"
    config.mascot["pmf"]["peptideTol"] = 0.5
    config.mascot["pmf"]["peptideTolUnits"] = "Da"
    config.mascot["pmf"]["proteinMass"] = 100

    mascot_panel.paramQuery_value.SetValue("100.1 500.0\n")

    assert mascot_panel.checkParams() is True


def test_checkParams_errors(mocker, mascot_panel):
    """Verify checkParams detects errors and shows dialog."""
    config.mascot["common"]["searchType"] = "pmf"
    config.mascot["common"]["userName"] = ""  # Missing name
    config.mascot["common"]["userEmail"] = "test@example.com"
    config.mascot["pmf"]["taxonomy"] = "All entries"
    config.mascot["pmf"]["database"] = "SwissProt"
    config.mascot["pmf"]["enzyme"] = "Trypsin"
    config.mascot["pmf"]["peptideTol"] = -1.0  # Negative tol
    config.mascot["pmf"]["peptideTolUnits"] = "Da"
    config.mascot["pmf"]["proteinMass"] = 100

    mascot_panel.paramQuery_value.SetValue("")  # Empty query

    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mock_bell = mocker.patch("wx.Bell")
    result = mascot_panel.checkParams()
    assert result is False
    assert mock_bell.called
    assert mock_dlg.called

    # Check for specific error messages in the call
    args, kwargs = mock_dlg.call_args
    error_message = kwargs.get("message", "")
    assert "name must be specified" in error_message
    assert "tolerance cannot be negative" in error_message
    assert "Query is empty" in error_message


def test_getServerParams_success(mocker, mascot_panel):
    """Verify getServerParams successfully parses mascot server config."""
    import mmass.gui.panel_mascot as mod

    mod.config.mascot["common"]["server"] = "TestServer"
    mod.libs.mascot["TestServer"] = {
        "host": "localhost",
        "path": "/mascot/",
        "params": "params.txt",
    }

    # Mock HTTP response
    mock_response_data = (
        "[DB]\nSwissProt\nNCBInr\n"
        "[TAXONOMY]\nAll entries\nHuman\n"
        "[CLE]\nTrypsin\nCNBr\n"
        "[MODS]\nOxidation (M)\nCarbamidomethyl (C)\n"
        "[HIDDEN_MODS]\nAcetyl (Protein N-term)\n"
        "[INSTRUMENT]\nESI-QUAD-TOF\n"
        "[QUANTITATION]\nNone\niTRAQ 4plex\n"
    )

    mock_response = mocker.Mock()
    mock_response.status = 200
    mock_response.read.return_value = mock_response_data.encode("utf-8")

    mock_conn = mocker.Mock()
    mock_conn.getresponse.return_value = mock_response

    mocker.patch("http.client.HTTPConnection", return_value=mock_conn)
    mocker.patch("socket.setdefaulttimeout")
    mascot_panel.getServerParams()

    assert mascot_panel.currentParams is not None
    assert "SwissProt" in mascot_panel.currentParams["DB"]
    assert "Human" in mascot_panel.currentParams["TAXONOMY"]
    assert "Oxidation (M)" in mascot_panel.currentParams["MODS"]
    assert "Acetyl (Protein N-term)" in mascot_panel.currentParams["HIDDEN_MODS"]


def test_getServerParams_failure(mocker, mascot_panel):
    """Verify getServerParams handles connection failure."""
    import mmass.gui.panel_mascot as mod

    mod.config.mascot["common"]["server"] = "TestServer"
    mod.libs.mascot["TestServer"] = {"host": "localhost", "path": "/", "params": ""}

    mocker.patch(
        "http.client.HTTPConnection", side_effect=Exception("Connection Refused")
    )
    mocker.patch("socket.setdefaulttimeout")
    result = mascot_panel.getServerParams()
    assert result is False
    assert mascot_panel.currentParams is None


def test_updateServerParams_success(mocker, mascot_panel):
    """Verify updateServerParams orchestrates thread and form update."""
    import mmass.gui.panel_mascot as mod

    mascot_panel.server_choice.Set(["TestServer"])
    mascot_panel.server_choice.SetStringSelection("TestServer")
    mod.libs.mascot["TestServer"] = {"host": "localhost", "path": "/", "params": ""}

    # Mock currentParams for updateForm to work
    mascot_panel.currentParams = {
        "DB": ["DB1"],
        "TAXONOMY": ["TAX1"],
        "CLE": ["CLE1"],
        "MODS": ["MOD1"],
        "HIDDEN_MODS": ["HMOD1"],
        "INSTRUMENT": ["INST1"],
        "QUANTITATION": ["QUANT1"],
    }

    # Mock threading to avoid real async execution
    mock_thread = mocker.Mock()
    mock_thread.is_alive.side_effect = [True, False]  # Pulse once then finish

    mocker.patch("threading.Thread", return_value=mock_thread)
    mocker.patch.object(mascot_panel, "onProcessing")
    mock_update_form = mocker.patch.object(mascot_panel, "updateForm")

    # Mock gauge.pulse to avoid timeout
    mocker.patch.object(mascot_panel.gauge, "pulse")

    mascot_panel.updateServerParams()

    assert mascot_panel.currentConnection is True
    assert mascot_panel.search_butt.IsEnabled()
    assert mock_update_form.called


def test_updateServerParams_failure(mocker, mascot_panel):
    """Verify updateServerParams handles server failure with retry dialog."""
    import mmass.gui.panel_mascot as mod

    mascot_panel.server_choice.Set(["TestServer"])
    mascot_panel.server_choice.SetStringSelection("TestServer")
    mod.libs.mascot["TestServer"] = {"host": "localhost", "path": "/", "params": ""}

    # Ensure currentParams is None to trigger failure path
    mascot_panel.currentParams = None

    # Mock threading to avoid real async execution
    mock_thread = mocker.Mock()
    mock_thread.is_alive.return_value = False

    mocker.patch("threading.Thread", return_value=mock_thread)
    mocker.patch.object(mascot_panel, "onProcessing")
    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mock_dlg.return_value.ShowModal.return_value = wx.ID_CANCEL  # User cancels retry
    mocker.patch("wx.Bell")

    # Mock gauge.pulse to avoid timeout
    mocker.patch.object(mascot_panel.gauge, "pulse")

    mascot_panel.updateServerParams()

    assert mascot_panel.currentConnection is False
    assert not mascot_panel.search_butt.IsEnabled()
    assert mock_dlg.called


def test_updateForm(mocker, mascot_panel):
    """Verify updateForm populates UI from currentParams."""
    mascot_panel.currentParams = {
        "DB": ["Database1", "Database2"],
        "TAXONOMY": ["Taxonomy1", "Taxonomy2"],
        "CLE": ["Enzyme1", "Enzyme2"],
        "INSTRUMENT": ["Inst1", "Inst2"],
        "QUANTITATION": ["None", "Quant1"],
        "MODS": ["Mod1"],
        "HIDDEN_MODS": ["HMod1"],
    }

    # Set search type to PMF
    config.mascot["common"]["searchType"] = "pmf"

    # Mock updateModification to avoid extra complexity here
    mocker.patch.object(mascot_panel, "updateModification")
    mascot_panel.updateForm()

    assert "Database1" in mascot_panel.paramPMFDatabase_choice.GetStrings()
    assert "Taxonomy2" in mascot_panel.paramPMFTaxonomy_choice.GetStrings()
    assert "Enzyme1" in mascot_panel.paramPMFEnzyme_choice.GetStrings()

    # Verify MIS too
    assert "Inst1" in mascot_panel.paramMISInstrument_choice.GetStrings()
    assert "Quant1" in mascot_panel.paramMISQuantitation_choice.GetStrings()


def test_updateModification(mascot_panel):
    """Verify updateModification populates listboxes correctly."""
    mascot_panel.currentParams = {
        "MODS": ["NormalMod1", "NormalMod2"],
        "HIDDEN_MODS": ["HiddenMod1"],
    }

    # Test without hidden mods
    config.mascot["pmf"]["hiddenMods"] = 0
    mascot_panel.updateModification(tool="pmf")

    assert "NormalMod1" in mascot_panel.paramPMFFixedMods_listbox.GetStrings()
    assert "HiddenMod1" not in mascot_panel.paramPMFFixedMods_listbox.GetStrings()

    # Test with hidden mods
    config.mascot["pmf"]["hiddenMods"] = 1
    mascot_panel.updateModification(tool="pmf")

    assert "NormalMod1" in mascot_panel.paramPMFFixedMods_listbox.GetStrings()
    assert "HiddenMod1" in mascot_panel.paramPMFFixedMods_listbox.GetStrings()

    # Test selection restoration
    config.mascot["pmf"]["fixedMods"] = ["NormalMod2"]
    mascot_panel.updateModification(tool="pmf")
    selections = mascot_panel.paramPMFFixedMods_listbox.GetSelections()
    selected_strings = [
        mascot_panel.paramPMFFixedMods_listbox.GetString(s) for s in selections
    ]
    assert "NormalMod2" in selected_strings


def test_makeMGFQuery_pmf(mascot_panel):
    """Verify MGF query generation for PMF."""
    config.mascot["common"]["searchType"] = "pmf"
    config.mascot["common"]["title"] = "Test PMF Title"
    config.mascot["common"]["userName"] = "Test User"
    config.mascot["common"]["userEmail"] = "test@example.com"
    config.mascot["pmf"]["database"] = "SwissProt"
    config.mascot["pmf"]["taxonomy"] = "All entries"
    config.mascot["pmf"]["enzyme"] = "Trypsin"
    config.mascot["pmf"]["miscleavages"] = "1"
    config.mascot["pmf"]["decoy"] = 0
    config.mascot["pmf"]["report"] = "50"
    config.mascot["pmf"]["fixedMods"] = ["FixedMod1"]
    config.mascot["pmf"]["variableMods"] = ["VarMod1"]
    config.mascot["pmf"]["proteinMass"] = 50.0
    config.mascot["pmf"]["peptideTol"] = 0.5
    config.mascot["pmf"]["peptideTolUnits"] = "Da"
    config.mascot["pmf"]["massType"] = "Monoisotopic"
    config.mascot["pmf"]["charge"] = "1+"

    mascot_panel.paramQuery_value.SetValue("100.1\t500.0\n200.2\t1000.0\n")

    query = mascot_panel.makeMGFQuery()

    assert "SEARCH=PMF" in query
    assert "COM=Test PMF Title" in query
    assert "USERNAME=Test User" in query
    assert "USEREMAIL=test@example.com" in query
    assert "DB=SwissProt" in query
    assert "TAXONOMY=All entries" in query
    assert "CLE=Trypsin" in query
    assert "PFA=1" in query
    assert "DECOY=0" in query
    assert "MODS=FixedMod1," in query
    assert "IT_MODS=VarMod1," in query
    assert "SEG=50.0" in query
    assert "TOL=0.5" in query
    assert "TOLU=Da" in query
    assert "MASS=Monoisotopic" in query
    assert "CHARGE=1+" in query
    assert "100.1\t500.0" in query


def test_makeMGFQuery_mis(mascot_panel):
    """Verify MGF query generation for MIS."""
    config.mascot["common"]["searchType"] = "mis"
    config.mascot["common"]["title"] = "Test MIS Title"
    config.mascot["mis"]["database"] = "NCBInr"
    config.mascot["mis"]["taxonomy"] = "Human"
    config.mascot["mis"]["enzyme"] = "Trypsin"
    config.mascot["mis"]["miscleavages"] = "2"
    config.mascot["mis"]["decoy"] = 1
    config.mascot["mis"]["report"] = "20"
    config.mascot["mis"]["fixedMods"] = ["FixedMod2"]
    config.mascot["mis"]["variableMods"] = ["VarMod2"]
    config.mascot["mis"]["peptideMass"] = 1234.56
    config.mascot["mis"]["peptideTol"] = 10.0
    config.mascot["mis"]["peptideTolUnits"] = "ppm"
    config.mascot["mis"]["msmsTol"] = 0.2
    config.mascot["mis"]["msmsTolUnits"] = "Da"
    config.mascot["mis"]["massType"] = "Average"
    config.mascot["mis"]["charge"] = "2+"
    config.mascot["mis"]["instrument"] = "ESI-QUAD-TOF"
    config.mascot["mis"]["quantitation"] = "None"
    config.mascot["mis"]["errorTolerant"] = 0

    mascot_panel.paramQuery_value.SetValue("100.1\t500.0\n")

    query = mascot_panel.makeMGFQuery()

    assert "SEARCH=MIS" in query
    assert "PRECURSOR=1234.56" in query
    assert "ITOL=0.2" in query
    assert "INSTRUMENT=ESI-QUAD-TOF" in query
    assert "BEGIN IONS" in query
    assert "PEPMASS=1234.56" in query
    assert "END IONS" in query


def test_makeMGFQuery_sq(mascot_panel):
    """Verify MGF query generation for SQ."""
    config.mascot["common"]["searchType"] = "sq"
    config.mascot["common"]["title"] = "Test SQ Title"
    config.mascot["sq"]["database"] = "SwissProt"
    config.mascot["sq"]["taxonomy"] = "All entries"
    config.mascot["sq"]["enzyme"] = "Trypsin"
    config.mascot["sq"]["miscleavages"] = "1"
    config.mascot["sq"]["decoy"] = 0
    config.mascot["sq"]["report"] = "AUTO"
    config.mascot["sq"]["fixedMods"] = []
    config.mascot["sq"]["variableMods"] = []
    config.mascot["sq"]["peptideTol"] = 1.0
    config.mascot["sq"]["peptideTolUnits"] = "Da"
    config.mascot["sq"]["msmsTol"] = 0.5
    config.mascot["sq"]["msmsTolUnits"] = "Da"
    config.mascot["sq"]["massType"] = "Monoisotopic"
    config.mascot["sq"]["charge"] = "1+"
    config.mascot["sq"]["instrument"] = "Default"
    config.mascot["sq"]["quantitation"] = "None"

    mascot_panel.paramQuery_value.SetValue("SQ-QUERY")

    query = mascot_panel.makeMGFQuery()

    assert "SEARCH=SQ" in query
    assert "SQ-QUERY" in query


def test_makeSearchHTML(mocker, mascot_panel):
    """Verify HTML wrapper generation."""
    import mmass.gui.panel_mascot as mod

    mod.config.mascot["common"]["server"] = "Matrix Science"
    mod.libs.mascot["Matrix Science"] = {
        "protocol": "http",
        "host": "www.matrixscience.com",
        "path": "/cgi/",
        "search": "search_form.pl",
    }

    dummy_query = "DUMMY MGF QUERY"
    mocker.patch.object(mascot_panel, "makeMGFQuery", return_value=dummy_query)
    html = mascot_panel.makeSearchHTML()

    assert '<?xml version="1.0" encoding="utf-8"?>' in html
    assert "<title>mMass - Mascot Search</title>" in html
    assert '<form action="http://www.matrixscience.com/cgi/search_form.pl?1"' in html
    assert dummy_query in html


def test_onSearch(mocker, mascot_panel):
    """Verify onSearch orchestrates parameter checking, HTML generation, and browser launch."""
    # Setup mocks
    mock_html = "<html>DUMMY</html>"

    mocker.patch.object(mascot_panel, "getParams", return_value=True)
    mocker.patch.object(mascot_panel, "checkParams", return_value=True)
    mocker.patch.object(mascot_panel, "makeSearchHTML", return_value=mock_html)

    # Mock Path.open and webbrowser
    mock_file_obj = mocker.mock_open()
    mocker.patch("mmass.gui.panel_mascot.Path.open", mock_file_obj)
    mock_browser_open = mocker.patch("mmass.gui.panel_mascot.webbrowser.open")

    # Mock dlgMessage to avoid hangs if something fails
    mocker.patch("mmass.gui.mwx.dlgMessage")

    mascot_panel.onSearch(None)

    # Verify file write
    mock_file_obj.assert_called_with("w", encoding="utf-8")

    # Verify browser open
    mock_browser_open.assert_called()


def test_onSearch_failure_during_file_op(mocker, mascot_panel):
    """Verify onSearch handles file operation errors."""
    mocker.patch.object(mascot_panel, "getParams", return_value=True)
    mocker.patch.object(mascot_panel, "checkParams", return_value=True)
    mocker.patch.object(mascot_panel, "makeSearchHTML", return_value="<html></html>")
    mocker.patch("mmass.gui.panel_mascot.Path.open", side_effect=Exception("Disk Full"))
    mock_bell = mocker.patch("wx.Bell")
    mock_dlg = mocker.patch("mmass.gui.mwx.dlgMessage")
    mascot_panel.onSearch(None)
    assert mock_bell.called
    assert mock_dlg.called


def test_onToolSelected_processing(mocker, mascot_panel):
    """Verify onToolSelected does nothing when processing is active."""
    mascot_panel.processing = "Active Thread"
    initial_tool = mascot_panel.currentTool

    mock_bell = mocker.patch("wx.Bell")
    mascot_panel.onToolSelected(tool="mis")
    assert mock_bell.called
    assert mascot_panel.currentTool == initial_tool


def test_onGetPeaklist_no_peaklist(mocker, mascot_panel, mock_parent):
    """Verify onGetPeaklist handles empty peaklist from parent."""
    mock_parent.getCurrentPeaklist.return_value = None
    mascot_panel.paramQuery_value.SetValue("old content")

    mock_event = mocker.Mock()  # To trigger wx.Bell
    mock_bell = mocker.patch("wx.Bell")
    mascot_panel.onGetPeaklist(mock_event)
    assert mascot_panel.paramQuery_value.GetValue() == ""
    assert mock_bell.called


def test_checkParams_extended(mocker, mascot_panel):
    """Verify checkParams covers more error scenarios for MIS and SQ."""
    # Test MIS Precursor mass out of range
    config.mascot["common"]["searchType"] = "mis"
    config.mascot["common"]["userName"] = "User"
    config.mascot["common"]["userEmail"] = "email"
    config.mascot["mis"]["taxonomy"] = "Tax"
    config.mascot["mis"]["database"] = "DB"
    config.mascot["mis"]["enzyme"] = "Enz"
    config.mascot["mis"]["peptideMass"] = 50  # Too small
    config.mascot["mis"]["peptideTol"] = 1.0
    config.mascot["mis"]["msmsTol"] = 0.5
    mascot_panel.paramQuery_value.SetValue("query")

    mocker.patch("mmass.gui.mwx.dlgMessage")
    assert mascot_panel.checkParams() is False

    # Test MIS Decoy and Error Tolerant conflict
    config.mascot["mis"]["peptideMass"] = 1000
    config.mascot["mis"]["decoy"] = 1
    config.mascot["mis"]["errorTolerant"] = 1
    assert mascot_panel.checkParams() is False

    # Test MIS Error Tolerant and Quantitation conflict
    config.mascot["mis"]["decoy"] = 0
    config.mascot["mis"]["quantitation"] = "iTRAQ"
    assert mascot_panel.checkParams() is False

    # Test MIS Error Tolerant and None Enzyme conflict
    config.mascot["mis"]["quantitation"] = "None"
    config.mascot["mis"]["enzyme"] = "None"
    assert mascot_panel.checkParams() is False

    # Test SQ with negative MSMS tol
    config.mascot["common"]["searchType"] = "sq"
    config.mascot["sq"]["msmsTol"] = -1.0
    assert mascot_panel.checkParams() is False


def test_updateModification_mis_sq(mascot_panel):
    """Verify updateModification for MIS and SQ tools."""
    mascot_panel.currentParams = {"MODS": ["Mod1"], "HIDDEN_MODS": ["HMod1"]}

    # Test MIS
    config.mascot["mis"]["hiddenMods"] = 1
    mascot_panel.updateModification(tool="mis")
    assert "Mod1" in mascot_panel.paramMISVariableMods_listbox.GetStrings()
    assert "HMod1" in mascot_panel.paramMISVariableMods_listbox.GetStrings()

    # Test SQ
    config.mascot["sq"]["hiddenMods"] = 0
    mascot_panel.updateModification(tool="sq")
    assert "Mod1" in mascot_panel.paramSQVariableMods_listbox.GetStrings()
    assert "HMod1" not in mascot_panel.paramSQVariableMods_listbox.GetStrings()


def test_onServerSelected(mocker, mascot_panel):
    """Verify onServerSelected calls updateServerParams."""
    mock_update = mocker.patch.object(mascot_panel, "updateServerParams")
    mascot_panel.onServerSelected(None)
    assert mock_update.called


def test_onClose_deletes_temp_file(mocker, mascot_panel):
    """Verify onClose attempts to delete the temporary HTML file."""
    mascot_panel.processing = None
    mocker.patch("tempfile.gettempdir", return_value="/tmp")
    mock_unlink = mocker.patch("mmass.gui.panel_mascot.Path.unlink")
    mocker.patch.object(mascot_panel, "Destroy")
    mascot_panel.onClose(None)
    assert mock_unlink.called


def test_getParams_mis(mascot_panel):
    """Verify MIS parameters extraction from UI."""
    config.mascot["common"]["searchType"] = "mis"

    mascot_panel.paramMISTitle_value.SetValue("MIS Search")
    mascot_panel.paramMISPeptideMass_value.SetValue("2000.0")
    mascot_panel.paramMISPeptideTol_value.SetValue("10.0")
    mascot_panel.paramMISMSMSTol_value.SetValue("0.5")

    assert mascot_panel.getParams() is True
    assert config.mascot["mis"]["peptideMass"] == 2000.0
    assert config.mascot["mis"]["peptideTol"] == 10.0
    assert config.mascot["mis"]["msmsTol"] == 0.5


def test_getParams_sq(mascot_panel):
    """Verify SQ parameters extraction from UI."""
    config.mascot["common"]["searchType"] = "sq"

    mascot_panel.paramSQTitle_value.SetValue("SQ Search")
    mascot_panel.paramSQPeptideTol_value.SetValue("1.5")
    mascot_panel.paramSQMSMSTol_value.SetValue("0.8")

    assert mascot_panel.getParams() is True
    assert config.mascot["sq"]["peptideTol"] == 1.5
    assert config.mascot["sq"]["msmsTol"] == 0.8
