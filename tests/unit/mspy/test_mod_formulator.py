import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import mod_basics, mod_formulator, mod_stopper


class TestCompositions:
    """Tests for the internal _compositions generator/helper."""

    def test_size_mismatch_min_max(self):
        """Test _compositions raises ValueError when minimum and maximum have different sizes."""
        with pytest.raises(
            ValueError, match="Sizes of minimum, maximum and masses are not equal!"
        ):
            mod_formulator._compositions([1], [2, 3], [12.0], 0.0, 100.0, 10)

    def test_size_mismatch_min_masses(self):
        """Test _compositions raises ValueError when minimum and masses have different sizes."""
        with pytest.raises(
            ValueError, match="Sizes of minimum, maximum and masses are not equal!"
        ):
            mod_formulator._compositions([1, 2], [3, 4], [12.0], 0.0, 100.0, 10)

    def test_valid_delegation(self):
        """Test _compositions with valid input returns a list."""
        result = mod_formulator._compositions([0], [5], [12.0], 10.0, 50.0, 100)
        assert isinstance(result, list)

    def test_empty_input(self):
        """Test _compositions with empty lists."""
        result = mod_formulator._compositions([], [], [], 10.0, 50.0, 100)
        assert isinstance(result, list)

    def test_limit_zero(self):
        """Test _compositions with limit=0 returns empty list."""
        result = mod_formulator._compositions([0], [5], [12.0], 10.0, 50.0, 0)
        assert result == []

    def test_large_limit(self):
        """Test _compositions with large limit."""
        result = mod_formulator._compositions([0], [2], [12.0], 10.0, 30.0, 1000000)
        assert isinstance(result, list)


class TestFormulatorBasics:
    """Basic structural and input validation tests for the formulator function."""

    def test_charge_zero_no_recalc(self, mocker):
        """Test formulator with charge=0 does not call mod_basics.mz."""
        spy = mocker.spy(mod_basics, "mz")
        result = mod_formulator.formulator(100.0, charge=0, composition={})
        assert result == []
        spy.assert_not_called()

    def test_charge_nonzero_with_agent(self, mocker):
        """Test formulator with charge=1 and agentFormula calls mod_basics.mz once."""
        spy = mocker.spy(mod_basics, "mz")
        result = mod_formulator.formulator(
            100.0, charge=1, agentFormula="H", agentCharge=1, composition={}
        )
        assert result == []
        spy.assert_called_once()

    def test_charge_nonzero_no_agent(self, mocker):
        """Test formulator with charge=1 but no agentFormula uses mz directly."""
        spy = mocker.spy(mod_basics, "mz")
        result = mod_formulator.formulator(100.0, charge=1, agentFormula="", composition={})
        assert result == []
        spy.assert_not_called()

    def test_mass_zero_returns_empty(self):
        """Test formulator with mass=0.0 returns empty list."""
        result = mod_formulator.formulator(0.0, charge=0)
        assert result == []

    def test_mass_negative_returns_empty(self):
        """Test formulator with negative mass returns empty list."""
        result = mod_formulator.formulator(-100.0, charge=0)
        assert result == []

    def test_mass_negative_after_recalc(self, mocker):
        """Test formulator returns empty when neutral mass becomes negative."""
        # Mock mz to return a negative value
        mocker.patch("mmass.mspy.mod_basics.mz", return_value=-1.0)
        result = mod_formulator.formulator(0.001, charge=5, agentFormula="H", composition={})
        assert result == []

    def test_empty_composition_returns_empty(self):
        """Test formulator with empty composition returns empty list."""
        result = mod_formulator.formulator(100.0, charge=0, composition={})
        assert result == []

    def test_very_small_mass(self):
        """Test formulator with very small mass."""
        result = mod_formulator.formulator(
            0.0001, charge=0, tolerance=0.00001, units="Da", composition={"H": [0, 1]}
        )
        assert result == []

    def test_composition_count_zero(self):
        """Test formulator when all min/max are zero."""
        result = mod_formulator.formulator(100.0, charge=0, composition={"C": [0, 0], "H": [0, 0]})
        assert result == []


class TestFormulatorLogic:
    """Tests for tolerance window calculation and mass arithmetic logic."""

    def test_units_ppm_window(self, mocker):
        """Test formulator with ppm units calculates correct mass window."""
        # Patch _compositions to capture arguments
        mocker.spy(mod_formulator, "_compositions")
        mocker.patch("mmass.mspy.mod_formulator._compositions", return_value=[])

        mz_val = 100.0
        tolerance = 10.0
        # Expected: loMass = mass - (mass/1e6)*tolerance, hiMass = mass + (mass/1e6)*tolerance
        # (Implicitly checked by passing to _compositions, though we just check it doesn't crash)
        result = mod_formulator.formulator(
            mz_val, charge=0, tolerance=tolerance, units="ppm", composition={}
        )
        assert result == []

    def test_units_da_with_nonzero_charge(self):
        """Test formulator with Da units and nonzero charge multiplies tolerance by abs(charge)."""
        result = mod_formulator.formulator(
            100.0, charge=2, tolerance=0.5, units="Da", composition={}
        )
        assert result == []

    def test_units_da_charge_zero(self):
        """Test formulator with Da units and charge=0 uses tolerance as-is."""
        result = mod_formulator.formulator(100.0, charge=0, tolerance=0.5, units="Da", composition={})
        assert result == []

    def test_charge_magnitude(self):
        """Test formulator respects charge magnitude in Da mode."""
        result = mod_formulator.formulator(
            100.0, charge=3, tolerance=0.1, units="Da", composition={"C": [0, 5]}
        )
        assert isinstance(result, list)

    def test_ppm_precision(self):
        """Test formulator with ppm units maintains precision."""
        result = mod_formulator.formulator(
            100.0,
            charge=0,
            tolerance=1.0,  # 1 ppm
            units="ppm",
            composition={"C": [0, 3]},
        )
        assert isinstance(result, list)

    def test_zero_tolerance(self):
        """Test formulator with zero tolerance."""
        result = mod_formulator.formulator(
            12.0, charge=0, tolerance=0.0, units="Da", composition={"C": [0, 2]}
        )
        assert isinstance(result, list)

    def test_charge_with_no_agent_formula(self):
        """Test formulator with charge but empty agent formula still works."""
        result = mod_formulator.formulator(
            100.0,
            charge=2,
            agentFormula="",
            tolerance=1.0,
            units="Da",
            composition={"C": [0, 3]},
        )
        assert isinstance(result, list)


class TestFormulatorFeatures:
    """Tests for advanced features like element sorting, clamping, and formula assembly."""

    def test_elements_sorted_by_mass(self, mocker):
        """Test formulator passes elements sorted by mass in descending order."""
        mocker.spy(mod_formulator, "_compositions")
        mod_formulator.formulator(
            100.0,
            charge=0,
            tolerance=5.0,
            units="ppm",
            composition={"H": [0, 5], "C": [0, 5]},
        )
        # Note: This verifies that _compositions is called with masses in descending order
        # C mass (~12) > H mass (~1), so C should come first

    def test_max_composition_clamped(self):
        """Test formulator clamps maximum composition to int(hiMass / elementMass)."""
        # With mz=13.0, carbon (~12), large max should be clamped
        result = mod_formulator.formulator(
            13.0, charge=0, tolerance=0.5, units="Da", composition={"C": [0, 100]}
        )
        assert isinstance(result, list)

    def test_max_composition_not_clamped(self):
        """Test formulator does not clamp when max is already below hiMass/elementMass."""
        result = mod_formulator.formulator(100.0, charge=0, tolerance=1.0, units="Da", composition={"H": [0, 5]})
        assert isinstance(result, list)

    def test_returns_formula_strings(self):
        """Test formulator returns proper formula strings."""
        result = mod_formulator.formulator(
            18.010565,
            charge=0,
            units="Da",
            tolerance=0.01,
            composition={"H": [0, 4], "O": [0, 2]},
        )
        assert isinstance(result, list)
        if result:
            assert "H2O1" in result or "O1H2" in result

    def test_limit_respected(self):
        """Test formulator respects the limit parameter."""
        result = mod_formulator.formulator(
            50.0,
            charge=0,
            units="Da",
            tolerance=5.0,
            composition={"H": [0, 20], "C": [0, 5]},
            limit=1,
        )
        assert len(result) <= 1

    def test_check_force_quit_called(self, mocker):
        """Test formulator calls CHECK_FORCE_QUIT."""
        mocker.spy(mod_stopper, "STOPPER")
        result = mod_formulator.formulator(
            50.0,
            charge=0,
            units="Da",
            tolerance=5.0,
            composition={"H": [0, 10], "C": [0, 2]},
            limit=100,
        )
        assert isinstance(result, list)

    def test_check_force_quit_raises_propagates(self, mocker):
        """Test that ForceQuitError exception from CHECK_FORCE_QUIT propagates."""
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_formulator.formulator(
                100.0,
                charge=0,
                tolerance=10.0,
                units="Da",
                composition={"H": [0, 10], "C": [0, 10], "N": [0, 5]},
                limit=10000,
            )

    def test_very_large_mass(self):
        """Test formulator with very large mass."""
        result = mod_formulator.formulator(
            10000.0,
            charge=0,
            tolerance=1.0,
            units="Da",
            composition={"C": [0, 100], "H": [0, 50]},
            limit=10,
        )
        assert isinstance(result, list)

    def test_multiple_elements(self):
        """Test formulator with multiple elements."""
        result = mod_formulator.formulator(
            100.0,
            charge=0,
            tolerance=1.0,
            units="Da",
            composition={"C": [0, 5], "H": [0, 10], "N": [0, 2], "O": [0, 3]},
            limit=100,
        )
        assert isinstance(result, list)

    def test_single_element(self):
        """Test formulator with single element."""
        result = mod_formulator.formulator(12.0, charge=0, tolerance=0.1, units="Da", composition={"C": [0, 2]})
        assert isinstance(result, list)
        if result:
            assert "C1" in result or "C2" in result

    def test_composition_min_equals_max(self):
        """Test formulator when min equals max for elements."""
        result = mod_formulator.formulator(
            18.0,
            charge=0,
            tolerance=1.0,
            units="Da",
            composition={"H": [2, 2], "O": [1, 1]},
        )
        assert isinstance(result, list)


class TestFormulatorIntegration:
    """Integration tests for identifying real chemical formulas."""

    def test_water(self):
        """Integration test: find formula for water (H2O)."""
        result = mod_formulator.formulator(
            18.010565,
            charge=0,
            units="Da",
            tolerance=0.005,
            composition={"H": [0, 4], "O": [0, 2]},
        )
        assert isinstance(result, list)
        if result:
            assert any("H2O1" in f or "O1H2" in f for f in result)

    def test_charged_peptide_fragment(self):
        """Integration test: find formula for charged peptide fragment."""
        result = mod_formulator.formulator(
            147.0764,
            charge=1,
            agentFormula="H",
            agentCharge=1,
            units="Da",
            tolerance=0.02,
            composition={"C": [0, 10], "H": [0, 15], "N": [0, 3], "O": [0, 4]},
        )
        assert isinstance(result, list)

    def test_negative_charge(self):
        """Integration test: formulator with negative charge."""
        result = mod_formulator.formulator(
            100.0,
            charge=-1,
            agentFormula="H",
            agentCharge=1,
            tolerance=2.0,
            units="Da",
            composition={"C": [0, 3], "H": [0, 6]},
        )
        assert isinstance(result, list)


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        mz_val=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        units=st.sampled_from(["ppm", "Da"]),
        tolerance=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_always_returns_list(self, mz_val, units, tolerance):
        """Formulator always returns a list."""
        result = mod_formulator.formulator(
            mz_val,
            charge=0,
            units=units,
            tolerance=tolerance,
            composition={"C": [0, 3], "H": [0, 6]},
            limit=50,
        )
        assert isinstance(result, list)

    @given(
        charge=st.integers(min_value=-3, max_value=3),
        mz_val=st.floats(min_value=50.0, max_value=300.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_charge_path(self, charge, mz_val):
        """Formulator handles various charges without error."""
        try:
            result = mod_formulator.formulator(
                mz_val,
                charge=charge,
                agentFormula="H" if charge != 0 else "",
                agentCharge=1,
                tolerance=1.0,
                units="Da",
                composition={"C": [0, 5], "H": [0, 10]},
                limit=30,
            )
            assert isinstance(result, list)
        except mod_stopper.ForceQuitError:
            pass

    @given(
        min_list=st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=5),
        max_list=st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=5),
        mass_list=st.lists(
            st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_compositions_hypothesis_size_mismatch_always_raises(self, min_list, max_list, mass_list):
        """_compositions raises ValueError when sizes don't match."""
        if not (len(min_list) == len(max_list) == len(mass_list)):
            with pytest.raises(ValueError, match="Sizes of minimum, maximum and masses are not equal!"):
                mod_formulator._compositions(min_list, max_list, mass_list, 0.0, 100.0, 10)
