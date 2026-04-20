import pytest
wx = pytest.importorskip("wx")

import numpy
from hypothesis import given, strategies as st, settings, HealthCheck
from mspy.plot_canvas import canvas, _scaleFont

@pytest.fixture(scope="session")
def wx_app():
    """Session-scoped fixture to initialize wx.App for headless UI testing."""
    app = wx.App(False)
    yield app
    # No explicit app.MainLoop() or app.Exit() needed for these tests

@pytest.fixture
def canvas_fixture(wx_app, mocker):
    """Fixture to provide an initialized canvas instance with a real parent frame."""
    # Create a real frame to act as the parent for the canvas
    parent_frame = wx.Frame(None)
    
    # Mock onSize only during initialization to avoid C++ assertion errors in headless environments
    orig_onSize = canvas.onSize
    canvas.onSize = mocker.Mock()
    
    # Instantiate the canvas
    plot_canvas = canvas(parent=parent_frame, size=(800, 600))
    
    # Restore the original onSize so it can be tested/used later
    canvas.onSize = orig_onSize
    
    # Provide a mock plotBuffer since onSize was skipped during __init__
    plot_canvas.plotBuffer = mocker.Mock()
    
    yield plot_canvas
    
    # Cleanup
    plot_canvas.Destroy()
    parent_frame.Destroy()

def mock_mouse_event(mocker, x, y, control_down=False):
    """Helper to create a mock wx.MouseEvent."""
    evt = mocker.Mock(spec=wx.MouseEvent)
    evt.GetPosition.return_value = (x, y)
    evt.GetX.return_value = x
    evt.GetY.return_value = y
    evt.ControlDown.return_value = control_down
    evt.ShiftDown.return_value = False
    evt.AltDown.return_value = False
    evt.LeftDown.return_value = True
    evt.LeftIsDown.return_value = True
    evt.GetWheelRotation.return_value = 0
    return evt

@pytest.fixture
def setup_canvas_for_tracking(canvas_fixture, mocker):
    """Fixture to prepare canvas for interaction/tracking tests."""
    # Step 1 Requirements:
    # Sets canvas_fixture.plotCoords = [10, 10, 190, 190]
    canvas_fixture.plotCoords = [10, 10, 190, 190]
    
    # Sets canvas_fixture.cursorPosition = [50.0, 100.0, 50, 100]
    canvas_fixture.cursorPosition = [50.0, 100.0, 50, 100]
    
    # Mocks canvas_fixture.getXY to return (50.0, 100.0)
    # This fixed the indexing error previously seen with side_effect functions
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 100.0))
    
    # Mocks canvas_fixture.getCursorLocation to return 'plot'
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    
    # Additional mocks for headless safety and required attributes
    mocker.patch.object(canvas_fixture, 'SetCursor')
    mocker.patch.object(canvas_fixture, 'drawInvertedText')
    
    # Set transformation to identity for predictable coordinate mapping
    canvas_fixture.pointScale = numpy.array([1.0, 1.0])
    canvas_fixture.pointShift = numpy.array([0.0, 0.0])
    
    # Mock DC
    mock_dc = mocker.Mock()
    # Fixed: GetTextExtent must return a tuple, not a mock, to support indexing like textSize[1]
    mock_dc.GetTextExtent.return_value = (50, 20)
    mocker.patch('wx.ClientDC', return_value=mock_dc)
    
    return canvas_fixture, mock_dc

def test_drawPointTracker(setup_canvas_for_tracking, mocker):
    """Test drawPointTracker logic for both Mac and non-Mac platforms."""
    canvas, mock_dc = setup_canvas_for_tracking
    
    # Mock currentObject and getPoint as per Step 2
    canvas.currentObject = mocker.Mock()
    mocker.patch.object(canvas, 'getPoint', return_value=(50, 80))
    
    # Parametrize platform check manually to cover both branches
    for platform in ['__WXMSW__', '__WXMAC__']:
        mocker.patch('wx.Platform', platform)
        mock_dc.DrawLine.reset_mock()
        
        canvas.drawPointTracker()
        
        # Verify vertical tracker line
        if platform == '__WXMAC__':
            mock_dc.DrawLine.assert_any_call(50, 10, 50, 189) # minY to maxY-1
        else:
            mock_dc.DrawLine.assert_any_call(50, 10, 50, 190) # minY to maxY
            
        # Verify horizontal crosshair line at currentY
        mock_dc.DrawLine.assert_any_call(45, 80, 56, 80) # x-5 to x+6 at y=80
        
        # Verify text was drawn since showCurXPos is True by default
        canvas.drawInvertedText.assert_called()

def test_canvas_initialization(wx_app, canvas_fixture):
    """Sanity test to verify that the canvas initializes correctly."""
    assert isinstance(canvas_fixture, canvas)
    assert isinstance(canvas_fixture.properties, dict)
    assert 'isotopeDistance' in canvas_fixture.properties

def test_scaleFont(wx_app):
    """Test _scaleFont helper function."""
    # Initialize a custom wx.Font base object
    base_font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "Arial")
    
    # Identity Check: scale == 1.0 should return the same object
    scaled_font_1 = _scaleFont(base_font, 1.0)
    assert scaled_font_1 is base_font
    
    # Magnification Check: scale == 2.0
    scaled_font_2 = _scaleFont(base_font, 2.0)
    # The implementation is: pointSize = pointSize * scale * 1.3
    # 10 * 2.0 * 1.3 = 26.0
    assert scaled_font_2.GetPointSize() == 26
    assert scaled_font_2.GetWeight() == base_font.GetWeight()
    assert scaled_font_2.GetStyle() == base_font.GetStyle()
    assert scaled_font_2.GetFamily() == base_font.GetFamily()
    
    # Minification Check: scale == 0.5
    scaled_font_05 = _scaleFont(base_font, 0.5)
    # 10 * 0.5 * 1.3 = 6.5
    # wx.Font might round this. Let's see what it returns.
    # In Python 2.7, 6.5 passed to wx.Font(pointSize, ...) might be cast to int.
    assert scaled_font_05.GetPointSize() in (6, 7)
    assert scaled_font_05.GetWeight() == base_font.GetWeight()
    assert scaled_font_05.GetStyle() == base_font.GetStyle()
    assert scaled_font_05.GetFamily() == base_font.GetFamily()

@pytest.mark.parametrize("lower, upper", [
    (0.1, 0.2),      # Small range
    (100, 1000),     # Standard range
    (1e5, 1e6)       # Large/Scientific range
])
def test_makeAxisTicks(canvas_fixture, lower, upper):
    """Test makeAxisTicks method."""
    ticks = canvas_fixture.makeAxisTicks(lower, upper)
    
    # Assert ticks is a standard Python list
    assert isinstance(ticks, list)
    assert len(ticks) > 0
    
    # Iterate over ticks asserting that each element is a tuple with 3 exact items:
    # a float, a string, and a string.
    for tick in ticks:
        assert isinstance(tick, tuple)
        assert len(tick) == 3
        assert isinstance(tick[0], (float, int, numpy.float64))
        assert isinstance(tick[1], str)
        assert tick[2] in ('major', 'minor')
    
    # Assert that ticks are within the requested range (with small tolerance for floats)
    # The implementation uses while t <= upper, so ticks should be <= upper.
    # It also ensures t starts such that the first tick is >= lower.
    assert ticks[0][0] >= lower - 1e-12
    assert ticks[-1][0] <= upper + 1e-12

def test_makeAxisTicks_formatting(canvas_fixture):
    """Test formatting-specific logic in makeAxisTicks."""
    # Scientific notation check (power > 4)
    # range 1e5 to 1.1e5 -> ideal = 1e4/7 = 1428 -> log10 = 3.15 -> power = 3.
    # Wait, power needs to be > 4 for scientific notation.
    # range 1e6 to 2e6 -> ideal = 1e6/7 = 142857 -> log10 = 5.15 -> power = 5.
    ticks = canvas_fixture.makeAxisTicks(1e6, 2e6)
    # The major ticks should have 'e' in their labels
    major_ticks = [t for t in ticks if t[2] == 'major']
    for t in major_ticks:
        assert 'e' in t[1].lower()
    
    # Small value formatting (power < 0)
    # range 0.001 to 0.002 -> ideal = 0.001/7 = 0.00014 -> log10 = -3.8 -> power = -4.
    # power < 0 but >= -4 should use decimal format with specific digits.
    ticks_small = canvas_fixture.makeAxisTicks(0.001, 0.002)
    major_ticks_small = [t for t in ticks_small if t[2] == 'major']
    # For power = -4, format should be '%6.4f'
    for t in major_ticks_small:
        assert '.' in t[1]
        assert 'e' not in t[1].lower()
    
    # Very small value (power < -4)
    ticks_tiny = canvas_fixture.makeAxisTicks(0.00001, 0.00002)
    # ideal = 0.00001/7 = 1.4e-6 -> power = -6.
    # power < -4 -> format = '%7.1e'
    major_ticks_tiny = [t for t in ticks_tiny if t[2] == 'major']
    for t in major_ticks_tiny:
        assert 'e' in t[1].lower()

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(x=st.floats(min_value=-1e6, max_value=1e6), y=st.floats(min_value=-1e6, max_value=1e6))
def test_coordinate_transformations_roundtrip(canvas_fixture, x, y):
    """Test roundtrip of positionUserToScreen and positionScreenToUser."""
    # Set artificial transformation parameters
    canvas_fixture.pointScale = numpy.array([2.5, -1.5])
    canvas_fixture.pointShift = numpy.array([10.0, 50.0])
    
    # Transform (x, y) using positionUserToScreen
    # positionUserToScreen takes userPos = (x, y)
    screen_pos = canvas_fixture.positionUserToScreen((x, y))
    
    # Transform back using positionScreenToUser
    # positionScreenToUser takes screenPos = (x, y)
    roundtrip_pos = canvas_fixture.positionScreenToUser(screen_pos)
    
    # Assert coordinates match (x, y) with tolerance
    numpy.testing.assert_allclose(roundtrip_pos, [x, y], atol=1e-7)

@pytest.mark.parametrize("c1, c2, expected", [
    # (x1, y1), (x2, y2) -> (x_start, y_start, width, height)
    ((10, 20), (30, 40), (20, 60, 40, 60)), # Top-left to bottom-right (user coords)
    ((30, 40), (10, 20), (20, 60, 40, 60)), # Bottom-right to top-left (user coords)
    ((10, 40), (30, 20), (20, 60, 40, 60)), # Bottom-left to top-right (user coords)
])
def test_pointToClientCoord_positive_dimensions(canvas_fixture, c1, c2, expected):
    """Test pointToClientCoord with bounding boxes in various orientations."""
    # Mock scale and shift:
    # pointScale = screen/user
    # x_screen = x_user * 2.0 + 0.0
    # y_screen = y_user * 3.0 + 0.0
    # BUT wait, the implementation is pointScale * userPos + pointShift
    # So for user y=20, y_screen = 20 * 3.0 = 60.
    # For user y=40, y_screen = 40 * 3.0 = 120.
    # pointToClientCoord uses positionUserToScreen.
    
    canvas_fixture.pointScale = numpy.array([2.0, 3.0])
    canvas_fixture.pointShift = numpy.array([0.0, 0.0])
    
    client_coord = canvas_fixture.pointToClientCoord(c1, c2)
    
    # client_coord = (x, y, width, height)
    assert client_coord == expected

@pytest.mark.parametrize("cursor_pos, expected_location", [
    ([0, 0, 50, 50], 'plot'),    # Inside (10, 10, 100, 100)
    ([0, 0, 50, 110], 'xAxis'),  # x inside, y > 100
    ([0, 0, 5, 50], 'yAxis'),    # x < 10, y inside
    ([0, 0, 110, 110], 'blank'), # Outside both
    ([0, 0, 10, 10], 'blank'),   # Edge check (exclusive)
    ([0, 0, 100, 100], 'blank'), # Edge check (exclusive)
])
def test_getCursorLocation(canvas_fixture, cursor_pos, expected_location):
    """Test getCursorLocation based on boundaries."""
    # Pre-configure plotCoords: (minX, minY, maxX, maxY)
    canvas_fixture.plotCoords = (10, 10, 100, 100)
    canvas_fixture.cursorPosition = cursor_pos
    
    assert canvas_fixture.getCursorLocation() == expected_location

def test_setProperties(canvas_fixture):
    """Test setProperties method."""
    canvas_fixture.setProperties(showGrid=False, maxZoom=0.05)
    assert canvas_fixture.properties['showGrid'] is False
    assert canvas_fixture.properties['maxZoom'] == 0.05

def test_setSize(canvas_fixture):
    """Test setSize method."""
    canvas_fixture.setSize(width=800, height=600)
    assert numpy.array_equal(canvas_fixture.plotBoxSize, numpy.array([800, 600]))
    # x0 = 0.5 * (800 - 800) = 0.0
    # y0 = 600 - 0.5 * (600 - 600) = 600.0
    assert numpy.array_equal(canvas_fixture.plotBoxOrigin, numpy.array([0.0, 600.0]))

def test_setCurrentObject(canvas_fixture):
    """Test setCurrentObject method."""
    dummy_obj = "dummy"
    canvas_fixture.setCurrentObject(dummy_obj)
    assert canvas_fixture.currentObject == dummy_obj

def test_setPrinterScale(canvas_fixture):
    """Test setPrinterScale method."""
    canvas_fixture.setPrinterScale(drawings=2, fonts=3)
    assert canvas_fixture.printerScale['drawings'] == 2
    assert canvas_fixture.printerScale['fonts'] == 3

def test_rememberView_capacity(canvas_fixture, mocker):
    """Test rememberView capacity constraint."""
    # Mock getCurrentXRange and getCurrentYRange since they are called if args are None
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(0, 10))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 100))
    
    # Clear memory
    canvas_fixture.viewMemory = [[], []]
    
    # Fill memory
    for i in range(55):
        canvas_fixture.rememberView((i, i+1), (0, 100))
    
    assert len(canvas_fixture.viewMemory[0]) == 50
    assert canvas_fixture.viewMemory[1] == []
    # Verify the last entry is the 55th one
    assert canvas_fixture.viewMemory[0][-1] == ((54, 55), (0, 100))

def test_rememberView_deduplication(canvas_fixture):
    """Test rememberView deduplication logic."""
    canvas_fixture.viewMemory = [[], []]
    canvas_fixture.rememberView((0, 10), (0, 100))
    canvas_fixture.rememberView((0, 10), (0, 100))
    assert len(canvas_fixture.viewMemory[0]) == 1

def test_rememberView_defaults(canvas_fixture, mocker):
    """Test rememberView with default arguments."""
    mock_x = mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(10, 20))
    mock_y = mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(30, 40))
    
    canvas_fixture.viewMemory = [[], []]
    canvas_fixture.rememberView()
    
    mock_x.assert_called_once()
    mock_y.assert_called_once()
    assert canvas_fixture.viewMemory[0][0] == ((10, 20), (30, 40))

def test_zoom_coordinate_swapping(canvas_fixture, mocker):
    """Test zoom swaps Y coordinates if yAxis[1] < yAxis[0]."""
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 100))
    
    # Setup lastDraw for graphics object
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 0), (100, 100))
    canvas_fixture.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    
    canvas_fixture.zoom(xAxis=(10, 20), yAxis=(50, 10))
    
    # Assert draw was called with swapped yAxis
    mock_draw.assert_called_once_with(mock_graphics, (10, 20), (10, 50))

def test_zoom_maxZoom_constraint(canvas_fixture, mocker):
    """Test zoom respects maxZoom constraint."""
    canvas_fixture.properties['maxZoom'] = 0.5
    canvas_fixture.properties['checkLimits'] = True
    
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(5, 15))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 100))
    
    # Setup lastDraw
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (5, 15), (0, 100))
    
    # Try to zoom to a range smaller than 0.5
    canvas_fixture.zoom(xAxis=(10, 10.1), yAxis=(0, 100))
    
    # It should fallback to current X range (5, 15)
    mock_draw.assert_called_once_with(mock_graphics, (5, 15), (0, 100))

def test_zoom_autoScaleY(canvas_fixture, mocker):
    """Test zoom with autoScaleY=True."""
    canvas_fixture.properties['autoScaleY'] = True
    
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 100))
    mock_get_max_y = mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(10, 200))
    
    # Setup lastDraw
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    
    canvas_fixture.zoom(xAxis=(0, 50))
    
    mock_get_max_y.assert_called_once_with(0, 50)
    mock_draw.assert_called_once_with(mock_graphics, (0, 50), (10, 200))

def test_refresh_same_scale(canvas_fixture, mocker):
    """Test refresh(fullsize=False) restores previous frame's axes."""
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    canvas_fixture.properties['autoScaleY'] = False
    canvas_fixture.properties['checkLimits'] = False
    
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (10, 20), (30, 40))
    
    canvas_fixture.refresh(fullsize=False)
    
    mock_draw.assert_called_once_with(mock_graphics, (10, 20), (30, 40))

def test_refresh_fullsize(canvas_fixture, mocker):
    """Test refresh(fullsize=True) uses bounding box."""
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    canvas_fixture.properties['checkLimits'] = False
    
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 10), (100, 200))
    canvas_fixture.lastDraw = (mock_graphics, (10, 20), (30, 40))
    
    canvas_fixture.refresh(fullsize=True)
    
    mock_graphics.getBoundingBox.assert_called_once()
    mock_draw.assert_called_once_with(mock_graphics, (0, 100), (10, 200))

def test_clear(canvas_fixture, mocker):
    """Test clear method resets state."""
    # Mock wx components
    mock_client_dc = mocker.patch('wx.ClientDC')
    mock_buffered_dc = mocker.patch('wx.BufferedDC')
    
    canvas_fixture.lastDraw = ("dummy", (0, 1), (0, 1))
    canvas_fixture.plotBuffer = wx.Bitmap(800, 600)
    canvas_fixture.clear()
    
    mock_buffered_dc.return_value.Clear.assert_called_once()
    assert canvas_fixture.lastDraw is None

# --- Step 5: Event Handlers (Mouse & Keyboard) ---

# Handle missing wx attributes in some versions
if not hasattr(wx, 'WXK_NEXT'):
    wx.WXK_NEXT = wx.WXK_PAGEDOWN
if not hasattr(wx, 'WXK_PRIOR'):
    wx.WXK_PRIOR = wx.WXK_PAGEUP

class MockEvent(object):
    """Factory for mock wx.MouseEvent and wx.KeyEvent."""
    def __init__(self, position=(0, 0), control=False, shift=False, alt=False, keyCode=0, wheelRotation=0):
        self.position = position
        self.control = control
        self.shift = shift
        self.alt = alt
        self.keyCode = keyCode
        self.wheelRotation = wheelRotation
        self.skipped = False

    def GetPosition(self):
        return self.position

    def ControlDown(self):
        return self.control

    def ShiftDown(self):
        return self.shift

    def AltDown(self):
        return self.alt

    def GetKeyCode(self):
        return self.keyCode

    def GetWheelRotation(self):
        return self.wheelRotation
    
    def Skip(self):
        self.skipped = True

@pytest.fixture
def mock_event_factory():
    return MockEvent

def test_onLMD_zoom(canvas_fixture, mocker, mock_event_factory):
    """Test onLMD sets mouseEvent to 'zoom' with ControlDown."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(100.0, 200.0))
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    mock_draw_zoom = mocker.patch.object(canvas_fixture, 'drawZoomBox')
    
    evt = mock_event_factory(position=(10, 20), control=True)
    canvas_fixture.onLMD(evt)
    
    assert canvas_fixture.mouseEvent == 'zoom'
    assert canvas_fixture.draggingStart == [100.0, 200.0, 10, 20]
    mock_draw_zoom.assert_called_once()

@pytest.mark.parametrize("mouseFnLMB, expected_event, draw_method", [
    ('point', 'point', 'drawPointTracker'),
    ('isotopes', 'isotopes', 'drawIsotopeRuler'),
    ('rectangle', 'rectangle', 'drawSelectionRect'),
    ('range', 'range', 'drawSelectionRange'),
    ('xDistance', 'distance', 'drawDistanceTracker'),
])
def test_onLMD_functions(canvas_fixture, mocker, mock_event_factory, mouseFnLMB, expected_event, draw_method):
    """Test onLMD sets various mouseEvents based on mouseFnLMB."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(100.0, 200.0))
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    mock_draw = mocker.patch.object(canvas_fixture, draw_method)
    
    canvas_fixture.mouseFnLMB = mouseFnLMB
    evt = mock_event_factory(position=(10, 20))
    canvas_fixture.onLMD(evt)
    
    assert canvas_fixture.mouseEvent == expected_event
    mock_draw.assert_called_once()

def test_onLMD_axis_shifts(canvas_fixture, mocker, mock_event_factory):
    """Test onLMD sets xShift/yShift for axis locations."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(0, 0))
    
    # Test xAxis
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='xAxis')
    canvas_fixture.onLMD(mock_event_factory())
    assert canvas_fixture.mouseEvent == 'xShift'
    
    # Reset and test yAxis
    canvas_fixture.mouseEvent = False
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='yAxis')
    canvas_fixture.onLMD(mock_event_factory())
    assert canvas_fixture.mouseEvent == 'yShift'

def test_onLMU_zoom_trigger(canvas_fixture, mocker, mock_event_factory):
    """Test onLMU triggers zoom() when mouseEvent is 'zoom'."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(200.0, 300.0))
    mocker.patch.object(canvas_fixture, 'drawZoomBox')
    mock_zoom = mocker.patch.object(canvas_fixture, 'zoom')
    
    # Pre-configure plotCoords, cursorPosition and mouseEvent
    canvas_fixture.plotCoords = (10, 10, 100, 100)
    canvas_fixture.mouseEvent = 'zoom'
    canvas_fixture.draggingStart = [100.0, 100.0, 10, 10]
    canvas_fixture.cursorPosition = [200.0, 300.0, 20, 20]
    canvas_fixture.properties['zoomAxis'] = 'xy'
    
    evt = mock_event_factory(position=(20, 20))
    canvas_fixture.onLMU(evt)
    
    mock_zoom.assert_called_once_with(xAxis=(100.0, 200.0), yAxis=(100.0, 300.0))
    assert canvas_fixture.mouseEvent is False

def test_onLMDC_plot(canvas_fixture, mocker, mock_event_factory):
    """Test onLMDC in the 'plot' area resets to full X and Y ranges."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 100))
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 50.0))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    mock_draw_tracker = mocker.patch.object(canvas_fixture, 'drawMouseTracker')
    
    # Setup lastDraw for graphics
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (10, 20))
    
    evt = mock_event_factory(position=(50, 50))
    canvas_fixture.onLMDC(evt)
    
    mock_draw.assert_called_once_with(mock_graphics, (0, 1000), (0, 100))
    mock_remember.assert_called_once_with((0, 1000), (0, 100))
    assert canvas_fixture.cursorPosition[2:] == [50, 50]
    mock_draw_tracker.assert_called_once()

def test_onLMDC_xAxis_autoScaleY_true(canvas_fixture, mocker, mock_event_factory):
    """Test onLMDC in the 'xAxis' area with autoScaleY=True."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', side_effect=['xAxis', 'blank'])
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(5, 50))
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 50.0))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    mock_draw_tracker = mocker.patch.object(canvas_fixture, 'drawMouseTracker')
    
    canvas_fixture.properties['autoScaleY'] = True
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (10, 20))
    
    evt = mock_event_factory(position=(50, 110))
    canvas_fixture.onLMDC(evt)
    
    mock_draw.assert_called_once_with(mock_graphics, (0, 1000), (5, 50))
    mock_remember.assert_called_once_with((0, 1000), (5, 50))
    mock_draw_tracker.assert_not_called()

def test_onLMDC_xAxis_autoScaleY_false(canvas_fixture, mocker, mock_event_factory):
    """Test onLMDC in the 'xAxis' area with autoScaleY=False."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', side_effect=['xAxis', 'blank'])
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(10, 20))
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 50.0))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['autoScaleY'] = False
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (10, 20))
    
    evt = mock_event_factory(position=(50, 110))
    canvas_fixture.onLMDC(evt)
    
    mock_draw.assert_called_once_with(mock_graphics, (0, 1000), (10, 20))
    mock_remember.assert_called_once_with((0, 1000), (10, 20))

def test_onLMDC_yAxis(canvas_fixture, mocker, mock_event_factory):
    """Test onLMDC in the 'yAxis' area resets Y range but keeps current X range."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', side_effect=['yAxis', 'blank'])
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 100))
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 50.0))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (10, 20))
    
    evt = mock_event_factory(position=(5, 50))
    canvas_fixture.onLMDC(evt)
    
    mock_draw.assert_called_once_with(mock_graphics, (100, 200), (0, 100))
    mock_remember.assert_called_once_with((100, 200), (0, 100))

def test_onLMDC_blank(canvas_fixture, mocker, mock_event_factory):
    """Test onLMDC in a 'blank' area returns early."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='blank')
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    
    evt = mock_event_factory(position=(110, 110))
    canvas_fixture.onLMDC(evt)
    
    mock_draw.assert_not_called()

def test_onRMDC_plot(canvas_fixture, mocker, mock_event_factory):
    """Test onRMDC in the 'plot' area resets to full X and Y ranges."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 100))
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(50.0, 50.0))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    mock_draw_tracker = mocker.patch.object(canvas_fixture, 'drawMouseTracker')
    
    # Setup lastDraw for graphics
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (10, 20))
    
    evt = mock_event_factory(position=(50, 50))
    canvas_fixture.onRMDC(evt)
    
    mock_draw.assert_called_once_with(mock_graphics, (0, 1000), (0, 100))
    mock_remember.assert_called_once_with((0, 1000), (0, 100))
    assert canvas_fixture.cursorPosition == [50.0, 50.0, 50, 50]
    mock_draw_tracker.assert_called_once()

@pytest.mark.parametrize("location", ['xAxis', 'yAxis', 'blank'])
def test_onRMDC_other_locations(canvas_fixture, mocker, mock_event_factory, location):
    """Test onRMDC in non-plot areas returns early."""
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value=location)
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    
    evt = mock_event_factory(position=(50, 50))
    canvas_fixture.onRMDC(evt)
    
    mock_draw.assert_not_called()

def test_onRMD_scenarios(canvas_fixture, mocker, mock_event_factory):
    """Test onRMD for zoom, xScale and yScale."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(100.0, 200.0))
    
    # Plot area -> zoom
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    canvas_fixture.mouseFnRMB = 'zoom'
    mock_draw_zoom = mocker.patch.object(canvas_fixture, 'drawZoomBox')
    canvas_fixture.onRMD(mock_event_factory())
    assert canvas_fixture.mouseEvent == 'zoom'
    mock_draw_zoom.assert_called_once()
    
    # xAxis -> xScale
    canvas_fixture.mouseEvent = False
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='xAxis')
    canvas_fixture.onRMD(mock_event_factory())
    assert canvas_fixture.mouseEvent == 'xScale'
    
    # yAxis -> yScale
    canvas_fixture.mouseEvent = False
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='yAxis')
    canvas_fixture.onRMD(mock_event_factory())
    assert canvas_fixture.mouseEvent == 'yScale'

def test_onRMU_view_memory(canvas_fixture, mocker, mock_event_factory):
    """Test onRMU remembers view for scaling events."""
    mocker.patch.object(canvas_fixture, 'FindFocus', return_value=canvas_fixture)
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(0, 0))
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    # Pre-configure plotCoords
    canvas_fixture.plotCoords = (10, 10, 100, 100)
    canvas_fixture.mouseEvent = 'xScale'
    canvas_fixture.onRMU(mock_event_factory())
    mock_remember.assert_called_once()
    assert canvas_fixture.mouseEvent is False

def test_onMMotion_handling(canvas_fixture, mocker, mock_event_factory):
    """Test onMMotion triggers appropriate handlers based on mouseEvent."""
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(150.0, 250.0))
    
    # Test xShift
    mock_shift = mocker.patch.object(canvas_fixture, 'shiftAxis')
    canvas_fixture.mouseEvent = 'xShift'
    canvas_fixture.onMMotion(mock_event_factory(position=(30, 40)))
    mock_shift.assert_called_once_with('x')
    assert canvas_fixture.cursorPosition == [150.0, 250.0, 30, 40]
    
    # Test yScale
    mock_scale = mocker.patch.object(canvas_fixture, 'scaleAxis')
    canvas_fixture.mouseEvent = 'yScale'
    canvas_fixture.onMMotion(mock_event_factory())
    mock_scale.assert_called_once_with('y')

def test_escMouseEvents(canvas_fixture, mocker):
    """Test escMouseEvents resets state."""
    # Pre-configure draggingStart for drawZoomBox
    canvas_fixture.draggingStart = [0, 0, 10, 10]
    canvas_fixture.plotCoords = (10, 10, 100, 100) # needed by drawZoomBox
    canvas_fixture.mouseEvent = 'zoom'
    canvas_fixture.mouseTracker = True
    
    # Mock drawZoomBox as it's called when mouseEvent is 'zoom'
    mock_draw_zoom = mocker.patch.object(canvas_fixture, 'drawZoomBox')
    
    canvas_fixture.escMouseEvents()
    
    assert canvas_fixture.mouseEvent is False
    assert canvas_fixture.draggingStart is False
    mock_draw_zoom.assert_called_once()
    # Note: mouseTracker is NOT cleared by escMouseEvents in current implementation

def test_onChar_navigation(canvas_fixture, mocker, mock_event_factory):
    """Test onChar for navigation keys (LEFT/RIGHT)."""
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['xMoveFactor'] = 0.1
    canvas_fixture.properties['autoScaleY'] = False
    
    # Setup lastDraw for graphics
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # Press LEFT (moves x axis by xMoveFactor * direction)
    # direction for LEFT is 1. shift = (100-200) * 0.1 * 1 = -10.
    # minX = 100 - 10 = 90, maxX = 200 - 10 = 190.
    evt = mock_event_factory(keyCode=wx.WXK_LEFT)
    canvas_fixture.onChar(evt)
    
    mock_draw.assert_called_with(mock_graphics, (90.0, 190.0), (0, 1000))

def test_onChar_scale_x_axis(canvas_fixture, mocker, mock_event_factory):
    """Test onChar for X-axis scaling with Alt modifier."""
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['xScaleFactor'] = 0.1
    canvas_fixture.properties['checkLimits'] = False
    canvas_fixture.properties['autoScaleY'] = False
    
    # Setup lastDraw for graphics
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # Alt + LEFT (direction = 1) -> Zoom out
    evt_left = mock_event_factory(keyCode=wx.WXK_LEFT, alt=True)
    canvas_fixture.onChar(evt_left)
    mock_draw.assert_called_with(mock_graphics, (90.0, 210.0), (0, 1000))
    mock_remember.assert_called_with((90.0, 210.0), (0, 1000))
    
    # Alt + RIGHT (direction = -1) -> Zoom in
    canvas_fixture.lastDraw = (mock_graphics, (90, 210), (0, 1000))
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(90, 210))
    mock_remember.reset_mock()
    
    evt_right = mock_event_factory(keyCode=wx.WXK_RIGHT, alt=True)
    canvas_fixture.onChar(evt_right)
    mock_draw.assert_called_with(mock_graphics, (102.0, 198.0), (0, 1000))
    mock_remember.assert_called_with((102.0, 198.0), (0, 1000))

def test_onChar_page_shifting(canvas_fixture, mocker, mock_event_factory):
    """Test onChar for page-wise X-axis shifting."""
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['checkLimits'] = False
    canvas_fixture.properties['autoScaleY'] = False
    
    # Setup lastDraw
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # PAGEUP / PRIOR (direction = 1) -> Move left
    for key in (wx.WXK_PAGEUP, wx.WXK_PRIOR):
        canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
        mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
        mock_remember.reset_mock()
        evt = mock_event_factory(keyCode=key)
        canvas_fixture.onChar(evt)
        mock_draw.assert_called_with(mock_graphics, (0.0, 100.0), (0, 1000))
        mock_remember.assert_called_with((0.0, 100.0), (0, 1000))
        
    # PAGEDOWN / NEXT (direction = -1) -> Move right
    for key in (wx.WXK_PAGEDOWN, wx.WXK_NEXT):
        canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
        mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
        mock_remember.reset_mock()
        evt = mock_event_factory(keyCode=key)
        canvas_fixture.onChar(evt)
        mock_draw.assert_called_with(mock_graphics, (200.0, 300.0), (0, 1000))
        mock_remember.assert_called_with((200.0, 300.0), (0, 1000))

def test_onChar_scale_y_axis(canvas_fixture, mocker, mock_event_factory):
    """Test onChar for Y-axis scaling."""
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mock_remember = mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['yScaleFactor'] = 0.1
    
    # Setup lastDraw
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # UP (direction = -1) -> Zoom in Y
    evt_up = mock_event_factory(keyCode=wx.WXK_UP)
    canvas_fixture.onChar(evt_up)
    mock_draw.assert_called_with(mock_graphics, (100, 200), (0, 900.0))
    mock_remember.assert_called_with((100, 200), (0, 900.0))
    
    # DOWN (direction = 1) -> Zoom out Y
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 900))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 900))
    mock_remember.reset_mock()
    evt_down = mock_event_factory(keyCode=wx.WXK_DOWN)
    canvas_fixture.onChar(evt_down)
    mock_draw.assert_called_with(mock_graphics, (100, 200), (0, 990.0))
    mock_remember.assert_called_with((100, 200), (0, 990.0))

def test_onChar_autoScaleY(canvas_fixture, mocker, mock_event_factory):
    """Test onChar triggers autoScaleY for relevant keys."""
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mock_get_max_y = mocker.patch.object(canvas_fixture, 'getMaxYRange', return_value=(50, 500))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    
    canvas_fixture.properties['autoScaleY'] = True
    canvas_fixture.properties['xMoveFactor'] = 0.1
    
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # LEFT key
    evt = mock_event_factory(keyCode=wx.WXK_LEFT)
    canvas_fixture.onChar(evt)
    
    # shift = (100-200) * 0.1 * 1 = -10. minX = 90, maxX = 190.
    mock_get_max_y.assert_called_with(90.0, 190.0)
    mock_draw.assert_called_with(mock_graphics, (90.0, 190.0), (50, 500))


def test_onChar_escape(canvas_fixture, mocker, mock_event_factory):
    """Test onChar calls escMouseEvents on Escape key."""
    mock_esc = mocker.patch.object(canvas_fixture, 'escMouseEvents')
    evt = mock_event_factory(keyCode=wx.WXK_ESCAPE)
    canvas_fixture.onChar(evt)
    mock_esc.assert_called_once()

def test_onMScroll_scaling(canvas_fixture, mocker, mock_event_factory):
    """Test onMScroll scales X axis with AltDown."""
    mocker.patch.object(canvas_fixture, 'getXY', return_value=(150.0, 0.0))
    mocker.patch.object(canvas_fixture, 'getCursorPosition', return_value=(150.0, 0.0))
    mocker.patch.object(canvas_fixture, 'getCurrentXRange', return_value=(100, 200))
    mocker.patch.object(canvas_fixture, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(canvas_fixture, 'getMaxXRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    mocker.patch.object(canvas_fixture, 'rememberView')
    
    canvas_fixture.properties['xScaleFactor'] = 0.1
    canvas_fixture.properties['autoScaleY'] = False
    canvas_fixture.properties['reverseScrolling'] = False
    
    # Setup lastDraw
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (100, 200), (0, 1000))
    
    # Scroll up (wheelRotation > 0) with Alt
    # direction = 1.
    # currX = 150.
    # minX -= (150-100) * 0.1 * 1 = 100 - 5 = 95
    # maxX += (200-150) * 0.1 * 1 = 200 + 5 = 205
    evt = mock_event_factory(wheelRotation=120, alt=True)
    canvas_fixture.onMScroll(evt)
    
    mock_draw.assert_called_with(mock_graphics, (95.0, 205.0), (0.0, 1000.0))

# --- Step 6: Rendering & Device Context (DC) Mocking ---

@pytest.fixture
def mock_dc(mocker):
    """Fixture to provide a mock wx.DC."""
    dc = mocker.Mock()
    dc.GetTextExtent.return_value = (50, 20)
    dc.GetCharHeight.return_value = 15
    dc.GetSize.return_value = (800, 600)
    dc.GetFont.return_value = wx.NullFont
    
    # Mocking DC methods
    dc.SetPen = mocker.Mock()
    dc.SetBrush = mocker.Mock()
    dc.SetFont = mocker.Mock()
    dc.SetBackground = mocker.Mock()
    dc.SetTextForeground = mocker.Mock()
    dc.SetLogicalFunction = mocker.Mock()
    dc.SetClippingRegion = mocker.Mock()
    dc.DestroyClippingRegion = mocker.Mock()
    dc.DrawLine = mocker.Mock()
    dc.DrawRectangle = mocker.Mock()
    dc.DrawText = mocker.Mock()
    dc.DrawRotatedText = mocker.Mock()
    dc.DrawCircle = mocker.Mock()
    dc.DrawPolygon = mocker.Mock()
    dc.Blit = mocker.Mock()
    dc.Clear = mocker.Mock()
    dc.SelectObject = mocker.Mock()
    return dc

@pytest.fixture
def patched_canvas(canvas_fixture, mocker, mock_dc):
    """Fixture to patch DC classes and provide a canvas ready for rendering tests."""
    mocker.patch('wx.ClientDC', return_value=mocker.Mock())
    mocker.patch('wx.BufferedDC', return_value=mock_dc)
    mocker.patch('wx.MemoryDC', return_value=mock_dc)
    mocker.patch('wx.BufferedPaintDC', return_value=mock_dc)
    
    # Patch Bitmap
    mocker.patch('wx.Bitmap', return_value=mocker.Mock())
    
    # Patch GDI objects to avoid C++ assertion errors in headless environments
    mocker.patch('wx.Pen', side_effect=lambda *args, **kwargs: mocker.Mock())
    mocker.patch('wx.Brush', side_effect=lambda *args, **kwargs: mocker.Mock())
    
    # Initialize basic sizing attributes
    canvas_fixture.setSize(800, 600)
    
    return canvas_fixture

def test_draw_basic(patched_canvas, mock_dc, mocker):
    """Test the main draw() method."""
    mock_graphics = mocker.Mock()
    mock_graphics.countGels.return_value = 0
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 100))
    mock_graphics.getLegend.return_value = []
    
    patched_canvas.properties['showXPosBar'] = True
    patched_canvas.properties['showYPosBar'] = True
    patched_canvas.properties['showLegend'] = True
    patched_canvas.properties['showGel'] = True
    patched_canvas.gelsCount = 1
    
    # Call draw
    patched_canvas.draw(mock_graphics, xAxis=(0, 1000), yAxis=(0, 100))
    
    # Verify DC interactions
    mock_dc.Clear.assert_called()
    mock_dc.SetFont.assert_called()
    
    # Verify graphics interactions
    mock_graphics.cropPoints.assert_called()
    mock_graphics.scaleAndShift.assert_called()
    mock_graphics.filterPoints.assert_called()
    mock_graphics.draw.assert_called_once()
    
    # Verify sub-renderers were likely called by checking DC calls
    assert mock_dc.DrawText.called
    assert mock_dc.DrawRectangle.called

def test_drawAxis(patched_canvas, mock_dc):
    """Test drawAxis specifically."""
    xticks = [(0, '0', 'major'), (500, '500', 'major'), (1000, '1000', 'major')]
    yticks = [(0, '0', 'major'), (50, '50', 'major'), (100, '100', 'major')]
    
    patched_canvas.plotCoords = (50, 50, 750, 550)
    patched_canvas.pointScale = numpy.array([0.7, -5.0])
    patched_canvas.pointShift = numpy.array([50.0, 550.0])
    patched_canvas.properties['showGrid'] = True
    patched_canvas.properties['showZero'] = True
    
    patched_canvas.drawAxis(mock_dc, xticks, yticks)
    
    # Check if lines and rectangles were drawn
    assert mock_dc.DrawRectangle.called
    assert mock_dc.DrawLine.called
    assert mock_dc.DrawText.called

def test_drawXPositionBar(patched_canvas, mock_dc, mocker):
    """Test drawXPositionBar with various xAxis ranges."""
    patched_canvas.plotCoords = (50, 50, 750, 550)
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    
    # Normal case
    patched_canvas.drawXPositionBar(mock_dc, (200, 800))
    assert mock_dc.DrawRectangle.called
    
    # Out of bounds left
    mock_dc.DrawPolygon.reset_mock()
    patched_canvas.drawXPositionBar(mock_dc, (-100, -50))
    assert mock_dc.DrawPolygon.called # Arrow should be drawn
    
    # Out of bounds right
    mock_dc.DrawPolygon.reset_mock()
    patched_canvas.drawXPositionBar(mock_dc, (1100, 1200))
    assert mock_dc.DrawPolygon.called

def test_drawYPositionBar(patched_canvas, mock_dc, mocker):
    """Test drawYPositionBar."""
    patched_canvas.plotCoords = (50, 50, 750, 550)
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    
    # Normal case
    patched_canvas.drawYPositionBar(mock_dc, (200, 800))
    assert mock_dc.DrawRectangle.called
    
    # Out of bounds
    mock_dc.DrawPolygon.reset_mock()
    patched_canvas.drawYPositionBar(mock_dc, (1100, 1200))
    assert mock_dc.DrawPolygon.called

def test_drawLegend(patched_canvas, mock_dc, mocker):
    """Test drawLegend."""
    mock_graphics = mocker.Mock()
    mock_graphics.getLegend.return_value = [("Spectrum 1", (255, 0, 0)), ("Spectrum 2", (0, 0, 255))]
    patched_canvas.plotCoords = (50, 50, 750, 550)
    
    patched_canvas.drawLegend(mock_dc, mock_graphics)
    
    assert mock_dc.DrawText.call_count >= 2
    assert mock_dc.DrawCircle.call_count >= 2

def test_drawGelView(patched_canvas, mock_dc, mocker):
    """Test drawGelView."""
    mock_graphics = mocker.Mock()
    patched_canvas.plotCoords = (50, 50, 750, 550)
    patched_canvas.pointShift = [0, 550]
    patched_canvas.gelsCount = 2
    patched_canvas.properties['gelHeight'] = 10
    
    patched_canvas.drawGelView(mock_dc, mock_graphics)
    
    assert mock_dc.SetClippingRegion.called
    mock_graphics.drawGel.assert_called_once()
    assert mock_dc.DrawRectangle.called

def test_drawTrackerRenderers(patched_canvas, mocker, mock_dc):
    """Test tracker renderers that use wx.ClientDC and wx.INVERT."""
    # We need to patch wx.ClientDC locally to return our mock_dc
    mocker.patch('wx.ClientDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 50, 750, 550)
    patched_canvas.cursorPosition = [100.0, 200.0, 150, 250]
    patched_canvas.draggingStart = [50.0, 50.0, 60, 60]
    
    # drawCursorTracker
    mock_dc.DrawLine.reset_mock()
    patched_canvas.drawCursorTracker()
    mock_dc.SetLogicalFunction.assert_any_call(wx.INVERT)
    assert mock_dc.DrawLine.called
    
    # drawZoomBox
    mock_dc.DrawRectangle.reset_mock()
    patched_canvas.properties['zoomAxis'] = 'xy'
    patched_canvas.drawZoomBox()
    assert mock_dc.DrawRectangle.called
    
    # drawDistanceTracker
    mock_dc.DrawLine.reset_mock()
    patched_canvas.mouseFnLMB = 'xDistance'
    mocker.patch.object(patched_canvas, 'getCursorLocation', return_value='plot')
    patched_canvas.drawDistanceTracker()
    assert mock_dc.DrawLine.called
    
    # drawPointTracker
    mock_dc.DrawLine.reset_mock()
    patched_canvas.currentObject = mocker.Mock()
    mocker.patch.object(patched_canvas, 'getPoint', return_value=(100.0, 100.0))
    patched_canvas.drawPointTracker()
    assert mock_dc.DrawLine.called
    
    # drawIsotopeRuler
    mock_dc.DrawLine.reset_mock()
    patched_canvas.currentCharge = 1
    patched_canvas.currentIsotopeLines = 0
    patched_canvas.drawIsotopeRuler()
    assert mock_dc.DrawLine.called
    
    # drawSelectionRect
    mock_dc.DrawRectangle.reset_mock()
    patched_canvas.drawSelectionRect()
    assert mock_dc.DrawRectangle.called
    
    # drawSelectionRange
    mock_dc.DrawLine.reset_mock()
    patched_canvas.drawSelectionRange()
    assert mock_dc.DrawLine.called

def test_setProperties_update(canvas_fixture):
    """Test setProperties updates existing keys and adds new ones."""
    # Test updating existing key
    canvas_fixture.setProperties(showGrid=False)
    assert canvas_fixture.properties['showGrid'] is False
    
    # Test adding new key
    canvas_fixture.setProperties(newKey="newValue")
    assert canvas_fixture.properties['newKey'] == "newValue"
    
    # Test multiple keys
    canvas_fixture.setProperties(autoScaleY=True, maxZoom=0.1)
    assert canvas_fixture.properties['autoScaleY'] is True
    assert canvas_fixture.properties['maxZoom'] == 0.1

def test_getMaxYRange_ySymmetry(canvas_fixture, mocker):
    """Test getMaxYRange with ySymmetry=True."""
    # Setup lastDraw with a mock graphics object
    mock_graphics = mocker.Mock()
    # Mock getBoundingBox to return p1, p2
    # p1 = (minX, minY), p2 = (maxX, maxY)
    mock_graphics.getBoundingBox.return_value = ((0, -10), (100, 50))
    canvas_fixture.lastDraw = (mock_graphics, (0, 100), (-10, 50))
    
    # Case 1: ySymmetry is False (default)
    assert canvas_fixture.getMaxYRange() == (-10, 50)
    
    # Case 2: ySymmetry is True
    canvas_fixture.properties['ySymmetry'] = True
    # maxY = max(abs(-10), abs(50)) = 50
    # expected: (-50, 50)
    assert canvas_fixture.getMaxYRange() == (-50, 50)
    
    # Case 3: ySymmetry is True, larger negative value
    mock_graphics.getBoundingBox.return_value = ((0, -100), (100, 50))
    # maxY = max(abs(-100), abs(50)) = 100
    # expected: (-100, 100)
    assert canvas_fixture.getMaxYRange() == (-100, 100)

def test_getDistance(canvas_fixture):
    """Test getDistance method."""
    # Case 1: mouseEvent is not 'distance'
    canvas_fixture.mouseEvent = 'zoom'
    assert canvas_fixture.getDistance() is False
    
    # Case 2: mouseEvent is 'distance'
    canvas_fixture.mouseEvent = 'distance'
    canvas_fixture.draggingStart = [100.0, 200.0]
    canvas_fixture.cursorPosition = [150.0, 250.0]
    # x2-x1 = 50.0, y2-y1 = 50.0
    assert canvas_fixture.getDistance() == [50.0, 50.0]

def test_getIsotopes(canvas_fixture, mocker):
    """Test getIsotopes method."""
    # Case 1: mouseEvent is not 'isotopes'
    canvas_fixture.mouseEvent = 'zoom'
    assert canvas_fixture.getIsotopes() is False
    
    # Case 2: mouseEvent is 'isotopes', but location not 'plot'
    canvas_fixture.mouseEvent = 'isotopes'
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='xAxis')
    assert canvas_fixture.getIsotopes() is False
    
    # Case 3: mouseEvent is 'isotopes' and location is 'plot'
    mocker.patch.object(canvas_fixture, 'getCursorLocation', return_value='plot')
    canvas_fixture.currentIsotopes = [1.0, 2.0, 3.0]
    assert canvas_fixture.getIsotopes() == [1.0, 2.0, 3.0]
    # Verify it returns a copy
    isotopes = canvas_fixture.getIsotopes()
    isotopes.append(4.0)
    assert canvas_fixture.currentIsotopes == [1.0, 2.0, 3.0]

def test_getPoint(canvas_fixture, mocker):
    """Test getPoint method."""
    # Case 1: currentObject is None
    canvas_fixture.currentObject = None
    assert canvas_fixture.getPoint() is None
    
    # Case 2: currentObject exists
    canvas_fixture.currentObject = "dummy"
    mock_graphics = mocker.Mock()
    canvas_fixture.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mock_graphics.getPoint.return_value = (50, 100)
    
    assert canvas_fixture.getPoint(xPos=50, coord='screen') == (50, 100)
    mock_graphics.getPoint.assert_called_once_with("dummy", 50, 'screen')

def test_getSelectionBox(canvas_fixture):
    """Test getSelectionBox method."""
    # Case 1: mouseEvent not in ('rectangle', 'range')
    canvas_fixture.mouseEvent = 'zoom'
    assert canvas_fixture.getSelectionBox() is False
    
    # Case 2: mouseEvent is 'rectangle'
    canvas_fixture.mouseEvent = 'rectangle'
    canvas_fixture.draggingStart = [100.0, 200.0]
    canvas_fixture.cursorPosition = [50.0, 300.0]
    # x1 = min(100, 50) = 50, y1 = min(200, 300) = 200
    # x2 = max(100, 50) = 100, y2 = max(200, 300) = 300
    assert canvas_fixture.getSelectionBox() == (50.0, 200.0, 100.0, 300.0)
    
    # Case 3: mouseEvent is 'range'
    canvas_fixture.mouseEvent = 'range'
    canvas_fixture.draggingStart = [10.0, 50.0]
    canvas_fixture.cursorPosition = [100.0, 20.0]
    # x1 = min(10, 100) = 10, y1 = min(50, 20) = 20
    # x2 = max(10, 100) = 100, y2 = max(50, 20) = 50
    assert canvas_fixture.getSelectionBox() == (10.0, 20.0, 100.0, 50.0)

def test_onPaint(patched_canvas, mocker):
    """Test onPaint interaction."""
    mock_paint_dc = mocker.patch('wx.BufferedPaintDC')
    patched_canvas.plotBuffer = mocker.Mock()
    patched_canvas.mouseTracker = False
    
    patched_canvas.onPaint(None)
    
    mock_paint_dc.assert_called_once()

def test_onSize(patched_canvas, mocker):
    """Test onSize interaction."""
    mocker.patch.object(patched_canvas, 'GetClientSize', return_value=(800, 600))
    mock_bitmap = mocker.patch('wx.Bitmap', return_value=mocker.Mock())
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    mock_clear = mocker.patch.object(patched_canvas, 'clear')
    
    # If lastDraw is None
    patched_canvas.lastDraw = None
    patched_canvas.onSize(None)
    mock_clear.assert_called_once()
    
    # If lastDraw exists
    mock_graphics = mocker.Mock()
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    mocker.patch.object(patched_canvas, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    
    patched_canvas.onSize(None)
    mock_draw.assert_called()

# --- Step 7: Printout & Export Testing ---

def test_getBitmap_defaults(patched_canvas, mocker, mock_dc):
    """Test canvas.getBitmap with default arguments."""
    mocker.patch.object(patched_canvas, 'GetClientSize', return_value=(800, 600))
    mock_set_size = mocker.patch.object(patched_canvas, 'setSize')
    mock_draw_outside = mocker.patch.object(patched_canvas, 'drawOutside')
    mock_refresh = mocker.patch.object(patched_canvas, 'refresh')
    
    patched_canvas.lastDraw = ("graphics", (0, 10), (0, 100))
    
    bitmap = patched_canvas.getBitmap()
    
    assert isinstance(bitmap, mocker.Mock) # Since wx.Bitmap is patched
    # setSize(width, height)
    mock_set_size.assert_any_call(800, 600)
    # drawOutside(dc, filterSize)
    # ratioW = 800/750 = 1.066, ratioH = 600/750 = 0.8. scale = max(0.8, 1) = 1.
    # filterSize = max(1*0.5, 0.5) = 0.5
    mock_draw_outside.assert_called_once_with(mock_dc, 0.5)
    # Revert state
    mock_set_size.assert_any_call()
    mock_refresh.assert_called_once()
    assert patched_canvas.printerScale['drawings'] == 1
    assert patched_canvas.printerScale['fonts'] == 1

def test_getBitmap_explicit(patched_canvas, mocker, mock_dc):
    """Test canvas.getBitmap with explicit arguments."""
    mock_set_size = mocker.patch.object(patched_canvas, 'setSize')
    mock_draw_outside = mocker.patch.object(patched_canvas, 'drawOutside')
    mock_refresh = mocker.patch.object(patched_canvas, 'refresh')
    
    patched_canvas.lastDraw = ("graphics", (0, 10), (0, 100))
    
    printerScale = {'drawings': 2, 'fonts': 2}
    patched_canvas.getBitmap(width=1000, height=800, printerScale=printerScale)
    
    # filterSize = max(2*0.5, 0.5) = 1.0
    mock_draw_outside.assert_called_once_with(mock_dc, 1.0)
    mock_refresh.assert_called_once()

def test_printout_basics(mocker):
    """Test printout basic methods."""
    from mspy.plot_canvas import printout
    mock_graph = mocker.Mock()
    po = printout(graph=mock_graph, filterSize=1.5, title="Test Print")
    
    assert po.HasPage(1) is True
    assert po.HasPage(2) is False
    assert po.GetPageInfo() == (1, 1, 1, 1)
    assert po.graph == mock_graph
    assert po.filterSize == 1.5

def test_printout_OnPrintPage_printing(mocker, mock_dc):
    """Test printout.OnPrintPage in printing mode."""
    from mspy.plot_canvas import printout
    mock_graph = mocker.Mock()
    po = printout(mock_graph, filterSize=2.0)
    
    # Mock wx.Printout methods
    mocker.patch.object(po, 'GetDC', return_value=mock_dc)
    mocker.patch.object(po, 'GetPPIPrinter', return_value=(300, 300))
    mocker.patch.object(po, 'GetPageSizePixels', return_value=(2000, 3000))
    mocker.patch.object(po, 'IsPreview', return_value=False)
    
    mock_dc.GetSize.return_value = (2000, 3000)
    
    # pixLeft = 300 / 25.4 = 11.811
    # plotAreaW = 2000 - 2 * 11.811 = 1976.378
    # plotAreaH = 3000 - 2 * 11.811 = 2976.378
    # ratioW = 1976.378 / 900 = 2.196
    # ratioH = 2976.378 / 900 = 3.307
    # scale = min(2.196, 3.307) = 2.196
    # if not IsPreview, scale = max(2.196, 2.5) = 2.5
    
    result = po.OnPrintPage(1)
    
    assert result is True
    mock_graph.setSize.assert_any_call(mocker.ANY, mocker.ANY)
    # Check scaling
    mock_graph.setPrinterScale.assert_any_call(drawings=2.5, fonts=2.5)
    # Check draw
    mock_graph.drawOutside.assert_called_once_with(mock_dc, 2.0)
    # Check revert
    mock_graph.setSize.assert_any_call()
    mock_graph.setPrinterScale.assert_any_call()
    mock_graph.refresh.assert_called_once()

def test_printout_OnPrintPage_preview(mocker, mock_dc):
    """Test printout.OnPrintPage in preview mode."""
    from mspy.plot_canvas import printout
    mock_graph = mocker.Mock()
    po = printout(mock_graph, filterSize=2.0)
    
    # Mock wx.Printout methods
    mocker.patch.object(po, 'GetDC', return_value=mock_dc)
    mocker.patch.object(po, 'GetPPIPrinter', return_value=(300, 300))
    mocker.patch.object(po, 'GetPageSizePixels', return_value=(2000, 3000))
    mocker.patch.object(po, 'IsPreview', return_value=True)
    
    # dcSize for preview is usually smaller than pageSize
    mock_dc.GetSize.return_value = (800, 1200)
    
    # ratioW = 800 / 2000 = 0.4
    # ratioH = 1200 / 3000 = 0.4
    
    result = po.OnPrintPage(1)
    
    assert result is True
    assert po.filterSize == 1
    # Check that setSize was called with scaled values
    # plotAreaW was ~1976, now ~1976 * 0.4 = 790.4
    args, kwargs = mock_graph.setSize.call_args_list[0]
    assert args[0] < 800
    assert args[1] < 1200

# --- Step 8: Additional Mouse Functions ---

def test_drawPointTracker_detailed(setup_canvas_for_tracking, mocker):
    """Detailed test for drawPointTracker covering platform branches."""
    canvas, dc = setup_canvas_for_tracking
    
    # Mock currentObject and getPoint
    canvas.currentObject = mocker.Mock()
    # screen (50, 80) -> user (50, 120)
    mocker.patch.object(canvas, 'getPoint', return_value=(50.0, 120.0))
    
    # Test non-Mac
    mocker.patch('wx.Platform', '__WXMSW__')
    dc.DrawLine.reset_mock()
    canvas.drawPointTracker()
    # Expect lines for crosshair and vertical line to active curve
    assert dc.DrawLine.call_count >= 2
    
    # Test Mac
    mocker.patch('wx.Platform', '__WXMAC__')
    dc.DrawLine.reset_mock()
    canvas.drawPointTracker()
    assert dc.DrawLine.call_count >= 2

@pytest.mark.parametrize("platform", ["__WXMSW__", "__WXMAC__"])
def test_drawIsotopeRuler_detailed(setup_canvas_for_tracking, mocker, platform):
    """Detailed test for drawIsotopeRuler covering platform branches and isotope calculations."""
    canvas, dc = setup_canvas_for_tracking
    mocker.patch('wx.Platform', platform)
    
    # Step 3 Requirements:
    # Set canvas_fixture.currentCharge = 2
    canvas.currentCharge = 2
    canvas.currentIsotopeLines = 0
    
    # Mock positionUserToScreen to return predictable coordinates
    mocker.patch.object(canvas, 'positionUserToScreen', side_effect=lambda pos: (pos[0], pos[1]))
    
    # Set currentObject and mock getPoint to ensure intensity is set and DrawCircle is called
    canvas.currentObject = mocker.Mock()
    mocker.patch.object(canvas, 'getPoint', side_effect=lambda x, coord: (x, 80.0) if abs(x-50.0) < 1.0 else (x, 150.0))

    # Trigger drawing
    dc.DrawLine.reset_mock()
    dc.DrawCircle.reset_mock()
    canvas.drawIsotopeRuler()
    
    # Verify DrawLine and DrawCircle are called
    assert dc.DrawLine.called
    assert dc.DrawCircle.called
    
    # Verify charge text was drawn
    canvas.drawInvertedText.assert_called()

def test_drawSelectionRect_detailed(setup_canvas_for_tracking):
    """Test drawSelectionRect with boundaries and specific dragging start."""
    canvas, dc = setup_canvas_for_tracking
    
    # Step 4 Requirements:
    # Set canvas_fixture.draggingStart = [40.0, 90.0, 40, 90]
    canvas.draggingStart = [40.0, 90.0, 40, 90]
    
    # Case 1: Inside bounds
    canvas.cursorPosition = [60.0, 110.0, 60, 110]
    dc.DrawRectangle.reset_mock()
    canvas.drawSelectionRect()
    # expected x=40, y=90, w=20, h=20
    dc.DrawRectangle.assert_called_with(40, 90, 20, 20)
    
    # Case 2: Outside bounds (clipped to max)
    # plotCoords = (10, 10, 190, 190)
    canvas.cursorPosition = [250.0, 250.0, 250, 250]
    dc.DrawRectangle.reset_mock()
    canvas.drawSelectionRect()
    # x2 clipped to maxXPlot-1 = 189
    # y2 clipped to maxYPlot-1 = 189
    # expected x=40, y=90, w=189-40=149, h=189-90=99
    dc.DrawRectangle.assert_called_with(40, 90, 149, 99)

    # Case 3: Outside bounds (clipped to min)
    canvas.cursorPosition = [0.0, 0.0, 0, 0]
    dc.DrawRectangle.reset_mock()
    canvas.drawSelectionRect()
    # x2 clipped to minXPlot = 10
    # y2 clipped to minYPlot = 10
    # expected x=40, y=90, w=10-40=-30, h=10-90=-80
    dc.DrawRectangle.assert_called_with(40, 90, -30, -80)

@pytest.mark.parametrize("platform", ["__WXMSW__", "__WXMAC__"])
def test_drawSelectionRange_detailed(setup_canvas_for_tracking, mocker, platform):
    """Test drawSelectionRange with platform branches and specific dragging start."""
    canvas, dc = setup_canvas_for_tracking
    mocker.patch('wx.Platform', platform)
    
    # Step 4 Requirements:
    # Set canvas_fixture.draggingStart = [40.0, 90.0, 40, 90]
    canvas.draggingStart = [40.0, 90.0, 40, 90]
    
    # Case 1: Normal range
    canvas.cursorPosition = [100.0, 90.0, 100, 90]
    dc.DrawLine.reset_mock()
    canvas.drawSelectionRange()
    assert dc.DrawLine.called
    assert dc.DrawLine.call_count >= 3

    # Case 2: Capped at minX
    canvas.cursorPosition = [0.0, 90.0, 0, 90]
    dc.DrawLine.reset_mock()
    canvas.drawSelectionRange()
    assert dc.DrawLine.called

    # Case 3: Capped at maxX
    canvas.cursorPosition = [200.0, 90.0, 200, 90]
    dc.DrawLine.reset_mock()
    canvas.drawSelectionRange()
    assert dc.DrawLine.called

def test_drawDistanceTracker_detailed(setup_canvas_for_tracking, mocker):
    """Detailed test for drawDistanceTracker covering x/y modes and platform branches."""
    canvas, dc = setup_canvas_for_tracking
    
    # Configure common state
    canvas.draggingStart = [40.0, 90.0, 40, 90]
    canvas.cursorPosition = [60.0, 110.0, 60, 110]
    canvas.properties['showCurDistance'] = True
    
    # Case 1: xDistance, Non-Mac
    mocker.patch('wx.Platform', '__WXMSW__')
    canvas.mouseFnLMB = 'xDistance'
    dc.DrawLine.reset_mock()
    canvas.drawInvertedText.reset_mock()
    canvas.drawDistanceTracker()
    # Expect vertical lines at x1 and x2, and a horizontal line at y2
    assert dc.DrawLine.call_count >= 3
    # xPosDigits=2 -> "20.00"
    canvas.drawInvertedText.assert_called_with(mocker.ANY, "20.00", mocker.ANY, mocker.ANY, mocker.ANY)

    # Case 2: yDistance, Mac
    mocker.patch('wx.Platform', '__WXMAC__')
    canvas.mouseFnLMB = 'yDistance'
    dc.DrawLine.reset_mock()
    canvas.drawInvertedText.reset_mock()
    canvas.drawDistanceTracker()
    # Expect horizontal lines at y1 and y2, and a vertical line at x2
    assert dc.DrawLine.call_count >= 3
    # yPosDigits=0 -> "20"
    canvas.drawInvertedText.assert_called_with(mocker.ANY, "20", mocker.ANY, mocker.ANY, mocker.ANY)

    # Case 3: Outside bounds (clipped)
    canvas.cursorPosition = [250.0, 250.0, 250, 250]
    dc.DrawLine.reset_mock()
    canvas.drawDistanceTracker()
    # Verify it still draws without error, coordinates should be clipped internally
    assert dc.DrawLine.called

@pytest.mark.parametrize("mouse_fn, expected_event, tracker_name", [
    ('point', 'point', 'drawPointTracker'),
    ('isotopes', 'isotopes', 'drawIsotopeRuler'),
    ('rectangle', 'rectangle', 'drawSelectionRect'),
    ('range', 'range', 'drawSelectionRange'),
    ('xDistance', 'distance', 'drawDistanceTracker'),
])
def test_mouse_tracking_state_machine(setup_canvas_for_tracking, mocker, mock_event_factory, mouse_fn, expected_event, tracker_name):
    """Test state transitions for additional mouse functions using parametrization."""
    canvas, dc = setup_canvas_for_tracking
    mocker.patch.object(canvas, 'FindFocus', return_value=canvas)
    
    canvas.mouseFnLMB = mouse_fn
    canvas.mouseEvent = False
    
    # Patch the specific tracker method
    mock_tracker = mocker.patch.object(canvas, tracker_name)
    
    # 1. LMD (Start)
    # Ensure event has GetPosition and other required methods
    evt_down = mock_event_factory(position=(50, 50))
    # We need to mock FindFocus because onLMD calls it. 
    # canvas_fixture already has it mocked in setup_canvas_for_tracking? No, it's mocked here.
    
    canvas.onLMD(evt_down)
    assert canvas.mouseEvent == expected_event
    assert mock_tracker.call_count == 1
    
    # 2. MMotion (Update)
    # onMMotion calls tracker twice: once to clear (INVERT), once to redraw
    evt_motion = mock_event_factory(position=(60, 60))
    canvas.onMMotion(evt_motion)
    assert mock_tracker.call_count == 3
    assert canvas.cursorPosition[2:] == [60, 60]
    
    # 3. LMU (End)
    # onLMU calls tracker once to clear
    evt_up = mock_event_factory(position=(60, 60))
    canvas.onLMU(evt_up)
    assert canvas.mouseEvent is False
    assert mock_tracker.call_count == 4

# --- Step 9: onMScroll Testing ---

@pytest.fixture
def setup_scroll(setup_canvas_for_tracking, mocker):
    """Combined fixture for scroll tests."""
    canvas, dc = setup_canvas_for_tracking
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0.0, 0.0), (1000.0, 1000.0))
    canvas.lastDraw = (mock_graphics, (100.0, 200.0), (0.0, 1000.0))
    return canvas, mock_graphics

@pytest.fixture
def mock_mouse_event_scroll(mocker):
    """Fixture to provide a mock wx.MouseEvent for scrolling tests."""
    evt = mocker.Mock(spec=wx.MouseEvent)
    evt.GetWheelRotation.return_value = 120
    evt.ShiftDown.return_value = False
    evt.AltDown.return_value = False
    evt.ControlDown.return_value = False
    evt.GetPosition.return_value = (100, 100)
    return evt

def test_onMScroll_early_exit_active_event(canvas_fixture, mock_mouse_event_scroll, mocker):
    """Step 2: Test Early Exit on Active Mouse Event."""
    canvas_fixture.mouseEvent = 'zoom'
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    canvas_fixture.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_not_called()

def test_onMScroll_clears_mouse_tracker(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 3: Test Mouse Tracker Clearing."""
    canvas, _ = setup_scroll
    canvas.mouseTracker = True
    mock_draw_tracker = mocker.patch.object(canvas, 'drawMouseTracker')
    mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw_tracker.assert_called_once()

@pytest.mark.parametrize("rotation, reverse, expected_direction", [
    (120, False, 1),
    (-120, False, -1),
    (120, True, -1),
    (-120, True, 1),
])
def test_onMScroll_scroll_direction(setup_scroll, mock_mouse_event_scroll, mocker, rotation, reverse, expected_direction):
    """Step 4: Test Scroll Direction and Inversion."""
    canvas, mock_graphics = setup_scroll
    mock_mouse_event_scroll.GetWheelRotation.return_value = rotation
    canvas.properties['reverseScrolling'] = reverse
    
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['xScrollFactor'] = 0.1
    canvas.properties['checkLimits'] = False
    
    # shift = (100 - 200) * 0.1 * direction = -10 * direction
    canvas.onMScroll(mock_mouse_event_scroll)
    
    expected_minX = 100.0 - 10.0 * expected_direction
    expected_maxX = 200.0 - 10.0 * expected_direction
    
    args, kwargs = mock_draw.call_args
    assert abs(args[1][0] - expected_minX) < 1e-9
    assert abs(args[1][1] - expected_maxX) < 1e-9

def test_onMScroll_isotoperuler_lines(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 5: Test Isotope Ruler Logic (Shift, Alt)."""
    canvas, _ = setup_scroll
    canvas.mouseFn = 'isotoperuler'
    mock_mouse_event_scroll.ShiftDown.return_value = True
    mock_mouse_event_scroll.AltDown.return_value = True
    canvas.currentIsotopeLines = 10
    mock_draw_tracker = mocker.patch.object(canvas, 'drawMouseTracker')
    
    canvas.onMScroll(mock_mouse_event_scroll)
    assert canvas.currentIsotopeLines == 11
    mock_draw_tracker.assert_called_once()
    
    canvas.currentIsotopeLines = 50
    canvas.onMScroll(mock_mouse_event_scroll)
    assert canvas.currentIsotopeLines == 50

def test_onMScroll_isotoperuler_charge(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 5: Test Isotope Ruler Logic (Shift)."""
    canvas, _ = setup_scroll
    canvas.mouseFn = 'isotoperuler'
    mock_mouse_event_scroll.ShiftDown.return_value = True
    mock_mouse_event_scroll.AltDown.return_value = False
    mock_mouse_event_scroll.ControlDown.return_value = False
    canvas.currentCharge = 10
    mock_draw_tracker = mocker.patch.object(canvas, 'drawMouseTracker')
    
    canvas.onMScroll(mock_mouse_event_scroll)
    assert canvas.currentCharge == 11
    
    canvas.currentCharge = 50
    canvas.onMScroll(mock_mouse_event_scroll)
    assert canvas.currentCharge == 50
    
    mock_mouse_event_scroll.GetWheelRotation.return_value = -120
    canvas.currentCharge = 1
    canvas.onMScroll(mock_mouse_event_scroll)
    assert canvas.currentCharge == 1

def test_onMScroll_scale_x_axis(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 6: Test X-Axis Scaling (Zooming)."""
    canvas, mock_graphics = setup_scroll
    mock_mouse_event_scroll.AltDown.return_value = True
    mocker.patch.object(canvas, 'getCursorPosition', return_value=(150.0, 500.0))
    
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['xScaleFactor'] = 0.1
    canvas.properties['checkLimits'] = False
    canvas.properties['maxZoom'] = 0.001
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (95.0, 205.0), (0.0, 1000.0))

def test_onMScroll_scale_x_axis_no_cursor(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 6: Test X-Axis Scaling with no cursor position."""
    canvas, _ = setup_scroll
    mock_mouse_event_scroll.AltDown.return_value = True
    mocker.patch.object(canvas, 'getCursorPosition', return_value=False)
    mock_draw = mocker.patch.object(canvas, 'draw')
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_not_called()

def test_onMScroll_scale_y_axis(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 7: Test Y-Axis Scaling."""
    canvas, mock_graphics = setup_scroll
    mock_mouse_event_scroll.ShiftDown.return_value = True
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['yScaleFactor'] = 0.1
    canvas.properties['ySymmetry'] = False
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (100.0, 200.0), (0.0, 900.0))

def test_onMScroll_scale_y_axis_symmetry(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 7: Test Y-Axis Scaling with symmetry."""
    canvas, mock_graphics = setup_scroll
    mocker.patch.object(canvas, 'getCursorLocation', return_value='yAxis')
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['yScaleFactor'] = 0.1
    canvas.properties['ySymmetry'] = True
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (100.0, 200.0), (-900.0, 900.0))

def test_onMScroll_shift_x_axis(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 8: Test X-Axis Shifting."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['xScrollFactor'] = 0.1
    canvas.properties['checkLimits'] = False
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (90.0, 190.0), (0.0, 1000.0))

def test_onMScroll_respects_max_zoom(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 9: Test X-Axis Scaling respects maxZoom."""
    canvas, _ = setup_scroll
    mock_mouse_event_scroll.AltDown.return_value = True
    mock_mouse_event_scroll.GetWheelRotation.return_value = -120 # direction -1 (zoom in)
    mocker.patch.object(canvas, 'getCursorPosition', return_value=(150.0, 500.0))
    mocker.patch.object(canvas, 'getCurrentXRange', return_value=(149.9999, 150.0001))
    
    mock_draw = mocker.patch.object(canvas, 'draw')
    
    canvas.properties['xScaleFactor'] = 0.1
    canvas.properties['checkLimits'] = False
    canvas.properties['maxZoom'] = 0.0005
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_not_called()

def test_onMScroll_respects_x_limits_zoom(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 9: Test X-Axis Scaling respects limits."""
    canvas, mock_graphics = setup_scroll
    mock_mouse_event_scroll.AltDown.return_value = True
    mocker.patch.object(canvas, 'getCursorPosition', return_value=(10.0, 500.0))
    mocker.patch.object(canvas, 'getCurrentXRange', return_value=(0.0, 100.0))
    
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['xScaleFactor'] = 1.0
    canvas.properties['checkLimits'] = True
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (0.0, 190.0), mocker.ANY)

def test_onMScroll_respects_x_limits_shift(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 9: Test X-Axis Shifting respects limits."""
    canvas, mock_graphics = setup_scroll
    mocker.patch.object(canvas, 'getCurrentXRange', return_value=(10.0, 110.0))
    
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['xScrollFactor'] = 1.0
    canvas.properties['checkLimits'] = True
    
    canvas.onMScroll(mock_mouse_event_scroll)
    mock_draw.assert_called_with(mock_graphics, (0.0, 100.0), mocker.ANY)

def test_onMScroll_auto_scale_y(setup_scroll, mock_mouse_event_scroll, mocker):
    """Step 10: Test Y-Axis Auto-Scaling."""
    canvas, mock_graphics = setup_scroll
    mock_get_max_y = mocker.patch.object(canvas, 'getMaxYRange', return_value=(10.0, 500.0))
    mock_draw = mocker.patch.object(canvas, 'draw')
    mocker.patch.object(canvas, 'rememberView')
    
    canvas.properties['autoScaleY'] = True
    
    canvas.onMScroll(mock_mouse_event_scroll)
    
    mock_get_max_y.assert_called()
    mock_draw.assert_called_with(mock_graphics, mocker.ANY, (10.0, 500.0))

# --- Step 10: onChar Navigation Tests ---

def test_onChar_full_size(setup_scroll, mocker, mock_event_factory):
    """Test onChar for HOME key with Control modifier (Full Size)."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mock_remember = mocker.patch.object(canvas, 'rememberView')
    
    # Mock ranges
    mocker.patch.object(canvas, 'getMaxXRange', return_value=(0.0, 1000.0))
    mocker.patch.object(canvas, 'getMaxYRange', return_value=(0.0, 5000.0))
    
    evt = mock_event_factory(keyCode=wx.WXK_HOME, control=True)
    canvas.onChar(evt)
    
    mock_draw.assert_called_with(mock_graphics, (0.0, 1000.0), (0.0, 5000.0))
    mock_remember.assert_called_with((0.0, 1000.0), (0.0, 5000.0))

def test_onChar_home(setup_scroll, mocker, mock_event_factory):
    """Test onChar for HOME key without modifiers (Plot Start)."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mock_remember = mocker.patch.object(canvas, 'rememberView')
    
    # Current range: (100, 200), diff = 100.
    # rangeXmin = 0.
    # New range: (0, 100).
    mocker.patch.object(canvas, 'getMaxXRange', return_value=(0.0, 1000.0))
    
    evt = mock_event_factory(keyCode=wx.WXK_HOME, control=False)
    canvas.onChar(evt)
    
    mock_draw.assert_called_with(mock_graphics, (0.0, 100.0), (0.0, 1000.0))
    mock_remember.assert_called_with((0.0, 100.0), (0.0, 1000.0))

def test_onChar_end(setup_scroll, mocker, mock_event_factory):
    """Test onChar for END key (Plot End)."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mock_remember = mocker.patch.object(canvas, 'rememberView')
    
    # Current range: (100, 200), diff = 100.
    # rangeXmax = 1000.
    # New range: (900, 1000).
    mocker.patch.object(canvas, 'getMaxXRange', return_value=(0.0, 1000.0))
    
    evt = mock_event_factory(keyCode=wx.WXK_END)
    canvas.onChar(evt)
    
    mock_draw.assert_called_with(mock_graphics, (900.0, 1000.0), (0.0, 1000.0))
    mock_remember.assert_called_with((900.0, 1000.0), (0.0, 1000.0))

def test_onChar_view_memory_back(setup_scroll, mocker, mock_event_factory):
    """Test onChar for BACK key (Zoom History Back)."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mock_remember = mocker.patch.object(canvas, 'rememberView')
    
    # Setup view memory
    # viewMemory[0] = history
    # viewMemory[1] = future
    view1 = ((0.0, 100.0), (0.0, 1000.0))
    view2 = ((50.0, 150.0), (0.0, 1000.0))
    canvas.viewMemory = [[view1, view2], []]
    
    evt = mock_event_factory(keyCode=wx.WXK_BACK)
    canvas.onChar(evt)
    
    # Should pop view2, put it in viewMemory[1], and set view to view1
    assert canvas.viewMemory[0] == [view1]
    assert canvas.viewMemory[1] == [view2]
    mock_draw.assert_called_with(mock_graphics, view1[0], view1[1])
    mock_remember.assert_not_called()

def test_onChar_view_memory_forth(setup_scroll, mocker, mock_event_factory):
    """Test onChar for BACK key with Alt modifier (Zoom History Forth)."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    mock_remember = mocker.patch.object(canvas, 'rememberView')
    
    # Setup view memory
    view1 = ((0.0, 100.0), (0.0, 1000.0))
    view2 = ((50.0, 150.0), (0.0, 1000.0))
    canvas.viewMemory = [[view1], [view2]]
    
    evt = mock_event_factory(keyCode=wx.WXK_BACK, alt=True)
    canvas.onChar(evt)
    
    # Should pop view2 from viewMemory[1], append to viewMemory[0], and set view to view2
    assert canvas.viewMemory[0] == [view1, view2]
    assert canvas.viewMemory[1] == []
    mock_draw.assert_called_with(mock_graphics, view2[0], view2[1])
    mock_remember.assert_not_called()

def test_onChar_view_memory_empty(setup_scroll, mocker, mock_event_factory):
    """Test onChar for BACK key when history/future is empty."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    
    # Empty history (length <= 1)
    canvas.viewMemory = [[((0.0, 100.0), (0.0, 1000.0))], []]
    evt = mock_event_factory(keyCode=wx.WXK_BACK)
    canvas.onChar(evt)
    mock_draw.assert_not_called()
    
    # Empty future
    canvas.viewMemory = [[((0.0, 100.0), (0.0, 1000.0))], []]
    evt = mock_event_factory(keyCode=wx.WXK_BACK, alt=True)
    canvas.onChar(evt)
    mock_draw.assert_not_called()

def test_onChar_maxZoom_constraint(setup_scroll, mocker, mock_event_factory):
    """Test onChar early return when maxZoom constraint is violated."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    
    # Set current range to width 100
    canvas.lastDraw = (mock_graphics, (100.0, 200.0), (0.0, 1000.0))
    canvas.properties['maxZoom'] = 110
    canvas.properties['xScaleFactor'] = 0.1
    
    # RIGHT key zooms in (direction = -1)
    # scale = (200 - 100) * 0.1 * -1 = -10
    # minX = 100 - (-10) = 110, maxX = 200 + (-10) = 190. Width = 80.
    # 80 < 110 (maxZoom) -> should return early.
    evt = mock_event_factory(keyCode=wx.WXK_RIGHT, alt=True)
    canvas.onChar(evt)
    
    mock_draw.assert_not_called()

def test_onChar_checkLimits_constraint(setup_scroll, mocker, mock_event_factory):
    """Test onChar coordinate clipping when checkLimits is True."""
    canvas, mock_graphics = setup_scroll
    mock_draw = mocker.patch.object(canvas, 'draw')
    
    # Set absolute limits
    mocker.patch.object(canvas, 'getMaxXRange', return_value=(0.0, 1000.0))
    canvas.properties['checkLimits'] = True
    canvas.properties['xScaleFactor'] = 0.1
    canvas.properties['xMoveFactor'] = 0.1
    
    # 1. Test Scale clipping
    # current range (5.0, 100.0)
    canvas.lastDraw = (mock_graphics, (5.0, 100.0), (0.0, 1000.0))
    # scale OUT (LEFT key, direction = 1)
    # scale = (100 - 5) * 0.1 * 1 = 9.5
    # minX = 5.0 - 9.5 = -4.5 -> clipped to 0.0
    # maxX = 100 + 9.5 = 109.5
    evt_scale = mock_event_factory(keyCode=wx.WXK_LEFT, alt=True)
    canvas.onChar(evt_scale)
    mock_draw.assert_called_with(mock_graphics, (0.0, 109.5), (0.0, 1000.0))
    
    # 2. Test Shift clipping
    # current range (0.0, 100.0)
    canvas.lastDraw = (mock_graphics, (0.0, 100.0), (0.0, 1000.0))
    # move LEFT (LEFT key, direction = 1)
    # shift = (0 - 100) * 0.1 * 1 = -10
    # minX + shift = 0 - 10 = -10 -> shift adjusted to 0 - 0 = 0
    evt_shift = mock_event_factory(keyCode=wx.WXK_LEFT)
    canvas.onChar(evt_shift)
    mock_draw.assert_called_with(mock_graphics, (0.0, 100.0), (0.0, 1000.0))

@pytest.mark.parametrize("showXPosBar", [True, False])
@pytest.mark.parametrize("showYPosBar", [True, False])
@pytest.mark.parametrize("showGel", [True, False])
@pytest.mark.parametrize("showLegend", [True, False])
def test_draw_layout_combinations(patched_canvas, mock_dc, mocker, showXPosBar, showYPosBar, showGel, showLegend):
    """Test draw() with various layout property combinations."""
    mock_graphics = mocker.Mock()
    mock_graphics.countGels.return_value = 1
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 100))
    mock_graphics.getLegend.return_value = []
    
    patched_canvas.properties['showXPosBar'] = showXPosBar
    patched_canvas.properties['showYPosBar'] = showYPosBar
    patched_canvas.properties['showGel'] = showGel
    patched_canvas.properties['showLegend'] = showLegend
    
    # Patch sub-renderers
    mock_drawXPos = mocker.patch.object(patched_canvas, 'drawXPositionBar')
    mock_drawYPos = mocker.patch.object(patched_canvas, 'drawYPositionBar')
    mock_drawGel = mocker.patch.object(patched_canvas, 'drawGelView')
    mock_drawLegend = mocker.patch.object(patched_canvas, 'drawLegend')
    
    patched_canvas.draw(mock_graphics, xAxis=(0, 1000), yAxis=(0, 100))
    
    assert mock_drawXPos.called == showXPosBar
    assert mock_drawYPos.called == showYPosBar
    assert mock_drawGel.called == showGel
    assert mock_drawLegend.called == showLegend

def test_drawCursorTracker_with_gel(patched_canvas, mocker, mock_dc):
    """Test drawCursorTracker when showGel is True."""
    mocker.patch('wx.ClientDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 100, 750, 550) # minYPlot = 100
    patched_canvas.cursorPosition = [100.0, 200.0, 150, 250]
    patched_canvas.properties['showGel'] = True
    patched_canvas.gelsCount = 2
    patched_canvas.properties['gelHeight'] = 10
    patched_canvas.printerScale = {'drawings': 1}
    
    # expected gel coordinates
    # minYGel = 100 - 9 = 91
    # maxYGel = 91 - 2 * 10 = 71
    
    mock_dc.DrawLine.reset_mock()
    patched_canvas.drawCursorTracker()
    
    # Verify vertical line in gel area
    # dc.DrawLine(x, minYGel, x, maxYGel) -> (150, 91, 150, 71)
    mock_dc.DrawLine.assert_any_call(150, 91, 150, 71)

def test_drawZoomBox_with_gel(patched_canvas, mocker, mock_dc):
    """Test drawZoomBox when showGel is True."""
    mocker.patch('wx.ClientDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 100, 750, 550)
    patched_canvas.draggingStart = [50.0, 50.0, 60, 120]
    patched_canvas.cursorPosition = [100.0, 100.0, 160, 220]
    patched_canvas.properties['showGel'] = True
    patched_canvas.properties['zoomAxis'] = 'x'
    patched_canvas.gelsCount = 2
    patched_canvas.properties['gelHeight'] = 10
    patched_canvas.printerScale = {'drawings': 1}
    
    # expected gel coordinates
    # minYGel = 100 - 8 = 92
    # maxYGel = 92 - 2 * 10 = 72
    # Then adjusted if zoomAxis == 'x':
    # minYGel += 1 = 93
    # maxYGel -= 1 = 71
    # dc.DrawRectangle(minX, maxYGel, maxX - minX, minYGel-maxYGel)
    # (60, 71, 100, 22)
    
    mock_dc.DrawRectangle.reset_mock()
    patched_canvas.drawZoomBox()
    
    mock_dc.DrawRectangle.assert_any_call(60, 71, 100, 22)

def test_drawIsotopeRuler_with_gel(patched_canvas, mocker, mock_dc):
    """Test drawIsotopeRuler when showGel is True."""
    mocker.patch('wx.ClientDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 100, 750, 550)
    patched_canvas.cursorPosition = [100.0, 200.0, 150, 250]
    patched_canvas.properties['showGel'] = True
    patched_canvas.gelsCount = 1
    patched_canvas.properties['gelHeight'] = 10
    patched_canvas.printerScale = {'drawings': 1}
    
    # Mock positionUserToScreen to return fixed values for isotopes
    mocker.patch.object(patched_canvas, 'positionUserToScreen', side_effect=lambda pos: (pos[0], pos[1]))
    
    # expected gel coordinates
    # minYGel = 100 - 9 = 91
    # maxYGel = 91 - 1 * 10 = 81
    
    mock_dc.DrawLine.reset_mock()
    patched_canvas.drawIsotopeRuler()
    
    # Verify isotope lines in gel area
    # dc.DrawLine(isotope[0], minYGel, isotope[0], maxYGel)
    mock_dc.DrawLine.assert_any_call(mocker.ANY, 91, mocker.ANY, 81)

@pytest.mark.parametrize("direction, expected_poly", [
    ('up', [(150, 251), (147, 258), (153, 258)]),
    ('down', [(150, 251), (147, 244), (153, 244)]),
    ('left', [(157, 253), (150, 256), (157, 259)]),
    ('right', [(143, 253), (150, 256), (143, 259)]),
])
def test_drawPointArrow_directions(patched_canvas, mocker, mock_dc, direction, expected_poly):
    """Test drawPointArrow with various directions."""
    # drawPointArrow uses wx.ClientDC and wx.BufferedDC internally
    mocker.patch('wx.ClientDC', return_value=mocker.Mock())
    mocker.patch('wx.BufferedDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 50, 750, 550)
    
    # Call drawPointArrow(x, y, direction)
    patched_canvas.drawPointArrow(150, 250, direction)
    
    # Verify dc.DrawPolygon was called with expected points
    # Note: y is shifted by +1 internally: y += 1 -> 251
    # For 'up': [(x, y), (x-3, y+7), (x+3, y+7)] -> [(150, 251), (147, 258), (153, 258)]
    # For 'down': [(x, y), (x-3, y-7), (x+3, y-7)] -> [(150, 251), (147, 244), (153, 244)]
    # For 'left': [(x+7, y+2), (x, y+5), (x+7, y+8)] -> [(157, 253), (150, 256), (157, 259)]
    # For 'right': [(x-7, y+2), (x, y+5), (x-7, y+8)] -> [(143, 253), (150, 256), (143, 259)]
    mock_dc.DrawPolygon.assert_called_once_with(expected_poly)

def test_drawPointArrow_clipping(patched_canvas, mocker, mock_dc):
    """Test drawPointArrow clipping at boundaries."""
    mocker.patch('wx.ClientDC', return_value=mocker.Mock())
    mocker.patch('wx.BufferedDC', return_value=mock_dc)
    
    patched_canvas.plotCoords = (50, 50, 750, 550)
    
    # Test clipping left
    mock_dc.DrawPolygon.reset_mock()
    patched_canvas.drawPointArrow(10, 250, 'up')
    # x becomes 50, direction becomes 'left'
    # y = 251
    # 'left': [(x+7, y+2), (x, y+5), (x+7, y+8)] -> [(57, 253), (50, 256), (57, 259)]
    mock_dc.DrawPolygon.assert_called_with([(57, 253), (50, 256), (57, 259)])
    
    # Test clipping right
    mock_dc.DrawPolygon.reset_mock()
    patched_canvas.drawPointArrow(800, 250, 'up')
    # x becomes 750-1 = 749, direction becomes 'right'
    # 'right': [(x-7, y+2), (x, y+5), (x-7, y+8)] -> [(742, 253), (749, 256), (742, 259)]
    mock_dc.DrawPolygon.assert_called_with([(742, 253), (749, 256), (742, 259)])

@pytest.mark.parametrize("showGrid", [True, False])
@pytest.mark.parametrize("showMinorTicks", [True, False])
@pytest.mark.parametrize("showZero", [True, False])
def test_drawAxis_variations(patched_canvas, mock_dc, showGrid, showMinorTicks, showZero):
    """Test drawAxis() with various property states."""
    # Setup ticks: one major, one minor on X; one zero, one major, one minor on Y
    xticks = [(500, '500', 'major'), (250, '', 'minor')]
    yticks = [(0, '0', 'major'), (50, '50', 'major'), (25, '', 'minor')]
    
    patched_canvas.plotCoords = (50, 50, 750, 550)
    patched_canvas.pointScale = numpy.array([0.7, -10.0])
    patched_canvas.pointShift = numpy.array([50.0, 550.0])
    
    patched_canvas.properties['showGrid'] = showGrid
    patched_canvas.properties['showMinorTicks'] = showMinorTicks
    patched_canvas.properties['showZero'] = showZero
    
    mock_dc.DrawLine.reset_mock()
    patched_canvas.drawAxis(mock_dc, xticks, yticks)
    
    # Total DrawLine calls calculation:
    # X Axis: 1 (major) + (1 if minor) + (1 if grid)
    # Y Axis: 2 (major) + (1 if minor) + (2 if grid) + (1 if zero)
    # Grand Total: 3 + (2 if minor) + (3 if grid) + (1 if zero)
    
    expected_calls = 3
    if showMinorTicks:
        expected_calls += 2
    if showGrid:
        expected_calls += 3
    if showZero:
        expected_calls += 1
        
    assert mock_dc.DrawLine.call_count == expected_calls
    
    # Verify DrawText calls
    # XTicks: 1 major -> 1 label
    # YTicks: 2 major -> 2 labels
    # Total 3 labels if no overlap (which they don't in this test setup)
    assert mock_dc.DrawText.call_count == 3

# --- Task 5: ensureVisible and highlightXPoints ---

def test_ensureVisible_no_points(canvas_fixture, mocker):
    """Test ensureVisible with empty points list (should return early)."""
    mock_draw = mocker.patch.object(canvas_fixture, 'draw')
    canvas_fixture.ensureVisible([])
    mock_draw.assert_not_called()

def test_ensureVisible_centering(patched_canvas, mocker):
    """Test ensureVisible centers the plot around given points."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((-1000, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    mocker.patch.object(patched_canvas, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(-1000, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    mocker.patch.object(patched_canvas, 'rememberView')

    # Points [70, 80], center = 75. 
    # Current range width = 100. Half-width = 50.
    # New range: minX = 70-50 = 20, maxX = 80+50 = 130.
    patched_canvas.ensureVisible([70, 80])
    
    mock_draw.assert_called_with(mock_graphics, (20, 130), (0, 1000))

def test_ensureVisible_limits(patched_canvas, mocker):
    """Test ensureVisible respects maxXRange limits."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    # Limits are 0 to 1000
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    
    # Points [10], center = 10. Half-width = 50.
    # Calculated minX = -40, maxX = 60.
    # Clipped: minX < 0 -> diff = 40. minX = 0, maxX = 60 + 40 = 100.
    patched_canvas.ensureVisible([10])
    
    mock_draw.assert_called_with(mock_graphics, (0.0, 100.0), mocker.ANY)

def test_ensureVisible_zoom(patched_canvas, mocker):
    """Test ensureVisible with zoom=True."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((-1000, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(-1000, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    
    # Points [100], center = 100. zoom = 10 (10%).
    # minX = 100 - 100*10/100 = 90
    # maxX = 100 + 100*10/100 = 110
    patched_canvas.ensureVisible([100], zoom=10)
    
    mock_draw.assert_called_with(mock_graphics, (90.0, 110.0), mocker.ANY)

def test_highlightXPoints(patched_canvas, mocker):
    """Test highlightXPoints calls ensureVisible and drawPointArrow."""
    mock_ensure = mocker.patch.object(patched_canvas, 'ensureVisible')
    mock_arrow = mocker.patch.object(patched_canvas, 'drawPointArrow')
    mocker.patch.object(patched_canvas, 'positionUserToScreen', return_value=(150, 0))
    patched_canvas.plotCoords = (0, 0, 800, 600)
    
    patched_canvas.highlightXPoints([100])
    
    mock_ensure.assert_called_once_with([100], False)
    mock_arrow.assert_called_once_with(150, 600)

# --- Task 6: zoom Variations ---

def test_zoom_xAxis_only(patched_canvas, mocker):
    """Test zoom with only xAxis provided."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    mocker.patch.object(patched_canvas, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    
    # autoScaleY=False
    patched_canvas.properties['autoScaleY'] = False
    patched_canvas.zoom(xAxis=(20, 80))
    
    mock_draw.assert_called_with(mock_graphics, (20, 80), (0, 1000))

def test_zoom_yAxis_only(patched_canvas, mocker):
    """Test zoom with only yAxis provided."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getCurrentXRange', return_value=(0, 100))
    mocker.patch.object(patched_canvas, 'getCurrentYRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 1000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    
    patched_canvas.zoom(yAxis=(200, 800))
    
    mock_draw.assert_called_with(mock_graphics, (0, 100), (200, 800))

def test_zoom_checkLimits_property(patched_canvas, mocker):
    """Test zoom respects checkLimits property."""
    mock_graphics = mocker.Mock()
    mock_graphics.getBoundingBox.return_value = ((0, 0), (1000, 1000))
    patched_canvas.lastDraw = (mock_graphics, (0, 100), (0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxXRange', return_value=(0, 1000))
    mocker.patch.object(patched_canvas, 'getMaxYRange', return_value=(0, 5000))
    mock_draw = mocker.patch.object(patched_canvas, 'draw')
    
    # 1. checkLimits=True
    patched_canvas.properties['checkLimits'] = True
    patched_canvas.zoom(xAxis=(-100, 2000))
    # xAxis: (-100, 2000) clipped to (0, 1000)
    mock_draw.assert_called_with(mock_graphics, (0, 1000), mocker.ANY)
    
    # 2. checkLimits=False
    patched_canvas.properties['checkLimits'] = False
    mock_draw.reset_mock()
    patched_canvas.zoom(xAxis=(-100, 2000))
    mock_draw.assert_called_with(mock_graphics, (-100, 2000), mocker.ANY)
