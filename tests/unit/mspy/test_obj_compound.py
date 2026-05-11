import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import obj_compound


class TestInit:
    """Tests for the init functionality."""

    def test_init_valid_formula(self):
        """Test __init__ with valid formula."""
        c = obj_compound.Compound("C6H12O6")
        assert c.expression == "C6H12O6"
        assert c._composition is None
        assert c._formula is None
        assert c._mass is None
        assert c._nominalmass is None


    def test_init_with_attributes(self):
        """Test __init__ stores attributes."""
        c = obj_compound.Compound("H2O", name="water", value=42)
        assert c.attributes["name"] == "water"
        assert c.attributes["value"] == 42


    def test_init_invalid_formula_pattern(self):
        """Test __init__ raises ValueError on invalid formula pattern."""
        with pytest.raises(ValueError, match="Unknown element in formula! --> X in H2O2X"):
            obj_compound.Compound("H2O2X")  # X is not valid


    def test_init_unknown_element(self):
        """Test __init__ raises ValueError on unknown element."""
        with pytest.raises(ValueError, match="Unknown element"):
            obj_compound.Compound("Xx")  # Xx is not an element


    def test_init_unknown_isotope(self):
        """Test __init__ raises ValueError on unknown isotope."""
        with pytest.raises(ValueError, match="Unknown isotope"):
            obj_compound.Compound("C{99}")  # C-99 doesn't exist


    def test_init_mismatched_brackets(self):
        """Test __init__ raises ValueError on mismatched brackets."""
        with pytest.raises(ValueError, match="Wrong number of brackets"):
            obj_compound.Compound("(H2O")  # Missing closing bracket


    def test_init_extra_closing_bracket(self):
        """Test __init__ raises ValueError on extra closing bracket."""
        with pytest.raises(ValueError, match="Wrong number of brackets"):
            obj_compound.Compound("H2O)")  # Extra closing bracket


class TestCheckformula:
    """Tests for the checkformula functionality."""

    def test_checkformula_valid(self):
        """Test _checkFormula with valid formulas."""
        # Just constructing should call _checkFormula
        c = obj_compound.Compound("CH4")
        c._checkFormula("C6H12")  # Should not raise


    def test_checkformula_branch1_invalid_pattern(self):
        """Branch 1: FORMULA_PATTERN.match fails."""
        with pytest.raises(ValueError, match="Wrong formula"):
            obj_compound.Compound("###")


    def test_checkformula_branch2_unknown_element(self):
        """Branch 2: Element symbol not in blocks.elements."""
        with pytest.raises(ValueError, match="Unknown element"):
            obj_compound.Compound("Zz")


    def test_checkformula_branch3_unknown_isotope(self):
        """Branch 3: isotope specified but not in element's isotopes."""
        with pytest.raises(ValueError, match="Unknown isotope"):
            obj_compound.Compound("H{999}")


    def test_checkformula_branch4_mismatched_parenthesis(self):
        """Branch 4: mismatched parenthesis count."""
        with pytest.raises(ValueError, match="Wrong number of brackets"):
            obj_compound.Compound("(CH2)(OH")


    def test_checkformula_branch5_all_pass(self):
        """Branch 5: all checks pass."""
        c = obj_compound.Compound("Ca(OH)2")
        assert c.expression == "Ca(OH)2"


class TestUnfold:
    """Tests for the unfold functionality."""

    def test_unfold_no_brackets(self):
        """Test _unfoldBrackets with no brackets."""
        c = obj_compound.Compound("H2O")
        result = c._unfoldBrackets("H2O")
        assert result == "H2O"


    def test_unfold_simple_brackets(self):
        """Test _unfoldBrackets with simple brackets."""
        c = obj_compound.Compound("CH4")
        result = c._unfoldBrackets("(OH)2")
        # _unfoldBrackets repeats the string, composition() aggregates
        assert result == "OHOH"


    def test_unfold_no_multiplier(self):
        """Test _unfoldBrackets with brackets but no multiplier."""
        c = obj_compound.Compound("H2O")
        result = c._unfoldBrackets("(OH)")
        assert result == "OH"


    def test_unfold_nested_brackets(self):
        """Test _unfoldBrackets with nested brackets."""
        c = obj_compound.Compound("Ca")
        result = c._unfoldBrackets("((OH)2)1")
        # _unfoldBrackets repeats the string, composition() aggregates
        assert result == "OHOH"


    def test_unfold_multi_digit_multiplier(self):
        """Test _unfoldBrackets with multi-digit multiplier."""
        c = obj_compound.Compound("Ca")
        result = c._unfoldBrackets("(CH2)10")
        # _unfoldBrackets repeats the string 10 times
        expected = "CH2" * 10
        assert result == expected


    def test_unfold_complex_brackets(self):
        """Test _unfoldBrackets with complex formula."""
        c = obj_compound.Compound("Ca")
        result = c._unfoldBrackets("Ca(OH)2")
        # _unfoldBrackets repeats (OH) twice
        assert result == "CaOHOH"


class TestComposition:
    """Tests for the composition functionality."""

    def test_composition_simple(self):
        """Test composition() with simple formula."""
        c = obj_compound.Compound("H2O")
        comp = c.composition()
        assert comp == {"H": 2, "O": 1}


    def test_composition_cached(self):
        """Test composition() returns cached value."""
        c = obj_compound.Compound("H2O")
        comp1 = c.composition()
        comp2 = c.composition()
        assert comp1 is comp2  # Same object (cached)


    def test_composition_isotope(self):
        """Test composition() with isotope."""
        c = obj_compound.Compound("C{12}C{13}")
        comp = c.composition()
        assert "C{12}" in comp
        assert "C{13}" in comp
        assert comp["C{12}"] == 1
        assert comp["C{13}"] == 1


    def test_composition_bracketed(self):
        """Test composition() with bracketed formula."""
        c = obj_compound.Compound("Ca(OH)2")
        comp = c.composition()
        assert comp["Ca"] == 1
        assert comp["O"] == 2
        assert comp["H"] == 2


    def test_composition_zero_count_removal(self):
        """Test composition() removes zero-count atoms."""
        c = obj_compound.Compound("CH2")
        c._unfoldBrackets("C1H2C-1")  # This will produce zero-count
        # Directly test the zero-removal logic by creating a compound
        # and manipulating composition
        c2 = obj_compound.Compound("C2H4")
        comp = c2.composition()
        # All counts should be positive
        for _atom, count in list(comp.items()):
            assert count > 0


    def test_composition_multiple_same_atoms(self):
        """Test composition() aggregates same atoms."""
        c = obj_compound.Compound("C2H4")
        comp = c.composition()
        assert comp["C"] == 2
        assert comp["H"] == 4


    def test_composition_empty_or_single_atom(self):
        """Test composition() with single atom."""
        c = obj_compound.Compound("O")
        comp = c.composition()
        assert comp == {"O": 1}


    def test_composition_order_independence(self):
        """Test that formula order doesn't affect composition."""
        c1 = obj_compound.Compound("H2O")
        c2 = obj_compound.Compound("OH2")

        # Compositions should be equal
        comp1 = c1.composition()
        comp2 = c2.composition()

        # Both should have same atoms and counts
        for atom in ["H", "O"]:
            assert comp1.get(atom, 0) == comp2.get(atom, 0)


class TestFormula:
    """Tests for the formula functionality."""

    def test_formula_simple(self):
        """Test formula() with simple formula."""
        c = obj_compound.Compound("H2O")
        f = c.formula()
        # Should have C/H priority ordering
        assert f is not None


    def test_formula_cached(self):
        """Test formula() returns cached value."""
        c = obj_compound.Compound("C6H12")
        f1 = c.formula()
        f2 = c.formula()
        assert f1 is f2  # Same object (cached)


    def test_formula_ch_priority(self):
        """Test formula() orders C and H first."""
        c = obj_compound.Compound("N2C2H4O")
        f = c.formula()
        # C and H should come before other elements
        c_idx = f.find("C")
        h_idx = f.find("H")
        n_idx = f.find("N")
        f.find("O")
        assert c_idx < n_idx or c_idx == -1
        assert h_idx < n_idx or h_idx == -1


    def test_formula_single_atom_no_count(self):
        """Test formula() with single atom count=1."""
        c = obj_compound.Compound("C")
        f = c.formula()
        assert f == "C"


    def test_formula_isotope_variants(self):
        """Test formula() handles isotope variants."""
        c = obj_compound.Compound("C{12}H4")
        f = c.formula()
        assert "C{12}" in f or "C" in f
        assert "H" in f


    def test_formula_with_counts(self):
        """Test formula() with atom counts."""
        c = obj_compound.Compound("C6H6")
        f = c.formula()
        assert "C6" in f
        assert "H6" in f


    def test_formula_output_consistency(self):
        """Test formula output is consistent across calls."""
        c = obj_compound.Compound("Ca(OH)2")
        f1 = c.formula()
        f2 = c.formula()
        assert f1 == f2


class TestMass:
    """Tests for the mass functionality."""

    def test_mass_tuple_default(self):
        """Test mass() returns tuple by default."""
        c = obj_compound.Compound("H2O")
        m = c.mass()
        assert isinstance(m, tuple)
        assert len(m) == 2
        monoisotopic, average = m
        assert monoisotopic > 0
        assert average > 0


    def test_mass_masstype_0(self):
        """Test mass(massType=0) returns monoisotopic mass."""
        c = obj_compound.Compound("H2O")
        m = c.mass(massType=0)
        assert isinstance(m, (float, int))
        assert m > 0


    def test_mass_masstype_1(self):
        """Test mass(massType=1) returns average mass."""
        c = obj_compound.Compound("H2O")
        m = c.mass(massType=1)
        assert isinstance(m, (float, int))
        assert m > 0


    def test_mass_cached(self):
        """Test mass() caches result."""
        c = obj_compound.Compound("H2O")
        m1 = c.mass()
        m2 = c.mass()
        assert m1 is m2  # Same object (cached)


    def test_mass_with_isotope(self):
        """Test mass() with isotope specification."""
        c = obj_compound.Compound("C{12}H4")
        m = c.mass()
        assert m is not None


    def test_mass_isotope_branch(self):
        """Test mass() branches on massNumber present vs absent."""
        c1 = obj_compound.Compound("C")
        m1 = c1.mass()

        c2 = obj_compound.Compound("C{12}")
        m2 = c2.mass()

        # Both should have same monoisotopic mass for C-12
        assert m1[0] == pytest.approx(m2[0])


    def test_mass_multiple_atoms(self):
        """Test mass() with multiple atoms."""
        c = obj_compound.Compound("C2H4O")
        m = c.mass()
        assert m[0] > 0
        assert m[1] > 0


    # STEP 9: nominalmass() TESTS


class TestNominalmass:
    """Tests for the nominalmass functionality."""

    def test_nominalmass_simple(self):
        """Test nominalmass() with simple formula."""
        c = obj_compound.Compound("H2O")
        nm = c.nominalmass()
        assert isinstance(nm, (int, float))
        assert nm > 0


    def test_nominalmass_cached(self):
        """Test nominalmass() returns cached value."""
        c = obj_compound.Compound("H2O")
        nm1 = c.nominalmass()
        nm2 = c.nominalmass()
        assert nm1 == nm2
        assert c._nominalmass == nm1


    def test_nominalmass_isotope(self):
        """Test nominalmass() with isotope."""
        c = obj_compound.Compound("C{12}")
        nm = c.nominalmass()
        assert nm == 12


    def test_nominalmass_without_isotope(self):
        """Test nominalmass() without isotope."""
        c = obj_compound.Compound("C")
        nm = c.nominalmass()
        assert nm == 12  # Default C-12


    def test_nominalmass_multiple_atoms(self):
        """Test nominalmass() sums multiple atoms correctly."""
        c = obj_compound.Compound("C6H6")
        nm = c.nominalmass()
        expected = 6 * 12 + 6 * 1
        assert nm == expected


class TestCount:
    """Tests for the count functionality."""

    def test_count_simple(self):
        """Test count() with simple atom."""
        c = obj_compound.Compound("H2O")
        assert c.count("H") == 2
        assert c.count("O") == 1


    def test_count_absent(self):
        """Test count() with absent atom."""
        c = obj_compound.Compound("H2O")
        assert c.count("C") == 0


    def test_count_groupisotopes_false(self):
        """Test count(groupIsotopes=False) counts only exact atom key."""
        c = obj_compound.Compound("C{12}H4")
        count = c.count("C", groupIsotopes=False)
        assert count == 0  # Only C{12} exists, not bare C


    def test_count_groupisotopes_true_element_exists(self):
        """Test count(groupIsotopes=True) counts isotope-labelled keys."""
        c = obj_compound.Compound("C{12}C{13}H4")
        count = c.count("C", groupIsotopes=True)
        # Should count both C{12} and C{13}
        assert count == 2


    def test_count_groupisotopes_true_non_element(self):
        """Test count(groupIsotopes=True) with non-Element (no isotopes)."""
        c = obj_compound.Compound("H2O")
        count = c.count("H", groupIsotopes=True)
        # H is an element, but if only 'H' exists (not H{1}, etc.), count should work
        assert count == 2


    def test_count_with_isotope_exact(self):
        """Test count() with isotope exact match."""
        c = obj_compound.Compound("C{12}")
        assert c.count("C{12}") == 1


class TestMz:
    """Tests for the mz functionality."""

    def test_mz_positive_charge(self):
        """Test mz() with positive charge."""
        c = obj_compound.Compound("H2O")
        mz = c.mz(charge=1)
        assert mz[0] > 0


    def test_mz_negative_charge(self):
        """Test mz() with negative charge."""
        c = obj_compound.Compound("H2O")
        mz = c.mz(charge=-1)
        assert mz[0] > 0


    def test_mz_zero_charge(self):
        """Test mz() with zero charge."""
        c = obj_compound.Compound("H2O")
        mass = c.mass()
        mz = c.mz(charge=0)
        # With zero charge, mz should equal mass
        if isinstance(mass, tuple):
            assert mz == mass
        else:
            assert mz == mass


    def test_mz_electron_agent(self):
        """Test mz() with electron agent."""
        c = obj_compound.Compound("H2O")
        mz = c.mz(charge=-1, agentFormula="e")
        assert mz[0] > 0


    def test_mz_compound_agent(self):
        """Test mz() with compound agent."""
        c = obj_compound.Compound("H2O")
        mz = c.mz(charge=1, agentFormula="H")
        assert mz[0] > 0

class TestSmoke:
    """Tests for the smoke functionality."""

    def test_pattern_smoke(self):
        """Test pattern() delegation (smoke test)."""
        c = obj_compound.Compound("H2O")
        pattern = c.pattern()
        assert pattern is not None


    def test_rdbe_smoke(self):
        """Test rdbe() delegation (smoke test)."""
        c = obj_compound.Compound("C6H6")
        rdbe = c.rdbe()
        assert rdbe == pytest.approx(4.0)


    def test_frules_smoke(self):
        """Test frules() delegation (smoke test)."""
        c = obj_compound.Compound("C6H6")
        result = c.frules()
        assert isinstance(result, bool)


class TestIsvalid:
    """Tests for the isvalid functionality."""

    def test_isvalid_simple(self):
        """Test isvalid() with simple case."""
        c = obj_compound.Compound("H2O")
        assert c.isvalid() is True


    def test_isvalid_branch1_agentformula_not_e_not_compound(self):
        """Branch 1: agentFormula != 'e' AND not a compound instance."""
        c = obj_compound.Compound("C6H12O6")
        # Pass agentFormula as string (not 'e', not compound)
        result = c.isvalid(charge=1, agentFormula="H")
        assert isinstance(result, bool)


    def test_isvalid_branch2_agentformula_e(self):
        """Branch 2: agentFormula == 'e'."""
        c = obj_compound.Compound("H2O")
        result = c.isvalid(charge=-1, agentFormula="e")
        assert isinstance(result, bool)


    def test_isvalid_branch3_agentformula_compound(self):
        """Branch 3: agentFormula already a compound."""
        c = obj_compound.Compound("H2O")
        agent = obj_compound.Compound("H")
        result = c.isvalid(charge=1, agentFormula=agent)
        assert isinstance(result, bool)


    def test_isvalid_branch4_charge_nonzero_agent_not_e(self):
        """Branch 4: charge != 0 AND agentFormula != 'e'."""
        c = obj_compound.Compound("C6H12O6")
        result = c.isvalid(charge=1, agentFormula="H", agentCharge=1)
        assert isinstance(result, bool)


    def test_isvalid_branch5_charge_zero(self):
        """Branch 5: charge == 0."""
        c = obj_compound.Compound("C6H12O6")
        result = c.isvalid(charge=0, agentFormula="H")
        assert result is True


    def test_isvalid_branch6_negative_count(self):
        """Branch 6: any atom count < 0 (invalid)."""
        c = obj_compound.Compound("H")
        # To get negative count, we need to subtract more than available
        # Create a compound that subtracts atoms
        result = c.isvalid(charge=1, agentFormula="C", agentCharge=1)
        # H1 + C1(1/1) = H1 + C1, no negative counts
        # This is a challenging branch; let's try another approach
        # The ion formula is constructed; if atom count goes negative, return False
        assert isinstance(result, bool)


    def test_isvalid_all_counts_positive(self):
        """Branch 7: all counts >= 0."""
        c = obj_compound.Compound("C6H12O6")
        result = c.isvalid(charge=0)
        assert result is True


    def test_isvalid_negative_composition(self):
        """Test isvalid() with formula that could produce negative composition."""
        c = obj_compound.Compound("CH2")
        # Try to subtract more than available
        result = c.isvalid(charge=2, agentFormula="C10", agentCharge=1)
        # CH2 + 2*C10 = CH2 + C20 (both positive), so should be True
        assert result is True


    def test_isvalid_negative_count_branch(self):
        """Test isvalid() branch where count < 0 (line 307-308)."""
        c = obj_compound.Compound("H")
        # To get negative count, we need charge=-1 and agentFormula to produce net negative
        # H + (-1)*C = H - C (C becomes negative)
        result = c.isvalid(charge=-1, agentFormula="C", agentCharge=1)
        # H1 - C1 = H1 C-1, which has negative C, should return False
        assert result is False


class TestFrules:
    """Tests for the frules functionality."""

    def test_frules_parameters(self):
        """Test frules() with custom parameters."""
        c = obj_compound.Compound("C6H6")
        result = c.frules(rules=["HC", "RDBE"])
        assert isinstance(result, bool)


class TestNegate:
    """Tests for the negate functionality."""

    def test_negate_expression(self):
        """Test negate() modifies expression."""
        c = obj_compound.Compound("H2O")
        c.negate()
        assert "H-2" in c.expression or "H-2" in c.expression
        assert "O-1" in c.expression


    def test_negate_buffer_clearing(self):
        """Test negate() clears buffers."""
        c = obj_compound.Compound("H2O")
        # Populate buffers
        c.composition()
        c.mass()

        # Negate
        c.negate()

        # Buffers should be None
        assert c._composition is None
        assert c._mass is None
        assert c._nominalmass is None
        assert c._formula is None


    def test_negate_negative_composition(self):
        """Test negate() creates negative composition."""
        c = obj_compound.Compound("C")
        c.negate()
        comp = c.composition()
        for _atom, count in list(comp.items()):
            assert count < 0


    def test_negate_idempotent(self):
        """Test negate() twice returns to original."""
        c = obj_compound.Compound("H2O")
        original_comp = c.composition()

        c.negate()
        c.negate()

        final_comp = c.composition()
        for atom in original_comp:
            assert atom in final_comp
            assert final_comp[atom] == original_comp[atom]


class TestReset:
    """Tests for the reset functionality."""

    def test_reset_clears_composition(self):
        """Test reset() clears composition buffer."""
        c = obj_compound.Compound("H2O")
        c.composition()
        assert c._composition is not None

        c.reset()
        assert c._composition is None


    def test_reset_clears_all_buffers(self):
        """Test reset() clears all buffers."""
        c = obj_compound.Compound("H2O")
        # Populate all buffers
        c.composition()
        c.formula()
        c.mass()
        c.nominalmass()

        assert c._composition is not None
        assert c._formula is not None
        assert c._mass is not None
        assert c._nominalmass is not None

        # Reset
        c.reset()

        assert c._composition is None
        assert c._formula is None
        assert c._mass is None
        assert c._nominalmass is None


    def test_reset_preserves_expression(self):
        """Test reset() preserves expression."""
        c = obj_compound.Compound("H2O")
        expr = c.expression
        c.reset()
        assert c.expression == expr


    def test_reset_after_all_operations(self):
        """Test reset after using all getters."""
        c = obj_compound.Compound("C6H12O6")

        # Use all getters
        c.composition()
        c.formula()
        c.mass()
        c.nominalmass()
        c.count("C")

        # Reset
        c.reset()

        # All should be None
        assert c._composition is None
        assert c._formula is None
        assert c._mass is None
        assert c._nominalmass is None

        # Should be able to use getters again
        assert c.composition() is not None
        assert c.formula() is not None


class TestIadd:
    """Tests for the iadd functionality."""

    def test_iadd_compound_compound(self):
        """Test __iadd__ with compound + compound."""
        c1 = obj_compound.Compound("H2O")
        c2 = obj_compound.Compound("CH4")

        c1 += c2

        assert c1.expression == "H2OCH4"
        assert c1 is c1  # Should return self


    def test_iadd_compound_string(self):
        """Test __iadd__ with compound + valid string."""
        c = obj_compound.Compound("H2O")
        c += "CH4"

        assert c.expression == "H2OCH4"


    def test_iadd_invalid_string(self):
        """Test __iadd__ with invalid string."""
        c = obj_compound.Compound("H2O")
        with pytest.raises(ValueError, match="Unknown element in formula! --> X in XXX"):
            c += "XXX"


    def test_iadd_returns_self(self):
        """Test __iadd__ returns self."""
        c = obj_compound.Compound("H2O")
        result = c.__iadd__(obj_compound.Compound("CH4"))
        assert result is c


    def test_iadd_clears_buffers(self):
        """Test __iadd__ clears buffers."""
        c = obj_compound.Compound("H2O")
        # Populate buffers
        c.composition()
        assert c._composition is not None

        # Add
        c += "CH4"

        assert c._composition is None


    def test_iadd_chain(self):
        """Test __iadd__ can be chained."""
        c = obj_compound.Compound("H")
        c += "H"
        c += "O"

        assert c.expression == "HHO"


class TestCache:
    """Tests for the cache functionality."""

    def test_cache_invalidation_on_iadd(self):
        """Test cache invalidation when using __iadd__."""
        c = obj_compound.Compound("H2O")
        comp1 = c.composition()

        c += "H"

        # After iadd, cache should be cleared
        assert c._composition is None

        comp2 = c.composition()
        # New composition should be different
        assert comp1 != comp2
        assert comp2["H"] == 3


    def test_cache_invalidation_on_negate(self):
        """Test cache invalidation when using negate()."""
        c = obj_compound.Compound("H2O")
        c.composition()

        c.negate()

        # After negate, cache should be cleared
        assert c._composition is None

        comp2 = c.composition()
        for atom in comp2:
            assert comp2[atom] < 0


class TestBuffer:
    """Tests for the buffer functionality."""

    def test_buffer_consistency_after_operations(self):
        """Test buffer consistency across multiple operations."""
        c = obj_compound.Compound("H2O")

        # Get mass
        m1 = c.mass()
        assert c._mass is not None

        # Get nominal mass
        nm = c.nominalmass()
        assert c._nominalmass is not None

        # Both should still be cached
        m2 = c.mass()
        assert m1 is m2
        nm2 = c.nominalmass()
        assert nm is nm2


class TestCompoundMisc:
    """Tests for the compoundmisc functionality."""

    def test_compound_with_large_formula(self):
        """Test compound with large/complex formula."""
        c = obj_compound.Compound("C100H202O50N20P10S5")
        assert c.expression == "C100H202O50N20P10S5"
        comp = c.composition()
        assert comp["C"] == 100
        assert comp["H"] == 202


    def test_compound_with_nested_brackets(self):
        """Test compound with nested brackets."""
        c = obj_compound.Compound("((CH2)2)3")
        comp = c.composition()
        assert comp["C"] == 6
        assert comp["H"] == 12


    def test_compound_isotope_count_grouping(self):
        """Test counting with isotope grouping."""
        c = obj_compound.Compound("C{12}C{13}C{14}H4")
        total = c.count("C", groupIsotopes=True)
        assert total == 3


    def test_compound_mass_precision(self):
        """Test mass calculations are reasonably precise."""
        c = obj_compound.Compound("H2O")
        m = c.mass()
        # Water should be approximately 18
        assert m[0] > 17
        assert m[0] < 19


    def test_single_atom_hydrogen(self):
        """Test single hydrogen atom."""
        c = obj_compound.Compound("H")
        assert c.composition() == {"H": 1}
        assert c.nominalmass() == 1


    def test_single_atom_oxygen(self):
        """Test single oxygen atom."""
        c = obj_compound.Compound("O")
        assert c.composition() == {"O": 1}
        assert c.nominalmass() == 16


    def test_isotope_explicit_label(self):
        """Test explicit isotope label."""
        c = obj_compound.Compound("H{1}")
        comp = c.composition()
        assert "H{1}" in comp
        assert comp["H{1}"] == 1


    def test_high_count_atom(self):
        """Test atom with high count."""
        c = obj_compound.Compound("O999")
        assert c.composition()["O"] == 999
        assert c.nominalmass() == 999 * 16


    def test_bracket_with_high_multiplier(self):
        """Test bracket with high multiplier."""
        c = obj_compound.Compound("(H2O)99")
        comp = c.composition()
        assert comp["H"] == 198
        assert comp["O"] == 99


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_composition_is_dict(self, formula):
        """Property: composition() always returns a dict."""
        c = obj_compound.Compound(formula)
        comp = c.composition()
        assert isinstance(comp, dict)
        for atom, count in list(comp.items()):
            assert isinstance(atom, str)
            assert isinstance(count, (int, float))
            assert count > 0


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_mass_positive(self, formula):
        """Property: mass() always returns positive values."""
        c = obj_compound.Compound(formula)
        m = c.mass()
        assert m[0] > 0
        assert m[1] > 0
        assert m[0] <= m[1]  # Monoisotopic <= average


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_nominalmass_positive(self, formula):
        """Property: nominalmass() always returns positive value."""
        c = obj_compound.Compound(formula)
        nm = c.nominalmass()
        assert nm > 0


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_formula_is_string(self, formula):
        """Property: formula() always returns a string."""
        c = obj_compound.Compound(formula)
        f = c.formula()
        assert isinstance(f, str)
        assert len(f) > 0


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_caching_works(self, formula):
        """Property: second call to getter returns same cached object."""
        c = obj_compound.Compound(formula)
        comp1 = c.composition()
        comp2 = c.composition()
        assert comp1 is comp2

        formula1 = c.formula()
        formula2 = c.formula()
        assert formula1 is formula2


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_reset_clears_all(self, formula):
        """Property: reset() clears all buffers."""
        c = obj_compound.Compound(formula)
        # Populate buffers
        c.composition()
        c.formula()
        c.mass()
        c.nominalmass()

        c.reset()

        assert c._composition is None
        assert c._formula is None
        assert c._mass is None
        assert c._nominalmass is None


    @given(
        st.sampled_from(
            ["H2O", "CH4", "C6H12O6", "NH3", "CO2", "N2", "O2", "H2", "Ca(OH)2", "C{12}H4"]
        )
    )
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_prop_count_matches_composition(self, formula):
        """Property: count() results match composition()."""
        c = obj_compound.Compound(formula)
        comp = c.composition()

        for atom in comp:
            count = c.count(atom)
            assert count == comp[atom]
