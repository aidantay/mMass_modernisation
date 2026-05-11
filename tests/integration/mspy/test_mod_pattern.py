import pytest

from mmass.mspy import mod_pattern, mod_stopper

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
def test_integration_pattern_with_charge_and_agent():
    """Integration test: pattern with charge and agent formula."""
    mod_stopper.start()
    result = mod_pattern.pattern(
        "H2O",
        fwhm=0.05,
        threshold=0.01,
        charge=1,
        agentFormula="H",
        agentCharge=1,
        real=False,
        model="gaussian",
    )
    assert isinstance(result, list)
    assert all(isinstance(peak, list) for peak in result)
    assert all(len(peak) == 2 for peak in result)


@pytest.mark.integration
def test_integration_pattern_multiple_compounds():
    """Integration test: pattern for various compounds."""
    mod_stopper.start()
    compounds = ["H2O", "CH4", "C6H12O6"]
    for compound_str in compounds:
        result = mod_pattern.pattern(compound_str, fwhm=0.1, threshold=0.01, real=False)
        assert isinstance(result, list)
        assert len(result) >= 1


@pytest.mark.integration
def test_integration_consolidate_with_multiple_calls():
    """Integration test: multiple _consolidate calls with different windows."""
    isotopes = [[100.0, 0.2], [100.05, 0.3], [100.15, 0.1], [100.3, 0.4]]
    result1 = mod_pattern._consolidate(isotopes, 0.05)
    result2 = mod_pattern._consolidate(isotopes, 0.2)
    result3 = mod_pattern._consolidate(isotopes, 0.5)

    # Larger window = fewer peaks
    assert len(result1) >= len(result2)
    assert len(result2) >= len(result3)
