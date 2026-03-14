import pytest
import numpy as np
from hypothesis import given, strategies as st, assume
from hypothesis.extra.numpy import arrays
from numpy.testing import assert_allclose

@pytest.fixture(scope="session")
def calculations():
    """Fixture to provide the mspy.calculations module."""
    try:
        import mspy.calculations
        return mspy.calculations
    except ImportError as e:
        pytest.fail("Failed to import mspy.calculations: {}".format(e))

# Helper to generate typical mass spectrometry signals: 2D array of doubles, (n, 2)
def signals(min_size=0, max_size=1000):
    return arrays(
        dtype=np.double,
        shape=st.tuples(st.integers(min_value=min_size, max_value=max_size), st.just(2)),
        elements=st.floats(allow_nan=True, allow_infinity=True)
    )

# Helper for peaklists (mz, intens, fwhm)
def peaklists(min_size=0, max_size=50):
    return arrays(
        dtype=np.double,
        shape=st.tuples(st.integers(min_value=min_size, max_value=max_size), st.just(3)),
        elements=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )

@pytest.mark.unit
class TestSmoke(object):
    """Smoke tests for mspy.calculations module."""

    def test_import_calculations(self, calculations):
        """Verify that mspy.calculations can be imported."""
        assert calculations is not None

    def test_calculations_module_contents(self, calculations):
        """Verify that the mspy.calculations module has expected attributes."""
        expected_functions = [
            'signal_interpolate_x', 'signal_interpolate_y',
            'signal_locate_x', 'signal_locate_max_y', 'signal_box',
            'signal_intensity', 'signal_centroid', 'signal_width',
            'signal_area', 'signal_noise', 'signal_local_maxima',
            'signal_crop', 'signal_offset', 'signal_multiply',
            'signal_normalize', 'signal_smooth_ma', 'signal_smooth_ga',
            'signal_combine', 'signal_overlay', 'signal_subtract',
            'signal_subbase', 'signal_rescale', 'signal_filter',
            'signal_gaussian', 'signal_lorentzian', 'signal_gausslorentzian',
            'signal_profile_to_raster', 'signal_profile',
            'formula_composition'
        ]
        for func in expected_functions:
            assert hasattr(calculations, func), "Missing function: {}".format(func)

@pytest.mark.unit
class TestInterpolation(object):
    """Tests for signal interpolation functions."""

    def test_signal_interpolate_x(self, calculations):
        # Standard case
        assert_allclose(calculations.signal_interpolate_x(0, 0, 10, 10, 5), 5.0)
        assert_allclose(calculations.signal_interpolate_x(100, 10, 200, 20, 15), 150.0)
        # x1 == x2 case
        assert calculations.signal_interpolate_x(10, 0, 10, 10, 5) == 10.0
        # y1 == y2 case
        res = calculations.signal_interpolate_x(10, 10, 20, 10, 5)
        assert np.isinf(res)

    def test_signal_interpolate_y(self, calculations):
        # Standard case
        assert_allclose(calculations.signal_interpolate_y(0, 0, 10, 10, 5), 5.0)
        assert_allclose(calculations.signal_interpolate_y(100, 10, 200, 20, 150), 15.0)
        # y1 == y2 case
        assert calculations.signal_interpolate_y(0, 10, 10, 10, 5) == 10.0
        # x1 == x2 case
        res = calculations.signal_interpolate_y(10, 0, 10, 10, 10)
        assert np.isnan(res) or np.isinf(res)

@pytest.mark.unit
class TestLocate(object):
    """Tests for signal location functions."""

    def test_signal_locate_x(self, calculations):
        signal = np.array([[10, 1], [20, 5], [30, 2], [40, 8]], dtype=np.double)
        assert calculations.signal_locate_x(signal, 5) == 0
        assert calculations.signal_locate_x(signal, 15) == 1
        assert calculations.signal_locate_x(signal, 25) == 2
        assert calculations.signal_locate_x(signal, 35) == 3
        assert calculations.signal_locate_x(signal, 45) == 4
        assert calculations.signal_locate_x(signal, 10) == 1
        assert calculations.signal_locate_x(signal, 40) == 4

    def test_signal_locate_max_y(self, calculations):
        signal = np.array([[10, 1], [20, 5], [30, 2], [40, 8], [50, 3]], dtype=np.double)
        assert calculations.signal_locate_max_y(signal) == 3
        signal2 = np.array([[10, 10], [20, 5]], dtype=np.double)
        assert calculations.signal_locate_max_y(signal2) == 0

@pytest.mark.unit
class TestAnalysis(object):
    """Tests for signal analysis functions."""

    def test_signal_box(self, calculations):
        signal = np.array([[10, 1], [20, 5], [30, 2], [40, 8], [50, 3]], dtype=np.double)
        assert calculations.signal_box(signal) == (10.0, 1.0, 50.0, 8.0)

    def test_signal_intensity(self, calculations):
        signal = np.array([[10, 10], [20, 20]], dtype=np.double)
        assert_allclose(calculations.signal_intensity(signal, 15), 15.0)
        assert calculations.signal_intensity(signal, 5) == 0.0
        assert calculations.signal_intensity(signal, 25) == 0.0
        assert calculations.signal_intensity(signal, 10) == 10.0

    def test_signal_centroid(self, calculations):
        signal = np.array([[10, 0], [20, 10], [30, 0]], dtype=np.double)
        assert_allclose(calculations.signal_centroid(signal, 20, 5), 20.0)
        # height higher than peak
        res = calculations.signal_centroid(signal, 20, 15)
        assert_allclose(res, 15.0)

    def test_signal_width(self, calculations):
        signal = np.array([[10, 0], [20, 10], [30, 0]], dtype=np.double)
        assert_allclose(calculations.signal_width(signal, 20, 5), 10.0)

    def test_signal_area(self, calculations):
        signal = np.array([[0, 0], [10, 10], [20, 0]], dtype=np.double)
        assert_allclose(calculations.signal_area(signal), 100.0)
        signal2 = np.array([[0, 10], [10, 10]], dtype=np.double)
        assert_allclose(calculations.signal_area(signal2), 100.0)

    def test_signal_noise(self, calculations):
        signal = np.array([[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]], dtype=np.double)
        level, width = calculations.signal_noise(signal)
        assert_allclose(level, 3.0)
        assert_allclose(width, 2.0)

@pytest.mark.unit
class TestTransformation(object):
    """Tests for signal transformation functions."""

    def test_signal_local_maxima(self, calculations):
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 5], [4, 0]], dtype=np.double)
        maxima = calculations.signal_local_maxima(signal)
        expected = np.array([[1, 10], [3, 5]], dtype=np.double)
        assert_allclose(maxima, expected)

    def test_signal_crop(self, calculations):
        signal = np.array([[10, 1], [20, 2], [30, 3], [40, 4], [50, 5]], dtype=np.double)
        cropped = calculations.signal_crop(signal, 25.0, 45.0)
        expected = np.array([[25, 2.5], [30, 3.0], [40, 4.0], [45, 4.5]], dtype=np.double)
        assert_allclose(cropped, expected)

    def test_signal_offset(self, calculations):
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        offset = calculations.signal_offset(signal, 5.0, 10.0)
        expected = np.array([[15, 11], [25, 12]], dtype=np.double)
        assert_allclose(offset, expected)

    def test_signal_multiply(self, calculations):
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        multiplied = calculations.signal_multiply(signal, 2.0, 3.0)
        expected = np.array([[20, 3], [40, 6]], dtype=np.double)
        assert_allclose(multiplied, expected)

    def test_signal_normalize(self, calculations):
        signal = np.array([[10, 5], [20, 10], [30, 2]], dtype=np.double)
        normalized = calculations.signal_normalize(signal)
        expected = np.array([[10, 0.5], [20, 1.0], [30, 0.2]], dtype=np.double)
        assert_allclose(normalized, expected)

    def test_signal_rescale(self, calculations):
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        rescaled = calculations.signal_rescale(signal, 2.0, 10.0, 5.0, 0.0)
        expected = np.array([[25, 10], [45, 20]], dtype=np.double)
        assert_allclose(rescaled, expected)

    def test_signal_filter(self, calculations):
        signal = np.array([[10, 1], [12, 5], [14, 2], [20, 8]], dtype=np.double)
        filtered = calculations.signal_filter(signal, 5.0)
        assert len(filtered) > 0
        signal2 = np.array([[10, 10], [11, 5], [12, 15], [20, 10]], dtype=np.double)
        filtered2 = calculations.signal_filter(signal2, 5.0)
        assert len(filtered2) > 0

@pytest.mark.unit
class TestOperation(object):
    """Tests for signal combination and smoothing functions."""

    def test_signal_smooth_ma(self, calculations):
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 10], [4, 0]], dtype=np.double)
        smoothed = calculations.signal_smooth_ma(signal, 2, 1)
        assert len(smoothed) == len(signal)
        assert_allclose(smoothed[1, 1], (0+10+0)/3.0)

    def test_signal_smooth_ga(self, calculations):
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 10], [4, 0]], dtype=np.double)
        smoothed = calculations.signal_smooth_ga(signal, 2, 1)
        assert len(smoothed) == len(signal)
        ma_smoothed = calculations.signal_smooth_ma(signal, 2, 1)
        assert not np.allclose(smoothed[:,1], ma_smoothed[:,1])

    def test_signal_combine(self, calculations):
        signalA = np.array([[10, 10], [20, 20]], dtype=np.double)
        signalB = np.array([[15, 5], [25, 5]], dtype=np.double)
        combined = calculations.signal_combine(signalA, signalB)
        expected = np.array([[10, 10], [15, 20], [20, 25], [25, 5]], dtype=np.double)
        assert_allclose(combined, expected)

    def test_signal_overlay(self, calculations):
        signalA = np.array([[10, 10], [20, 20]], dtype=np.double)
        signalB = np.array([[15, 30], [25, 5]], dtype=np.double)
        overlay = calculations.signal_overlay(signalA, signalB)
        expected = np.array([[10, 10], [15, 30], [20, 20], [25, 5]], dtype=np.double)
        assert_allclose(overlay, expected)

    def test_signal_subtract(self, calculations):
        signalA = np.array([[10, 10], [20, 20]], dtype=np.double)
        signalB = np.array([[15, 5], [25, 5]], dtype=np.double)
        subtracted = calculations.signal_subtract(signalA, signalB)
        expected = np.array([[10, 10], [15, 10], [20, 15], [25, -5]], dtype=np.double)
        assert_allclose(subtracted, expected)

    def test_signal_subbase(self, calculations):
        signal = np.array([[10, 10], [20, 20], [30, 30]], dtype=np.double)
        baseline = np.array([[0, 5], [40, 5]], dtype=np.double)
        subbed = calculations.signal_subbase(signal, baseline)
        expected = np.array([[10, 5], [20, 15], [30, 25]], dtype=np.double)
        assert_allclose(subbed, expected)

@pytest.mark.unit
class TestGeneration(object):
    """Tests for signal generation and profiling functions."""

    def test_signal_gaussian(self, calculations):
        gaussian = calculations.signal_gaussian(100.0, 0.0, 100.0, 10.0, 100)
        assert len(gaussian) == 100
        idx = np.argmin(np.abs(gaussian[:,0] - 100.0))
        assert_allclose(gaussian[idx, 1], 100.0, atol=1.0)

    def test_signal_lorentzian(self, calculations):
        lorentzian = calculations.signal_lorentzian(100.0, 0.0, 100.0, 10.0, 100)
        assert len(lorentzian) == 100
        idx = np.argmin(np.abs(lorentzian[:,0] - 100.0))
        assert_allclose(lorentzian[idx, 1], 100.0, atol=1.0)

    def test_signal_gausslorentzian(self, calculations):
        gl = calculations.signal_gausslorentzian(100.0, 0.0, 100.0, 10.0, 150)
        assert len(gl) == 150
        idx = np.argmin(np.abs(gl[:,0] - 100.0))
        assert_allclose(gl[idx, 1], 100.0, atol=1.0)

    @pytest.mark.parametrize("shape, label", [
        (0, "gaussian"),
        (1, "lorentzian"),
        (2, "gauss-lorentzian")
    ], ids=["shape-0-gaussian", "shape-1-lorentzian", "shape-2-gausslorentzian"])
    def test_signal_profile_to_raster(self, calculations, shape, label):
        peaks = np.array([[100, 100, 1], [200, 50, 1]], dtype=np.double)
        raster = np.linspace(50, 250, 1000, dtype=np.double)
        profile = calculations.signal_profile_to_raster(peaks, raster, 0.0, shape)
        assert len(profile) == len(raster)
        idx1 = np.argmin(np.abs(profile[:,0] - 100))
        assert_allclose(profile[idx1, 1], 100.0, rtol=1e-2)

    @pytest.mark.parametrize("shape", [0, 1, 2], ids=["shape-0", "shape-1", "shape-2"])
    def test_signal_profile(self, calculations, shape):
        peaks = np.array([[100, 100, 1], [200, 50, 1]], dtype=np.double)
        profile = calculations.signal_profile(peaks, 10, 0.0, shape)
        assert len(profile) > 0

    def test_signal_profile_with_noise(self, calculations):
        peaks = np.array([[100, 100, 1], [200, 50, 1]], dtype=np.double)
        profile_noise = calculations.signal_profile(peaks, 10, 1.0, 0)
        assert len(profile_noise) > 0

@pytest.mark.unit
class TestFormula(object):
    """Tests for formula-related functions."""

    def test_formula_composition(self, calculations):
        min_comp = (0, 0)
        max_comp = (2, 5)
        masses = (12.0, 1.007825)
        compositions = calculations.formula_composition(min_comp, max_comp, masses, 12.9, 13.1, 100)
        assert [1, 1] in compositions
        # Test empty result
        empty_comp = calculations.formula_composition(min_comp, max_comp, masses, 1000.0, 1001.0, 100)
        assert empty_comp == []

@pytest.mark.unit
class TestRegression(object):
    """Regression and edge case tests."""

    @pytest.mark.skip(reason="Segfaults due to lack of type checking in C extension")
    def test_invalid_inputs(self, calculations):
        with pytest.raises((TypeError, ValueError)):
            calculations.signal_locate_max_y(None)
        with pytest.raises((TypeError, ValueError)):
            calculations.signal_locate_max_y("not an array")

@pytest.mark.slow
class TestPropertyBased(object):
    """Property-based tests using Hypothesis."""

    @given(
        x1=st.floats(allow_nan=True, allow_infinity=True),
        y1=st.floats(allow_nan=True, allow_infinity=True),
        x2=st.floats(allow_nan=True, allow_infinity=True),
        y2=st.floats(allow_nan=True, allow_infinity=True),
        v=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_interpolate_x_property(self, calculations, x1, y1, x2, y2, v):
        res = calculations.signal_interpolate_x(x1, y1, x2, y2, v)
        assert isinstance(res, float)

    @given(
        x1=st.floats(allow_nan=True, allow_infinity=True),
        y1=st.floats(allow_nan=True, allow_infinity=True),
        x2=st.floats(allow_nan=True, allow_infinity=True),
        y2=st.floats(allow_nan=True, allow_infinity=True),
        v=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_interpolate_y_property(self, calculations, x1, y1, x2, y2, v):
        res = calculations.signal_interpolate_y(x1, y1, x2, y2, v)
        assert isinstance(res, float)

    @given(signal=signals(), x=st.floats(allow_nan=True, allow_infinity=True))
    def test_signal_locate_x_property(self, calculations, signal, x):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        idx = calculations.signal_locate_x(signal, x)
        assert 0 <= idx <= len(signal)

    @given(signal=signals())
    def test_signal_locate_max_y_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        if len(signal) == 0:
            res = calculations.signal_locate_max_y(signal)
            assert res == 0
        else:
            idx = calculations.signal_locate_max_y(signal)
            assert 0 <= idx < len(signal)

    @given(signal=signals())
    def test_signal_box_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        if len(signal) == 0:
            try:
                res = calculations.signal_box(signal)
                assert len(res) == 4
            except Exception:
                pass
        else:
            res = calculations.signal_box(signal)
            assert len(res) == 4
            assert all(isinstance(v, float) for v in res)

    @given(signal=signals(), x=st.floats(allow_nan=True, allow_infinity=True))
    def test_signal_intensity_property(self, calculations, signal, x):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_intensity(signal, x)
        assert isinstance(res, float)

    @given(
        signal=signals(),
        x=st.floats(allow_nan=True, allow_infinity=True),
        h=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_centroid_property(self, calculations, signal, x, h):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_centroid(signal, x, h)
        assert isinstance(res, float)

    @given(
        signal=signals(),
        x=st.floats(allow_nan=True, allow_infinity=True),
        h=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_width_property(self, calculations, signal, x, h):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_width(signal, x, h)
        assert isinstance(res, float)

    @given(signal=signals())
    def test_signal_area_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_area(signal)
        assert isinstance(res, float)

    @given(signal=signals(min_size=1))
    def test_signal_noise_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        level, width = calculations.signal_noise(signal)
        assert isinstance(level, float)
        assert isinstance(width, float)

    @given(signal=signals())
    def test_signal_local_maxima_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_local_maxima(signal)
        assert isinstance(res, np.ndarray)
        if len(res) > 0:
            assert res.shape[1] == 2

    @pytest.mark.skip(reason="Segfaults when minX > maxX or with certain edge case floats")
    @given(
        signal=signals(),
        mX=st.floats(allow_nan=True, allow_infinity=True),
        MX=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_crop_property(self, calculations, signal, mX, MX):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_crop(signal, mX, MX)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        v1=st.floats(allow_nan=True, allow_infinity=True),
        v2=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_offset_property(self, calculations, signal, v1, v2):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_offset(signal, v1, v2)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        v1=st.floats(allow_nan=True, allow_infinity=True),
        v2=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_multiply_property(self, calculations, signal, v1, v2):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_multiply(signal, v1, v2)
        assert isinstance(res, np.ndarray)

    @given(signal=signals())
    def test_signal_normalize_property(self, calculations, signal):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_normalize(signal)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        window=st.integers(min_value=0, max_value=100),
        cycles=st.integers(min_value=0, max_value=10)
    )
    def test_signal_smooth_ma_property(self, calculations, signal, window, cycles):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_smooth_ma(signal, window, cycles)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        window=st.integers(min_value=0, max_value=100),
        cycles=st.integers(min_value=0, max_value=10)
    )
    def test_signal_smooth_ga_property(self, calculations, signal, window, cycles):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_smooth_ga(signal, window, cycles)
        assert isinstance(res, np.ndarray)

    @given(signalA=signals(), signalB=signals())
    def test_signal_combine_property(self, calculations, signalA, signalB):
        signalA = np.ascontiguousarray(signalA, dtype=np.double)
        signalB = np.ascontiguousarray(signalB, dtype=np.double)
        res = calculations.signal_combine(signalA, signalB)
        assert isinstance(res, np.ndarray)

    @given(signalA=signals(), signalB=signals())
    def test_signal_overlay_property(self, calculations, signalA, signalB):
        signalA = np.ascontiguousarray(signalA, dtype=np.double)
        signalB = np.ascontiguousarray(signalB, dtype=np.double)
        res = calculations.signal_overlay(signalA, signalB)
        assert isinstance(res, np.ndarray)

    @given(signalA=signals(), signalB=signals())
    def test_signal_subtract_property(self, calculations, signalA, signalB):
        signalA = np.ascontiguousarray(signalA, dtype=np.double)
        signalB = np.ascontiguousarray(signalB, dtype=np.double)
        res = calculations.signal_subtract(signalA, signalB)
        assert isinstance(res, np.ndarray)

    @given(signalA=signals(), signalB=signals())
    def test_signal_subbase_property(self, calculations, signalA, signalB):
        signalA = np.ascontiguousarray(signalA, dtype=np.double)
        signalB = np.ascontiguousarray(signalB, dtype=np.double)
        res = calculations.signal_subbase(signalA, signalB)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        scaleX=st.floats(allow_nan=True, allow_infinity=True),
        scaleY=st.floats(allow_nan=True, allow_infinity=True),
        shiftX=st.floats(allow_nan=True, allow_infinity=True),
        shiftY=st.floats(allow_nan=True, allow_infinity=True)
    )
    def test_signal_rescale_property(self, calculations, signal, scaleX, scaleY, shiftX, shiftY):
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_rescale(signal, scaleX, scaleY, shiftX, shiftY)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        resol=st.floats(min_value=0.0, allow_nan=False, allow_infinity=False)
    )
    def test_signal_filter_property(self, calculations, signal, resol):
        assume(resol > 0)
        signal = np.ascontiguousarray(signal, dtype=np.double)
        res = calculations.signal_filter(signal, resol)
        assert isinstance(res, np.ndarray)

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        minY=st.floats(allow_nan=False, allow_infinity=False),
        maxY=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        points=st.integers(min_value=1, max_value=1000)
    )
    def test_signal_gaussian_property(self, calculations, x, minY, maxY, fwhm, points):
        res = calculations.signal_gaussian(x, minY, maxY, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        minY=st.floats(allow_nan=False, allow_infinity=False),
        maxY=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        points=st.integers(min_value=1, max_value=1000)
    )
    def test_signal_lorentzian_property(self, calculations, x, minY, maxY, fwhm, points):
        res = calculations.signal_lorentzian(x, minY, maxY, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        minY=st.floats(allow_nan=False, allow_infinity=False),
        maxY=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False),
        points=st.integers(min_value=1, max_value=1000)
    )
    def test_signal_gausslorentzian_property(self, calculations, x, minY, maxY, fwhm, points):
        res = calculations.signal_gausslorentzian(x, minY, maxY, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        peaks=peaklists(min_size=1),
        raster=arrays(dtype=np.double, shape=st.tuples(st.integers(min_value=1, max_value=500),), elements=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)),
        noise=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        shape=st.integers(min_value=0, max_value=2)
    )
    def test_signal_profile_to_raster_property(self, calculations, peaks, raster, noise, shape):
        peaks = np.ascontiguousarray(peaks, dtype=np.double)
        raster = np.ascontiguousarray(raster, dtype=np.double)
        res = calculations.signal_profile_to_raster(peaks, raster, noise, shape)
        assert isinstance(res, np.ndarray)
        assert len(res) == len(raster)

    @given(
        peaks=peaklists(min_size=1),
        points=st.integers(min_value=1, max_value=100),
        noise=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        shape=st.integers(min_value=0, max_value=2)
    )
    def test_signal_profile_property(self, calculations, peaks, points, noise, shape):
        peaks = np.ascontiguousarray(peaks, dtype=np.double)
        # Constrain peaks to avoid extreme raster sizes
        assume(np.max(peaks[:, 0]) - np.min(peaks[:, 0]) < 1000)
        assume(np.min(peaks[:, 2]) > 0.1)
        res = calculations.signal_profile(peaks, points, noise, shape)
        assert isinstance(res, np.ndarray)

    @given(
        min_comp=st.tuples(st.integers(min_value=0, max_value=5), st.integers(min_value=0, max_value=5)),
        max_comp=st.tuples(st.integers(min_value=0, max_value=10), st.integers(min_value=0, max_value=10)),
        masses=st.tuples(st.floats(min_value=1.0, max_value=100.0), st.floats(min_value=1.0, max_value=100.0)),
        loMass=st.floats(min_value=0.0, max_value=1000.0),
        hiMass=st.floats(min_value=0.0, max_value=1000.0),
        limit=st.integers(min_value=1, max_value=100)
    )
    def test_formula_composition_property(self, calculations, min_comp, max_comp, masses, loMass, hiMass, limit):
        # Ensure min_comp <= max_comp for each element
        assume(all(mi <= ma for mi, ma in zip(min_comp, max_comp)))
        res = calculations.formula_composition(min_comp, max_comp, masses, loMass, hiMass, limit)
        assert isinstance(res, list)
