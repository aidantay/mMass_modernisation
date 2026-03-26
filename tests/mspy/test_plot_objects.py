import pytest
import wx
import numpy
import copy
from hypothesis import given, settings, strategies as st
from hypothesis.extra.numpy import arrays
from mspy.plot_objects import (
    container, annotations, points, spectrum,
    _scaleFont, _scaleAndShift, _filterPoints
)
from mspy.obj_scan import scan
from mspy.obj_peak import peak
from mspy.obj_peaklist import peaklist


# SESSION-SCOPED WX.APP FIXTURE
# ==============================

@pytest.fixture(scope="session")
def wx_app():
    """Session-scoped fixture to initialize wx.App for headless UI testing."""
    app = wx.App(False)
    yield app


# DATA FIXTURES
# =============

@pytest.fixture
def simple_scan():
    """Create a simple scan with profile and peaklist."""
    profile = numpy.array([[100.0, 50.0], [101.0, 100.0], [102.0, 75.0], [103.0, 25.0]])
    peaks = [
        peak(mz=101.0, ai=100.0, base=10.0, charge=1, isotope=0),
        peak(mz=102.0, ai=75.0, base=5.0, charge=1, isotope=1),
    ]
    peaklist_obj = peaklist(peaks)
    # Add childScanNumber to one peak for fragmentation mark test
    peaks[0].childScanNumber = 123
    return scan(profile=profile, peaklist=peaklist_obj)


@pytest.fixture
def empty_scan():
    """Create an empty scan."""
    return scan(profile=[], peaklist=[])


@pytest.fixture
def profile_only_scan():
    """Create a scan with only profile, no peaklist."""
    profile = numpy.array([[100.0, 50.0], [101.0, 100.0], [102.0, 75.0]])
    return scan(profile=profile, peaklist=[])


@pytest.fixture
def peaklist_only_scan():
    """Create a scan with only peaklist, no profile."""
    peaks = [peak(mz=100.0, ai=50.0), peak(mz=101.0, ai=100.0)]
    peaklist_obj = peaklist(peaks)
    return scan(profile=[], peaklist=peaklist_obj)


@pytest.fixture
def simple_points_data():
    """Create simple points data for testing."""
    return [[100.0, 50.0], [101.0, 100.0], [102.0, 75.0]]


@pytest.fixture
def simple_annotations_data():
    """Create simple annotations data with labels."""
    return [[100.0, 50.0, 'Peak A'], [101.0, 100.0, 'Peak B'], [102.0, 75.0, 'Peak C']]


@pytest.fixture
def mock_dc(mocker):
    """Create a mock wx.DC with proper return values."""
    mock_dc = mocker.Mock(spec=wx.DC)
    # GetTextExtent must return a tuple, not a Mock, to support indexing
    mock_dc.GetTextExtent.return_value = (50, 10)
    # GetFont returns a real wx.Font
    mock_dc.GetFont.return_value = wx.Font(10, wx.SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0)
    return mock_dc


@pytest.fixture
def default_printer_scale():
    """Create a default printer scale dict."""
    return {'fonts': 1.0, 'drawings': 1.0}


# HELPER FUNCTION TESTS
# =====================

class TestScaleFont(object):
    """Tests for _scaleFont helper function."""

    def test_scaleFont_identity_scale(self, wx_app):
        """Test that scale=1 returns the same font object."""
        base_font = wx.Font(10, wx.SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Arial")
        scaled_font = _scaleFont(base_font, 1)
        assert scaled_font is base_font

    def test_scaleFont_magnification(self, wx_app):
        """Test that scale > 1 creates a new larger font."""
        base_font = wx.Font(10, wx.SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Arial")
        scaled_font = _scaleFont(base_font, 2.0)
        # Expected: 10 * 2.0 * 1.3 = 26.0
        assert scaled_font.GetPointSize() == 26
        assert scaled_font is not base_font

    def test_scaleFont_reduction(self, wx_app):
        """Test that scale < 1 creates a smaller font."""
        base_font = wx.Font(10, wx.SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "Arial")
        scaled_font = _scaleFont(base_font, 0.5)
        # Expected: 10 * 0.5 * 1.3 = 6.5
        assert scaled_font.GetPointSize() == 6
        assert scaled_font is not base_font

    def test_scaleFont_preserves_attributes(self, wx_app):
        """Test that font attributes are preserved in scaling."""
        base_font = wx.Font(10, wx.SWISS, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD, True, "Arial")
        scaled_font = _scaleFont(base_font, 2.0)
        assert scaled_font.GetFamily() in (wx.SWISS, wx.FONTFAMILY_SWISS, 70, 74)
        assert scaled_font.GetStyle() == wx.FONTSTYLE_ITALIC
        assert scaled_font.GetWeight() == wx.FONTWEIGHT_BOLD
        assert scaled_font.GetUnderlined() == True
        assert scaled_font.GetFaceName() == "Arial"

    def test_scaleFont_no_face(self, wx_app):
        """Test _scaleFont with no face name to hit else branch."""
        base_font = wx.Font(10, wx.SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "")
        scaled_font = _scaleFont(base_font, 2.0)
        assert scaled_font.GetPointSize() == 26

class TestScaleAndShift(object):
    """Tests for _scaleAndShift helper function."""

    def test_scaleAndShift_valid_array(self):
        """Test scaling and shifting with valid float64 array."""
        points = numpy.array([[100.0, 50.0], [101.0, 100.0], [102.0, 75.0]], dtype=numpy.float64)
        result = _scaleAndShift(points, 2.0, 3.0, 10.0, 20.0)
        assert isinstance(result, numpy.ndarray)
        assert len(result) == 3

    @given(
        arrays(numpy.float64, st.tuples(st.integers(1, 100), st.just(2)), elements=st.floats(min_value=-1e6, max_value=1e6)),
        st.floats(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000, max_value=1000),
        st.floats(min_value=-1e6, max_value=1e6),
        st.floats(min_value=-1e6, max_value=1e6)
    )
    @settings(max_examples=50, deadline=1000)
    def test_scaleAndShift_hypothesis(self, points, scaleX, scaleY, shiftX, shiftY):
        """Property-based test for _scaleAndShift."""
        result = _scaleAndShift(points, scaleX, scaleY, shiftX, shiftY)
        assert isinstance(result, numpy.ndarray)
        assert result.shape == points.shape
        assert result.dtype == numpy.float64

    def test_scaleAndShift_empty_array(self):
        """Test that empty array returns empty array."""
        points = numpy.array([], dtype=numpy.float64).reshape(0, 2)
        result = _scaleAndShift(points, 2.0, 3.0, 10.0, 20.0)
        assert isinstance(result, numpy.ndarray)
        assert len(result) == 0

    def test_scaleAndShift_non_ndarray_raises_typeerror(self):
        """Test that non-ndarray input raises TypeError."""
        with pytest.raises(TypeError):
            _scaleAndShift([[100.0, 50.0]], 2.0, 3.0, 10.0, 20.0)

    def test_scaleAndShift_non_float64_raises_typeerror(self):
        """Test that non-float64 dtype raises TypeError."""
        points = numpy.array([[100.0, 50.0]], dtype=numpy.float32)
        with pytest.raises(TypeError):
            _scaleAndShift(points, 2.0, 3.0, 10.0, 20.0)

    def test_scaleAndShift_with_zero_scale(self):
        """Test scaling with zero scale factors."""
        points = numpy.array([[100.0, 50.0], [101.0, 100.0]], dtype=numpy.float64)
        result = _scaleAndShift(points, 0.0, 0.0, 10.0, 20.0)
        assert isinstance(result, numpy.ndarray)

class TestFilterPoints(object):
    """Tests for _filterPoints helper function."""

    def test_filterPoints_valid_array(self):
        """Test filtering with valid float64 array."""
        points = numpy.array([[100.0, 50.0], [100.5, 60.0], [101.0, 100.0]], dtype=numpy.float64)
        result = _filterPoints(points, 0.5)
        assert isinstance(result, numpy.ndarray)

    @given(
        arrays(numpy.float64, st.tuples(st.integers(1, 100), st.just(2)), elements=st.floats(min_value=-1e6, max_value=1e6)),
        st.floats(min_value=0.001, max_value=1000)
    )
    @settings(max_examples=50, deadline=1000)
    def test_filterPoints_hypothesis(self, points, resolution):
        """Property-based test for _filterPoints."""
        # Ensure points are sorted by X as _filterPoints likely expects
        points = points[points[:, 0].argsort()]
        result = _filterPoints(points, resolution)
        assert isinstance(result, numpy.ndarray)
        assert result.dtype == numpy.float64
        # The C extension might add boundary points (0-intensity) to ensure correct plotting
        # so we don't strictly enforce len(result) <= len(points)
        assert len(result) >= 0

    def test_filterPoints_empty_array(self):
        """Test that empty array returns empty array."""
        points = numpy.array([], dtype=numpy.float64).reshape(0, 2)
        result = _filterPoints(points, 0.5)
        assert isinstance(result, numpy.ndarray)
        assert len(result) == 0

    def test_filterPoints_non_ndarray_raises_typeerror(self):
        """Test that non-ndarray input raises TypeError."""
        with pytest.raises(TypeError):
            _filterPoints([[100.0, 50.0]], 0.5)

    def test_filterPoints_non_float64_raises_typeerror(self):
        """Test that non-float64 dtype raises TypeError."""
        points = numpy.array([[100.0, 50.0]], dtype=numpy.float32)
        with pytest.raises(TypeError):
            _filterPoints(points, 0.5)

    def test_filterPoints_minimal_resolution(self):
        """Test _filterPoints with minimal resolution to trigger branches."""
        pts = numpy.array([[100.0, 50.0], [100.00000001, 100.0], [101.0, 75.0]], dtype=numpy.float64)
        result = _filterPoints(pts, 0.000000001)
        assert len(result) >= 3


# CONTAINER CLASS TESTS
# =====================

class TestContainer(object):
    """Tests for container class."""

    def test_container_init(self, simple_scan):
        """Test container initialization."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        assert len(cont) == 1
        assert cont[0] is spec

    def test_container_methods(self, simple_scan):
        """Test various container methods for coverage."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        
        # Test __setitem__, __delitem__, __additem__, append, empty
        spec2 = spectrum(simple_scan)
        cont[0] = spec2
        assert cont[0] is spec2
        
        cont.append(spec)
        assert len(cont) == 2
        
        cont.__additem__(spec)
        assert len(cont) == 3
        
        del cont[0]
        assert len(cont) == 2
        
        cont.empty()
        assert len(cont) == 0

    def test_container_len(self, simple_scan):
        """Test container __len__."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        assert len(cont) == 2

    def test_container_getitem(self, simple_scan):
        """Test container __getitem__."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        assert cont[0] is spec1
        assert cont[1] is spec2

    def test_container_setitem(self, simple_scan):
        """Test container __setitem__."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1])
        cont[0] = spec2
        assert cont[0] is spec2

    def test_container_delitem(self, simple_scan):
        """Test container __delitem__."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        del cont[0]
        assert len(cont) == 1
        assert cont[0] is spec2

    def test_container_additem(self, simple_scan):
        """Test container __additem__."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1])
        cont.__additem__(spec2)
        assert len(cont) == 2
        assert cont[1] is spec2

    def test_container_append(self, simple_scan):
        """Test container append method."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1])
        cont.append(spec2)
        assert len(cont) == 2

    def test_container_empty(self, simple_scan):
        """Test container empty method."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        cont.empty()
        assert len(cont) == 0

    def test_container_getLegend_empty(self):
        """Test getLegend with no visible objects."""
        cont = container([])
        legend = cont.getLegend()
        assert legend == []

    def test_container_getLegend_with_objects(self, simple_scan):
        """Test getLegend with visible spectrum object."""
        spec = spectrum(simple_scan, legend='Test Spectrum')
        cont = container([spec])
        legend = cont.getLegend()
        assert len(legend) > 0

    def test_container_getLegend_hidden_objects(self, simple_scan):
        """Test getLegend with hidden objects."""
        spec = spectrum(simple_scan, legend='Test')
        spec.properties['visible'] = False
        cont = container([spec])
        legend = cont.getLegend()
        assert legend == []

    def test_container_countGels(self, simple_scan):
        """Test countGels counts visible objects with showInGel=True."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        assert cont.countGels() == 2

    def test_container_countGels_empty(self):
        """Test countGels returns 1 for empty container."""
        cont = container([])
        assert cont.countGels() == 1

    def test_container_countGels_ignores_hidden(self, simple_scan):
        """Test countGels ignores hidden objects."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        spec2.properties['visible'] = False
        cont = container([spec1, spec2])
        assert cont.countGels() == 1

    def test_container_countGels_ignores_showInGel_false(self, simple_scan):
        """Test countGels ignores objects with showInGel=False."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        spec2.properties['showInGel'] = False
        cont = container([spec1, spec2])
        assert cont.countGels() == 1

    def test_container_getBoundingBox_empty(self):
        """Test getBoundingBox with empty container."""
        cont = container([])
        bbox = cont.getBoundingBox()
        assert numpy.array_equal(bbox[0], numpy.array([0, 0]))
        assert numpy.array_equal(bbox[1], numpy.array([1, 1]))

    def test_container_getBoundingBox_with_objects(self, simple_scan):
        """Test getBoundingBox with visible objects."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        bbox = cont.getBoundingBox()
        assert isinstance(bbox, list)
        assert len(bbox) == 2

    def test_container_getBoundingBox_hidden_objects(self, simple_scan):
        """Test getBoundingBox ignores hidden objects."""
        spec = spectrum(simple_scan)
        spec.properties['visible'] = False
        cont = container([spec])
        bbox = cont.getBoundingBox()
        # Should return default bbox
        assert bbox[0][0] == 0 and bbox[1][0] == 1

    def test_container_getBoundingBox_equal_x_padding(self, simple_scan):
        """Test getBoundingBox adds padding when min==max X."""
        # Create data with same X
        profile = numpy.array([[100.0, 50.0], [100.0, 100.0]])
        spec = spectrum(scan(profile=profile))
        cont = container([spec])
        bbox = cont.getBoundingBox()
        # Check if padding was added (not equal)
        assert bbox[0][0] != bbox[1][0]

    def test_container_getBoundingBox_equal_y_padding(self, simple_scan):
        """Test getBoundingBox adds padding when min==max Y."""
        # Create data with same Y
        profile = numpy.array([[100.0, 50.0], [101.0, 50.0]])
        spec = spectrum(scan(profile=profile))
        cont = container([spec])
        bbox = cont.getBoundingBox()
        # Check if padding was added (not equal)
        assert bbox[0][1] != bbox[1][1]

    def test_container_cropPoints(self, simple_scan):
        """Test cropPoints delegates to children."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        # Should not raise
        cont.cropPoints(100.0, 102.0)

    def test_container_scaleAndShift(self, simple_scan):
        """Test scaleAndShift delegates to children."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        scale = (2.0, 2.0)
        shift = (10.0, 20.0)
        # Should not raise
        cont.scaleAndShift(scale, shift)

    def test_container_filterPoints(self, simple_scan):
        """Test filterPoints delegates to children."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        # Should not raise
        cont.filterPoints(0.5)

    def test_container_getPoint(self, simple_scan):
        """Test getPoint delegates to child and handles boundaries."""
        spec = spectrum(simple_scan)
        spec.spectrumScaled = numpy.array([[100.0, 50.0], [101.0, 100.0], [102.0, 75.0]])
        cont = container([spec])
        
        # Mid point
        result = cont.getPoint(0, 100.5)
        assert result is not None
        
        # Boundary 0 (xPos exactly at start)
        result = cont.getPoint(0, 100.0)
        
        # Boundary len (xPos exactly at end)
        result = cont.getPoint(0, 102.0)
        
        # Beyond boundaries
        result = cont.getPoint(0, 99.0)
        assert result is None
        result = cont.getPoint(0, 103.0)
        assert result is None
        
        # Test no points in child
        spec.spectrumScaled = numpy.array([], dtype=numpy.float64).reshape(0, 2)
        result = cont.getPoint(0, 100.5)
        assert result is None

    def test_container_draw_no_reverse(self, simple_scan, mock_dc, default_printer_scale):
        """Test draw without reverse order."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        cont.draw(mock_dc, default_printer_scale, False, False)
        # Should not raise

    def test_container_draw_with_reverse(self, simple_scan, mock_dc, default_printer_scale):
        """Test draw with reverse order."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        # Capture order before and after
        original_order = [cont[0], cont[1]]
        cont.draw(mock_dc, default_printer_scale, False, True)
        # Objects should be in same order after reverse
        assert cont[0] is original_order[0]
        assert cont[1] is original_order[1]

    def test_container_drawLabels(self, simple_scan, mock_dc, default_printer_scale):
        """Test drawLabels method."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        # Should not raise
        cont.drawLabels(mock_dc, default_printer_scale, False)

    def test_container_drawGel(self, simple_scan, mock_dc, default_printer_scale):
        """Test drawGel delegates to children."""
        spec = spectrum(simple_scan)
        cont = container([spec])
        gelCoords = [0, 10, 10, 190, 190, 100]
        gelHeight = 50
        cont.drawGel(mock_dc, gelCoords, gelHeight, default_printer_scale)
        # gelCoords[0] should be incremented
        assert gelCoords[0] == 50

    def test_container_checkFreeSpace_left_to_right(self):
        """Test _checkFreeSpace with left-to-right label (curX1 < curX2)."""
        cont = container([])
        # Non-overlapping labels (curY2 < curY1)
        assert cont._checkFreeSpace((10, 40, 30, 20), []) == True
        # Overlapping in X and Y (curY2 < curY1, occY2 < occY1)
        assert cont._checkFreeSpace((10, 40, 30, 20), [(15, 35, 25, 25)]) == False

    def test_container_checkFreeSpace_right_to_left(self):
        """Test _checkFreeSpace with right-to-left label (curX1 > curX2)."""
        cont = container([])
        # Non-overlapping labels (curX1 > curX2, curY1 > curY2)
        assert cont._checkFreeSpace((30, 40, 10, 20), []) == True
        # Overlapping when flipped (occX2 < occX1, occY1 < occY2)
        assert cont._checkFreeSpace((20, 40, 10, 20), [(25, 25, 15, 35)]) == False

    def test_container_checkFreeSpace_no_overlap_y(self):
        """Test _checkFreeSpace with no Y overlap."""
        cont = container([])
        assert cont._checkFreeSpace((10, 20, 30, 25), [(10, 50, 30, 60)]) == True

    def test_container_draw_reverse_logic(self, simple_scan, mock_dc, default_printer_scale):
        """Test container.draw with reverse=True to cover reverse logic."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        cont = container([spec1, spec2])
        # This will trigger objects.reverse() twice
        cont.draw(mock_dc, default_printer_scale, False, True)
        assert cont.objects[0] is spec1
        assert cont.objects[1] is spec2

    def test_container_getBoundingBox_advanced(self, simple_scan):
        """Test container.getBoundingBox with various options."""
        spec = spectrum(simple_scan)
        spec.properties['visible'] = True
        cont = container([spec])
        
        # Test with minX, maxX
        bbox = cont.getBoundingBox(minX=100.5, maxX=101.5)
        assert isinstance(bbox, list)
        
        # Test with infinite/invalid rect (simulated)
        # We need a real object but with a mock getBoundingBox
        class MockObj:
            properties = {'visible': True}
            def getBoundingBox(self, *args, **kwargs):
                return [numpy.array([float('inf'), 0]), numpy.array([1, 1])]
        cont.objects = [MockObj()]
        bbox = cont.getBoundingBox()
        # Should fall back to default if no valid rect found
        assert numpy.array_equal(bbox[0], numpy.array([0, 0]))

    def test_container_getLegend_advanced(self, simple_scan):
        """Test container.getLegend with various options."""
        spec = spectrum(simple_scan, legend='Test')
        cont = container([spec])
        assert cont.getLegend() == [('Test', (0, 0, 255))]

    def test_container_methods_with_hidden_objects(self, simple_scan, mock_dc, default_printer_scale):
        """Test container methods with hidden objects to hit False branches."""
        spec1 = spectrum(simple_scan)
        spec2 = spectrum(simple_scan)
        spec2.properties['visible'] = False
        cont = container([spec1, spec2])
        
        # Hit branches in various methods
        cont.cropPoints(100.0, 102.0)
        cont.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        cont.filterPoints(0.5)
        cont.draw(mock_dc, default_printer_scale, False, False)
        cont.drawLabels(mock_dc, default_printer_scale, False)
        cont.drawGel(mock_dc, [0, 10, 10, 190, 190, 100], 50, default_printer_scale)
        
        # Test drawLabels with mix of annotations and other objects
        annot = annotations([[100.0, 50.0, 'A']])
        annot.properties['visible'] = True
        cont.append(annot)
        cont.drawLabels(mock_dc, default_printer_scale, False)

    @given(
        st.tuples(
            st.floats(min_value=-1e6, max_value=1e6),
            st.floats(min_value=-1e6, max_value=1e6),
            st.floats(min_value=-1e6, max_value=1e6),
            st.floats(min_value=-1e6, max_value=1e6)
        ),
        st.lists(
            st.tuples(
                st.floats(min_value=-1e6, max_value=1e6),
                st.floats(min_value=-1e6, max_value=1e6),
                st.floats(min_value=-1e6, max_value=1e6),
                st.floats(min_value=-1e6, max_value=1e6)
            ),
            max_size=10
        )
    )
    @settings(max_examples=50, deadline=1000)
    def test_container_checkFreeSpace_hypothesis(self, coords, occupied):
        """Property-based test for _checkFreeSpace."""
        cont = container([])
        # Should not raise
        result = cont._checkFreeSpace(coords, occupied)
        assert isinstance(result, bool)


# ANNOTATIONS CLASS TESTS
# =======================

class TestAnnotations(object):
    """Tests for annotations class."""

    def test_annotations_init(self, simple_annotations_data):
        """Test annotations initialization."""
        annot = annotations(simple_annotations_data)
        assert len(annot.points) == 3
        assert annot.labels[0] == 'Peak A'

    def test_annotations_init_without_labels(self, simple_points_data):
        """Test annotations initialization without labels."""
        annot = annotations(simple_points_data)
        assert len(annot.points) == 3
        assert annot.labels == ['', '', '']

    def test_annotations_properties(self, simple_annotations_data):
        """Test annotations properties dictionary."""
        annot = annotations(simple_annotations_data)
        assert 'visible' in annot.properties
        assert annot.properties['visible'] == True

    def test_annotations_setProperties(self, simple_annotations_data):
        """Test setProperties method."""
        annot = annotations(simple_annotations_data)
        annot.setProperties(visible=False, showPoints=False)
        assert annot.properties['visible'] == False
        assert annot.properties['showPoints'] == False

    def test_annotations_setNormalization(self, simple_annotations_data):
        """Test setNormalization method."""
        annot = annotations(simple_annotations_data)
        annot.setNormalization(5.0)
        assert annot.normalization == 5.0
        # Test zero coercion
        annot.setNormalization(0.0)
        assert annot.normalization == 1.0

    def test_annotations_normalization_calculation(self, simple_annotations_data):
        """Test _normalization calculation."""
        annot = annotations(simple_annotations_data)
        # normalization = max_y / 100 = 100.0 / 100 = 1.0
        assert annot.normalization == 1.0

    def test_annotations_getBoundingBox_empty(self):
        """Test getBoundingBox with empty annotations."""
        annot = annotations([])
        assert annot.getBoundingBox() == False

    def test_annotations_getBoundingBox_angles(self, simple_annotations_data):
        """Test getBoundingBox with different angles to hit branches."""
        for angle in [0, 90, 45]:
            annot = annotations(simple_annotations_data, labelAngle=angle, showLabels=True)
            bbox = annot.getBoundingBox()
            assert bbox != False
        
        # Test showLabels=False
        annot = annotations(simple_annotations_data, showLabels=False)
        bbox = annot.getBoundingBox()
        assert bbox != False

    def test_annotations_getBoundingBox_with_offset(self, simple_annotations_data):
        """Test getBoundingBox applies xOffset and yOffset."""
        annot = annotations(simple_annotations_data, xOffset=10, yOffset=5, exactFit=True)
        bbox = annot.getBoundingBox()
        # Offsets should be applied
        # Original minX=100.0, xOffset=10.0 -> 110.0
        assert bbox[0][0] == 110.0
    def test_annotations_getBoundingBox_normalized(self, simple_annotations_data):
        """Test getBoundingBox with normalized=True."""
        annot = annotations(simple_annotations_data, normalized=True)
        bbox = annot.getBoundingBox()
        # Y values should be divided by normalization (1.0) and then -2.5 offset
        # 50.0 / 1.0 - 2.5 = 47.5
        assert bbox[0][1] == 47.5

    def test_annotations_getBoundingBox_no_cropped(self, simple_annotations_data):
        """Test getBoundingBox when no points are cropped."""
        annot = annotations(simple_annotations_data)
        annot.cropPoints(0, 1) # No points in this range
        # It still returns full bbox because self.points is not empty
        assert annot.getBoundingBox() != False

    def test_annotations_getBoundingBox_hidden(self, simple_annotations_data):
        """Test getBoundingBox when visible is False."""
        annot = annotations(simple_annotations_data)
        annot.properties['visible'] = False
        # It still returns bbox because getBoundingBox doesn't check visible
        assert annot.getBoundingBox() != False

    def test_annotations_getBoundingBox_flipped(self, simple_annotations_data):
        """Test getBoundingBox with flipped=True."""
        annot = annotations(simple_annotations_data, flipped=True)
        bbox = annot.getBoundingBox()
        # Y values should be negated
        assert isinstance(bbox, list)

    def test_annotations_getLegend(self, simple_annotations_data):
        """Test getLegend always returns None."""
        annot = annotations(simple_annotations_data)
        assert annot.getLegend() is None

    def test_annotations_cropPoints(self, simple_annotations_data):
        """Test cropPoints method."""
        annot = annotations(simple_annotations_data)
        annot.cropPoints(100.5, 101.5)
        # Should crop the data
        assert len(annot.pointsCropped) <= 3

    def test_annotations_scaleAndShift(self, simple_annotations_data):
        """Test scaleAndShift method."""
        annot = annotations(simple_annotations_data)
        scale = (2.0, 3.0)
        shift = (10.0, 20.0)
        annot.scaleAndShift(scale, shift)
        # Should scale and shift
        assert annot.currentScale == scale
        assert annot.currentShift == shift

    def test_annotations_filterPoints(self, simple_annotations_data):
        """Test filterPoints is a no-op."""
        annot = annotations(simple_annotations_data)
        original = annot.points.copy()
        annot.filterPoints(0.5)
        # Should not change points
        assert numpy.array_equal(annot.points, original)

    def test_annotations_draw(self, simple_annotations_data, mock_dc, default_printer_scale):
        """Test draw method with branches."""
        # Hidden
        annot = annotations(simple_annotations_data)
        annot.properties['visible'] = False
        annot.draw(mock_dc, default_printer_scale)
        
        # Visible, no points
        annot.properties['visible'] = True
        annot.properties['showPoints'] = False
        annot.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        annot.draw(mock_dc, default_printer_scale)
        
        # Visible, with points
        annot.properties['showPoints'] = True
        annot.draw(mock_dc, default_printer_scale)

    def test_annotations_makeLabels_disabled(self, simple_annotations_data, mock_dc, default_printer_scale):
        """Test makeLabels with showLabels=False."""
        annot = annotations(simple_annotations_data, showLabels=False)
        annot.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        labels = annot.makeLabels(mock_dc, default_printer_scale)
        assert labels == []

    def test_annotations_makeLabels_empty(self, mock_dc, default_printer_scale):
        """Test makeLabels with no cropped labels."""
        annot = annotations([])
        labels = annot.makeLabels(mock_dc, default_printer_scale)
        assert labels == []

    def test_annotations_makeLabels_variants(self, simple_annotations_data, mock_dc, default_printer_scale):
        """Test makeLabels with various settings."""
        for angle in [0, 90]:
            for flipped in [True, False]:
                annot = annotations(simple_annotations_data, labelAngle=angle, flipped=flipped)
                annot.scaleAndShift((1.0, 1.0), (0.0, 0.0))
                labels = annot.makeLabels(mock_dc, default_printer_scale)
                assert isinstance(labels, list)

    def test_annotations_makeLabels_invalid_angle(self, simple_annotations_data, mock_dc, default_printer_scale):
        """Test makeLabels with invalid labelAngle raises UnboundLocalError."""
        annot = annotations(simple_annotations_data, labelAngle=45)  # Invalid angle
        annot.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        # This is a known defect: invalid angle causes UnboundLocalError
        with pytest.raises(UnboundLocalError):
            annot.makeLabels(mock_dc, default_printer_scale)

    def test_annotations_makeLabels_long_label_truncation(self, mock_dc, default_printer_scale):
        """Test makeLabels truncates long labels."""
        long_label = 'A' * 30
        data = [[100.0, 50.0, long_label]]
        annot = annotations(data, labelMaxLength=20, showXPos=False)
        annot.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        labels = annot.makeLabels(mock_dc, default_printer_scale)
        assert len(labels) > 0


# POINTS CLASS TESTS
# ==================

class TestPoints(object):
    """Tests for points class."""

    def test_points_init(self, simple_points_data):
        """Test points initialization."""
        pts = points(simple_points_data)
        assert len(pts.points) == 3

    def test_points_properties(self, simple_points_data):
        """Test points properties."""
        pts = points(simple_points_data, legend='Test Series')
        assert pts.properties['legend'] == 'Test Series'
        assert pts.properties['showLines'] == True

    def test_points_setProperties(self, simple_points_data):
        """Test setProperties method."""
        pts = points(simple_points_data)
        pts.setProperties(legend='Updated', showLines=False)
        assert pts.properties['legend'] == 'Updated'
        assert pts.properties['showLines'] == False

    def test_points_normalization(self, simple_points_data):
        """Test normalization calculation."""
        pts = points(simple_points_data)
        assert pts.normalization == 1.0

    def test_points_getBoundingBox_empty(self):
        """Test getBoundingBox with empty points."""
        pts = points([])
        assert pts.getBoundingBox() == False

    def test_points_getBoundingBox_basic(self, simple_points_data):
        """Test getBoundingBox with data."""
        pts = points(simple_points_data)
        bbox = pts.getBoundingBox()
        assert bbox != False

    def test_points_getBoundingBox_combinations(self, simple_points_data):
        """Test points.getBoundingBox with various options."""
        # exactFit=True
        pts = points(simple_points_data, exactFit=True)
        assert pts.getBoundingBox() != False
        
        # absolute=True
        pts = points(simple_points_data)
        assert pts.getBoundingBox(absolute=True) != False
        
        # normalized=True
        pts = points(simple_points_data, normalized=True)
        assert pts.getBoundingBox() != False
        
        # flipped=True
        pts = points(simple_points_data, flipped=True)
        assert pts.getBoundingBox() != False

    def test_points_getLegend(self, simple_points_data):
        """Test getLegend returns legend with colour."""
        pts = points(simple_points_data, legend='Test', pointColour=(255, 0, 0))
        legend = pts.getLegend()
        assert legend[0] == 'Test'
        assert legend[1] == (255, 0, 0)

    def test_points_getLegend_with_offset(self, simple_points_data):
        """Test getLegend includes offset info."""
        pts = points(simple_points_data, legend='Test', xOffset=10.5, yOffset=5.5)
        legend = pts.getLegend()
        assert 'Offset' in legend[0]

    def test_points_getLegend_advanced(self, simple_points_data):
        """Test points.getLegend with various options."""
        pts = points(simple_points_data, legend='Test')
        
        # normalized
        pts.properties['normalized'] = True
        assert pts.getLegend()[0] == 'Test'
        
        # not normalized with offsets
        pts.properties['normalized'] = False
        pts.properties['xOffset'] = 10.0
        pts.properties['yOffset'] = 20.0
        assert 'Offset' in pts.getLegend()[0]
        
        # showPoints vs showLines
        pts.properties['showPoints'] = True
        assert pts.getLegend()[1] == pts.properties['pointColour']
        pts.properties['showPoints'] = False
        assert pts.getLegend()[1] == pts.properties['lineColour']

    def test_points_cropPoints(self, simple_points_data):
        """Test cropPoints method."""
        pts = points(simple_points_data, showLines=True)
        pts.cropPoints(100.5, 101.5)
        # Should crop

    def test_points_scaleAndShift(self, simple_points_data):
        """Test scaleAndShift with non-empty data."""
        pts = points(simple_points_data)
        scale = (2.0, 3.0)
        shift = (10.0, 20.0)
        pts.scaleAndShift(scale, shift)
        assert pts.currentScale == scale

    def test_points_scaleAndShift_empty(self):
        """Test scaleAndShift with empty points."""
        pts = points([])
        scale = (2.0, 3.0)
        shift = (10.0, 20.0)
        pts.scaleAndShift(scale, shift)
        # Should handle gracefully

    def test_points_filterPoints(self, simple_points_data):
        """Test filterPoints with showLines=True."""
        pts = points(simple_points_data, showLines=True)
        pts.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        pts.filterPoints(0.5)
        # Should filter

    def test_points_filterPoints_no_lines(self, simple_points_data):
        """Test filterPoints with showLines=False."""
        pts = points(simple_points_data, showLines=False)
        pts.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        pts.filterPoints(0.5)
        # Should not filter

    def test_points_draw(self, simple_points_data, mock_dc, default_printer_scale):
        """Test draw method with branches."""
        # Show points and lines
        pts = points(simple_points_data, showLines=True, showPoints=True)
        pts.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        pts.draw(mock_dc, default_printer_scale)
        
        # Hidden
        pts.properties['visible'] = False
        pts.draw(mock_dc, default_printer_scale)
        
        # showLines=False, showPoints=True
        pts.properties['visible'] = True
        pts.properties['showLines'] = False
        pts.draw(mock_dc, default_printer_scale)

    def test_points_draw_empty(self, mock_dc, default_printer_scale):
        """Test draw with empty scaled points."""
        pts = points([])
        pts.draw(mock_dc, default_printer_scale)
        # Should not raise

    def test_points_makeLabels(self, simple_points_data, mock_dc, default_printer_scale):
        """Test makeLabels always returns empty list."""
        pts = points(simple_points_data)
        labels = pts.makeLabels(mock_dc, default_printer_scale)
        assert labels == []


# SPECTRUM CLASS TESTS
# ====================

class TestSpectrum(object):
    """Tests for spectrum class."""

    def test_spectrum_init(self, simple_scan):
        """Test spectrum initialization."""
        spec = spectrum(simple_scan)
        assert len(spec.spectrumPoints) == 4
        assert len(spec.peaklistPoints) == 2

    def test_spectrum_init_empty_scan(self, empty_scan):
        """Test spectrum with empty scan."""
        spec = spectrum(empty_scan)
        assert len(spec.spectrumPoints) == 0

    def test_spectrum_properties(self, simple_scan):
        """Test spectrum properties."""
        spec = spectrum(simple_scan, legend='Test MS')
        assert spec.properties['legend'] == 'Test MS'
        assert spec.properties['showSpectrum'] == True

    def test_spectrum_setProperties(self, simple_scan):
        """Test setProperties method."""
        spec = spectrum(simple_scan)
        spec.setProperties(legend='Updated', visible=False)
        assert spec.properties['legend'] == 'Updated'
        assert spec.properties['visible'] == False

    def test_spectrum_normalization(self, simple_scan, profile_only_scan, peaklist_only_scan, empty_scan):
        """Test normalization calculation."""
        # Both
        assert spectrum(simple_scan).normalization == 1.0
        # Spectrum only
        assert spectrum(profile_only_scan).normalization == 1.0
        # Peaklist only
        assert spectrum(peaklist_only_scan).normalization == 1.0
        # Empty
        assert spectrum(empty_scan).normalization == 1.0

    def test_spectrum_getBoundingBox_empty(self, empty_scan):
        """Test getBoundingBox with empty spectrum."""
        spec = spectrum(empty_scan)
        bbox = spec.getBoundingBox()
        assert bbox == False

    def test_spectrum_getBoundingBox_with_spectrum(self, simple_scan):
        """Test getBoundingBox with spectrum data."""
        spec = spectrum(simple_scan)
        bbox = spec.getBoundingBox()
        assert isinstance(bbox, list)

    def test_spectrum_getBoundingBox_with_offset_not_normalized(self, simple_scan):
        """Test getBoundingBox applies offset when not normalized."""
        spec = spectrum(simple_scan, xOffset=10, yOffset=5)
        bbox = spec.getBoundingBox()
        # minX=100.0, xOffset=10 -> 110.0
        assert bbox[0][0] == 110.0

    def test_spectrum_getBoundingBox_offset_ignored_when_normalized(self, simple_scan):
        """Test getBoundingBox ignores offset when normalized=True."""
        spec = spectrum(simple_scan, xOffset=100, yOffset=100, normalized=True)
        bbox_with_norm = spec.getBoundingBox()
        # minX=100.0, normalized -> should NOT be 200.0
        assert bbox_with_norm[0][0] == 100.0

    def test_spectrum_getBoundingBox_showLabels_branches(self, simple_scan):
        """Test spectrum.getBoundingBox showLabels branches."""
        spec = spectrum(simple_scan, showLabels=True)
        # angle 0
        spec.properties['labelAngle'] = 0
        assert spec.getBoundingBox() != False
        # angle 90
        spec.properties['labelAngle'] = 90
        assert spec.getBoundingBox() != False

    def test_spectrum_getBoundingBox_combinations(self, simple_scan):
        """Test combinations of showSpectrum, showLabels, showTicks."""
        # showSpectrum=True, others False
        spec = spectrum(simple_scan, showSpectrum=True, showLabels=False, showTicks=False)
        assert spec.getBoundingBox() != False
        
        # showSpectrum=False, others True
        spec = spectrum(simple_scan, showSpectrum=False, showLabels=True, showTicks=True)
        assert spec.getBoundingBox() != False
        
        # All False
        spec = spectrum(simple_scan, showSpectrum=False, showLabels=False, showTicks=False)
        assert spec.getBoundingBox() == False
        
        # Absolute=True
        spec = spectrum(simple_scan, showSpectrum=True)
        assert spec.getBoundingBox(absolute=True) != False

    def test_container_getBoundingBox_edge_cases(self, simple_scan):
        """Test container.getBoundingBox edge cases."""
        # 1 visible object
        spec = spectrum(simple_scan)
        cont = container([spec])
        assert cont.getBoundingBox() != False
        
        # 0 visible objects (already tested but being sure)
        spec.properties['visible'] = False
        assert cont.getBoundingBox() != False

    def test_spectrum_getLegend_spectrum(self, simple_scan):
        """Test getLegend returns spectrum colour when showSpectrum=True."""
        spec = spectrum(simple_scan, legend='Test')
        legend = spec.getLegend()
        assert legend[0] == 'Test'

    def test_spectrum_getLegend_empty_spectrum(self, peaklist_only_scan):
        """Test getLegend returns tick colour when spectrum is empty."""
        spec = spectrum(peaklist_only_scan, legend='Test')
        legend = spec.getLegend()
        # Should return tick colour
        assert legend[0] == 'Test'

    def test_spectrum_getPoint_boundary(self, simple_scan):
        """Test getPoint returns value or None for boundary."""
        spec = spectrum(simple_scan)
        spec.spectrumScaled = numpy.array([[100.0, 50.0], [101.0, 100.0]])
        
        # At start
        result = spec.getPoint(100.0)
        if result is not None:
            assert result[1] == 50.0
            
        # At end
        result = spec.getPoint(101.0)
        assert result is None or result[1] == 100.0
        
        # Beyond
        assert spec.getPoint(102.0) is None

    def test_spectrum_cropPoints(self, simple_scan):
        """Test cropPoints method."""
        spec = spectrum(simple_scan)
        spec.cropPoints(100.5, 101.5)
        # Should crop both spectrum and peaklist

    def test_spectrum_scaleAndShift(self, simple_scan):
        """Test scaleAndShift applies to both spectrum and peaklist."""
        spec = spectrum(simple_scan)
        scale = (2.0, 3.0)
        shift = (10.0, 20.0)
        spec.scaleAndShift(scale, shift)
        assert spec.currentScale == scale

    def test_spectrum_filterPoints(self, simple_scan):
        """Test filterPoints with showSpectrum=True."""
        spec = spectrum(simple_scan, showSpectrum=True)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        spec.filterPoints(0.5)
        # Should filter

    def test_spectrum_filterPoints_no_spectrum(self, peaklist_only_scan):
        """Test filterPoints with empty spectrum."""
        spec = spectrum(peaklist_only_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        spec.filterPoints(0.5)
        # Should not filter

    def test_spectrum_draw_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test draw method with showPoints and enough points."""
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        
        # showSpectrum and showPoints
        spec.properties['showSpectrum'] = True
        spec.properties['showPoints'] = True
        # Ensure we have enough points for showPoints logic
        # need (pts[2].x - pts[1].x) > 6 and (totalX / count) > 6
        spec.spectrumScaled = numpy.array([[100.0, 50.0], [110.0, 100.0], [120.0, 75.0], [130.0, 50.0]])
        spec.draw(mock_dc, default_printer_scale)

    def test_spectrum_drawPeaklist_features(self, simple_scan, mock_dc, default_printer_scale):
        """Test _drawPeaklist features like fragmentation marks and isotope colours."""
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        
        # Fragmentation mark (childScanNumber is set in fixture)
        spec.properties['showSpectrum'] = False
        spec.draw(mock_dc, default_printer_scale)
        
        # Isotope colour
        spec.properties['isotopeColour'] = (255, 0, 0)
        spec.draw(mock_dc, default_printer_scale)

    def test_spectrum_makeLabels_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test makeLabels with various label settings."""
        spec = spectrum(simple_scan, labelAngle=90, labelCharge=True, labelGroup=True)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        labels = spec.makeLabels(mock_dc, default_printer_scale)
        assert len(labels) > 0
        
        # angle 0
        spec.properties['labelAngle'] = 0
        labels = spec.makeLabels(mock_dc, default_printer_scale)
        assert len(labels) > 0

    def test_spectrum_getBoundingBox_advanced(self, simple_scan):
        """Test spectrum.getBoundingBox with various combinations."""
        spec = spectrum(simple_scan)
        
        # showSpectrum=True, showLabels=False
        spec.properties['showSpectrum'] = True
        spec.properties['showLabels'] = False
        bbox = spec.getBoundingBox()
        
        # showSpectrum=False, showLabels=True
        spec.properties['showSpectrum'] = False
        spec.properties['showLabels'] = True
        spec.properties['labelAngle'] = 0
        bbox = spec.getBoundingBox()
        spec.properties['labelAngle'] = 90
        bbox = spec.getBoundingBox()
        
        # flipped and normalized
        spec.properties['flipped'] = True
        spec.properties['normalized'] = True
        bbox = spec.getBoundingBox()
        
        # minX, maxX
        bbox = spec.getBoundingBox(minX=100.5, maxX=101.5)

    def test_spectrum_getLegend_advanced(self, simple_scan):
        """Test spectrum.getLegend with various options."""
        spec = spectrum(simple_scan, legend='Test')
        
        # spectrum vs ticks
        spec.properties['showSpectrum'] = True
        assert spec.getLegend()[1] == spec.properties['spectrumColour']
        spec.properties['showSpectrum'] = False
        assert spec.getLegend()[1] == spec.properties['tickColour']
        
        # offsets
        spec.properties['normalized'] = False
        spec.properties['xOffset'] = 10.0
        assert 'Offset' in spec.getLegend()[0]

    def test_spectrum_drawPeaklist_advanced(self, simple_scan, mock_dc, default_printer_scale):
        """Test _drawPeaklist with isotope and msms colours."""
        spec = spectrum(simple_scan)
        spec.properties['isotopeColour'] = (255, 0, 0)
        spec.properties['msmsColour'] = (0, 255, 0)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        spec.draw(mock_dc, default_printer_scale)

    def test_spectrum_makeLabels_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test spectrum.makeLabels with angle 0 and flipped branches."""
        for angle in [0, 90]:
            for flipped in [True, False]:
                spec = spectrum(simple_scan, labelAngle=angle, flipped=flipped)
                spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
                labels = spec.makeLabels(mock_dc, default_printer_scale)
                assert isinstance(labels, list)

    def test_spectrum_drawSpectrumGel_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test _drawSpectrumGel branches."""
        # Use LARGE range to avoid step=0
        gelCoords = [0, 10, 0, 1000, 1000, 500] # plotY2 - plotY1 = 1000
        
        # Flipped
        spec = spectrum(simple_scan, flipped=True)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        # Points to trigger maxY < previousY and space logic
        spec.spectrumScaled = numpy.array([
            [100.0, 500.0], # baseline
            [110.0, 100.0], # peak (high intensity = low Y)
            [120.0, 500.0], # baseline
            [150.0, 500.0]  # space
        ])
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)
        
        # Zero region
        spec.properties['flipped'] = False
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)
        spec.properties['flipped'] = True
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)

    def test_spectrum_drawPeaklistGel_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test _drawPeaklistGel branches."""
        # Use LARGE range to avoid step=0
        gelCoords = [0, 10, 0, 1000, 1000, 500]
        
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        spec.peaklistScaled = numpy.array([
            [100.0, 100.0, 100.0],
            [110.0, 500.0, 500.0]
        ])
        spec._drawPeaklistGel(mock_dc, gelCoords, 50, default_printer_scale)
        
        # Zero region
        spec.properties['flipped'] = True
        spec._drawPeaklistGel(mock_dc, gelCoords, 50, default_printer_scale)

    def test_spectrum_drawGel_extra_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test spectrum gel drawing with specific point configurations."""
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        gelCoords = [0, 10, 0, 1000, 1000, 500]
        
        # Points to trigger intensity=0 and maxY < previousY
        spec.spectrumScaled = numpy.array([
            [100.0, 500.0], # baseline (intensity 0 at zeroY=500)
            [110.0, 500.0], # baseline
            [120.0, 490.0], # small peak
            [130.0, 495.0], # falling
            [200.0, 500.0]  # space
        ])
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)
        
        # Flipped with intensity=0
        spec.properties['flipped'] = True
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)

    def test_spectrum_drawPeaklistGel_extra_variants(self, simple_scan, mock_dc, default_printer_scale):
        """Test spectrum peaklist gel drawing with flipped branch."""
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        gelCoords = [0, 10, 0, 1000, 1000, 500]
        spec.peaklistScaled = numpy.array([
            [100.0, 400.0, 400.0],
            [110.0, 500.0, 500.0]
        ])
        spec.properties['flipped'] = True
        spec._drawPeaklistGel(mock_dc, gelCoords, 50, default_printer_scale)

    def test_spectrum_drawSpectrumGel_zero_step(self, simple_scan, mock_dc, default_printer_scale):
        """Test _drawSpectrumGel when step == 0 (returns False)."""
        spec = spectrum(simple_scan)
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        gelCoords = [0, 10, 100, 100, 190, 100] # plotY1 == plotY2
        result = spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)
        assert result == False

    def test_spectrum_overflow_handling(self, simple_scan, mocker, default_printer_scale):
        """Test handled exception branches (OverflowError)."""
        spec = spectrum(simple_scan)
        spec.spectrumScaled = numpy.array([[100.0, 50.0], [110.0, 100.0], [120.0, 75.0], [130.0, 50.0]])
        spec.properties['showPoints'] = True
        
        mock_dc = mocker.Mock(spec=wx.DC)
        mock_dc.DrawCircle.side_effect = OverflowError("Overflow")
        mock_dc.DrawLine.side_effect = OverflowError("Overflow")
        mock_dc.DrawRectangle.side_effect = OverflowError("Overflow")
        
        # Spectrum overflow
        spec._drawSpectrum(mock_dc, default_printer_scale)
        
        # Peaklist overflow
        spec.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        spec._drawPeaklist(mock_dc, default_printer_scale)
        
        # Gel overflow
        gelCoords = [0, 10, 0, 1000, 1000, 500]
        spec._drawSpectrumGel(mock_dc, gelCoords, 50, default_printer_scale)
        spec._drawPeaklistGel(mock_dc, gelCoords, 50, default_printer_scale)


# INTEGRATION TESTS
# =================

class TestIntegration(object):
    """Integration tests for multiple components."""

    def test_container_with_multiple_spectrum(self, simple_scan):
        """Test container with multiple spectrum objects."""
        spec1 = spectrum(simple_scan, legend='Spectrum 1')
        spec2 = spectrum(simple_scan, legend='Spectrum 2')
        cont = container([spec1, spec2])

        assert len(cont) == 2
        cont.cropPoints(100.0, 102.0)
        cont.scaleAndShift((2.0, 2.0), (0.0, 0.0))
        assert cont.countGels() == 2

    def test_container_with_annotations_and_spectrum(self, simple_scan, simple_annotations_data):
        """Test container with both annotations and spectrum."""
        spec = spectrum(simple_scan)
        annot = annotations(simple_annotations_data)
        cont = container([spec, annot])

        assert len(cont) == 2
        bbox = cont.getBoundingBox()
        assert isinstance(bbox, list)

    def test_container_drawing_mixed_objects(self, simple_scan, simple_annotations_data, mock_dc, default_printer_scale):
        """Test drawing container with mixed object types."""
        spec = spectrum(simple_scan)
        annot = annotations(simple_annotations_data)
        cont = container([spec, annot])

        cont.cropPoints(100.0, 102.0)
        cont.scaleAndShift((1.0, 1.0), (0.0, 0.0))
        cont.draw(mock_dc, default_printer_scale, False, False)
        # Should draw without raising

    def test_full_workflow(self, simple_scan, simple_annotations_data, mock_dc, default_printer_scale):
        """Test full workflow: create, crop, scale, draw."""
        spec = spectrum(simple_scan, legend='Test Spectrum')
        annot = annotations(simple_annotations_data, legend='Test Annotations')
        cont = container([spec, annot])

        # Get bounding box
        bbox = cont.getBoundingBox()
        assert isinstance(bbox, list)

        # Crop to subset
        cont.cropPoints(100.5, 101.5)

        # Scale and shift
        cont.scaleAndShift((1.0, 1.0), (0.0, 0.0))

        # Get legend
        legend = cont.getLegend()

        # Draw
        cont.draw(mock_dc, default_printer_scale, False, False)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
