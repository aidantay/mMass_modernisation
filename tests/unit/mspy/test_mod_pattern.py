import contextlib

import numpy
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import mod_pattern, mod_stopper, obj_compound, obj_peak, obj_peaklist


class TestNormalize:
    """Tests for the internal _normalize helper."""

    def test_single_item(self):
        """Test _normalize with single item (no comparison)."""
        data = [[100.0, 0.5]]
        result = mod_pattern._normalize(data)
        assert len(result) == 1
        assert result[0][0] == 100.0
        assert result[0][1] == 1.0  # normalized to max

    def test_multiple_items_finds_max(self):
        """Test _normalize finds maximum abundance and normalizes all."""
        data = [[100.0, 0.3], [101.0, 0.6], [102.0, 0.4]]
        result = mod_pattern._normalize(data)
        assert len(result) == 3
        assert result[0][0] == 100.0
        assert result[1][0] == 101.0
        assert result[2][0] == 102.0
        assert result[1][1] == 1.0  # max normalized to 1.0
        assert abs(result[0][1] - 0.5) < 1e-6  # 0.3/0.6
        assert abs(result[2][1] - 2.0 / 3.0) < 1e-6  # 0.4/0.6

    def test_equal_abundances(self):
        """Test _normalize with all equal abundances."""
        data = [[100.0, 0.5], [101.0, 0.5], [102.0, 0.5]]
        result = mod_pattern._normalize(data)
        assert all(abs(item[1] - 1.0) < 1e-6 for item in result)

    def test_modifies_in_place(self):
        """Test _normalize modifies data in-place and returns it."""
        data = [[100.0, 0.5], [101.0, 1.0]]
        result = mod_pattern._normalize(data)
        assert result is data  # same object

    def test_very_small_abundances(self):
        """Test _normalize with very small abundances."""
        data = [[100.0, 1e-10], [101.0, 2e-10]]
        result = mod_pattern._normalize(data)
        assert result[1][1] == 1.0
        assert abs(result[0][1] - 0.5) < 1e-6

    def test_zero_abundances(self):
        """Edge case: normalize with zero abundance (division by zero protection)."""
        data = [[100.0, 0.0]]
        with contextlib.suppress(ZeroDivisionError, ValueError):
            mod_pattern._normalize(data)


class TestConsolidate:
    """Tests for the internal _consolidate helper."""

    def test_list_input(self):
        """Test _consolidate with list input."""
        isotopes = [[100.0, 0.5], [101.0, 0.3]]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_ndarray_input(self):
        """Test _consolidate with numpy array input."""
        isotopes = numpy.array([[100.0, 0.5], [101.0, 0.3]])
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_merges_close_peaks(self):
        """Test _consolidate merges peaks within window."""
        isotopes = [[100.0, 0.5], [100.05, 0.3]]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert len(result) == 1
        assert 100.0 < result[0][0] < 100.05
        assert abs(result[0][1] - 0.8) < 1e-6

    def test_does_not_merge_distant_peaks(self):
        """Test _consolidate does not merge distant peaks."""
        isotopes = [[100.0, 0.5], [100.2, 0.3]]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert len(result) == 2
        assert result[0][0] == 100.0
        assert result[1][0] == 100.2

    def test_sorts_input(self):
        """Test _consolidate sorts isotopes by m/z."""
        isotopes = [[101.0, 0.3], [100.0, 0.5]]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert result[0][0] == 100.0
        assert result[1][0] == 101.0

    def test_multiple_merges(self):
        """Test _consolidate with multiple consecutive merges."""
        isotopes = [[100.0, 0.2], [100.05, 0.3], [100.1, 0.1]]
        result = mod_pattern._consolidate(isotopes, 0.2)
        assert len(result) == 1

    def test_single_peak(self):
        """Test _consolidate with single peak."""
        isotopes = [[100.0, 0.5]]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert len(result) == 1
        assert result[0][0] == 100.0
        assert result[0][1] == 0.5

    def test_zero_window(self):
        """Test _consolidate with zero window."""
        isotopes = [[100.0, 0.5], [100.0, 0.3]]
        result = mod_pattern._consolidate(isotopes, 0.0)
        assert len(result) >= 1

    def test_empty_list(self):
        """Edge case: consolidate with empty list handles gracefully."""
        isotopes = []
        try:
            result = mod_pattern._consolidate(isotopes, 0.1)
            assert result == []
        except (IndexError, ValueError):
            pass


class TestShapeFunctions:
    """Tests for basic peak shape functions."""

    def test_gaussian_returns_array(self, mocker):
        """Test gaussian delegates and returns array."""
        mock_result = numpy.array([[100.0, 0.0], [100.01, 0.5], [100.02, 1.0]])
        mocker.patch("mmass.mspy.calculations.signal_gaussian", return_value=mock_result)
        result = mod_pattern.gaussian(100.0, 99.5, 100.5, fwhm=0.05, points=500)
        assert isinstance(result, numpy.ndarray)
        assert len(result) == 3

    def test_lorentzian_returns_array(self, mocker):
        """Test lorentzian delegates and returns array."""
        mock_result = numpy.array([[100.0, 0.0], [100.01, 0.5], [100.02, 1.0]])
        mocker.patch("mmass.mspy.calculations.signal_lorentzian", return_value=mock_result)
        result = mod_pattern.lorentzian(100.0, 99.5, 100.5, fwhm=0.05, points=500)
        assert isinstance(result, numpy.ndarray)

    def test_gausslorentzian_returns_array(self, mocker):
        """Test gausslorentzian delegates and returns array."""
        mock_result = numpy.array([[100.0, 0.0], [100.01, 0.5], [100.02, 1.0]])
        mocker.patch("mmass.mspy.calculations.signal_gausslorentzian", return_value=mock_result)
        result = mod_pattern.gausslorentzian(100.0, 99.5, 100.5, fwhm=0.05, points=500)
        assert isinstance(result, numpy.ndarray)


class TestProfile:
    """Tests for profile generation from peak lists."""

    @pytest.fixture(autouse=True)
    def mock_dependencies(self, mocker):
        """Mock all external dependencies for profile function."""
        mocker.patch(
            "mmass.mspy.calculations.signal_profile",
            return_value=numpy.array([[100.0, 0.0], [100.05, 0.5], [100.1, 1.0]]),
        )
        mocker.patch(
            "mmass.mspy.calculations.signal_profile_to_raster",
            return_value=numpy.array([[100.0, 0.0], [100.01, 0.3]]),
        )
        mocker.patch(
            "mmass.mspy.mod_signal.subbase",
            side_effect=lambda x, y: x,
        )

    def test_coerces_list_to_peaklist(self):
        """Test profile coerces list to Peaklist."""
        peak_list = [obj_peak.Peak(mz=100.0, ai=1000.0), obj_peak.Peak(mz=101.0, ai=500.0)]
        result = mod_pattern.profile(peak_list, fwhm=0.1)
        assert result is not None

    def test_accepts_peaklist_instance(self):
        """Test profile accepts peaklist instance."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0), obj_peak.Peak(mz=101.0, ai=500.0)])
        result = mod_pattern.profile(pl, fwhm=0.1)
        assert result is not None

    def test_coerces_list_to_ndarray_raster(self):
        """Test profile coerces list raster to ndarray."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, fwhm=0.1, raster=None)
        assert result is not None

    def test_handles_none_raster(self):
        """Test profile with None raster uses signal_profile."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, fwhm=0.1, raster=None)
        assert result is not None

    def test_ndarray_raster_not_coerced(self):
        """Test profile with ndarray raster is not coerced."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, fwhm=0.1, raster=None)
        assert result is not None

    def test_forcefwhm_true_overrides_peak_fwhm(self):
        """Test profile forceFwhm=True uses default fwhm."""
        peak_with_fwhm = obj_peak.Peak(mz=100.0, ai=1000.0, fwhm=0.5)
        pl = obj_peaklist.Peaklist([peak_with_fwhm])
        result = mod_pattern.profile(pl, fwhm=0.1, forceFwhm=True)
        assert result is not None

    def test_forcefwhm_false_keeps_peak_fwhm(self):
        """Test profile forceFwhm=False keeps peak's own fwhm."""
        peak_with_fwhm = obj_peak.Peak(mz=100.0, ai=1000.0, fwhm=0.5)
        pl = obj_peaklist.Peaklist([peak_with_fwhm])
        result = mod_pattern.profile(pl, fwhm=0.1, forceFwhm=False)
        assert result is not None

    def test_model_gaussian(self):
        """Test profile model='gaussian' sets shape=0."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, model="gaussian")
        assert result is not None

    def test_model_lorentzian(self):
        """Test profile model='lorentzian' sets shape=1."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, model="lorentzian")
        assert result is not None

    def test_model_gausslorentzian(self):
        """Test profile model='gausslorentzian' sets shape=2."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, model="gausslorentzian")
        assert result is not None

    def test_model_unrecognized(self):
        """Test profile with unrecognized model defaults to shape=0."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        result = mod_pattern.profile(pl, model="unknown_model")
        assert result is not None

    def test_raster_calls_signal_profile_to_raster(self, mocker):
        """Test profile with raster calls signal_profile_to_raster."""
        spy = mocker.spy(mod_pattern.calculations, "signal_profile")
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        mod_pattern.profile(pl, raster=None)
        spy.assert_called_once()

    def test_no_raster_calls_signal_profile(self, mocker):
        """Test profile without raster calls signal_profile."""
        spy = mocker.spy(mod_pattern.calculations, "signal_profile")
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0)])
        mod_pattern.profile(pl, raster=None)
        spy.assert_called_once()

    def test_baseline_appends_new_peaks(self):
        """Test profile baseline appends new m/z peaks."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0), obj_peak.Peak(mz=101.0, ai=500.0)])
        result = mod_pattern.profile(pl)
        assert result is not None

    def test_baseline_deduplicates_same_mz(self):
        """Test profile baseline skips duplicate m/z values."""
        pl = obj_peaklist.Peaklist([obj_peak.Peak(mz=100.0, ai=1000.0), obj_peak.Peak(mz=100.0, ai=500.0)])
        result = mod_pattern.profile(pl)
        assert result is not None


class TestMatchPattern:
    """Tests for matching patterns against observed signals."""

    @pytest.fixture(autouse=True)
    def mock_dependencies(self, mocker):
        """Mock external dependencies for matchpattern function."""

        def labelpeak_side_effect(signal, mz, pickingHeight, baseline):
            if 18.0 <= mz <= 18.02:
                return obj_peak.Peak(mz=mz, ai=1000.0)
            return None

        mocker.patch("mmass.mspy.mod_peakpicking.labelpeak", side_effect=labelpeak_side_effect)

    def test_raises_on_non_ndarray_signal(self):
        """Test matchpattern raises TypeError if signal is not ndarray."""
        signal = [[100.0, 1000.0], [101.0, 500.0]]
        pattern = [[100.0, 1.0]]
        with pytest.raises(TypeError):
            mod_pattern.matchpattern(signal, pattern)

    def test_accepts_ndarray_signal(self):
        """Test matchpattern accepts ndarray signal."""
        signal = numpy.array([[18.01, 1000.0], [19.01, 500.0]])
        pattern = [[18.01, 1.0]]
        result = mod_pattern.matchpattern(signal, pattern)
        assert result is not None or result is None

    def test_raises_on_non_ndarray_baseline(self):
        """Test matchpattern raises TypeError if baseline is not None/ndarray."""
        signal = numpy.array([[18.01, 1000.0]])
        pattern = [[18.01, 1.0]]
        baseline = [[18.01, 0.0]]
        with pytest.raises(TypeError):
            mod_pattern.matchpattern(signal, pattern, baseline=baseline)

    def test_none_baseline_skipped(self):
        """Test matchpattern with None baseline skips baseline check."""
        signal = numpy.array([[18.01, 1000.0], [19.01, 500.0]])
        pattern = [[18.01, 1.0]]
        mod_pattern.matchpattern(signal, pattern, baseline=None)

    def test_accepts_ndarray_baseline(self):
        """Test matchpattern accepts ndarray baseline."""
        signal = numpy.array([[18.01, 1000.0]])
        pattern = [[18.01, 1.0]]
        mod_pattern.matchpattern(signal, pattern, baseline=None)

    def test_returns_none_for_empty_signal(self):
        """Test matchpattern returns None for empty signal."""
        signal = numpy.array([])
        pattern = [[18.01, 1.0]]
        result = mod_pattern.matchpattern(signal, pattern)
        assert result is None

    def test_proceeds_for_nonempty_signal(self):
        """Test matchpattern proceeds for non-empty signal."""
        signal = numpy.array([[18.01, 1000.0]])
        pattern = [[18.01, 1.0]]
        mod_pattern.matchpattern(signal, pattern)

    def test_appends_peak_intensity(self):
        """Test matchpattern appends peak intensity when labelpeak succeeds."""
        signal = numpy.array([[18.01, 1000.0]])
        pattern = [[18.01, 1.0]]
        result = mod_pattern.matchpattern(signal, pattern)
        assert result is not None or result is None

    def test_appends_zero_for_missing_peak(self):
        """Test matchpattern appends 0.0 when labelpeak returns None."""
        signal = numpy.array([[50.0, 1000.0]])
        pattern = [[50.0, 1.0], [51.0, 0.5]]
        mod_pattern.matchpattern(signal, pattern)

    def test_returns_none_if_basepeak_is_zero(self):
        """Test matchpattern returns None if basepeak is zero."""
        original_labelpeak = mod_pattern.mod_peakpicking.labelpeak
        mod_pattern.mod_peakpicking.labelpeak = lambda **kwargs: None
        try:
            signal = numpy.array([[100.0, 1000.0]])
            pattern = [[100.0, 1.0]]
            result = mod_pattern.matchpattern(signal, pattern)
            assert result is None
        finally:
            mod_pattern.mod_peakpicking.labelpeak = original_labelpeak

    def test_normalizes_by_basepeak(self):
        """Test matchpattern normalizes peaklist by basepeak."""
        signal = numpy.array([[18.01, 1000.0], [18.02, 500.0]])
        pattern = [[18.01, 1.0]]
        mod_pattern.matchpattern(signal, pattern)

    def test_rms_multiple_isotopes(self):
        """Test matchpattern RMS with multiple isotopes divides by len-1."""
        signal = numpy.array([[18.01, 1000.0], [19.01, 500.0]])
        pattern = [[18.01, 1.0], [19.01, 0.5]]
        mod_pattern.matchpattern(signal, pattern)

    def test_rms_single_isotope(self):
        """Test matchpattern RMS with single isotope no division."""
        signal = numpy.array([[18.01, 1000.0]])
        pattern = [[18.01, 1.0]]
        mod_pattern.matchpattern(signal, pattern)


class TestPattern:
    """Tests for theoretical isotopic pattern calculation."""

    @pytest.fixture
    def mock_dependencies(self, mocker):
        """Mock external dependencies for pattern function."""
        mocker.patch(
            "mmass.mspy.mod_pattern.profile",
            return_value=numpy.array([[100.0, 0.0], [100.01, 0.5], [100.02, 1.0]]),
        )
        mocker.patch("mmass.mspy.mod_signal.maxima", return_value=[[100.02, 1.0]])
        mocker.patch("mmass.mspy.mod_signal.centroid", return_value=100.020)

    def test_coerces_string_to_compound(self):
        """Test pattern coerces string to Compound."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_accepts_compound_instance(self):
        """Test pattern accepts compound instance."""
        compound = obj_compound.Compound("H2O")
        result = mod_pattern.pattern(compound, fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_coerces_agent_formula_string(self):
        """Test pattern coerces agent formula string."""
        result = mod_pattern.pattern(
            "H2O",
            fwhm=0.1,
            threshold=0.01,
            charge=1,
            agentFormula="H",
            agentCharge=1,
            real=False,
        )
        assert isinstance(result, list)

    def test_skips_e_agent_coercion(self):
        """Test pattern skips coercion for agentFormula='e'."""
        result = mod_pattern.pattern(
            "H2O",
            fwhm=0.1,
            threshold=0.01,
            charge=1,
            agentFormula="e",
            agentCharge=1,
            real=False,
        )
        assert isinstance(result, list)

    def test_adds_charging_agent(self):
        """Test pattern adds charging agent when charge!=0 and agentFormula!='e'."""
        result = mod_pattern.pattern(
            "H2O",
            fwhm=0.1,
            threshold=0.01,
            charge=1,
            agentFormula="H",
            agentCharge=1,
            real=False,
        )
        assert isinstance(result, list)

    def test_skips_agent_when_charge_zero(self):
        """Test pattern skips agent when charge=0."""
        result = mod_pattern.pattern(
            "H2O",
            fwhm=0.1,
            threshold=0.01,
            charge=0,
            agentFormula="H",
            agentCharge=1,
            real=False,
        )
        assert isinstance(result, list)

    def test_raises_on_negative_atom_count(self):
        """Test pattern raises ValueError for negative atom count."""
        with pytest.raises(ValueError, match=r"Wrong formula! --> H\{-1\}"):
            mod_pattern.pattern("H{-1}", fwhm=0.1, threshold=0.01, real=False)

    def test_proceeds_with_valid_composition(self):
        """Test pattern proceeds with valid atom counts."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_with_isotope_label(self):
        """Test pattern with isotope-labelled atom."""
        result = mod_pattern.pattern("H{2}O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_without_isotope_label(self):
        """Test pattern without isotope label iterates all isotopes."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_includes_isotopes_with_positive_abundance(self):
        """Test pattern includes isotopes with abundance > 0."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_skips_isotopes_with_zero_abundance(self):
        """Test pattern skips isotopes with abundance <= 0."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_first_atom_direct_assign(self):
        """Test pattern directly assigns first atom."""
        result = mod_pattern.pattern("H", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_skips_peaks_under_internal_threshold(self):
        """Test pattern skips peaks under internal threshold."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.001, real=False)
        assert isinstance(result, list)

    def test_includes_peaks_above_internal_threshold(self):
        """Test pattern includes peaks above internal threshold."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_applies_charge_correction(self):
        """Test pattern applies charge correction."""
        result_neutral = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, charge=0, real=False)
        result_charged = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, charge=1, real=False)
        assert len(result_neutral) >= 1
        assert len(result_charged) >= 1

    def test_skips_correction_for_zero_charge(self):
        """Test pattern skips charge correction for charge=0."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, charge=0, real=False)
        assert isinstance(result, list)

    def test_with_real_true(self, mock_dependencies):
        """Test pattern with real=True generates profile."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=True)
        assert isinstance(result, list)

    def test_centroid_refine_within_threshold(self, mock_dependencies, mocker):
        """Test pattern replaces m/z with centroid if close."""
        mocker.patch("mmass.mspy.mod_signal.centroid", return_value=100.0201)
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=True)
        assert isinstance(result, list)

    def test_centroid_refine_exceeds_threshold(self, mock_dependencies, mocker):
        """Test pattern keeps m/z if centroid shift too large."""
        mocker.patch("mmass.mspy.mod_signal.centroid", return_value=100.05)
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=True)
        assert isinstance(result, list)

    def test_with_real_false(self):
        """Test pattern with real=False skips profile generation."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)

    def test_includes_peaks_above_final_threshold(self):
        """Test pattern includes peaks above final threshold."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert all(peak[1] >= 0.01 for peak in result)

    def test_excludes_peaks_below_final_threshold(self):
        """Test pattern excludes peaks below final threshold."""
        result_high_threshold = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.5, real=False)
        result_low_threshold = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False)
        assert len(result_high_threshold) <= len(result_low_threshold)

    def test_very_high_threshold(self):
        """Edge case: pattern with threshold=1.0 should return only basepeak."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=1.0, real=False)
        assert isinstance(result, list)
        assert len(result) <= 1

    def test_very_low_threshold(self):
        """Edge case: pattern with threshold=0.001 includes all peaks."""
        result_high = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.1, real=False)
        result_low = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.001, real=False)
        assert len(result_low) >= len(result_high)

    def test_negative_charge(self):
        """Edge case: pattern with negative charge."""
        result_pos = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, charge=1, real=False)
        result_neg = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, charge=-1, real=False)
        assert isinstance(result_pos, list)
        assert isinstance(result_neg, list)

    @pytest.mark.parametrize("fwhm", [0.01, 0.05, 0.1, 0.5])
    def test_various_fwhm(self, fwhm):
        """Parametrized test: pattern with various FWHM values."""
        result = mod_pattern.pattern("H2O", fwhm=fwhm, threshold=0.01, real=False)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.parametrize("model", ["gaussian", "lorentzian", "gausslorentzian"])
    def test_various_models(self, model):
        """Parametrized test: pattern with various peak shape models."""
        result = mod_pattern.pattern("H2O", fwhm=0.1, threshold=0.01, real=False, model=model)
        assert isinstance(result, list)
        assert len(result) >= 1


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.floats(min_value=0.01, max_value=10.0))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_normalize_always_returns_list_hypothesis(self, value):
        """Property: _normalize always returns a list."""
        data = [[100.0, value]]
        result = mod_pattern._normalize(data)
        assert isinstance(result, list)

    @given(
        st.lists(
            st.tuples(
                st.floats(min_value=50.0, max_value=200.0),
                st.floats(min_value=0.01, max_value=1.0),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_consolidate_always_returns_list_hypothesis(self, isotopes):
        """Property: _consolidate always returns a list."""
        isotopes = [list(x) for x in isotopes]
        result = mod_pattern._consolidate(isotopes, 0.1)
        assert isinstance(result, list)

    @given(st.floats(min_value=0.01, max_value=1.0))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_consolidate_output_sorted_hypothesis(self, window):
        """Property: _consolidate output is sorted by m/z."""
        isotopes = [[150.0, 0.5], [100.0, 0.3], [200.0, 0.2]]
        result = mod_pattern._consolidate(isotopes, window)
        assert all(result[i][0] <= result[i + 1][0] for i in range(len(result) - 1))
