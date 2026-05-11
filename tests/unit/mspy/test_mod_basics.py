import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mmass.mspy import mod_basics, obj_compound


class TestDelta:
    """Tests for the delta function which calculates mass differences in various units."""

    @pytest.mark.parametrize(
        ("measured", "counted", "unit", "expected"),
        [
            (1000.1, 1000.0, "ppm", 100.0),
            (1000.1, 1000.0, "Da", 0.1),
            (1000.1, 1000.0, "%", 0.01),
            (500.0, 1000.0, "ppm", -500000.0),
            (1001.0, 1000.0, "ppm", 1000.0),
            (1000.0, 1000.0, "ppm", 0.0),
        ],
    )
    def test_delta_units(self, measured, counted, unit, expected):
        """Test delta calculation with different units (ppm, Da, %)."""
        # Arrange
        # Handled by parametrize

        # Act
        result = mod_basics.delta(measured, counted, units=unit)

        # Assert
        assert result == pytest.approx(expected)

    def test_delta_invalid_unit(self):
        """Test that an invalid unit raises a ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown units for delta!"):
            mod_basics.delta(1000.0, 1000.0, units="invalid")


class TestNominalMass:
    """Tests for the nominalmass function with various rounding strategies."""

    @pytest.mark.parametrize(
        ("mass", "rounding", "expected"),
        [
            (1.1, "floor", 1.0),
            (1.9, "floor", 1.0),
            (1.1, "ceil", 2.0),
            (1.9, "ceil", 2.0),
            (1.1, "round", 1.0),
            (1.9, "round", 2.0),
            (1.5, "round", 2.0),
            (-1.1, "floor", -2.0),
            (-1.9, "floor", -2.0),
            (-1.1, "ceil", -1.0),
            (-1.9, "ceil", -1.0),
            (-1.1, "round", -1.0),
            (-1.9, "round", -2.0),
            (-1.5, "round", -2.0),
        ],
    )
    def test_nominalmass_rounding(self, mass, rounding, expected):
        """Test nominal mass calculation with different rounding methods."""
        # Arrange
        # Handled by parametrize

        # Act
        result = mod_basics.nominalmass(mass, rounding=rounding)

        # Assert
        assert result == expected

    def test_nominalmass_invalid_rounding(self):
        """Test that an invalid rounding method raises a ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown nominal mass rounding!"):
            mod_basics.nominalmass(1.5, rounding="invalid")


class TestMassDefect:
    """Tests for the md function which calculates various types of mass defects."""

    @pytest.mark.parametrize(
        ("md_type", "rounding", "expected"),
        [
            ("fraction", "floor", 0.12345),
            ("standard", "floor", 0.12345),
            ("standard", "ceil", -0.87655),             # 1000.12345 - 1001.0
            ("relative", "floor", 123.43476),  # 1e6 * (1000.12345 - 1000.0) / 1000.12345
        ],
        ids=["fraction", "standard_floor", "standard_ceil", "relative_floor"],
    )
    def test_md_types(self, md_type, rounding, expected):
        """Test standard, fraction, and relative mass defect types."""
        # Arrange
        mass = 1000.12345

        # Act
        res = mod_basics.md(mass, mdType=md_type, rounding=rounding)

        # Assert
        assert res == pytest.approx(expected)

    @pytest.mark.parametrize("kendrickFormula", ["CH2", obj_compound.Compound("CH2")])
    def test_md_kendrick(self, kendrickFormula):
        """Test Kendrick mass defect with both formula string and Compound object."""
        # Arrange
        mass = 1000.12345
        ch2 = obj_compound.Compound("CH2")
        kf = float(ch2.nominalmass()) / ch2.mass(0)
        expected_km = mod_basics.nominalmass(mass * kf, "floor") - (mass * kf)

        # Act
        result = mod_basics.md(mass, mdType="kendrick", kendrickFormula=kendrickFormula)

        # Assert
        assert result == pytest.approx(expected_km, abs=1e-7)

    def test_md_invalid_type(self):
        """Test that an invalid mass defect type raises a ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown mass defect type!"):
            mod_basics.md(1000.0, mdType="invalid")


class TestMZ:
    """Tests for the mz function which calculates m/z from neutral mass or vice versa."""

    @pytest.fixture
    def h_agent_mass(self):
        """Calculate the mass of a proton (hydrogen agent minus electron)."""
        h = obj_compound.Compound("H")
        h_mass = h.mass()
        return (
            h_mass[0] - mod_basics.ELECTRON_MASS,
            h_mass[1] - mod_basics.ELECTRON_MASS,
        )

    @pytest.mark.parametrize(
        "input_mass",
        [
            1000.0,
            (1000.0, 1000.1),
        ],
        ids=["float_mass", "tuple_mass"],
    )
    def test_mz_charge_zero(self, input_mass):
        """Test that charge zero returns the neutral mass unchanged."""
        # Arrange
        # Handled by parametrize

        # Act
        res_mass = mod_basics.mz(input_mass, 0)

        # Assert
        assert res_mass == input_mass

    def test_mz_current_charge_float(self, h_agent_mass):
        """Test calculation of neutral mass from a charged species (float input)."""
        # Arrange
        z = 1
        mass = 1000.0
        expected = mass * abs(z) - h_agent_mass[0] * (z / 1.0)

        # Act
        res_neutral = mod_basics.mz(mass, 0, currentCharge=z, agentFormula="H")

        # Assert
        assert res_neutral == pytest.approx(expected)

    def test_mz_current_charge_tuple(self, h_agent_mass):
        """Test calculation of neutral mass from a charged species (tuple input)."""
        # Arrange
        z = 1
        mass = (1000.0, 1000.0)
        expected = (
            mass[0] * abs(z) - h_agent_mass[0] * (z / 1.0),
            mass[1] * abs(z) - h_agent_mass[1] * (z / 1.0)
        )

        # Act
        res_neutral = mod_basics.mz(mass, 0, currentCharge=z, agentFormula="H")

        # Assert
        assert res_neutral == pytest.approx(expected)

    @pytest.mark.parametrize(
        "input_mass",
        [
            (1000.0, 1000.1),
            [1000.0, 1000.1],
        ],
        ids=["tuple_mass", "list_mass"],
    )
    def test_mz_mass_types(self, h_agent_mass, input_mass):
        """Test that the mz function handles tuple and list mass inputs."""
        # Arrange
        expected = (
            (1000.0 + h_agent_mass[0]) / 1.0,
            (1000.1 + h_agent_mass[1]) / 1.0
        )

        # Act
        res = mod_basics.mz(input_mass, 1)

        # Assert
        assert res == pytest.approx(expected)

    @pytest.mark.parametrize(
        "agent_input",
        [
            "H",
            obj_compound.Compound("H"),
        ],
        ids=["string", "compound"]
    )
    def test_mz_ionization_agent(self, h_agent_mass, agent_input):
        """Test m/z calculation with a string or Compound ionization agent."""
        # Arrange
        mass = 1000.0
        charge = 1
        agent_charge = 1
        expected = (mass + h_agent_mass[0]) / abs(charge)

        # Act
        res = mod_basics.mz(mass, charge, agentFormula=agent_input, agentCharge=agent_charge)

        # Assert
        assert res == pytest.approx(expected)

    def test_mz_ionization_agent_electron(self):
        """Test m/z calculation with an electron ionization agent."""
        # Arrange
        mass = 1000.0
        charge = -1
        agent_charge = -1
        agent_input = "e"
        expected = (mass + mod_basics.ELECTRON_MASS * abs(charge)) / abs(charge)

        # Act
        res = mod_basics.mz(mass, charge, agentFormula=agent_input, agentCharge=agent_charge)

        # Assert
        assert res == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("mass_type", "expected_index"),
        [
            (0, 0),
            (1, 1),
        ],
        ids=["monoisotopic", "average"],
    )
    def test_mz_massType(self, h_agent_mass, mass_type, expected_index):
        """Test specifying whether to use monoisotopic (0) or average (1) mass."""
        # Arrange
        mass = 1000.0

        # Act
        res = mod_basics.mz(mass, 1, massType=mass_type)

        # Assert
        assert res == pytest.approx(mass + h_agent_mass[expected_index])


class TestRDBE:
    """Tests for the rdbe function (Ring and Double Bond Equivalents)."""

    @pytest.mark.parametrize(
        ("input_formula", "expected_rdbe"),
        [
            ("C6H6", 4.0),
            ("C6H12", 1.0),
            ("H2O", 0.0),
            (obj_compound.Compound("C6H6"), 4.0),
            ("C{12}C{13}", 3.0),
            ("He", 1.0),
        ],
        ids=["benzene", "cyclohexane", "water", "compound_obj", "duplicate_isotopes", "zero_valence"],
    )
    def test_rdbe(self, input_formula, expected_rdbe):
        """Test RDBE calculation for standard organic compounds, duplicate isotopes, and zero valence elements."""
        # Arrange
        # Handled by parametrize

        # Act
        result = mod_basics.rdbe(input_formula)

        # Assert
        assert result == pytest.approx(expected_rdbe)


class TestFormulaRules:
    """Tests for the frules function which applies chemical formula validation rules."""

    @pytest.mark.parametrize(
        ("formula", "rules", "expected"),
        [
            # --- HC Rules ---
            ("C6H6", ["HC"], True),
            ("C20H1", ["HC"], False),
            ("CH4", ["HC"], False),

            # --- NOPSC Rules ---
            ("C10N2O2P2S2", ["NOPSC"], True),
            ("CN5", ["NOPSC"], False),
            ("CO4", ["NOPSC"], False),
            ("CP3", ["NOPSC"], False),
            ("CS4", ["NOPSC"], False),

            # --- NOPS Boundaries ---
            ("C10N2O2P2S2", ["NOPS"], True),
            ("C10N4O4P4", ["NOPS"], True),
            ("C10N10O2P2S2", ["NOPS"], False),
            ("C10N2O20P2S2", ["NOPS"], False),
            ("C10N2O2P4S2", ["NOPS"], False),
            ("C10N2O2P2S3", ["NOPS"], False),
            ("C10N11O4P4", ["NOPS"], False),
            ("C10N4O22P4", ["NOPS"], False),
            ("C10N4O4P6", ["NOPS"], False),
            ("C10N19O2S2", ["NOPS"], False),
            ("C10N2O14S2", ["NOPS"], False),
            ("C10N2O2S8", ["NOPS"], False),
            ("C10N3P2S2", ["NOPS"], False),
            ("C10N2P3S2", ["NOPS"], False),
            ("C10N2P2S3", ["NOPS"], False),
            ("C10O14P2S2", ["NOPS"], False),
            ("C10O2P3S2", ["NOPS"], False),
            ("C10O2P2S3", ["NOPS"], False),

            # --- RDBE & Mixed Rules ---
            ("C6H6", ["RDBE"], True),
            ("C41H2", ["RDBE"], False),
            ("H6", ["RDBE"], False),
            ("C6H6", ["RDBEInt"], True),
            ("C6H7", ["RDBEInt"], False),
            ("C6H7", ["HC", "NOPSC", "RDBE"], True),

            # --- Object Instance Support ---
            (obj_compound.Compound("C6H6"), ["HC", "NOPSC", "NOPS", "RDBE", "RDBEInt"], True),
        ],
        ids=[
            "hc_pass", "hc_fail_low", "hc_fail_high",
            "nopsc_pass", "nopsc_fail_n", "nopsc_fail_o", "nopsc_fail_p", "nopsc_fail_s",
            "nops_pass", "nops_pass_branch_261", "nops_fail_n1", "nops_fail_o1", "nops_fail_p1", "nops_fail_s1",
            "nops_fail_n2", "nops_fail_o2", "nops_fail_p2", "nops_fail_n3", "nops_fail_o3", "nops_fail_s2",
            "nops_fail_n4", "nops_fail_p3", "nops_fail_s3", "nops_fail_o4", "nops_fail_p4", "nops_fail_s4",
            "rdbe_pass", "rdbe_fail_c41h2", "rdbe_fail_h6", "rdbeint_pass", "rdbeint_fail", "mixed_rules_pass",
            "compound_object_pass"
        ]
    )
    def test_frules_validation(self, formula, rules, expected):
        """Test formula validations across all rule types and data inputs."""
        # Arrange
        # Handled by parametrize

        # Act
        result = mod_basics.frules(formula, rules=rules)

        # Assert
        assert result is expected

    @pytest.mark.parametrize(
        ("rules", "rdbe_range", "expected"),
        [
            (["HC", "NOPSC", "NOPS", "RDBE", "RDBEInt"], (-1000, 1000), True),
            (["RDBE"], (1, 10), False),
        ],
        ids=["pass_all", "fail_rdbe"]
    )
    def test_frules_carbonless(self, rules, rdbe_range, expected):
        """Test that carbon-less compounds are handled correctly in formula rules."""
        # Arrange
        # Handled by parametrize

        # Act
        result = mod_basics.frules("H2O", rules=rules, RDBE=rdbe_range)

        # Assert
        assert result is expected


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        measured=st.floats(
            min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        counted=st.floats(
            min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
    )
    def test_delta_ppm_hypothesis(self, measured, counted):
        """Property-based test for delta in ppm."""
        res = mod_basics.delta(measured, counted, units="ppm")
        expected = (measured - counted) / counted * 1000000
        assert res == pytest.approx(expected)

    @given(
        mass=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        rounding=st.sampled_from(["floor", "ceil", "round"]),
    )
    def test_nominalmass_hypothesis(self, mass, rounding):
        """Property-based test for nominal mass calculation."""
        res = mod_basics.nominalmass(mass, rounding=rounding)
        if rounding == "floor":
            assert res == math.floor(mass)
        elif rounding == "ceil":
            assert res == math.ceil(mass)
        elif rounding == "round":
            assert res == round(mass)
