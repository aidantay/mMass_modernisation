import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mmass.mspy import mod_envfit, obj_peak, obj_peaklist


@pytest.fixture
def envfit_obj():
    """Returns EnvFit('H2O', 1, [0, 1])."""
    return mod_envfit.EnvFit("H2O", 1, [0, 1])


@pytest.fixture
def dummy_signal():
    """Returns np.array([[18.0, 100.0], [19.0, 50.0], [20.0, 10.0]])."""
    return np.array([[18.0, 100.0], [19.0, 50.0], [20.0, 10.0]])


class TestEnvFitInit:
    """Tests for EnvFit initialization and range setup."""

    def test_init_success(self):
        """Test successful initialization with standard parameters."""
        ef = mod_envfit.EnvFit("H2O", 1, [0, 1], loss="H", gain="H{2}")
        assert ef._lossFormula == "H-1"
        assert ef._gainFormula == "H{2}"
        assert ef.formula == "H2O"
        assert ef.charge == 1
        # Check mzrange is set and reasonable for H2O and H2O with H replaced by H2, charge 1
        # H2O + H+ = 19.018
        # H1 O1 H{2}1 + H+ = 20.024
        assert ef.mzrange[0] < 19.1
        assert ef.mzrange[1] > 19.9

    def test_init_invalid_compound(self, mocker):
        """Test initialization skip invalid compound."""
        # Mock obj_compound.compound
        mock_cls = mocker.patch("mmass.mspy.obj_compound.Compound")

        # 1st call: loss = obj_compound.Compound(loss) in __init__
        mock_loss = mocker.Mock()
        mock_loss.formula.return_value = "H-1"

        # 2nd call: Compound = obj_compound.Compound(item) for x=0 in _initModels
        mock_comp0 = mocker.Mock()
        mock_comp0.isvalid.return_value = True
        # _initRange calls min(scales) compound pattern
        mock_comp0.pattern.return_value = np.array([[19.0, 100.0]])

        # 3rd call: Compound = obj_compound.Compound(item) for x=1 in _initModels
        mock_comp1 = mocker.Mock()
        mock_comp1.isvalid.return_value = False  # Should skip this one

        mock_cls.side_effect = [mock_loss, mock_comp0, mock_comp1]

        ef = mod_envfit.EnvFit("H2O", 1, [0, 1])

        assert 0 in ef.models
        assert 1 not in ef.models
        assert len(ef.models) == 1

    def test_init_range(self):
        """Verify _initRange sets mzrange correctly."""
        # For H2O, charge 0, scales [0, 1]
        # x=0: H2O. mz ~ 18.01
        # x=1: H1 O1 H{2}1. mz ~ 19.017
        ef = mod_envfit.EnvFit("H2O", 0, [0, 1])
        # x1, x2 from pattern(fwhm=0.5)
        # H2O pattern[0][0] is 18.0105
        # H1 O1 H{2}1 pattern[0][0] is 19.0168
        # mzrange[0] = min(18.01, 19.01) * 0.999 = 17.99
        # mzrange[1] = max(18.01, 19.01) * 1.001 = 19.03
        assert 17.9 < ef.mzrange[0] < 18.1
        assert 19.0 < ef.mzrange[1] < 19.1


class TestEnvFitProcessing:
    """Tests for high-level data processing and fitting methods."""

    def test_topoints_list_input(self, envfit_obj):
        """Test topoints with points as a list [[19.02, 100.0]], check if ef.data is numpy.ndarray."""
        points = [[19.02, 100.0]]
        # For H2O, charge 1 (from fixture), 19.02 is within range.
        envfit_obj.topoints(points, autoAlign=False)
        assert isinstance(envfit_obj.data, np.ndarray)
        assert envfit_obj.data.shape == (1, 2)
        assert envfit_obj.data[0][0] == 19.02

    def test_topoints_outside_range(self, envfit_obj):
        """Test topoints with points that are outside ef.mzrange, check if it returns False."""
        # mzrange for H2O, charge 1 is roughly [18.9, 20.1]
        points = [[10.0, 100.0], [30.0, 50.0]]
        result = envfit_obj.topoints(points)
        assert result is False
        assert len(envfit_obj.data) == 0

    def test_topoints_autoAlign_false(self, mocker, envfit_obj):
        """Test topoints with autoAlign=False, verify _alignData is NOT called."""
        mocker.patch.object(envfit_obj, "_alignData")
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])

        # Needs valid point
        mz = envfit_obj.mzrange[0] + 0.1
        envfit_obj.topoints([[mz, 100.0]], autoAlign=False)

        envfit_obj._alignData.assert_not_called()

    def test_topoints_autoAlign_true(self, mocker, envfit_obj):
        """Test topoints with autoAlign=True, verify _alignData IS called."""
        mocker.patch.object(envfit_obj, "_alignData")
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])

        # Needs valid point
        mz = envfit_obj.mzrange[0] + 0.1
        envfit_obj.topoints([[mz, 100.0]], autoAlign=True)

        envfit_obj._alignData.assert_called_once()

    def test_topoints_leastSquare_zero(self, mocker, envfit_obj):
        """Test topoints where _leastSquare returns [0, 0] (for 2 models), check if it returns False."""
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0], [1.0]]), [0, 1]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[0.0, 0.0])

        mz = envfit_obj.mzrange[0] + 0.1
        result = envfit_obj.topoints([[mz, 100.0]])

        assert result is False

    def test_topoints_success(self, mocker, envfit_obj):
        """Test topoints with successful fit. Verify self.composition, self.ncomposition, self.average, and self.model."""
        # Mock models for x=0 and x=1
        # _makeModels returns (models_matrix, exchanged_list)
        # models_matrix should be (n_models, n_points)
        models_matrix = np.array([[0.8], [0.4]])  # 2 models, 1 point
        exchanged = [0, 1]
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(models_matrix, exchanged))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=np.array([100.0, 50.0]))

        mz = envfit_obj.mzrange[0] + 0.1
        points = [[mz, 120.0]]

        result = envfit_obj.topoints(points, autoAlign=False)

        assert result is True
        # sum(fit) = 150.0
        # f = 1/150.0
        # self.models[0][2] = 100.0, [3] = 100/150 = 2/3
        # self.models[1][2] = 50.0, [3] = 50/150 = 1/3
        assert envfit_obj.composition[0] == 100.0
        assert envfit_obj.composition[1] == 50.0
        assert pytest.approx(envfit_obj.ncomposition[0]) == 2.0 / 3.0
        assert pytest.approx(envfit_obj.ncomposition[1]) == 1.0 / 3.0

        # average = 0 * 2/3 + 1 * 1/3 = 1/3
        assert pytest.approx(envfit_obj.average) == 1.0 / 3.0

        # self.model = concat(raster, intensities)
        # intensities = sum(models * [[x] for x in fit], axis=0)
        # intensities = 0.8 * 100.0 + 0.4 * 50.0 = 80.0 + 20.0 = 100.0
        assert envfit_obj.model.shape == (1, 2)
        assert envfit_obj.model[0][0] == mz
        assert envfit_obj.model[0][1] == 100.0

    def test_envelope(self, mocker, envfit_obj):
        """Test envelope generation."""
        # Setup models with some abundances
        envfit_obj.models[0][1] = [(18.0, 1.0)]
        envfit_obj.models[0][2] = 100.0
        envfit_obj.models[1][1] = [(19.0, 1.0)]
        envfit_obj.models[1][2] = 50.0

        mock_profile = mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[18.0, 100.0], [19.0, 50.0]]))

        result = envfit_obj.envelope(points=20)

        assert isinstance(result, np.ndarray)
        # Verify mod_pattern.profile was called with merged isotopes
        # isotopes should be [(18.0, 100.0), (19.0, 50.0)]
        args, kwargs = mock_profile.call_args
        isotopes = args[0]
        assert (18.0, 100.0) in isotopes
        assert (19.0, 50.0) in isotopes
        assert kwargs["points"] == 20

    def test_topeaklist(self, mocker, envfit_obj):
        """Test topeaklist method."""
        mock_topoints = mocker.patch.object(envfit_obj, "topoints", return_value=True)

        pl = obj_peaklist.Peaklist()
        # Ensure peaks are within mzrange of envfit_obj (H2O, charge 1)
        # mzrange is roughly [19.0, 20.03]
        p1 = obj_peak.Peak(19.01, 100.0)
        p2 = obj_peak.Peak(20.01, 50.0)
        pl.append(p1)
        pl.append(p2)

        envfit_obj.topeaklist(pl, fwhm=0.2, forceFwhm=True)

        # Verify topoints was called with correct points
        assert mock_topoints.called
        _args, kwargs = mock_topoints.call_args
        points = kwargs["points"]
        assert points.shape == (2, 2)
        assert points[0][0] == 19.01
        assert points[0][1] == 100.0
        assert kwargs["fwhm"] == 0.2

    def test_tospectrum_baseline_none(self, envfit_obj, dummy_signal, mocker):
        """Test tospectrum with baseline=None."""
        # Mock mod_signal.locate to return indices for cropping
        mock_locate = mocker.patch("mmass.mspy.mod_signal.locate", side_effect=[0, len(dummy_signal)])

        # Mock mod_peakpicking.labelscan to return a mock peaklist
        mock_peaklist = mocker.Mock()
        mock_labelscan = mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)
        mock_topeaklist = mocker.patch.object(envfit_obj, "topeaklist", return_value=True)
        result = envfit_obj.tospectrum(dummy_signal, fwhm=0.2, baseline=None)

        # Verify mod_signal.locate calls for cropping
        assert mock_locate.call_count == 2

        # Verify mod_peakpicking.labelscan call
        # Use call_args to avoid ValueError with np array comparison in assert_called_once_with
        mock_labelscan.assert_called_once()
        _args, kwargs = mock_labelscan.call_args
        np.testing.assert_array_equal(kwargs["signal"], dummy_signal)
        assert kwargs["pickingHeight"] == 0.9
        assert kwargs["relThreshold"] == 0.0
        assert kwargs["baseline"] is None

        # Verify remshoulders call on the returned peaklist
        mock_peaklist.remshoulders.assert_called_once_with(fwhm=0.2)

        # Verify topeaklist call
        mock_topeaklist.assert_called_once_with(
            peaklist=mock_peaklist,
            fwhm=0.2,
            forceFwhm=True,
            autoAlign=True,
            iterLimit=None,
            relThreshold=0.0,
        )
        assert result is True

    def test_tospectrum_baseline_provided(self, envfit_obj, dummy_signal, mocker):
        """Test tospectrum with baseline provided."""
        # Mock dependencies to avoid side effects
        mocker.patch("mmass.mspy.mod_signal.locate", side_effect=[0, len(dummy_signal)])
        mock_peaklist = mocker.Mock()
        mock_labelscan = mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)
        mock_topeaklist = mocker.patch.object(envfit_obj, "topeaklist", return_value=True)

        # Mock mod_signal.subbase
        updated_spectrum = np.array([[18.0, 100.0]])
        mock_subbase = mocker.patch("mmass.mspy.mod_signal.subbase", return_value=updated_spectrum)

        # Use a list for baseline to avoid ValueError at 'if baseline != None:' in mod_envfit.py
        # subbase is mocked anyway, so it doesn't matter if it's a list or array here for the logic.
        baseline_list = [[18.0, 0.0], [19.0, 0.0], [20.0, 0.0]]
        result = envfit_obj.tospectrum(dummy_signal, baseline=baseline_list)

        # Verify mod_signal.subbase call
        mock_subbase.assert_called_once()
        args, _kwargs = mock_subbase.call_args
        np.testing.assert_array_equal(args[0], dummy_signal)
        assert args[1] == baseline_list

        # Verify mod_peakpicking.labelscan call with baseline
        mock_labelscan.assert_called_once()
        _, ls_kwargs = mock_labelscan.call_args
        assert ls_kwargs["baseline"] == baseline_list

        # Verify self.spectrum updated
        np.testing.assert_array_equal(envfit_obj.spectrum, updated_spectrum)

        # Verify remshoulders call on the returned peaklist
        mock_peaklist.remshoulders.assert_called_once_with(fwhm=0.1)

        # Verify topeaklist call
        mock_topeaklist.assert_called_once_with(
            peaklist=mock_peaklist,
            fwhm=0.1,
            forceFwhm=True,
            autoAlign=True,
            iterLimit=None,
            relThreshold=0.0,
        )
        assert result is True

    def test_topeaklist_list_input(self, mocker, envfit_obj):
        """Test topeaklist with list input."""
        mocker.patch.object(envfit_obj, "topoints", return_value=True)
        envfit_obj.topeaklist([[19.0, 100.0]], fwhm=0.2)
        assert envfit_obj.topoints.called

    def test_topeaklist_fwhm_from_basepeak(self, mocker, envfit_obj):
        """Test topeaklist getting fwhm from basepeak."""
        pl = obj_peaklist.Peaklist()
        p = obj_peak.Peak(19.01, 100.0)
        p.fwhm = 0.5
        pl.append(p)

        mock_topoints = mocker.patch.object(envfit_obj, "topoints", return_value=True)
        envfit_obj.topeaklist(pl, forceFwhm=False)

        # Verify topoints was called with fwhm=0.5
        kwargs = mock_topoints.call_args[1]
        assert kwargs["fwhm"] == 0.5

    def test_topoints_ndarray_input(self, mocker, envfit_obj):
        """Test topoints with ndarray input."""
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])

        mz = envfit_obj.mzrange[0] + 0.1
        points = np.array([[mz, 100.0]])
        envfit_obj.topoints(points, autoAlign=False)


class TestEnvFitInternals:
    """Tests for internal helper methods used for modeling and fitting."""

    def test_makeModels_raster_logic(self, mocker, envfit_obj):
        """Test _makeModels with raster logic and mz checks."""
        # H2O + H+ at ~19.018

        # 1. Trigger mz[0] > rasterMax (continue)
        raster = np.array([10.0, 11.0])  # rasterMax = 11.1
        models, exchanged = envfit_obj._makeModels(raster)
        assert len(models) == 0
        assert len(exchanged) == 0

        # 2. Trigger mz[1] < rasterMin (continue)
        raster = np.array([30.0, 31.0])  # rasterMin = 29.9
        models, exchanged = envfit_obj._makeModels(raster)
        assert len(models) == 0
        assert len(exchanged) == 0

        # 3. Trigger mz within raster (no continue)
        # Mock mod_pattern.profile to avoid the bug in mod_pattern.py (raster != None)
        mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[19.0, 1.0], [20.0, 1.0]]))
        raster = np.array([19.0, 20.0])
        models, exchanged = envfit_obj._makeModels(raster)
        assert len(models) > 0

    def test_makeModels_pattern_generation(self, mocker, envfit_obj):
        """Test _makeModels pattern generation and reset=False."""
        # Mock compound.pattern and mod_pattern.profile
        mock_pattern_call = mocker.patch("mmass.mspy.obj_compound.Compound.pattern", return_value=[(19.018, 1.0)])
        mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[19.018, 1.0]]))

        # Raster covering H2O
        raster = np.array([18.0, 19.0, 20.0])

        # 1. First call with reset=True (default)
        models, exchanged = envfit_obj._makeModels(raster, reset=True)
        assert len(models) == 2
        assert 0 in exchanged
        assert 1 in exchanged
        assert mock_pattern_call.call_count == 2  # 1 for scale 0, 1 for scale 1

        # 2. Second call with reset=False, should NOT call pattern again if already exists
        mock_pattern_call.reset_mock()
        models, exchanged = envfit_obj._makeModels(raster, reset=False)
        assert mock_pattern_call.call_count == 0

        # 3. Third call with reset=True, should call pattern again
        models, exchanged = envfit_obj._makeModels(raster, reset=True)
        assert mock_pattern_call.call_count == 2

    def test_makeModels_no_any_model(self, mocker, envfit_obj):
        """Test _makeModels when profile returns all zeros (model.any() is False)."""
        mocker.patch("mmass.mspy.obj_compound.Compound.pattern", return_value=[(19.018, 1.0)])

        # Return all zeros for profile
        mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[19.0, 0.0], [20.0, 0.0]]))

        raster = np.array([19.0, 20.0])
        models, exchanged = envfit_obj._makeModels(raster)

        # model.any() should be False for [0.0, 0.0]
        assert len(models) == 0
        assert len(exchanged) == 0

    def test_alignData_no_isotopes(self, mocker, envfit_obj):
        """Test _alignData when isotopes list is empty."""
        mocker.patch.object(envfit_obj, "_makeModels", return_value=([], []))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[])

        # Use valid data to get past earlier checks if any
        envfit_obj.data = np.array([[19.0, 100.0]])
        envfit_obj._alignData()
        # Should just return without errors
        assert True

    def test_alignData_calibrants(self, mocker, envfit_obj):
        """Test _alignData with various calibrant selection scenarios."""
        # Setup data and mocked models
        envfit_obj.data = np.array([[19.01, 100.0], [20.01, 50.0], [21.01, 25.0]])
        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])

        # Set pattern for models[0] so isotopes is not empty
        envfit_obj.models[0][1] = [(19.0, 1.0)]

        # Mock mod_pattern.profile
        mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[19.0, 100.0]]))

        # Mock mod_peakpicking.labelscan to return 3 peaks
        mock_peaklist = [
            obj_peak.Peak(19.0, 100.0),
            obj_peak.Peak(20.0, 50.0),
            obj_peak.Peak(21.0, 25.0),
        ]
        mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)

        # Mock mod_calibration.calibration
        # Return (lambda params, x: x + params[0], [0.0], 0.0)
        mock_cal = mocker.patch("mmass.mspy.mod_calibration.calibration", return_value=(lambda p, x: x + p[0], [0.01], 0.0))

        # 1. Test linear calibration (2 or 3 calibrants)
        envfit_obj._alignData()
        assert mock_cal.called
        assert mock_cal.call_args[1]["model"] == "linear"

        # 2. Test quadratic calibration (> 3 calibrants)
        mock_peaklist = [
            obj_peak.Peak(19.0, 100.0),
            obj_peak.Peak(20.0, 50.0),
            obj_peak.Peak(21.0, 25.0),
            obj_peak.Peak(22.0, 10.0),
        ]
        envfit_obj.data = np.array(
            [[19.01, 100.0], [20.01, 50.0], [21.01, 25.0], [22.01, 10.0]]
        )
        mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)
        envfit_obj._alignData()
        assert mock_cal.call_args[1]["model"] == "quadratic"

    def test_alignData_edge_cases(self, mocker, envfit_obj):
        """Test edge cases in _alignData calibrant selection loop."""
        # Data: [mz, intensity]
        envfit_obj.data = np.array(
            [
                [19.01, 100.0],  # Case B: new calibrant
                [19.02, 110.0],  # Case A: better calibrant (replaces 19.01)
                [20.50, 50.0],  # Case C: error > tolerance (break inner loop)
                [18.00, 10.0],  # Case D: error < -tolerance (continue inner loop)
            ]
        )

        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])
        mocker.patch("mmass.mspy.mod_pattern.profile", return_value=np.array([[19.0, 100.0]]))

        # Tolerance is self.fwhm/1.5 = 0.1/1.5 = 0.066
        # obj_peak.Peak(19.0, 100.0)
        # 19.01: error = 0.01 <= 0.066 -> Case B
        # 19.02: error = 0.02 <= 0.066 -> Case A (same peak, higher intensity)
        # 20.50: error = 1.5 > 0.066 -> Case C (break)

        # We need to make sure 18.00 is checked. If we have multiple peaks, we can trigger Case D.
        # Peak list sorted by m/z
        mock_peaklist = [obj_peak.Peak(19.0, 100.0), obj_peak.Peak(22.0, 50.0)]
        mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)
        mock_cal = mocker.patch("mmass.mspy.mod_calibration.calibration", return_value=(lambda p, x: x, [0.0], 0.0))

        envfit_obj._alignData()
        # Only 1 calibrant should be found because only 19.02 matches 19.0.
        # 22.0 doesn't match any point with tolerance.
        # If len(calibrants) <= 1, it returns.
        assert not mock_cal.called

    def test_leastSquare_convergence(self, mocker, envfit_obj):
        """Test _leastSquare with convergence and negative parameter handling."""
        # Data and models (1 point, 1 model)
        data = np.array([100.0])
        models = np.array([[1.0]])

        # Mock solveLinEq to return delta
        mocker.patch(
            "mmass.mspy.mod_envfit.solveLinEq",
            side_effect=[
                np.array([10.0]),   # 1st iteration: params=50+10=60
                np.array([-70.0]),  # 2nd iteration: params=60-70=-10 -> clipped to 0
                np.array([0.0]),    # 3rd iteration
            ],
        )

        # Mock _chiSquare
        # return [chisq_value, chisq_deriv], alpha
        mocker.patch.object(
            envfit_obj,
            "_chiSquare",
            side_effect=[
                ([1000.0, [100.0]], np.array([[1.0]])),  # Init
                ([500.0, [50.0]], np.array([[1.0]])),    # 1st loop (60)
                ([250.0, [25.0]], np.array([[1.0]])),    # 2nd loop (0)
                ([249.999, [20.0]], np.array([[1.0]])),  # 3rd loop (break)
            ],
        )

        res = envfit_obj._leastSquare(data, models, chiLimit=0.1)
        # Normf = 100/100 = 1.0. Next_params /= 1.0.
        # Result should be 0.0 after second iteration + clipped
        assert res[0] >= 0.0

    def test_leastSquare_divergence(self, mocker, envfit_obj):
        """Test _leastSquare when chi-square increases."""
        data = np.array([100.0])
        models = np.array([[1.0]])

        # Mock solveLinEq
        mocker.patch("mmass.mspy.mod_envfit.solveLinEq", return_value=np.array([10.0]))

        # Mock _chiSquare
        mocker.patch.object(
            envfit_obj,
            "_chiSquare",
            side_effect=[
                ([1000.0, [100.0]], np.array([[1.0]])),  # Init
                ([1200.0, [110.0]], np.array([[1.0]])),  # 1st loop: chisq increased!
                ([800.0, [50.0]], np.array([[1.0]])),    # 2nd loop: convergence
            ],
        )

        # 1st loop: next_chisq (1200) > chisq (1000). l = 5*l.
        # 2nd loop: next_chisq (800) < chisq (1000). chisq - next_chisq = 200 > chiLimit (0.1).
        # break on 3rd loop with small diff
        mocker.patch.object(
            envfit_obj,
            "_chiSquare",
            side_effect=[
                ([1000.0, [100.0]], np.array([[1.0]])),  # Init
                ([1200.0, [110.0]], np.array([[1.0]])),  # 1st loop
                ([800.0, [50.0]], np.array([[1.0]])),    # 2nd loop
                ([799.99, [40.0]], np.array([[1.0]])),   # 3rd loop (break)
            ],
        )

        res = envfit_obj._leastSquare(data, models, chiLimit=0.1)
        assert res is not None

    def test_leastSquare_iterLimit(self, mocker, envfit_obj):
        """Test _leastSquare with iterLimit."""
        data = np.array([100.0])
        models = np.array([[1.0]])

        mocker.patch("mmass.mspy.mod_envfit.solveLinEq", return_value=np.array([1.0]))

        # Always returning smaller chi-square but large enough difference to not break
        mocker.patch.object(envfit_obj, "_chiSquare", return_value=([1000.0, [10.0]], np.array([[1.0]])))

        # Force many iterations by returning slightly smaller chisq each time
        chisqs = [([1000.0 - i, [10.0]], np.array([[1.0]])) for i in range(10)]
        mocker.patch.object(envfit_obj, "_chiSquare", side_effect=chisqs)

        res = envfit_obj._leastSquare(data, models, iterLimit=2)
        assert res is not None

    def test_chiSquare(self, envfit_obj):
        """Test _chiSquare calculation."""
        data = np.array([100.0, 50.0])
        models = np.array([[1.0, 0.0], [0.0, 1.0]])
        params = [90.0, 40.0]

        # differences = sum([[1,0],[0,1]] * [[90],[40]], axis=0) - [100, 50]
        # differences = [90, 40] - [100, 50] = [-10, -10]
        # chisq_value = (-10)**2 + (-10)**2 = 100 + 100 = 200

        chisq, alpha = envfit_obj._chiSquare(data, models, params)

        assert chisq[0] == 200.0
        # chisq_deriv: for x=0 (mz=0), data=100, models=[1,0], diff=-10. deriv=[1,0]. chisq_deriv += -20 * [1,0] = [-20, 0]
        # for x=1 (mz=1), data=50, models=[0,1], diff=-10. deriv=[0,1]. chisq_deriv += -20 * [0,1] = [-20, -20]
        assert chisq[1] == [-20.0, -20.0]
        # alpha: x=0, d=[1,0]. d[:,newaxis]*d = [[1,0],[0,0]]. alpha = [[1,0],[0,0]]
        # x=1, d=[0,1]. d[:,newaxis]*d = [[0,0],[0,1]]. alpha = [[1,0],[0,1]]
        assert np.array_equal(alpha, np.array([[1.0, 0.0], [0.0, 1.0]]))

    def test_alignData_multiple_points_per_peak(self, mocker, envfit_obj):
        """Test _alignData with multiple points matching same peak."""
        # Data: two points at 19.0, second one is more intense
        # calibrants[-1][0] == peak.mz is point[0] == peak.mz
        envfit_obj.data = np.array([[19.0, 100.0], [19.0, 200.0], [20.0, 50.0]])
        envfit_obj.spectrum = np.array([[19.0, 100.0], [20.0, 50.0]])

        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])
        envfit_obj.models[0][1] = [(19.0, 1.0), (20.0, 0.5)]

        mock_peaklist = [obj_peak.Peak(19.0, 100.0), obj_peak.Peak(20.0, 50.0)]
        mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)

        mock_cal = mocker.patch("mmass.mspy.mod_calibration.calibration", return_value=(lambda p, x: x, [0.0], 0.0))

        envfit_obj._alignData()
        assert mock_cal.called
        # verify calibrants list passed to calibration
        # Should have [(19.0, 19.0), (20.0, 20.0)]
        args = mock_cal.call_args[0]
        calibrants = args[0]
        assert len(calibrants) == 2
        assert calibrants[0] == (
            19.0,
            19.0,
        )  # Replaced by the second point (19.0, 200.0)

    def test_alignData_too_few_calibrants(self, mocker, envfit_obj):
        """Test _alignData with too few calibrants."""
        envfit_obj.data = np.array([[19.01, 100.0]])
        envfit_obj.models[0][1] = [(19.0, 1.0)]

        mocker.patch.object(envfit_obj, "_makeModels", return_value=(np.array([[1.0]]), [0]))
        mocker.patch.object(envfit_obj, "_leastSquare", return_value=[1.0])
        mock_peaklist = [obj_peak.Peak(19.0, 100.0)]
        mocker.patch("mmass.mspy.mod_peakpicking.labelscan", return_value=mock_peaklist)
        mock_cal = mocker.patch("mmass.mspy.mod_calibration.calibration")

        envfit_obj._alignData()
        mock_cal.assert_not_called()


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @settings(deadline=1000)
    @given(
        formula=st.sampled_from(["H2O", "C6H12O6", "NH3"]),
        charge=st.integers(min_value=0, max_value=1),
        scales=st.lists(
            st.integers(min_value=0, max_value=1), min_size=1, max_size=2, unique=True
        ),
        loss=st.just("H"),
        gain=st.just("H{2}"),
    )
    def test_init_robustness(self, formula, charge, scales, loss, gain):
        """Property-based test for envfit initialization."""
        # This should not raise any unhandled exceptions for these standard inputs
        ef = mod_envfit.EnvFit(formula, charge, scales, loss=loss, gain=gain)
        assert isinstance(ef, mod_envfit.EnvFit)
        assert len(ef.models) <= len(scales)
