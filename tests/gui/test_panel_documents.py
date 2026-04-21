import wx

from mmass.gui.ids import *
from mmass.gui.panel_documents import documentsTree, fileDropTarget, panelDocuments


# Dummy data classes to simulate mspy and doc objects without triggering heavy business logic
class DummyDocument:
    """Dummy document class."""

    def __init__(self, title="", visible=True, colour=(0, 0, 255), dirty=False):
        self.title = title
        self.visible = visible
        self.colour = colour
        self.dirty = dirty
        self.offset = [0, 0]
        self.style = wx.SOLID
        self.spectrum = type(
            "DummySpectrum", (object,), {"hasprofile": lambda self: True}
        )()
        self.annotations = []
        self.sequences = []
        self.bulletIndex = -1


class DummySequence:
    """Dummy sequence class."""

    def __init__(self, title=""):
        self.title = title
        self.matches = []

    def formula(self):
        return "C10H20"


class DummyAnnotation:
    """Dummy annotation class."""

    def __init__(
        self, label="", mz=0.0, formula=None, charge=1, radical=False, theoretical=None
    ):
        self.label = label
        self.mz = mz
        self.formula = formula
        self.charge = charge
        self.radical = radical
        self.theoretical = theoretical

    def delta(self, units):
        return 0.1


class DummyMatch:
    """Dummy match class."""

    def __init__(
        self,
        label="",
        mz=0.0,
        theoretical=None,
        formula=None,
        charge=1,
        radical=False,
        sequenceRange=None,
    ):
        self.label = label
        self.mz = mz
        self.theoretical = theoretical
        self.formula = formula
        self.charge = charge
        self.radical = radical
        self.sequenceRange = sequenceRange

    def delta(self, units):
        return 0.1


# MockParent class implementing required callbacks
class MockParent(wx.Frame):
    """Mock parent class with MagicMock callbacks."""

    def __init__(self, mocker):
        wx.Frame.__init__(self, None)
        self.onDocumentClose = mocker.MagicMock()
        self.onSequenceDelete = mocker.MagicMock()
        self.onDocumentSolo = mocker.MagicMock()
        self.onDocumentEnable = mocker.MagicMock()
        self.onDocumentSelected = mocker.MagicMock()
        self.onSequenceSelected = mocker.MagicMock()
        self.onDocumentDropped = mocker.MagicMock()
        self.onDocumentNew = mocker.MagicMock()
        self.onDocumentNewFromClipboard = mocker.MagicMock()
        self.onDocumentOpen = mocker.MagicMock()
        self.onDocumentInfo = mocker.MagicMock()
        self.onDocumentColour = mocker.MagicMock()
        self.onDocumentStyle = mocker.MagicMock()
        self.onDocumentFlip = mocker.MagicMock()
        self.onDocumentOffset = mocker.MagicMock()
        self.onDocumentNotationsDelete = mocker.MagicMock()
        self.onDocumentDuplicate = mocker.MagicMock()
        self.onDocumentCloseAll = mocker.MagicMock()
        self.onDocumentAnnotationsCalibrateBy = mocker.MagicMock()
        self.onDocumentAnnotationsDelete = mocker.MagicMock()
        self.onSequenceNew = mocker.MagicMock()
        self.onToolsSequence = mocker.MagicMock()
        self.onSequenceMatchesCalibrateBy = mocker.MagicMock()
        self.onSequenceMatchesDelete = mocker.MagicMock()
        self.onDocumentChanged = mocker.MagicMock()
        self.updateNotationMarks = mocker.MagicMock()
        self.updateMassPoints = mocker.MagicMock()
        self.onToolsMassCalculator = mocker.MagicMock()
        self.onToolsMassToFormula = mocker.MagicMock()
        self.onToolsEnvelopeFit = mocker.MagicMock()


# Test fileDropTarget
def test_fileDropTarget(mocker):
    """Test fileDropTarget correctly calls the callback."""
    mock_fn = mocker.MagicMock()
    target = fileDropTarget(mock_fn)

    paths = ["/path/to/file.mgf"]
    target.OnDropFiles(0, 0, paths)

    mock_fn.assert_called_once_with(paths=paths)


# Test documentsTree core data methods
def test_documentsTree_core_methods(wx_app, mocker):
    """Test documentsTree core data methods (getItemType, getItemIndent, getItemByData)."""
    frame = wx.Frame(None)
    tree = documentsTree(frame, -1)

    # Patch doc and mspy classes to match Dummy classes for getItemType
    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)

    # Create dummy data
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    annot_data = DummyAnnotation(label="Annot 1")
    match_data = DummyMatch(label="Match 1")

    doc_data.sequences = [seq_data]
    doc_data.annotations = [annot_data]
    seq_data.matches = [match_data]

    # Append items
    doc_item = tree.appendDocument(doc_data)

    # Get child items
    annots_node, cookie = tree.GetFirstChild(doc_item)  # "Annotations" node
    annot_item, cookie2 = tree.GetFirstChild(annots_node)  # individual annotation
    seq_item, cookie3 = tree.GetNextChild(doc_item, cookie)  # sequence item
    match_item, cookie4 = tree.GetFirstChild(seq_item)  # match item

    # Verify getItemType
    assert tree.getItemType(doc_item) == "document"
    assert tree.getItemType(annots_node) == "annotations"
    assert tree.getItemType(annot_item) == "annotation"
    assert tree.getItemType(seq_item) == "sequence"
    assert tree.getItemType(match_item) == "match"
    assert tree.getItemType(tree.GetRootItem()) is None

    # Verify getItemIndent
    assert tree.getItemIndent(doc_item) == 1
    assert tree.getItemIndent(annots_node) == 2
    assert tree.getItemIndent(annot_item) == 3
    assert tree.getItemIndent(seq_item) == 2
    assert tree.getItemIndent(match_item) == 3
    assert tree.getItemIndent(tree.GetRootItem()) == 0

    # Verify getItemByData
    assert tree.getItemByData(doc_data) == doc_item
    assert tree.getItemByData(doc_data.annotations) == annots_node
    assert tree.getItemByData(annot_data) == annot_item
    assert tree.getItemByData(seq_data) == seq_item
    assert tree.getItemByData(match_data) == match_item
    assert tree.getItemByData("NonExistent") is False

    frame.Destroy()


def test_documentsTree_visual_updates(wx_app, mocker):
    """Test documentsTree node appending and visual updates (Step 4)."""
    frame = wx.Frame(None)
    tree = documentsTree(frame, -1)

    # Patch doc and mspy classes to match Dummy classes for appendDocument
    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)

    # Create dummy data
    doc_data = DummyDocument(title="Doc 1", colour=(255, 0, 0), visible=True)
    seq_data = DummySequence(title="Seq 1")
    doc_data.sequences = [seq_data]

    # Test appendDocument
    doc_item = tree.appendDocument(doc_data)
    assert tree.GetItemText(doc_item) == "Doc 1"
    assert doc_data.bulletIndex != -1
    assert tree.GetItemImage(doc_item) == doc_data.bulletIndex

    # Test annotations node
    annots_node, cookie = tree.GetFirstChild(doc_item)
    assert tree.GetItemText(annots_node) == "Annotations"
    assert tree.GetItemImage(annots_node) == 2  # 2 is 'bulletsAnnotationsOn'

    # Test sequence node
    seq_item, cookie = tree.GetNextChild(doc_item, cookie)
    assert tree.GetItemText(seq_item) == "Seq 1"
    assert tree.GetItemImage(seq_item) == 4  # 4 is 'bulletsSequenceOn'

    # Test enableItemTree(item, False)
    tree.enableItemTree(doc_item, False)
    assert tree.GetItemTextColour(doc_item) == (150, 150, 150)
    assert tree.GetItemImage(doc_item) == 1  # 1 is disabled doc bullet
    assert tree.GetItemTextColour(annots_node) == (150, 150, 150)
    assert tree.GetItemImage(annots_node) == 3  # 3 is 'bulletsAnnotationsOff'
    assert tree.GetItemTextColour(seq_item) == (150, 150, 150)
    assert tree.GetItemImage(seq_item) == 5  # 5 is 'bulletsSequenceOff'

    # Test updateDocumentColour(item)
    old_bullet_index = doc_data.bulletIndex
    doc_data.colour = (0, 255, 0)
    tree.updateDocumentColour(
        seq_item
    )  # pass child item to check getParentItem(item, 1)
    assert doc_data.bulletIndex > old_bullet_index
    assert tree.GetItemImage(doc_item) == doc_data.bulletIndex

    frame.Destroy()


def test_panelDocuments_initialization(wx_app, mocker):
    """Test panelDocuments initialization and UI (Step 5)."""
    parent = MockParent(mocker)
    documents = [DummyDocument(title="Doc 1")]

    # Patch config.main to avoid KeyError
    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)

    assert panel.parent == parent
    assert panel.documents == documents
    assert hasattr(panel, "documentTree")
    assert isinstance(panel.documentTree, documentsTree)

    # Assert toolbar buttons
    assert hasattr(panel, "add_butt")
    assert isinstance(panel.add_butt, wx.BitmapButton)
    assert hasattr(panel, "delete_butt")
    assert isinstance(panel.delete_butt, wx.BitmapButton)

    # Assert buttons are added to the sizer
    sizer_items = [
        item.GetWindow() for item in panel.GetSizer().GetChildren() if item.IsWindow()
    ]
    assert panel.documentTree in sizer_items

    # toolbar is the second item in mainSizer
    toolbar_panel = sizer_items[1]
    assert toolbar_panel.GetSizer() is not None

    # The toolbar panel has a VERTICAL sizer containing a HORIZONTAL sizer
    toolbar_main_sizer = toolbar_panel.GetSizer()
    inner_sizer = toolbar_main_sizer.GetChildren()[0].GetSizer()
    assert inner_sizer is not None

    toolbar_items = [
        item.GetWindow() for item in inner_sizer.GetChildren() if item.IsWindow()
    ]
    assert panel.add_butt in toolbar_items
    assert panel.delete_butt in toolbar_items

    parent.Destroy()


def test_panelDocuments_onKey(wx_app, mocker):
    """Test onKey event handler (Step 6)."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    doc_data.sequences = [seq_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)

    # Select document and press DELETE
    doc_item = tree.appendDocument(doc_data)
    tree.SelectItem(doc_item)

    mock_event = mocker.MagicMock(spec=wx.TreeEvent)
    mock_event.GetKeyCode.return_value = wx.WXK_DELETE
    mock_event.GetKeyEvent.return_value = mocker.MagicMock()

    panel.onKey(mock_event)
    parent.onDocumentClose.assert_called_once()

    # Select sequence and press DELETE
    seq_item = tree.getItemByData(seq_data)
    tree.SelectItem(seq_item)

    panel.onKey(mock_event)
    parent.onSequenceDelete.assert_called_once()

    parent.Destroy()


def test_panelDocuments_onLMD(wx_app, mocker):
    """Test onLMD event handler (Step 6)."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    doc_item = tree.appendDocument(doc_data)

    # Mock MouseEvent and HitTest
    mock_event = mocker.MagicMock(spec=wx.MouseEvent)
    mock_event.GetPosition.return_value = (10, 10)
    mock_event.AltDown.return_value = False
    mock_event.ControlDown.return_value = False

    mocker.patch.object(
        tree, "HitTest", return_value=(doc_item, wx.TREE_HITTEST_ONITEMICON)
    )
    panel.onLMD(mock_event)
    parent.onDocumentEnable.assert_called_once_with(0)

    # Test Solo (AltDown)
    mock_event.AltDown.return_value = True
    mocker.patch.object(tree, "HitTest", return_value=(doc_item, 0))
    panel.onLMD(mock_event)
    parent.onDocumentSolo.assert_called_once_with(0)

    parent.Destroy()


def test_panelDocuments_onItemSelecting(wx_app, mocker):
    """Test onItemSelecting event handler (Step 6)."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1", visible=False)
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    doc_item = tree.appendDocument(doc_data)

    mock_event = mocker.MagicMock(spec=wx.TreeEvent)
    mock_event.GetItem.return_value = doc_item

    panel.onItemSelecting(mock_event)
    mock_event.Veto.assert_called_once()

    parent.Destroy()


def test_panelDocuments_onRMU(wx_app, mocker):
    """Test onRMU context menu generation (Step 7)."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    annot_data = DummyAnnotation(label="Annot 1")
    doc_data.sequences = [seq_data]
    doc_data.annotations = [annot_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    mocker.patch("mmass.gui.panel_documents.config.spectrum", {"normalize": False})
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    # Mock PopupMenu to avoid actually trying to show it
    panel.PopupMenu = mocker.MagicMock()

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    MockMenu = mocker.patch("mmass.gui.panel_documents.wx.Menu")

    class MenuTracker:
        def __init__(self):
            self.menus = []

        def __call__(self, *args, **kwargs):
            m = mocker.MagicMock()
            # Mock Append to track IDs
            m.Append = mocker.MagicMock()
            m.AppendMenu = mocker.MagicMock()
            m.Enable = mocker.MagicMock()
            m.Check = mocker.MagicMock()
            self.menus.append(m)
            return m

    tracker = MenuTracker()
    MockMenu.side_effect = tracker

    doc_item = tree.appendDocument(doc_data)

    # Select Document and trigger RMU
    tree.SelectItem(doc_item)
    panel.onRMU(None)

    # The first menu created is 'menu'
    menu = tracker.menus[0]
    appended_ids = [
        call[0][0] for call in menu.Append.call_args_list if len(call[0]) > 0
    ]
    assert ID_sequenceNew in appended_ids
    assert ID_documentFlip in appended_ids
    assert ID_documentClose in appended_ids

    # Select Sequence and trigger RMU
    tracker.menus = []
    seq_item = tree.getItemByData(seq_data)
    tree.SelectItem(seq_item)
    panel.onRMU(None)

    menu = tracker.menus[0]
    appended_ids = [
        call[0][0] for call in menu.Append.call_args_list if len(call[0]) > 0
    ]
    assert ID_sequenceDigest in appended_ids
    assert ID_sequenceSearch in appended_ids

    # Select Annotation and trigger RMU
    tracker.menus = []
    annots_node = tree.getItemByData(doc_data.annotations)
    annot_item, cookie = tree.GetFirstChild(annots_node)
    tree.SelectItem(annot_item)
    panel.onRMU(None)

    menu = tracker.menus[0]
    appended_ids = [
        call[0][0] for call in menu.Append.call_args_list if len(call[0]) > 0
    ]
    assert ID_documentAnnotationEdit in appended_ids
    assert ID_documentAnnotationDelete in appended_ids

    parent.Destroy()


def test_panelDocuments_API_Synchronization(wx_app, mocker):
    """Test panelDocuments API Synchronization methods (Step 8)."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1", dirty=False)
    annot1 = DummyAnnotation(label="Annot 1", mz=100.0)
    doc_data.annotations = [annot1]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)

    doc_item = tree.appendDocument(doc_data)

    # 1. Test updateDocumentTitle(docIndex)
    # Not dirty
    panel.updateDocumentTitle(0)
    assert tree.GetItemText(doc_item) == "Doc 1"

    # Dirty
    doc_data.dirty = True
    panel.updateDocumentTitle(0)
    assert tree.GetItemText(doc_item) == "*Doc 1"

    # 2. Test updateAnnotations(docIndex)
    annots_node = tree.getItemByData(doc_data.annotations)
    assert tree.GetChildrenCount(annots_node, recursively=False) == 1

    # Add another annotation to data
    annot2 = DummyAnnotation(label="Annot 2", mz=200.0)
    doc_data.annotations.append(annot2)

    panel.updateAnnotations(0)
    assert tree.GetChildrenCount(annots_node, recursively=False) == 2

    # Check labels
    child, cookie = tree.GetFirstChild(annots_node)
    assert "Annot 1" in tree.GetItemText(child)
    child, cookie = tree.GetNextChild(annots_node, cookie)
    assert "Annot 2" in tree.GetItemText(child)

    # 3. Test selectDocument(docIndex)
    # If we call panel.selectDocument(0)
    panel.selectDocument(0)

    assert tree.IsBold(doc_item)
    parent.onDocumentSelected.assert_called_with(0)

    # Select None
    # Note: selectDocument(None) calls Unselect() but not highlightDocument(None)
    # so the item might stay bold in the current implementation.
    # We verify that parent.onDocumentSelected(None) is called.
    panel.selectDocument(None)
    parent.onDocumentSelected.assert_called_with(None)

    parent.Destroy()


def test_panelDocuments_onItemActivated(wx_app, mocker):
    """Test onItemActivated event handler."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    annot_data = DummyAnnotation(label="Annot 1")
    match_data = DummyMatch(label="Match 1")
    doc_data.sequences = [seq_data]
    doc_data.annotations = [annot_data]
    seq_data.matches = [match_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)

    doc_item = tree.appendDocument(doc_data)
    annots_node = tree.getItemByData(doc_data.annotations)
    annot_item, _ = tree.GetFirstChild(annots_node)
    seq_item = tree.getItemByData(seq_data)
    match_item, _ = tree.GetFirstChild(seq_item)

    mock_event = mocker.MagicMock(spec=wx.TreeEvent)

    # Test document activation
    mock_event.GetItem.return_value = doc_item
    panel.onItemActivated(mock_event)
    parent.onDocumentInfo.assert_called_once()

    # Test sequence activation
    mock_event.GetItem.return_value = seq_item
    panel.onItemActivated(mock_event)
    parent.onToolsSequence.assert_called_once()

    # Test annotation activation (calls onNotationEdit)
    mock_edit = mocker.patch.object(panel, "onNotationEdit")
    mock_event.GetItem.return_value = annot_item
    panel.onItemActivated(mock_event)
    mock_edit.assert_called_once()

    # Test match activation
    mock_edit.reset_mock()
    mock_event.GetItem.return_value = match_item
    panel.onItemActivated(mock_event)
    mock_edit.assert_called_once()

    # Test disabled document
    doc_data.visible = False
    mock_event.GetItem.return_value = doc_item
    mock_bell = mocker.patch("wx.Bell")
    panel.onItemActivated(mock_event)
    mock_bell.assert_called_once()

    parent.Destroy()


def test_panelDocuments_onAdd_onDelete(wx_app, mocker):
    """Test onAdd and onDelete button handlers."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    doc_data.sequences = [seq_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    panel.PopupMenu = mocker.MagicMock()
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    MockMenu = mocker.patch("mmass.gui.panel_documents.wx.Menu")

    menu = mocker.MagicMock()
    MockMenu.return_value = menu

    doc_item = tree.appendDocument(doc_data)
    tree.SelectItem(doc_item)

    # Test onAdd
    panel.onAdd(None)
    assert menu.Enable.called
    panel.PopupMenu.assert_called_with(menu)

    # Test onDelete
    panel.onDelete(None)
    assert menu.Enable.called
    panel.PopupMenu.assert_called_with(menu)

    parent.Destroy()


def test_panelDocuments_NotationHandlers(wx_app, mocker):
    """Test onNotationEdit and onNotationDelete."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    annot_data = DummyAnnotation(label="Annot 1", mz=100.0)
    match_data = DummyMatch(label="Match 1", mz=200.0)
    doc_data.annotations = [annot_data]
    seq_data = DummySequence(title="Seq 1")
    seq_data.matches = [match_data]
    doc_data.sequences = [seq_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)
    MockDlg = mocker.patch("mmass.gui.panel_documents.dlgNotation")

    doc_item = tree.appendDocument(doc_data)
    annots_node = tree.getItemByData(doc_data.annotations)
    annot_item, _ = tree.GetFirstChild(annots_node)
    seq_item = tree.getItemByData(seq_data)
    match_item, _ = tree.GetFirstChild(seq_item)

    # Test onNotationEdit - Annotation
    tree.SelectItem(annot_item)
    dlg = MockDlg.return_value
    dlg.ShowModal.return_value = wx.ID_OK

    panel.onNotationEdit()
    parent.onDocumentChanged.assert_called_with(items=("annotations"))

    # Test onNotationEdit - Match
    tree.SelectItem(match_item)
    panel.onNotationEdit()
    parent.onDocumentChanged.assert_called_with(items=("matches"))

    # Test onNotationDelete - Annotation
    tree.SelectItem(annot_item)
    panel.onNotationDelete()
    parent.onDocumentAnnotationsDelete.assert_called_with(annotIndex=0)

    # Test onNotationDelete - Match
    tree.SelectItem(match_item)
    panel.onNotationDelete()
    parent.onSequenceMatchesDelete.assert_called_with(matchIndex=0)

    parent.Destroy()


def test_panelDocuments_SendToHandlers(wx_app, mocker):
    """Test onSendToMassCalculator, onSendToMassToFormula, onSendToEnvelopeFit."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    annot_data = DummyAnnotation(
        label="Annot 1", mz=100.0, formula="C1H1", charge=1, radical=False
    )
    match_data = DummyMatch(
        label="Match 1",
        mz=200.0,
        formula="C2H2",
        charge=2,
        radical=True,
        sequenceRange=[10, 20],
    )
    doc_data.sequences = [seq_data]
    doc_data.annotations = [annot_data]
    seq_data.matches = [match_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    mocker.patch(
        "mmass.gui.panel_documents.config.envelopeFit", {"loss": "H", "gain": "H{2}"}
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)

    doc_item = tree.appendDocument(doc_data)
    seq_item = tree.getItemByData(seq_data)
    annots_node = tree.getItemByData(doc_data.annotations)
    annot_item, _ = tree.GetFirstChild(annots_node)
    match_item, _ = tree.GetFirstChild(seq_item)

    # 1. onSendToMassCalculator
    # Sequence
    tree.SelectItem(seq_item)
    panel.onSendToMassCalculator()
    parent.onToolsMassCalculator.assert_called_with(formula="C10H20")

    # Annotation (not radical)
    tree.SelectItem(annot_item)
    panel.onSendToMassCalculator()
    parent.onToolsMassCalculator.assert_called_with(
        formula="C1H1", charge=1, agentFormula="H", agentCharge=1
    )

    # Match (radical)
    tree.SelectItem(match_item)
    panel.onSendToMassCalculator()
    parent.onToolsMassCalculator.assert_called_with(
        formula="C2H2", charge=2, agentFormula="e", agentCharge=-1
    )

    # 2. onSendToMassToFormula
    # Annotation
    tree.SelectItem(annot_item)
    panel.onSendToMassToFormula()
    parent.onToolsMassToFormula.assert_called_with(
        mass=100.0, charge=1, agentFormula="H"
    )

    # Match (radical)
    tree.SelectItem(match_item)
    panel.onSendToMassToFormula()
    parent.onToolsMassToFormula.assert_called_with(
        mass=200.0, charge=2, agentFormula="e"
    )

    # 3. onSendToEnvelopeFit
    # Sequence
    tree.SelectItem(seq_item)
    panel.onSendToEnvelopeFit()
    parent.onToolsEnvelopeFit.assert_called_with(sequence=seq_data)

    # Annotation
    tree.SelectItem(annot_item)
    panel.onSendToEnvelopeFit()
    parent.onToolsEnvelopeFit.assert_called_with(formula="C1H1", charge=1)

    # Match
    tree.SelectItem(match_item)
    panel.onSendToEnvelopeFit()
    parent.onToolsEnvelopeFit.assert_called_with(
        formula="C2H2", charge=2, scale=[0, 10]
    )

    parent.Destroy()


def test_panelDocuments_DocumentMethods(wx_app, mocker):
    """Test document methods: appendLastDocument, deleteDocument, enableDocument, updateDocumentColour."""
    parent = MockParent(mocker)
    doc_data1 = DummyDocument(title="Doc 1")
    documents = [doc_data1]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    doc_item1 = tree.appendDocument(doc_data1)

    # appendLastDocument
    doc_data2 = DummyDocument(title="Doc 2")
    documents.append(doc_data2)
    panel.appendLastDocument()
    assert tree.getItemByData(doc_data2) is not False

    # enableDocument
    panel.enableDocument(0, False)
    assert tree.GetItemTextColour(doc_item1) == (150, 150, 150)

    # updateDocumentColour
    doc_data1.colour = (0, 255, 0)
    panel.updateDocumentColour(0)
    # Indirectly verified by no crash and internal state change

    # deleteDocument
    panel.deleteDocument(0)
    assert tree.getItemByData(doc_data1) is False

    parent.Destroy()


def test_panelDocuments_SequenceMethods(wx_app, mocker):
    """Test sequence methods: selectSequence, appendLastSequence, deleteSequence, updateSequenceTitle, updateSequenceMatches."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data1 = DummySequence(title="Seq 1")
    doc_data.sequences = [seq_data1]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)

    doc_item = tree.appendDocument(doc_data)
    seq_item1 = tree.getItemByData(seq_data1)

    # selectSequence
    panel.selectSequence(0, 0)
    assert tree.GetSelection() == seq_item1

    # appendLastSequence
    seq_data2 = DummySequence(title="Seq 2")
    doc_data.sequences.append(seq_data2)
    panel.appendLastSequence(0)
    seq_item2 = tree.getItemByData(seq_data2)
    assert seq_item2 is not False

    # updateSequenceTitle
    seq_data1.title = "New Seq Title"
    panel.updateSequenceTitle(0, 0)
    assert tree.GetItemText(seq_item1) == "New Seq Title"

    # updateSequenceMatches
    match1 = DummyMatch(label="Match 1", mz=100.0)
    seq_data1.matches = [match1]
    panel.updateSequenceMatches(0, 0, expand=True)
    assert tree.GetChildrenCount(seq_item1, recursively=False) == 1

    # deleteSequence
    panel.deleteSequence(0, 0)
    assert tree.getItemByData(seq_data1) is False

    parent.Destroy()


def test_panelDocuments_updateSequences(wx_app, mocker):
    """Test updateSequences method."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data1 = DummySequence(title="Seq 1")
    doc_data.sequences = [seq_data1]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)

    doc_item = tree.appendDocument(doc_data)

    # Add new sequence
    seq_data2 = DummySequence(title="Seq 2")
    doc_data.sequences.append(seq_data2)

    # updateSequences
    panel.updateSequences(0)
    assert tree.getItemByData(seq_data2) is not False
    assert tree.getItemByData(seq_data1) is not False

    parent.Destroy()


def test_panelDocuments_onDelete_ItemSpecific(wx_app, mocker):
    """Test onDelete button handlers for various selected item types."""
    parent = MockParent(mocker)
    doc_data = DummyDocument(title="Doc 1")
    seq_data = DummySequence(title="Seq 1")
    annot_data = DummyAnnotation(label="Annot 1")
    match_data = DummyMatch(label="Match 1")
    doc_data.sequences = [seq_data]
    doc_data.annotations = [annot_data]
    seq_data.matches = [match_data]
    documents = [doc_data]

    mocker.patch(
        "mmass.gui.panel_documents.config.main",
        {"mzDigits": 4, "ppmDigits": 2, "errorUnits": "ppm"},
    )
    panel = panelDocuments(parent, documents)
    panel.PopupMenu = mocker.MagicMock()
    tree = panel.documentTree

    mocker.patch("mmass.gui.panel_documents.doc.document", DummyDocument)
    mocker.patch("mmass.gui.panel_documents.mspy.sequence", DummySequence)
    mocker.patch("mmass.gui.panel_documents.doc.annotation", DummyAnnotation)
    mocker.patch("mmass.gui.panel_documents.doc.match", DummyMatch)
    MockMenu = mocker.patch("mmass.gui.panel_documents.wx.Menu")

    menu = mocker.MagicMock()
    MockMenu.return_value = menu

    doc_item = tree.appendDocument(doc_data)
    annots_node = tree.getItemByData(doc_data.annotations)
    annot_item, _ = tree.GetFirstChild(annots_node)
    seq_item = tree.getItemByData(seq_data)
    match_item, _ = tree.GetFirstChild(seq_item)

    # Test Annotation selected
    tree.SelectItem(annot_item)
    panel.onDelete(None)

    # Test Sequence selected
    tree.SelectItem(seq_item)
    panel.onDelete(None)

    # Test Match selected
    tree.SelectItem(match_item)
    panel.onDelete(None)

    parent.Destroy()
