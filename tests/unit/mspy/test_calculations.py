import numpy as np
import numpy.testing as npt
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from mmass.mspy import calculations


def signals(min_size: int = 0, max_size: int = 1000) -> st.SearchStrategy[np.ndarray]:
    """Strategy to generate typical mass spectrometry signals: (n, 2) array of doubles."""
    return arrays(
        dtype=np.double,
        shape=st.tuples(
            st.integers(min_value=min_size, max_value=max_size), st.just(2)
        ),
        elements=st.floats(allow_nan=True, allow_infinity=True),
    )


def peaklists(min_size: int = 0, max_size: int = 50) -> st.SearchStrategy[np.ndarray]:
    """Strategy for peaklists: (n, 3) array of doubles (mz, intens, fwhm)."""
    return arrays(
        dtype=np.double,
        shape=st.tuples(
            st.integers(min_value=min_size, max_value=max_size), st.just(3)
        ),
        elements=st.floats(
            min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False
        ),
    )


class TestMedian:
    """Tests for signal_median function."""

    @pytest.mark.parametrize(
        ("arr", "expected"),
        [
            ([1, 2, 3, 4, 5], 3.0),
            ([1, 2, 3, 4], 2.5),
            ([], 0.0),
        ],
        ids=["odd_length", "even_length", "empty"],
    )
    def test_signal_median(self, arr, expected):
        """Test median calculation on numeric arrays."""
        # Arrange
        np_arr = np.array(arr, dtype=np.double)

        # Act
        actual = calculations.signal_median(np_arr)

        # Assert
        assert actual == expected


class TestInterpolation:
    """Tests for signal interpolation functions."""

    @pytest.mark.parametrize(
        ("x1", "y1", "x2", "y2", "v", "expected"),
        [
            (0, 0, 10, 10, 5, 5.0),
            (100, 10, 200, 20, 15, 150.0),
            (10, 0, 10, 10, 5, 10.0),
            (10, 10, 20, 10, 5, np.inf),
        ],
        ids=["standard1", "standard2", "x1_eq_x2", "y1_eq_y2"],
    )
    def test_signal_interpolate_x(self, x1, y1, x2, y2, v, expected):
        """Test X interpolation between two points."""
        # Arrange
        # Handled by parametrize

        # Act
        res = calculations.signal_interpolate_x(x1, y1, x2, y2, v)

        # Assert
        if np.isinf(expected):
            assert np.isinf(res)
        else:
            npt.assert_allclose(res, expected)

    @pytest.mark.parametrize(
        ("x1", "y1", "x2", "y2", "v", "expected"),
        [
            (0, 0, 10, 10, 5, 5.0),
            (100, 10, 200, 20, 150, 15.0),
            (0, 10, 10, 10, 5, 10.0),
            (10, 0, 10, 10, 10, np.nan),
        ],
        ids=["standard1", "standard2", "y1_eq_y2", "x1_eq_x2"],
    )
    def test_signal_interpolate_y(self, x1, y1, x2, y2, v, expected):
        """Test Y interpolation between two points."""
        # Arrange
        # Handled by parametrize

        # Act
        res = calculations.signal_interpolate_y(x1, y1, x2, y2, v)

        # Assert
        if np.isnan(expected):
            assert np.isnan(res) or np.isinf(res)
        else:
            npt.assert_allclose(res, expected)


class TestLocate:
    """Tests for signal location functions."""

    @pytest.mark.parametrize(
        ("x", "expected"),
        [
            (5, 0),
            (15, 1),
            (25, 2),
            (35, 3),
            (45, 4),
            (10, 1),
            (40, 4),
        ],
    )
    def test_signal_locate_x(self, x, expected):
        """Test finding the index of an X value in a signal array."""
        # Arrange
        signal = np.array([[10, 1], [20, 5], [30, 2], [40, 8]], dtype=np.double)

        # Act
        idx = calculations.signal_locate_x(signal, x)

        # Assert
        assert idx == expected

    @pytest.mark.parametrize(
        ("signal_data", "expected"),
        [
            ([[10, 1], [20, 5], [30, 2], [40, 8], [50, 3]], 3),
            ([[10, 10], [20, 5]], 0),
        ],
        ids=["max_inner", "max_first"],
    )
    def test_signal_locate_max_y(self, signal_data, expected):
        """Test finding the index of the maximum Y value in a signal."""
        # Arrange
        signal = np.array(signal_data, dtype=np.double)

        # Act
        idx = calculations.signal_locate_max_y(signal)

        # Assert
        assert idx == expected


class TestAnalysis:
    """Tests for signal analysis functions."""

    def test_signal_box(self):
        """Test bounding box calculation for a signal."""
        # Arrange
        signal = np.array(
            [[10, 1], [20, 5], [30, 2], [40, 8], [50, 3]], dtype=np.double
        )

        # Act
        box = calculations.signal_box(signal)

        # Assert
        assert box == (10.0, 1.0, 50.0, 8.0)

    @pytest.mark.parametrize(
        ("x", "expected"),
        [
            (15, 15.0),
            (5, 0.0),
            (25, 0.0),
            (10, 10.0),
        ],
        ids=["interpolate", "out_left", "out_right", "exact_point"],
    )
    def test_signal_intensity(self, x, expected):
        """Test Y intensity lookup/interpolation at a given X."""
        # Arrange
        signal = np.array([[10, 10], [20, 20]], dtype=np.double)

        # Act
        intensity = calculations.signal_intensity(signal, x)

        # Assert
        npt.assert_allclose(intensity, expected)

    @pytest.mark.parametrize(
        ("x", "h", "expected"),
        [
            (20, 5, 20.0),
            (20, 15, 15.0),
        ],
        ids=["normal_height", "height_above_peak"],
    )
    def test_signal_centroid(self, x, h, expected):
        """Test centroid calculation for a peak in a signal."""
        # Arrange
        signal = np.array([[10, 0], [20, 10], [30, 0]], dtype=np.double)

        # Act
        res = calculations.signal_centroid(signal, x, h)

        # Assert
        npt.assert_allclose(res, expected)

    def test_signal_width(self):
        """Test peak width calculation at a given height."""
        # Arrange
        signal = np.array([[10, 0], [20, 10], [30, 0]], dtype=np.double)

        # Act
        width = calculations.signal_width(signal, 20, 5)

        # Assert
        npt.assert_allclose(width, 10.0)

    @pytest.mark.parametrize(
        ("signal_data", "expected"),
        [
            ([[0, 0], [10, 10], [20, 0]], 100.0),
            ([[0, 10], [10, 10]], 100.0),
        ],
        ids=["triangle", "rectangle"],
    )
    def test_signal_area(self, signal_data, expected):
        """Test area under the curve calculation for a signal."""
        # Arrange
        signal = np.array(signal_data, dtype=np.double)

        # Act
        area = calculations.signal_area(signal)

        # Assert
        npt.assert_allclose(area, expected)

    def test_signal_noise(self):
        """Test signal noise level and width estimation."""
        # Arrange
        signal = np.array([[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]], dtype=np.double)

        # Act
        level, width = calculations.signal_noise(signal)

        # Assert
        npt.assert_allclose(level, 3.0)
        npt.assert_allclose(width, 2.0)


class TestTransformation:
    """Tests for signal transformation functions."""

    def test_signal_local_maxima(self):
        """Test extraction of local maxima from a signal."""
        # Arrange
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 5], [4, 0]], dtype=np.double)
        expected = np.array([[1, 10], [3, 5]], dtype=np.double)

        # Act
        maxima = calculations.signal_local_maxima(signal)

        # Assert
        npt.assert_allclose(maxima, expected)

    def test_signal_crop(self):
        """Test cropping a signal to a specific X range."""
        # Arrange
        signal = np.array([[10, 1], [20, 2], [30, 3], [40, 4], [50, 5]], dtype=np.double)
        expected = np.array([[25, 2.5], [30, 3.0], [40, 4.0], [45, 4.5]], dtype=np.double)

        # Act
        cropped = calculations.signal_crop(signal, 25.0, 45.0)

        # Assert
        npt.assert_allclose(cropped, expected)

    def test_signal_offset(self):
        """Test applying X and Y offsets to a signal."""
        # Arrange
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        expected = np.array([[15, 11], [25, 12]], dtype=np.double)

        # Act
        offset = calculations.signal_offset(signal, 5.0, 10.0)

        # Assert
        npt.assert_allclose(offset, expected)

    def test_signal_multiply(self):
        """Test multiplying X and Y values of a signal by factors."""
        # Arrange
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        expected = np.array([[20, 3], [40, 6]], dtype=np.double)

        # Act
        multiplied = calculations.signal_multiply(signal, 2.0, 3.0)

        # Assert
        npt.assert_allclose(multiplied, expected)

    def test_signal_normalize(self):
        """Test normalizing signal Y values to [0, 1] range."""
        # Arrange
        signal = np.array([[10, 5], [20, 10], [30, 2]], dtype=np.double)
        expected = np.array([[10, 0.5], [20, 1.0], [30, 0.2]], dtype=np.double)

        # Act
        normalized = calculations.signal_normalize(signal)

        # Assert
        npt.assert_allclose(normalized, expected)

    def test_signal_rescale(self):
        """Test combined scaling and shifting of a signal."""
        # Arrange
        signal = np.array([[10, 1], [20, 2]], dtype=np.double)
        expected = np.array([[25, 10], [45, 20]], dtype=np.double)

        # Act
        rescaled = calculations.signal_rescale(signal, 2.0, 10.0, 5.0, 0.0)

        # Assert
        npt.assert_allclose(rescaled, expected)

    @pytest.mark.parametrize(
        "signal_data",
        [
            [[10, 1], [12, 5], [14, 2], [20, 8]],
            [[10, 10], [11, 5], [12, 15], [20, 10]],
        ],
        ids=["filter1", "filter2"],
    )
    def test_signal_filter(self, signal_data):
        """Test resolution-based filtering of signal points."""
        # Arrange
        signal = np.array(signal_data, dtype=np.double)

        # Act
        filtered = calculations.signal_filter(signal, 5.0)

        # Assert
        assert len(filtered) > 0


class TestOperation:
    """Tests for signal combination and smoothing functions."""

    def test_signal_smooth_ma(self):
        """Test moving average smoothing."""
        # Arrange
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 10], [4, 0]], dtype=np.double)

        # Act
        smoothed = calculations.signal_smooth_ma(signal, 2, 1)

        # Assert
        assert len(smoothed) == len(signal)
        npt.assert_allclose(smoothed[1, 1], (0 + 10 + 0) / 3.0)

    def test_signal_smooth_ga(self):
        """Test Gaussian smoothing."""
        # Arrange
        signal = np.array([[0, 0], [1, 10], [2, 0], [3, 10], [4, 0]], dtype=np.double)
        expected = np.array([[0.0, 1.2631536], [1.0, 7.4736928], [2.0, 2.5263072], [3.0, 7.4736928], [4.0, 1.2631536]], dtype=np.double)

        # Act
        smoothed = calculations.signal_smooth_ga(signal, 2, 1)

        # Assert
        npt.assert_allclose(smoothed, expected)

    def test_signal_combine(self):
        """Test combining (adding) two signals."""
        # Arrange
        signal_a = np.array([[10, 10], [20, 20]], dtype=np.double)
        signal_b = np.array([[15, 5], [25, 5]], dtype=np.double)
        expected = np.array([[10, 10], [15, 20], [20, 25], [25, 5]], dtype=np.double)

        # Act
        combined = calculations.signal_combine(signal_a, signal_b)

        # Assert
        npt.assert_allclose(combined, expected)

    def test_signal_overlay(self):
        """Test overlaying two signals (merging by X)."""
        # Arrange
        signal_a = np.array([[10, 10], [20, 20]], dtype=np.double)
        signal_b = np.array([[15, 30], [25, 5]], dtype=np.double)
        expected = np.array([[10, 10], [15, 30], [20, 20], [25, 5]], dtype=np.double)

        # Act
        overlay = calculations.signal_overlay(signal_a, signal_b)

        # Assert
        npt.assert_allclose(overlay, expected)

    def test_signal_subtract(self):
        """Test subtracting one signal from another."""
        # Arrange
        signal_a = np.array([[10, 10], [20, 20]], dtype=np.double)
        signal_b = np.array([[15, 5], [25, 5]], dtype=np.double)
        expected = np.array([[10, 10], [15, 10], [20, 15], [25, -5]], dtype=np.double)

        # Act
        subtracted = calculations.signal_subtract(signal_a, signal_b)

        # Assert
        npt.assert_allclose(subtracted, expected)

    def test_signal_subbase(self):
        """Test subtracting a baseline from a signal."""
        # Arrange
        signal = np.array([[10, 10], [20, 20], [30, 30]], dtype=np.double)
        baseline = np.array([[0, 5], [40, 5]], dtype=np.double)
        expected = np.array([[10, 5], [20, 15], [30, 25]], dtype=np.double)

        # Act
        subbed = calculations.signal_subbase(signal, baseline)

        # Assert
        npt.assert_allclose(subbed, expected)


class TestGeneration:
    """Tests for signal generation and profiling functions."""

    def test_signal_gaussian(self):
        """Test generating a Gaussian peak signal."""
        # Act
        gaussian = calculations.signal_gaussian(100.0, 0.0, 100.0, 10.0, 100)

        # Assert
        assert len(gaussian) == 100
        idx = np.argmin(np.abs(gaussian[:, 0] - 100.0))
        npt.assert_allclose(gaussian[idx, 1], 100.0, atol=1.0)

    def test_signal_lorentzian(self):
        """Test generating a Lorentzian peak signal."""
        # Act
        lorentzian = calculations.signal_lorentzian(100.0, 0.0, 100.0, 10.0, 100)

        # Assert
        assert len(lorentzian) == 100
        idx = np.argmin(np.abs(lorentzian[:, 0] - 100.0))
        npt.assert_allclose(lorentzian[idx, 1], 100.0, atol=1.0)

    def test_signal_gausslorentzian(self):
        """Test generating a mixed Gauss-Lorentzian peak signal."""
        # Act
        gl = calculations.signal_gausslorentzian(100.0, 0.0, 100.0, 10.0, 150)

        # Assert
        assert len(gl) == 150
        idx = np.argmin(np.abs(gl[:, 0] - 100.0))
        npt.assert_allclose(gl[idx, 1], 100.0, atol=1.0)

    @pytest.mark.parametrize(
        ("shape", "label"),
        [(0, "gaussian"), (1, "lorentzian"), (2, "gauss-lorentzian")],
        ids=["shape-0-gaussian", "shape-1-lorentzian", "shape-2-gausslorentzian"],
    )
    def test_signal_profile_to_raster(self, shape, label):
        """Test profiling peaks onto a predefined raster."""
        # Arrange
        peaks = np.array([[100, 100, 1], [200, 50, 1]], dtype=np.double)
        raster = np.linspace(50, 250, 1000, dtype=np.double)

        # Act
        profile = calculations.signal_profile_to_raster(peaks, raster, 0.0, shape)

        # Assert
        assert len(profile) == len(raster)
        idx1 = np.argmin(np.abs(profile[:, 0] - 100))
        npt.assert_allclose(profile[idx1, 1], 100.0, rtol=1e-2)

    @pytest.mark.parametrize(
        ("shape", "noise"),
        [
            (0, 0.0),
            (1, 0.0),
            (2, 0.0),
            (0, 1.0),
        ],
        ids=["shape-0-no-noise", "shape-1-no-noise", "shape-2-no-noise", "shape-0-with-noise"]
    )
    def test_signal_profile(self, shape, noise):
        """Test profiling peaks with automatic raster generation and noise addition."""
        # Arrange
        peaks = np.array([[100, 100, 1], [200, 50, 1]], dtype=np.double)

        # Act
        profile = calculations.signal_profile(peaks, 10, noise, shape)

        # Assert
        assert len(profile) > 0


class TestFormula:
    """Tests for formula-related functions."""

    @pytest.mark.parametrize(
        ("min_comp", "max_comp", "masses", "lo_mass", "hi_mass", "limit", "expected_comps"),
        [
            ((0, 0), (2, 5), (12.0, 1.007825), 12.9, 13.1, 100, [[1, 1]]),
            ((0, 0), (2, 5), (12.0, 1.007825), 1000.0, 1001.0, 100, []),
        ],
        ids=["valid_mass_window", "out_of_bounds_window"],
    )
    def test_formula_composition(
        self, min_comp, max_comp, masses, lo_mass, hi_mass, limit, expected_comps
    ):
        """Test brute-force formula composition search within a mass window."""
        # Arrange
        # Parameters handled by parametrize

        # Act
        compositions = calculations.formula_composition(
            min_comp, max_comp, masses, lo_mass, hi_mass, limit
        )

        # Assert
        if not expected_comps:
            assert compositions == []
        else:
            for comp in expected_comps:
                assert comp in compositions


class TestRegression:
    """Regression and edge case tests."""

    def test_invalid_inputs(self):
        """Test that invalid inputs raise appropriate errors."""
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            calculations.signal_locate_max_y(None)
        with pytest.raises((TypeError, ValueError)):
            calculations.signal_locate_max_y("not an array")


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        arr=arrays(
            dtype=np.double,
            shape=st.tuples(st.integers(min_value=0, max_value=100)),
            elements=st.floats(allow_nan=True, allow_infinity=True),
        )
    )
    def test_signal_median(self, arr):
        """Verify that signal_median always returns a float."""
        res = calculations.signal_median(arr)
        assert isinstance(res, float)

    @given(
        x1=st.floats(allow_nan=True, allow_infinity=True),
        y1=st.floats(allow_nan=True, allow_infinity=True),
        x2=st.floats(allow_nan=True, allow_infinity=True),
        y2=st.floats(allow_nan=True, allow_infinity=True),
        v=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_interpolate_x(self, x1, y1, x2, y2, v):
        """Verify that signal_interpolate_x always returns a float."""
        res = calculations.signal_interpolate_x(x1, y1, x2, y2, v)
        assert isinstance(res, float)

    @given(
        x1=st.floats(allow_nan=True, allow_infinity=True),
        y1=st.floats(allow_nan=True, allow_infinity=True),
        x2=st.floats(allow_nan=True, allow_infinity=True),
        y2=st.floats(allow_nan=True, allow_infinity=True),
        v=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_interpolate_y(self, x1, y1, x2, y2, v):
        """Verify that signal_interpolate_y always returns a float."""
        res = calculations.signal_interpolate_y(x1, y1, x2, y2, v)
        assert isinstance(res, float)

    @given(signal=signals(), x=st.floats(allow_nan=True, allow_infinity=True))
    def test_signal_locate_x(self, signal, x):
        """Verify that signal_locate_x returns a valid index."""
        idx = calculations.signal_locate_x(signal, x)
        assert 0 <= idx <= len(signal)

    @given(signal=signals())
    def test_signal_locate_max_y(self, signal):
        """Verify that signal_locate_max_y returns a valid index."""
        if len(signal) == 0:
            res = calculations.signal_locate_max_y(signal)
            assert res == 0
        else:
            idx = calculations.signal_locate_max_y(signal)
            assert 0 <= idx < len(signal)

    @given(signal=signals())
    def test_signal_box(self, signal):
        """Verify that signal_box returns a 4-tuple of floats or handles empty signals."""
        res = calculations.signal_box(signal)
        assert len(res) == 4
        assert all(isinstance(v, float) for v in res)

    @given(signal=signals(), x=st.floats(allow_nan=True, allow_infinity=True))
    def test_signal_intensity(self, signal, x):
        """Verify that signal_intensity always returns a float."""
        res = calculations.signal_intensity(signal, x)
        assert isinstance(res, float)

    @given(
        signal=signals(),
        x=st.floats(allow_nan=True, allow_infinity=True),
        h=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_centroid(self, signal, x, h):
        """Verify that signal_centroid always returns a float."""
        res = calculations.signal_centroid(signal, x, h)
        assert isinstance(res, float)

    @given(
        signal=signals(),
        x=st.floats(allow_nan=True, allow_infinity=True),
        h=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_width(self, signal, x, h):
        """Verify that signal_width always returns a float."""
        res = calculations.signal_width(signal, x, h)
        assert isinstance(res, float)

    @given(signal=signals())
    def test_signal_area(self, signal):
        """Verify that signal_area always returns a float."""
        res = calculations.signal_area(signal)
        assert isinstance(res, float)

    @given(signal=signals(min_size=1))
    def test_signal_noise(self, signal):
        """Verify that signal_noise returns two floats."""
        level, width = calculations.signal_noise(signal)
        assert isinstance(level, float)
        assert isinstance(width, float)

    @given(signal=signals())
    def test_signal_local_maxima(self, signal):
        """Verify that signal_local_maxima returns a numpy array."""
        res = calculations.signal_local_maxima(signal)
        assert isinstance(res, np.ndarray)
        if len(res) > 0:
            assert res.shape[1] == 2

    @given(
        signal=signals(),
        min_x=st.floats(allow_nan=True, allow_infinity=True),
        max_x=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_crop(self, signal, min_x, max_x):
        """Verify that signal_crop returns a numpy array."""
        res = calculations.signal_crop(signal, min_x, max_x)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        v1=st.floats(allow_nan=True, allow_infinity=True),
        v2=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_offset(self, signal, v1, v2):
        """Verify that signal_offset returns a numpy array."""
        res = calculations.signal_offset(signal, v1, v2)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        v1=st.floats(allow_nan=True, allow_infinity=True),
        v2=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_multiply(self, signal, v1, v2):
        """Verify that signal_multiply returns a numpy array."""
        res = calculations.signal_multiply(signal, v1, v2)
        assert isinstance(res, np.ndarray)

    @given(signal=signals())
    def test_signal_normalize(self, signal):
        """Verify that signal_normalize returns a numpy array."""
        res = calculations.signal_normalize(signal)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        scale_x=st.floats(allow_nan=True, allow_infinity=True),
        scale_y=st.floats(allow_nan=True, allow_infinity=True),
        shift_x=st.floats(allow_nan=True, allow_infinity=True),
        shift_y=st.floats(allow_nan=True, allow_infinity=True),
    )
    def test_signal_rescale(self, signal, scale_x, scale_y, shift_x, shift_y):
        """Verify that signal_rescale returns a numpy array."""
        res = calculations.signal_rescale(signal, scale_x, scale_y, shift_x, shift_y)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        resol=st.floats(min_value=0.0, allow_nan=False, allow_infinity=False),
    )
    def test_signal_filter(self, signal, resol):
        """Verify that signal_filter returns a numpy array."""
        assume(resol > 0)
        res = calculations.signal_filter(signal, resol)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        window=st.integers(min_value=0, max_value=100),
        cycles=st.integers(min_value=0, max_value=10),
    )
    def test_signal_smooth_ma(self, signal, window, cycles):
        """Verify that signal_smooth_ma returns a numpy array."""
        res = calculations.signal_smooth_ma(signal, window, cycles)
        assert isinstance(res, np.ndarray)

    @given(
        signal=signals(),
        window=st.integers(min_value=0, max_value=100),
        cycles=st.integers(min_value=0, max_value=10),
    )
    def test_signal_smooth_ga(self, signal, window, cycles):
        """Verify that signal_smooth_ga returns a numpy array."""
        res = calculations.signal_smooth_ga(signal, window, cycles)
        assert isinstance(res, np.ndarray)

    @given(signal_a=signals(), signal_b=signals())
    def test_signal_combine(self, signal_a, signal_b):
        """Verify that signal_combine returns a numpy array."""
        signal_a = np.ascontiguousarray(signal_a, dtype=np.double)
        signal_b = np.ascontiguousarray(signal_b, dtype=np.double)
        res = calculations.signal_combine(signal_a, signal_b)
        assert isinstance(res, np.ndarray)

    @given(signal_a=signals(), signal_b=signals())
    def test_signal_overlay(self, signal_a, signal_b):
        """Verify that signal_overlay returns a numpy array."""
        signal_a = np.ascontiguousarray(signal_a, dtype=np.double)
        signal_b = np.ascontiguousarray(signal_b, dtype=np.double)
        res = calculations.signal_overlay(signal_a, signal_b)
        assert isinstance(res, np.ndarray)

    @given(signal_a=signals(), signal_b=signals())
    def test_signal_subtract(self, signal_a, signal_b):
        """Verify that signal_subtract returns a numpy array."""
        signal_a = np.ascontiguousarray(signal_a, dtype=np.double)
        signal_b = np.ascontiguousarray(signal_b, dtype=np.double)
        res = calculations.signal_subtract(signal_a, signal_b)
        assert isinstance(res, np.ndarray)

    @given(signal_a=signals(), signal_b=signals())
    def test_signal_subbase(self, signal_a, signal_b):
        """Verify that signal_subbase returns a numpy array."""
        signal_a = np.ascontiguousarray(signal_a, dtype=np.double)
        signal_b = np.ascontiguousarray(signal_b, dtype=np.double)
        res = calculations.signal_subbase(signal_a, signal_b)
        assert isinstance(res, np.ndarray)

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        min_y=st.floats(allow_nan=False, allow_infinity=False),
        max_y=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(
            min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        points=st.integers(min_value=1, max_value=1000),
    )
    def test_signal_gaussian(self, x, min_y, max_y, fwhm, points):
        """Verify that signal_gaussian returns a valid numpy array."""
        res = calculations.signal_gaussian(x, min_y, max_y, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        min_y=st.floats(allow_nan=False, allow_infinity=False),
        max_y=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(
            min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        points=st.integers(min_value=1, max_value=1000),
    )
    def test_signal_lorentzian(self, x, min_y, max_y, fwhm, points):
        """Verify that signal_lorentzian returns a valid numpy array."""
        res = calculations.signal_lorentzian(x, min_y, max_y, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        x=st.floats(allow_nan=False, allow_infinity=False),
        min_y=st.floats(allow_nan=False, allow_infinity=False),
        max_y=st.floats(allow_nan=False, allow_infinity=False),
        fwhm=st.floats(
            min_value=0.0001, max_value=1000.0, allow_nan=False, allow_infinity=False
        ),
        points=st.integers(min_value=1, max_value=1000),
    )
    def test_signal_gausslorentzian(self, x, min_y, max_y, fwhm, points):
        """Verify that signal_gausslorentzian returns a valid numpy array."""
        res = calculations.signal_gausslorentzian(x, min_y, max_y, fwhm, points)
        assert isinstance(res, np.ndarray)
        assert len(res) == points

    @given(
        peaks=peaklists(min_size=1),
        raster=arrays(
            dtype=np.double,
            shape=st.tuples(
                st.integers(min_value=1, max_value=500),
            ),
            elements=st.floats(
                min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False
            ),
        ),
        noise=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        shape=st.integers(min_value=0, max_value=2),
    )
    def test_signal_profile_to_raster(self, peaks, raster, noise, shape):
        """Verify that signal_profile_to_raster returns a valid numpy array."""
        peaks = np.ascontiguousarray(peaks, dtype=np.double)
        raster = np.ascontiguousarray(raster, dtype=np.double)
        res = calculations.signal_profile_to_raster(peaks, raster, noise, shape)
        assert isinstance(res, np.ndarray)
        assert len(res) == len(raster)

    @given(
        peaks=peaklists(min_size=1),
        points=st.integers(min_value=1, max_value=100),
        noise=st.floats(
            min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
        ),
        shape=st.integers(min_value=0, max_value=2),
    )
    def test_signal_profile(self, peaks, points, noise, shape):
        """Verify that signal_profile returns a valid numpy array."""
        peaks = np.ascontiguousarray(peaks, dtype=np.double)
        # Constrain peaks to avoid extreme raster sizes
        assume(np.max(peaks[:, 0]) - np.min(peaks[:, 0]) < 1000)
        assume(np.min(peaks[:, 2]) > 0.1)
        res = calculations.signal_profile(peaks, points, noise, shape)
        assert isinstance(res, np.ndarray)

    @given(
        min_comp=st.tuples(
            st.integers(min_value=0, max_value=5), st.integers(min_value=0, max_value=5)
        ),
        max_comp=st.tuples(
            st.integers(min_value=0, max_value=10),
            st.integers(min_value=0, max_value=10),
        ),
        masses=st.tuples(
            st.floats(min_value=1.0, max_value=100.0),
            st.floats(min_value=1.0, max_value=100.0),
        ),
        lo_mass=st.floats(min_value=0.0, max_value=1000.0),
        hi_mass=st.floats(min_value=0.0, max_value=1000.0),
        limit=st.integers(min_value=1, max_value=100),
    )
    def test_formula_composition(
        self, min_comp, max_comp, masses, lo_mass, hi_mass, limit
    ):
        """Verify that formula_composition returns a list of compositions."""
        # Ensure min_comp <= max_comp for each element
        assume(all(mi <= ma for mi, ma in zip(min_comp, max_comp, strict=False)))
        res = calculations.formula_composition(
            min_comp, max_comp, masses, lo_mass, hi_mass, limit
        )
        assert isinstance(res, list)
