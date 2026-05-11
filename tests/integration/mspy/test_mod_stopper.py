import contextlib

import pytest

from mmass.mspy import mod_stopper

# ============================================================================
# Integration tests with singleton STOPPER
# ============================================================================

@pytest.mark.integration
def test_singleton_stopper_and_stop_start_integration():
    """Test integration of singleton STOPPER with stop() and start()."""
    mod_stopper.start()
    assert mod_stopper.STOPPER.value is False

    mod_stopper.stop()
    assert mod_stopper.STOPPER.value is True

    mod_stopper.start()
    assert mod_stopper.STOPPER.value is False


@pytest.mark.integration
def test_check_force_quit_function_references_singleton():
    """Test that CHECK_FORCE_QUIT function operates on singleton STOPPER."""
    mod_stopper.stop()
    assert mod_stopper.STOPPER.value is True

    with contextlib.suppress(mod_stopper.ForceQuitError):
        mod_stopper.CHECK_FORCE_QUIT()

    assert mod_stopper.STOPPER.value is False


@pytest.mark.integration
def test_multiple_stopper_instances_are_independent():
    """Test that multiple stopper instances are independent."""
    s1 = mod_stopper.Stopper()
    s2 = mod_stopper.Stopper()

    s1.enable()
    assert s1.value is True
    assert s2.value is False

    s2.enable()
    assert s1.value is True
    assert s2.value is True

    s1.disable()
    assert s1.value is False
    assert s2.value is True
