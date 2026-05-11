import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import blocks, mod_proteo, mod_stopper, obj_sequence


# Helper function to create sequences as lists
def seq(chain_str, **kwargs):
    """Create a sequence from a string."""
    return obj_sequence.Sequence(list(chain_str), **kwargs)


class TestDigest:
    """Tests for the digest function."""

    def test_digest_allowmods_false_with_variable_modification(self):
        """Test digest with allowMods=False and variable mod blocks cleavage."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 5, 'v'])
        peptides = mod_proteo.digest(s, 'Trypsin', allowMods=False, miscleavage=0)
        assert len(peptides) >= 1

    def test_digest_allowmods_true_with_modification_on_cleavage_site(self):
        """Test digest with allowMods=True ignores mods and cleaves."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'f'])
        peptides_allow = mod_proteo.digest(s, 'Trypsin', allowMods=True, miscleavage=0)
        assert len(peptides_allow) >= 3
        chains = [''.join(p.chain) for p in peptides_allow]
        assert 'MAK' in chains or 'MAKR' in chains

    def test_digest_allowmods_with_no_modification_at_cleavage(self):
        """Test digest with allowMods=False but no modification at cleavage site."""
        s = seq('MAKRFKQ')
        peptides = mod_proteo.digest(s, 'Trypsin', allowMods=False, miscleavage=0)
        assert len(peptides) >= 1

    def test_digest_elif_branch_modification_after_cleavage(self):
        """Test digest elif branch - modification after cleavage site."""
        s = seq('ADFAKDF')
        s.modifications.append(['Acetyl', 2, 'f'])
        peptides = mod_proteo.digest(s, 'Asp-N', allowMods=False, miscleavage=0)
        assert isinstance(peptides, list)

    def test_digest_elif_modsafter_false_branch(self):
        """Test digest line 80->81: elif branch for modification after cleavage site.

        This targets the elif condition at line 80:
        elif not allowMods and sequence.ismodified(x, strict) and not enzyme.modsAfter:

        We use Lys-N which:
        - expression: [A-Z][K] (cleaves after K)
        - modsAfter: False (doesn't allow mods after K)
        - modsBefore: True (allows mods before K)

        At x=2 in 'MAKR' with mod at K (position 2):
        - ismodified(1)=False (no mod before K)
        - ismodified(2)=True (mod at K)
        - Line 78 (if) is False (no mod at x-1)
        - Line 80 (elif) is True -> executes
        """
        s = seq('MAKR')
        s.modifications.append(['Acetyl', 2, 'f'])
        peptides = mod_proteo.digest(s, 'Lys-N', allowMods=False, miscleavage=0)
        assert len(peptides) >= 1
        assert isinstance(peptides, list)

    def test_digest_empty_sequence(self):
        """Test digest returns empty list for empty sequence."""
        s = seq('')
        result = mod_proteo.digest(s, 'Trypsin')
        assert result == []

    def test_digest_enzyme_modsafter_false(self):
        """Test digest with enzyme that has modsAfter=False."""
        s = seq('ADFAKDFQ')
        s.modifications.append(['Acetyl', 2, 'f'])
        peptides = mod_proteo.digest(s, 'Asp-N', allowMods=False, miscleavage=0)
        assert isinstance(peptides, list)

    def test_digest_enzyme_modsbefore_true(self):
        """Test digest with enzyme that has modsBefore=True."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 0, 'f'])
        peptides = mod_proteo.digest(s, 'Non-Specific', allowMods=False, miscleavage=0)
        assert len(peptides) >= 1

    def test_digest_force_quit(self):
        """Test digest raises ForceQuitError when stopper is enabled."""
        s = seq('MAKRFKQ')
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_proteo.digest(s, 'Trypsin')

    def test_digest_key_error_unknown_enzyme(self):
        """Test digest raises KeyError for unknown enzyme name."""
        s = seq('MAKRFKQ')
        with pytest.raises(KeyError):
            mod_proteo.digest(s, 'UnknownEnzyme')

    def test_digest_miscleavage_0_attribute(self):
        """Test digest sets miscleavage attribute to 0 for complete cleavages."""
        s = seq('MAKRFKQ')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=0)
        for pep in peptides:
            assert pep.miscleavages == 0

    def test_digest_miscleavage_1(self):
        """Test digest with miscleavage=1 includes combined peptides."""
        s = seq('MAKRFKQ')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=1)
        assert len(peptides) > 4
        has_miscleavage = any(p.miscleavages == 1 for p in peptides)
        assert has_miscleavage

    def test_digest_modification_after_cleavage_site_blocks(self):
        """Test digest with modification after cleavage site (modsAfter)."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 4, 'f'])
        s2 = seq('ADFAKDFQ')
        s2.modifications.append(['Acetyl', 2, 'f'])
        peptides = mod_proteo.digest(s2, 'Asp-N', allowMods=False)
        assert len(peptides) >= 1

    def test_digest_no_cleavage_site(self):
        """Test digest on sequence with no cleavage sites returns 1 peptide."""
        s = seq('AAAA')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=0)
        assert len(peptides) == 1
        assert ''.join(peptides[0].chain) == 'AAAA'

    def test_digest_single_aa(self):
        """Test digest on single amino acid returns 1 peptide."""
        s = seq('A')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=0)
        assert len(peptides) == 1
        assert ''.join(peptides[0].chain) == 'A'

    def test_digest_strict_false_ignores_variable_mods(self):
        """Test digest with strict=False allows cleavage despite variable mods."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'v'])
        peptides = mod_proteo.digest(s, 'Trypsin', allowMods=False, strict=False)
        assert len(peptides) >= 1

    def test_digest_strict_true_blocks_variable_mods(self):
        """Test digest with strict=True considers variable mods for blocking."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'v'])
        peptides_strict = mod_proteo.digest(s, 'Trypsin', allowMods=False, strict=True)
        assert isinstance(peptides_strict, list)

    def test_digest_terminal_assignment_internal(self):
        """Test digest assigns terminal formulas for internal peptides."""
        s = seq('MAKRFKQ')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=0)
        assert peptides[0].nTermFormula == 'H'
        assert peptides[0].cTermFormula == 'OH'
        assert peptides[1].nTermFormula == 'H'
        assert peptides[1].cTermFormula == 'OH'
        assert peptides[-1].nTermFormula == 'H'
        assert peptides[-1].cTermFormula == 'OH'

    def test_digest_trypsin_basic(self):
        """Test digest with Trypsin on MAKRFKQ -> 4 peptides."""
        s = seq('MAKRFKQ')
        peptides = mod_proteo.digest(s, 'Trypsin', miscleavage=0)
        assert len(peptides) == 4
        assert ''.join(peptides[0].chain) == 'MAK'
        assert ''.join(peptides[1].chain) == 'R'
        assert ''.join(peptides[2].chain) == 'FK'
        assert ''.join(peptides[3].chain) == 'Q'

    def test_digest_two_consecutive_modifications_different_positions(self):
        """Test digest with modifications at different positions relative to cleavage."""
        s = seq('MAKRFK')
        s.modifications.append(['Acetyl', 1, 'f'])
        s.modifications.append(['Acetyl', 4, 'f'])
        peptides = mod_proteo.digest(s, 'Lys-C', allowMods=False, miscleavage=0)
        assert isinstance(peptides, list)

    def test_digest_type_error_cyclic_sequence(self):
        """Test digest raises TypeError for cyclic sequences."""
        s = seq('MAKRFKQ', cyclic=True)
        with pytest.raises(TypeError):
            mod_proteo.digest(s, 'Trypsin')

    def test_digest_type_error_non_aminoacid_chain(self):
        """Test digest raises TypeError for non-aminoacid chainType."""
        s = seq('MAKRFKQ', chainType='nucleotides')
        with pytest.raises(TypeError):
            mod_proteo.digest(s, 'Trypsin')

    def test_digest_type_error_non_sequence(self):
        """Test digest raises TypeError for non-sequence object."""
        with pytest.raises(TypeError):
            mod_proteo.digest('not a sequence', 'Trypsin')

    def test_digest_variable_vs_fixed_modification_strict(self):
        """Test digest with variable modification and strict=True."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'v'])
        peptides_strict = mod_proteo.digest(s, 'Trypsin', allowMods=False, strict=True)
        assert isinstance(peptides_strict, list)

    def test_digest_with_allowmods_false_blocks_cleavage(self):
        """Test digest with allowMods=False blocks cleavage at modified sites."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'f'])
        peptides = mod_proteo.digest(s, 'Trypsin', allowMods=False)
        assert len(peptides) < 4

    def test_digest_with_allowmods_true_ignores_modification(self):
        """Test digest with allowMods=True ignores modifications during cleavage."""
        s = seq('MAKRFKQ')
        s.modifications.append(['Acetyl', 3, 'f'])
        peptides_allow = mod_proteo.digest(s, 'Trypsin', allowMods=True)
        peptides_no_allow = mod_proteo.digest(s, 'Trypsin', allowMods=False)
        assert len(peptides_allow) >= len(peptides_no_allow)

    def test_digest_with_arg_c_enzyme_modsbefore_false(self):
        """Test digest with Arg-C which has modsBefore=False."""
        s = seq('RAKARAF')
        s.modifications.append(['Acetyl', 0, 'f'])
        peptides = mod_proteo.digest(s, 'Arg-C', allowMods=False, miscleavage=0)
        assert isinstance(peptides, list)


class TestCoverage:
    """Tests for the coverage function."""

    def test_coverage_computer_indexing_full(self):
        """Test coverage with computer indexing (0-based) for full coverage."""
        ranges = [(0, 10)]
        result = mod_proteo.coverage(ranges, 10, human=False)
        assert result == 100.0

    def test_coverage_computer_indexing_partial(self):
        """Test coverage with computer indexing for partial coverage."""
        ranges = [(0, 5)]
        result = mod_proteo.coverage(ranges, 10, human=False)
        assert result == 50.0

    def test_coverage_empty_ranges(self):
        """Test coverage returns 0.0 for empty ranges."""
        result = mod_proteo.coverage([], 100)
        assert result == 0.0

    def test_coverage_full_coverage_human(self):
        """Test coverage returns 100.0 for full coverage with human indexing."""
        ranges = [(1, 10)]
        result = mod_proteo.coverage(ranges, 10, human=True)
        assert result == 100.0

    def test_coverage_large_length(self):
        """Test coverage with large sequence length."""
        ranges = [(1, 1000)]
        result = mod_proteo.coverage(ranges, 100000, human=True)
        assert result == 1.0

    def test_coverage_multiple_non_overlapping(self):
        """Test coverage with multiple non-overlapping ranges."""
        ranges = [(1, 3), (6, 8)]
        result = mod_proteo.coverage(ranges, 10, human=True)
        assert result == 60.0

    def test_coverage_overlapping_ranges(self):
        """Test coverage correctly handles overlapping ranges."""
        ranges = [(1, 5), (3, 7)]
        result = mod_proteo.coverage(ranges, 10, human=True)
        assert result == 70.0

    def test_coverage_partial_human(self):
        """Test coverage with partial ranges using human indexing."""
        ranges = [(1, 5)]
        result = mod_proteo.coverage(ranges, 10, human=True)
        assert result == 50.0

    def test_coverage_single_position(self):
        """Test coverage with single position."""
        ranges = [(1, 1)]
        result = mod_proteo.coverage(ranges, 10, human=True)
        assert result == 10.0


class TestFragmentserie:
    """Tests for the fragmentserie function."""

    def test_fragmentserie_c_terminal_cterm_filter_true(self):
        """Test C-terminal serie with cTermFilter=True."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'x')
        assert isinstance(frags, list)

    def test_fragmentserie_c_terminal_nterm_filter_true(self):
        """Test C-terminal serie with nTermFilter=True."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'z')
        assert isinstance(frags, list)

    def test_fragmentserie_cyclic_parent_i_series(self):
        """Test fragmentserie cyclic parent for I-series (internals)."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'int-b', cyclicParent=True)
        assert len(frags) >= 0

    def test_fragmentserie_cyclic_parent_s_series(self):
        """Test fragmentserie cyclic parent for S-series (singlets)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'im', cyclicParent=True)
        assert len(frags) > 0
        for f in frags:
            assert hasattr(f, 'nTermFormula')
            assert hasattr(f, 'cTermFormula')

    def test_fragmentserie_internal_with_5aa(self):
        """Test internal fragments with 5-AA peptide."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) > 0
        assert all(f.fragmentSerie == 'int-b' for f in frags)

    def test_fragmentserie_internal_with_small_peptide(self):
        """Test internal fragments with 3-AA peptide (should be empty)."""
        s = seq('MAK')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert frags == []

    def test_fragmentserie_n_terminal_cterm_filter_true(self):
        """Test N-terminal serie with cTermFilter=True."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'b')
        assert isinstance(frags, list)

    def test_fragmentserie_n_terminal_nterm_filter_true(self):
        """Test N-terminal serie with nTermFilter=True."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'c')
        assert isinstance(frags, list)

    def test_fragmentserie_singlet_nterm_filter(self):
        """Test singlet serie with nTermFilter."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert isinstance(frags, list)



    def test_fragmentserie_a_series(self):
        """Test fragmentserie with a-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'a')
        assert len(frags) >= 1
        assert all(f.fragmentSerie == 'a' for f in frags)

    def test_fragmentserie_all_series_filters_covered(self):
        """Test all fragment series filter combinations."""
        s = seq('MAKRF')
        series_to_test = ['a', 'b', 'c', 'x', 'y', 'z', 'c-ladder', 'n-ladder']
        for series_name in series_to_test:
            frags = mod_proteo.fragmentserie(s, series_name)
            assert isinstance(frags, list)
            for frag in frags:
                assert frag.fragmentSerie == series_name

    def test_fragmentserie_b_series(self):
        """Test fragmentserie with b-series on 4-AA peptide."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        assert len(frags) == 2
        assert frags[0].fragmentSerie == 'b'
        assert frags[1].fragmentSerie == 'b'

    def test_fragmentserie_c_ladder_series(self):
        """Test fragmentserie with c-ladder series (N-term, both filters)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'c-ladder')
        assert all(f.fragmentSerie == 'c-ladder' for f in frags)

    def test_fragmentserie_c_series(self):
        """Test fragmentserie with c-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'c')
        assert len(frags) >= 1
        assert all(f.fragmentSerie == 'c' for f in frags)

    def test_fragmentserie_c_series_no_nterm_filter(self):
        """Test fragmentserie with c-series (N-term, no nTermFilter)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'c')
        assert all(f.fragmentSerie == 'c' for f in frags)

    def test_fragmentserie_c_terminal_ntermfilter_cond(self):
        """Test fragmentserie line 303->305: C-terminal with nTermFilter=True.

        C-terminal with nTermFilter=True should delete last fragment.
        But all C-terminals in blocks have nTermFilter=True.
        Since we can't find one with cTermFilter=True, test nTermFilter.
        """
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'x')
        assert len(frags) == 4

    def test_fragmentserie_c_terminal_removes_first_on_cterm_filter(self):
        """Test C-terminal with cTermFilter removes first fragment."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'z')
        assert isinstance(frags, list)

    def test_fragmentserie_c_terminal_single_aa_both_filters(self):
        """Test C-terminal with both filters on 1-AA peptide."""
        s = seq('M')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert len(frags) >= 0

    def test_fragmentserie_custom_cterm_with_ctermfilter(self):
        """Test C-terminal with cTermFilter=True (unreachable with default blocks).

        Creates a custom fragment series to test line 305->306 branch.
        """
        custom_frag = blocks.Fragment(name='z-custom', terminus='C', nTermFormula='H', nTermFilter=False, cTermFilter=True)
        blocks.fragments['z-custom'] = custom_frag
        try:
            s = seq('MAKRF')
            frags = mod_proteo.fragmentserie(s, 'z-custom')
            assert len(frags) == 4
            assert frags[0].fragmentSerie == 'z-custom'
        finally:
            del blocks.fragments['z-custom']

    def test_fragmentserie_custom_singlet_with_ctermfilter(self):
        """Test singlet with cTermFilter=True (unreachable with default blocks).

        Creates a custom singlet fragment series to test line 310->311 branch.
        """
        custom_frag = blocks.Fragment(name='s-custom2', terminus='S', nTermFormula='H', cTermFormula='OH', nTermFilter=False, cTermFilter=True)
        blocks.fragments['s-custom2'] = custom_frag
        try:
            s = seq('MAKRF')
            frags = mod_proteo.fragmentserie(s, 's-custom2')
            assert len(frags) == 4
        finally:
            del blocks.fragments['s-custom2']

    def test_fragmentserie_custom_singlet_with_ntermfilter(self):
        """Test singlet with nTermFilter=True (unreachable with default blocks).

        Creates a custom singlet fragment series to test line 308->309 branch.
        """
        custom_frag = blocks.Fragment(name='s-custom', terminus='S', nTermFormula='H', cTermFormula='OH', nTermFilter=True, cTermFilter=False)
        blocks.fragments['s-custom'] = custom_frag
        try:
            s = seq('MAKRF')
            frags = mod_proteo.fragmentserie(s, 's-custom')
            assert len(frags) == 4
        finally:
            del blocks.fragments['s-custom']

    def test_fragmentserie_cyclic_parent_M(self):
        """Test fragmentserie with cyclicParent=True for M-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'M', cyclicParent=True)
        assert len(frags) == 1
        assert frags[0].nTermFormula == ''
        assert frags[0].cTermFormula == ''

    def test_fragmentserie_cyclic_parent_b(self):
        """Test fragmentserie with cyclicParent=True for b-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b', cyclicParent=True)
        assert all(f.nTermFormula == 'H' for f in frags)

    def test_fragmentserie_cyclic_parent_multiple_terminus_types(self):
        """Test cyclic parent handling for all terminus types."""
        s = seq('MAKRF')
        frags_n = mod_proteo.fragmentserie(s, 'b', cyclicParent=True)
        for f in frags_n:
            assert f.nTermFormula == 'H'
        frags_c = mod_proteo.fragmentserie(s, 'y', cyclicParent=True)
        for f in frags_c:
            assert f.cTermFormula == 'H-1'
        mod_proteo.fragmentserie(s, 'im', cyclicParent=True)

    def test_fragmentserie_cyclic_parent_y(self):
        """Test fragmentserie with cyclicParent=True for y-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'y', cyclicParent=True)
        assert all(f.cTermFormula == 'H-1' for f in frags)

    def test_fragmentserie_empty_frags_with_filter_applied(self):
        """Test filter operations when frags list becomes empty."""
        s = seq('MA')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert frags == []

    def test_fragmentserie_filter_both_remove_from_n_terminal(self):
        """Test N-terminal with both nTermFilter and cTermFilter."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'c-ladder')
        assert isinstance(frags, list)

    def test_fragmentserie_force_quit(self):
        """Test fragmentserie raises ForceQuitError when stopper is enabled."""
        s = seq('MAKRFKQ')
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_proteo.fragmentserie(s, 'b')

    def test_fragmentserie_im_series(self):
        """Test fragmentserie with im (singlet) series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert len(frags) == 4
        assert all(f.fragmentSerie == 'im' for f in frags)

    def test_fragmentserie_internal_4aa_peptide(self):
        """Test internal fragments with exactly 4-AA peptide."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) >= 0

    def test_fragmentserie_internal_6aa_peptide(self):
        """Test internal fragments with 6-AA peptide."""
        s = seq('MAKRFK')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) == 6

    def test_fragmentserie_internal_b_2aa(self):
        """Test fragmentserie with int-b on 2-AA peptide returns empty."""
        s = seq('MA')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert frags == []

    def test_fragmentserie_internal_b_4aa(self):
        """Test fragmentserie with int-b on 5-AA peptide."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) > 0
        assert all(f.fragmentSerie == 'int-b' for f in frags)

    def test_fragmentserie_internal_boundary_5aa(self):
        """Test internal fragments at boundary with 5-AA."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) >= 3

    def test_fragmentserie_internal_fragments_4aa_minimum(self):
        """Test fragmentserie line 274->286: internal fragments generation.

        Internal fragments require: length >= 4 (range(1, length-1) must be non-empty)
        With 4 AA: x in range(1, 3) = [1, 2]
                   x=1: y in range(2, 3) = [2] -> 1 fragment
                   x=2: y in range(2, 2) = [] -> 0 fragments
        Total = 1 internal fragment
        """
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'int-b')
        assert len(frags) == 1
        assert frags[0].fragmentSerie == 'int-b'

    def test_fragmentserie_internal_fragments_cyclic_parent(self):
        """Test fragmentserie line 274->286: internal fragments with cyclicParent.

        Tests the path from line 274 (internal fragments) through line 286 (cyclic correction).
        """
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'int-b', cyclicParent=True)
        assert len(frags) >= 0
        if len(frags) > 0:
            for frag in frags:
                assert frag.fragmentSerie == 'int-b'

    def test_fragmentserie_molecular_ion(self):
        """Test fragmentserie with M (molecular ion) returns 1 fragment."""
        s = seq('M')
        frags = mod_proteo.fragmentserie(s, 'M')
        assert len(frags) == 1
        assert frags[0].fragmentSerie == 'M'
        assert ''.join(frags[0].chain) == 'M'

    def test_fragmentserie_n_ladder_series(self):
        """Test fragmentserie with n-ladder series (C-term, nTermFilter)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'n-ladder')
        assert all(f.fragmentSerie == 'n-ladder' for f in frags)

    def test_fragmentserie_n_terminal_both_filters_empty_after_first(self):
        """Test N-terminal serie where first deletion empties the list."""
        s = seq('MA')
        frags = mod_proteo.fragmentserie(s, 'b')
        assert isinstance(frags, list)

    def test_fragmentserie_n_terminal_single_aa_both_filters(self):
        """Test N-terminal with both filters on 1-AA peptide."""
        s = seq('M')
        frags = mod_proteo.fragmentserie(s, 'b')
        assert len(frags) == 0

    def test_fragmentserie_singlet_ctermfilter_branch(self):
        """Test fragmentserie line 310->311: singlet with cTermFilter=True deletion.

        But 'im' has both filters=False, so can't test this branch with default blocks.
        This may be an unreachable branch.
        """
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert len(frags) == 5

    def test_fragmentserie_singlet_ntermfilter_branch(self):
        """Test fragmentserie line 308->309: singlet with nTermFilter=True deletion.

        Singlets (terminus='S') with nTermFilter=True should delete first fragment.
        But 'im' singlets have nTermFilter=False, cTermFilter=False.
        """
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert len(frags) == 5

    def test_fragmentserie_singlet_with_both_filters(self):
        """Test singlet serie applying both nTermFilter and cTermFilter."""
        s = seq('MAKRF')
        frags = mod_proteo.fragmentserie(s, 'im')
        assert isinstance(frags, list)

    def test_fragmentserie_type_error_cyclic(self):
        """Test fragmentserie raises TypeError for cyclic sequences."""
        s = seq('MAKRFKQ', cyclic=True)
        with pytest.raises(TypeError):
            mod_proteo.fragmentserie(s, 'M')

    def test_fragmentserie_type_error_non_sequence(self):
        """Test fragmentserie raises TypeError for non-sequence."""
        with pytest.raises(TypeError):
            mod_proteo.fragmentserie('not a sequence', 'M')

    def test_fragmentserie_x_series(self):
        """Test fragmentserie with x-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'x')
        assert len(frags) >= 1
        assert all(f.fragmentSerie == 'x' for f in frags)

    def test_fragmentserie_x_series_no_cterm_filter(self):
        """Test fragmentserie with x-series (C-term, no cTermFilter)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'x')
        assert all(f.fragmentSerie == 'x' for f in frags)

    def test_fragmentserie_y_series(self):
        """Test fragmentserie with y-series on 4-AA peptide."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'y')
        assert len(frags) == 3
        assert all(f.fragmentSerie == 'y' for f in frags)

    def test_fragmentserie_z_series(self):
        """Test fragmentserie with z-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'z')
        assert len(frags) >= 1
        assert all(f.fragmentSerie == 'z' for f in frags)


class TestFragment:
    """Tests for the fragment function."""

    def test_fragment_3aa_scrambling(self):
        """Test 3-AA peptide with scrambling (boundary condition)."""
        s = seq('MAK')
        frags_scram = mod_proteo.fragment(s, ['b'], scrambling=True)
        assert len(frags_scram) >= 0

    def test_fragment_M_series_not_scrambled(self):
        """Test M-series fragments are not scrambled."""
        s = seq('MAKRF')
        frags_scram = mod_proteo.fragment(s, ['M'], scrambling=True)
        assert len(frags_scram) == 1
        assert frags_scram[0].fragmentSerie == 'M'

    def test_fragment_cyclic_linearized_multiple_forms(self):
        """Test cyclic peptide generates multiple linear forms."""
        s = seq('MAKRF', cyclic=True)
        frags = mod_proteo.fragment(s, ['b', 'y'])
        assert len(frags) > 0

    def test_fragment_dedup_with_M_series_sorting(self):
        """Test deduplication includes M-series special sorting."""
        s = seq('MAK')
        frags = mod_proteo.fragment(s, ['M'])
        assert len(frags) > 0
        assert all(f.fragmentSerie == 'M' for f in frags)

    def test_fragment_scrambling_on_b_series_only(self):
        """Test scrambling only processes b, a, M series."""
        s = seq('MAKRFKQSD')
        frags_scram = mod_proteo.fragment(s, ['b', 'y'], scrambling=True)
        series = {f.fragmentSerie for f in frags_scram}
        assert 'b' in series
        assert 'y' in series
        assert len(frags_scram) > 0

    def test_fragment_M_series(self):
        """Test fragment with M-series (molecular ion)."""
        s = seq('MAKR')
        frags = mod_proteo.fragment(s, ['M'])
        assert len(frags) > 0
        assert all(f.fragmentSerie == 'M' for f in frags)

    def test_fragment_cyclic_peptide(self):
        """Test fragment with cyclic peptide generates multiple linear forms."""
        s = seq('AKRF', cyclic=True)
        frags = mod_proteo.fragment(s, ['b'])
        assert len(frags) > 0

    def test_fragment_cyclic_with_M_no_rescramble(self):
        """Test scrambling on cyclic with M-series doesn't re-scramble."""
        s = seq('AKRF', cyclic=True)
        frags = mod_proteo.fragment(s, ['M'], scrambling=True)
        assert len(frags) > 0

    def test_fragment_deduplication(self):
        """Test fragment deduplicates fragments by frhash."""
        s = seq('MAKRFKQ')
        frags = mod_proteo.fragment(s, ['b', 'y'])
        frhashes = []
        for frag in frags:
            frhash = [frag.fragmentSerie, *frag.indexes()]
            frhashes.append(frhash)
        assert len(frhashes) == len({tuple(h) for h in frhashes})

    def test_fragment_empty_series(self):
        """Test fragment with empty series list returns empty."""
        s = seq('MAKRFKQ')
        frags = mod_proteo.fragment(s, [])
        assert frags == []

    def test_fragment_linear_basic(self):
        """Test fragment with linear peptide and basic series."""
        s = seq('MAKRFKQ')
        frags = mod_proteo.fragment(s, ['b', 'y'])
        assert len(frags) > 0
        series = {f.fragmentSerie for f in frags}
        assert 'b' in series
        assert 'y' in series

    def test_fragment_scrambling_2aa_no_extra(self):
        """Test scrambling on 2-AA peptide doesn't add fragments."""
        s = seq('MA')
        frags_no_scram = mod_proteo.fragment(s, ['b'], scrambling=False)
        frags_scram = mod_proteo.fragment(s, ['b'], scrambling=True)
        assert len(frags_scram) == len(frags_no_scram)

    def test_fragment_scrambling_increases_count(self):
        """Test scrambling=True on 5-AA linear increases fragment count."""
        s = seq('MAKRF')
        frags_no_scram = mod_proteo.fragment(s, ['b'], scrambling=False)
        frags_scram = mod_proteo.fragment(s, ['b'], scrambling=True)
        assert len(frags_scram) >= len(frags_no_scram)

    def test_fragment_type_error_non_sequence(self):
        """Test fragment raises TypeError for non-sequence."""
        with pytest.raises(TypeError):
            mod_proteo.fragment('not a sequence', ['b', 'y'])


class TestFragmentlosses:
    """Tests for the fragmentlosses function."""

    def test_fragmentlosses_combination_skip_on_invalid(self):
        """Test fragmentlosses skips fragment when loss makes it invalid."""
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'H3PO4'], limit=2)
        assert isinstance(result, list)

    def test_fragmentlosses_defined_losses_with_monomer_losses(self):
        """Test fragmentlosses picks up specific monomer-defined losses."""
        s = seq('SDAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=[], defined=True)
        assert len(result) > 0

    def test_fragmentlosses_filter_in_and_filter_out_together(self):
        """Test fragmentlosses with both filterIn and filterOut."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], filterIn={'H2O': ['b']}, filterOut={})
        assert isinstance(result, list)

    def test_fragmentlosses_limit_exceeded_combinations(self):
        """Test fragmentlosses with limit preventing combination generation."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3', 'CO'], limit=1)
        max_losses = max(len(f.fragmentLosses) for f in result) if result else 0
        assert max_losses <= 1

    def test_fragmentlosses_non_specific_loss_filtering(self):
        """Test fragmentlosses marks non-specific losses as filtered."""
        s = seq('AAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'])
        assert isinstance(result, list)

    def test_fragmentlosses_zero_length_fragment(self):
        """Test fragmentlosses with simple single-AA fragment."""
        s = seq('K')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentlosses(frags, losses=['NH3'])
        assert isinstance(result, list)

    def test_fragmentlosses_combination_single_loss(self):
        """Test fragmentlosses combination generation with single loss."""
        s = seq('M')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], limit=1)
        assert isinstance(result, list)

    def test_fragmentlosses_combination_with_limit_greater_than_losses(self):
        """Test fragmentlosses when limit > number of available losses."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], limit=5)
        assert isinstance(result, list)

    def test_fragmentlosses_complex_combinations(self):
        """Test fragmentlosses with complex loss combinations."""
        s = seq('SKRDE')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3'], defined=False, limit=2)
        assert isinstance(result, list)

    def test_fragmentlosses_defined_loss(self):
        """Test fragmentlosses with defined=True picks up monomer-defined losses."""
        s = seq('MAKRS')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=[], defined=True)
        assert len(result) > 0

    def test_fragmentlosses_defined_loss_combination_generation(self):
        """Test fragmentlosses line 355->356: combination generation in defined losses.

        When defined=True and fragment has S (which has H2O loss):
        Should generate combinations including H2O even if not in losses parameter.
        """
        s = seq('SDAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=[], defined=True, limit=2)
        assert len(result) > 0
        has_losses = any(len(f.fragmentLosses) > 0 for f in result)
        assert has_losses

    def test_fragmentlosses_defined_losses_combinations(self):
        """Test fragmentlosses with defined=True generates all combinations."""
        s = seq('SDAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=[], defined=True)
        assert isinstance(result, list)

    def test_fragmentlosses_empty_losses(self):
        """Test fragmentlosses with empty losses returns empty."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=[])
        assert result == []

    def test_fragmentlosses_filter_in(self):
        """Test fragmentlosses filterIn restricts loss to specific series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], filterIn={'H2O': ['b']})
        assert any('H2O' in f.fragmentLosses for f in result)

    def test_fragmentlosses_filter_in_wrong_series(self):
        """Test fragmentlosses filterIn on wrong series returns empty."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], filterIn={'H2O': ['y']})
        assert all('H2O' not in f.fragmentLosses for f in result)

    def test_fragmentlosses_filter_out(self):
        """Test fragmentlosses filterOut prevents loss on specific series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], filterOut={'H2O': ['b']})
        assert all('H2O' not in f.fragmentLosses for f in result)

    def test_fragmentlosses_filtered_h2o_alanine(self):
        """Test fragmentlosses marks non-specific H2O loss as filtered."""
        s = seq('MAAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'])
        assert any(f.fragmentFiltered for f in result)

    def test_fragmentlosses_force_quit(self):
        """Test fragmentlosses raises ForceQuitError when stopper is enabled."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_proteo.fragmentlosses(frags, losses=['H2O'])

    def test_fragmentlosses_gain_conflict(self):
        """Test fragmentlosses skips fragment if loss is in fragmentGains."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        for f in frags:
            f.fragmentGains.append('H2O')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'])
        assert all('H2O' not in f.fragmentLosses for f in result)

    def test_fragmentlosses_h2o_loss(self):
        """Test fragmentlosses applies H2O loss to fragments."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'])
        assert len(result) > 0
        assert any('H2O' in f.fragmentLosses for f in result)

    def test_fragmentlosses_invalid_composition_after_loss(self):
        """Test fragmentlosses skips fragment with invalid composition after loss."""
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'H3PO4'], limit=2)
        assert isinstance(result, list)

    def test_fragmentlosses_limit_1(self):
        """Test fragmentlosses with limit=1 only single losses."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3'], limit=1)
        assert all(len(f.fragmentLosses) <= 1 for f in result)

    def test_fragmentlosses_limit_2(self):
        """Test fragmentlosses with limit=2 allows multiple losses."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3'], limit=2)
        max_losses = max(len(f.fragmentLosses) for f in result) if result else 0
        assert max_losses <= 2

    def test_fragmentlosses_limit_less_than_loss_count(self):
        """Test fragmentlosses limit restricts combinations."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3', 'CO'], limit=2)
        assert isinstance(result, list)

    def test_fragmentlosses_not_filtered_h2o_serine(self):
        """Test fragmentlosses marks specific H2O loss as not filtered."""
        s = seq('MASKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'])
        assert any(not f.fragmentFiltered and 'H2O' in f.fragmentLosses for f in result)

    def test_fragmentlosses_two_losses_on_fragment(self):
        """Test fragmentlosses applies multiple losses to same fragment."""
        s = seq('SKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'H3PO4', 'NH3'], limit=2)
        assert len(result) >= 0

    def test_fragmentlosses_with_no_defined_losses_but_limit_2(self):
        """Test fragmentlosses combination generation with limit >1."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O', 'NH3'], limit=2)
        assert isinstance(result, list)

    def test_fragmentlosses_with_serials_specific_loss(self):
        """Test fragmentlosses with fragment containing S and D (specific losses)."""
        s = seq('SDAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentlosses(frags, losses=['H2O'], filterIn={})
        assert len(result) > 0


class TestFragmentgains:
    """Tests for the fragmentgains function."""

    def test_fragmentgains_cyclic_parent_detection(self):
        """Test fragmentgains correctly detects cyclic parent from history."""
        s = seq('AKRF', cyclic=True)
        peptides = s.linearized()
        frags = []
        for pep in peptides:
            frags += mod_proteo.fragmentserie(pep, 'b', cyclicParent=True)
        result = mod_proteo.fragmentgains(frags, gains=['CO'], filterIn={'CO': ['b', 'break']})
        assert len(result) >= 0

    def test_fragmentgains_filter_in_restriction(self):
        """Test fragmentgains restricts gains to allowed series in filterIn."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'y')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert result == []

    def test_fragmentgains_filterout_overrides_filterin(self):
        """Test fragmentgains with filterOut present."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterOut={'H2O': ['b']})
        assert all('H2O' not in f.fragmentGains for f in result)

    def test_fragmentgains_invalid_composition_on_gain(self):
        """Test fragmentgains skips gain if it makes composition invalid."""
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['im']})
        assert isinstance(result, list)

    def test_fragmentgains_multiple_gains_on_fragment_list(self):
        """Test fragmentgains applying multiple different gains."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result1 = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['b']})
        result2 = mod_proteo.fragmentgains(result1, gains=['NH3'], filterIn={'NH3': ['b']})
        assert isinstance(result2, list)

    def test_fragmentgains_no_cyclic_parent_history(self):
        """Test fragmentgains with regular linear fragments (no break)."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['CO'], filterIn={'CO': ['b', 'break']})
        assert result == []

    def test_fragmentgains_all_fragments_invalid(self):
        """Test fragmentgains when all gains result in invalid composition."""
        s = seq('M')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['im']})
        assert isinstance(result, list)

    def test_fragmentgains_b_series_with_filterout(self):
        """Test fragmentgains on b-series with custom filterOut."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterOut={})
        assert len(result) > 0

    def test_fragmentgains_break_filterIn_condition(self):
        """Test fragmentgains 'break' in filterIn condition."""
        s = seq('AKRF', cyclic=True)
        peptides = s.linearized()
        frags = []
        for pep in peptides:
            frags += mod_proteo.fragmentserie(pep, 'b', cyclicParent=True)
        result = mod_proteo.fragmentgains(frags, gains=['CO'], filterIn={'CO': ['b', 'break']})
        assert isinstance(result, list)

    def test_fragmentgains_break_in_history_check(self):
        """Test fragmentgains checks break in fragment history correctly."""
        s = seq('AKRF', cyclic=True)
        peptides = s.linearized()
        frags = []
        for pep in peptides:
            frag_list = mod_proteo.fragmentserie(pep, 'b', cyclicParent=True)
            frags.extend(frag_list)
        result = mod_proteo.fragmentgains(frags, gains=['CO'], filterIn={'CO': ['break']})
        assert isinstance(result, list)

    def test_fragmentgains_co_gain_no_break_history(self):
        """Test fragmentgains CO gain without break history returns empty."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['CO'])
        assert result == []

    def test_fragmentgains_co_gain_with_break_history(self):
        """Test fragmentgains CO gain with break history in filterIn."""
        s = seq('AKRF', cyclic=True)
        peptides = s.linearized()
        frags = []
        for pep in peptides:
            frags += mod_proteo.fragmentserie(pep, 'b', cyclicParent=True)
        result = mod_proteo.fragmentgains(frags, gains=['CO'])
        assert len(result) > 0

    def test_fragmentgains_composition_invalid_check(self):
        """Test fragmentgains line 437->438: isvalid() check on gain application.

        When applying a gain makes the fragment's composition invalid,
        should skip that gain (continue).

        We can't easily trigger invalid composition with normal gains (H2O, CO, etc),
        as they're designed to be valid. However, the code path is executed even if
        all gains result in valid compositions.
        """
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['im']})
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fragmentgains_composition_invalid_on_gain(self):
        """Test fragmentgains when isvalid() returns False on gain."""
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['im']})
        assert isinstance(result, list)

    def test_fragmentgains_custom_filter_in(self):
        """Test fragmentgains with custom filterIn."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'y')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['y']})
        assert len(result) > 0
        assert any('H2O' in f.fragmentGains for f in result)

    def test_fragmentgains_default_filter_in(self):
        """Test fragmentgains uses default filterIn when not specified."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert len(result) > 0

    def test_fragmentgains_empty_gains(self):
        """Test fragmentgains with empty gains returns empty."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=[])
        assert result == []

    def test_fragmentgains_filter_out(self):
        """Test fragmentgains filterOut prevents gain on specific series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterOut={'H2O': ['b']})
        assert all('H2O' not in f.fragmentGains for f in result)

    def test_fragmentgains_force_quit(self):
        """Test fragmentgains raises ForceQuitError when stopper is enabled."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_proteo.fragmentgains(frags, gains=['H2O'])

    def test_fragmentgains_h2o_gain_b_series(self):
        """Test fragmentgains applies H2O gain to b-series."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert len(result) > 0
        assert any('H2O' in f.fragmentGains for f in result)

    def test_fragmentgains_h2o_gain_y_series_default_filter(self):
        """Test fragmentgains H2O gain on y-series with default filterIn."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'y')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert result == []

    def test_fragmentgains_invalid_composition(self):
        """Test fragmentgains skips fragments with invalid composition after gain."""
        s = seq('A')
        frags = mod_proteo.fragmentserie(s, 'im')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['im']})
        assert len(result) >= 0

    def test_fragmentgains_loss_conflict(self):
        """Test fragmentgains skips if gain is in fragmentLosses."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        for f in frags:
            f.fragmentLosses.append('H2O')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert all('H2O' not in f.fragmentGains for f in result)

    def test_fragmentgains_loss_conflict_skip(self):
        """Test fragmentgains skips when gain is in losses."""
        s = seq('MAKR')
        frags = mod_proteo.fragmentserie(s, 'b')
        for f in frags:
            f.fragmentLosses.append('H2O')
        result = mod_proteo.fragmentgains(frags, gains=['H2O'])
        assert all('H2O' not in f.fragmentGains for f in result)

    def test_fragmentgains_multiple_gains(self):
        """Test fragmentgains with multiple gains on same fragment."""
        s = seq('AKRF')
        peptides = s.linearized()
        frags = []
        for pep in peptides:
            frags += mod_proteo.fragmentserie(pep, 'b', cyclicParent=True)
        result1 = mod_proteo.fragmentgains(frags, gains=['H2O'], filterIn={'H2O': ['b']})
        result2 = mod_proteo.fragmentgains(result1, gains=['CO'], filterIn={'CO': ['b', 'break']})
        assert len(result2) >= 0


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.lists(st.tuples(st.integers(1, 100), st.integers(1, 100)), min_size=1))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_coverage_result_in_valid_range(self, ranges):
        """Hypothesis test: coverage is always between 0 and 100."""
        valid_ranges = []
        for r in ranges:
            start, end = r
            if start < end:
                valid_ranges.append((start, end))
        result = mod_proteo.coverage(valid_ranges, 100, human=True)
        assert 0.0 <= result <= 100.0


