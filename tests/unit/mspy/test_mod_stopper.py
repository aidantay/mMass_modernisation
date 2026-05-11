import contextlib

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mmass.mspy import mod_stopper


class TestForceQuitError:
    """Tests for ForceQuitError exception."""

    def test_forcequit_is_exception(self):
        """Test that ForceQuitError is a subclass of Exception."""
        assert issubclass(mod_stopper.ForceQuitError, Exception)

    def test_forcequit_raise_and_catch(self):
        """Test that ForceQuitError can be raised and caught."""
        with pytest.raises(mod_stopper.ForceQuitError):
            raise mod_stopper.ForceQuitError()

    def test_forcequit_raise_with_message(self):
        """Test that ForceQuitError can be raised with a message argument."""
        with pytest.raises(mod_stopper.ForceQuitError) as exc_info:
            raise mod_stopper.ForceQuitError("Test message")
        assert str(exc_info.value) == "Test message"


class TestStopper:
    """Tests for the Stopper class."""

    def test_stopper_init_creates_instance(self):
        """Test that Stopper() creates a stopper instance."""
        s = mod_stopper.Stopper()
        assert isinstance(s, mod_stopper.Stopper)

    def test_stopper_init_value_is_false(self):
        """Test that stopper.__init__ sets value to False."""
        s = mod_stopper.Stopper()
        assert s.value is False

    def test_stopper_nonzero_false_initially(self):
        """Test that bool(stopper) is False initially."""
        s = mod_stopper.Stopper()
        assert not s
        assert bool(s) is False

    def test_stopper_nonzero_true_after_enable(self):
        """Test that bool(stopper) is True after enable()."""
        s = mod_stopper.Stopper()
        s.enable()
        assert s
        assert bool(s) is True

    def test_stopper_nonzero_false_after_disable(self):
        """Test that bool(stopper) is False after disable()."""
        s = mod_stopper.Stopper()
        s.enable()
        s.disable()
        assert not s
        assert bool(s) is False

    def test_stopper_repr_false_initially(self):
        """Test that repr(stopper) is 'False' initially."""
        s = mod_stopper.Stopper()
        assert repr(s) == "False"

    def test_stopper_repr_true_after_enable(self):
        """Test that repr(stopper) is 'True' after enable()."""
        s = mod_stopper.Stopper()
        s.enable()
        assert repr(s) == "True"

    def test_stopper_repr_false_after_disable(self):
        """Test that repr(stopper) is 'False' after disable()."""
        s = mod_stopper.Stopper()
        s.enable()
        s.disable()
        assert repr(s) == "False"

    def test_stopper_enable_sets_value_true(self):
        """Test that enable() sets value to True."""
        s = mod_stopper.Stopper()
        s.enable()
        assert s.value is True

    def test_stopper_enable_idempotent(self):
        """Test that calling enable() twice has the same effect as once."""
        s = mod_stopper.Stopper()
        s.enable()
        s.enable()
        assert s.value is True

    def test_stopper_disable_sets_value_false(self):
        """Test that disable() sets value to False."""
        s = mod_stopper.Stopper()
        s.enable()
        s.disable()
        assert s.value is False

    def test_stopper_disable_idempotent(self):
        """Test that calling disable() twice has the same effect as once."""
        s = mod_stopper.Stopper()
        s.enable()
        s.disable()
        s.disable()
        assert s.value is False

    def test_stopper_check_false_does_not_raise(self):
        """Test that check() does not raise when value is False."""
        s = mod_stopper.Stopper()
        s.check()  # Should not raise

    def test_stopper_check_false_value_stays_false(self):
        """Test that check() keeps value as False when initially False."""
        s = mod_stopper.Stopper()
        s.check()
        assert s.value is False

    def test_stopper_check_true_raises_forcequit(self):
        """Test that check() raises ForceQuitError when value is True."""
        s = mod_stopper.Stopper()
        s.enable()
        with pytest.raises(mod_stopper.ForceQuitError):
            s.check()

    def test_stopper_check_true_resets_to_false(self):
        """Test that check() resets value to False after raising ForceQuitError."""
        s = mod_stopper.Stopper()
        s.enable()
        with contextlib.suppress(mod_stopper.ForceQuitError):
            s.check()
        assert s.value is False

    def test_stopper_check_second_call_does_not_raise(self):
        """Test that second call to check() does not raise after reset."""
        s = mod_stopper.Stopper()
        s.enable()
        with contextlib.suppress(mod_stopper.ForceQuitError):
            s.check()
        s.check()  # Should not raise

    def test_stopper_enable_disable_enable_cycle(self):
        """Test enable -> disable -> enable cycle maintains correct state."""
        s = mod_stopper.Stopper()
        s.enable()
        assert s.value is True
        s.disable()
        assert s.value is False
        s.enable()
        assert s.value is True

    def test_stopper_check_after_multiple_enables(self):
        """Test check() after multiple consecutive enables."""
        s = mod_stopper.Stopper()
        s.enable()
        s.enable()
        s.enable()
        with pytest.raises(mod_stopper.ForceQuitError):
            s.check()
        assert s.value is False

    def test_stopper_disable_after_check_reset(self):
        """Test disable() after check() has reset the value."""
        s = mod_stopper.Stopper()
        s.enable()
        with contextlib.suppress(mod_stopper.ForceQuitError):
            s.check()
        s.disable()
        assert s.value is False


class TestModuleFunctions:
    """Tests for module-level functions in mod_stopper."""

    def test_stopper_singleton_is_instance(self):
        """Test that STOPPER is an instance of stopper class."""
        assert isinstance(mod_stopper.STOPPER, mod_stopper.Stopper)

    def test_stopper_singleton_initial_state(self):
        """Test that STOPPER initial state is False after start()."""
        mod_stopper.start()
        assert mod_stopper.STOPPER.value is False

    def test_check_force_quit_is_stopper_check(self):
        """Test that CHECK_FORCE_QUIT is a reference to STOPPER.check."""
        assert mod_stopper.STOPPER.check == mod_stopper.CHECK_FORCE_QUIT

    def test_stop_sets_stopper_value_true(self):
        """Test that stop() sets STOPPER.value to True."""
        mod_stopper.stop()
        assert mod_stopper.STOPPER.value is True

    def test_start_sets_stopper_value_false(self):
        """Test that start() sets STOPPER.value to False."""
        mod_stopper.stop()
        mod_stopper.start()
        assert mod_stopper.STOPPER.value is False

    def test_stop_then_check_force_quit_raises(self):
        """Test that stop() followed by CHECK_FORCE_QUIT() raises ForceQuitError."""
        mod_stopper.stop()
        with pytest.raises(mod_stopper.ForceQuitError):
            mod_stopper.CHECK_FORCE_QUIT()

    def test_stop_then_check_force_quit_resets(self):
        """Test that CHECK_FORCE_QUIT() resets STOPPER after raising."""
        mod_stopper.stop()
        with contextlib.suppress(mod_stopper.ForceQuitError):
            mod_stopper.CHECK_FORCE_QUIT()
        assert mod_stopper.STOPPER.value is False

    def test_start_then_check_force_quit_does_not_raise(self):
        """Test that start() followed by CHECK_FORCE_QUIT() does not raise."""
        mod_stopper.start()
        mod_stopper.CHECK_FORCE_QUIT()  # Should not raise


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.booleans())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_stopper_enable_disable_produces_valid_bool(self, enabled):
        """Test that enable/disable sequences always produce valid bool values."""
        s = mod_stopper.Stopper()
        if enabled:
            s.enable()
        else:
            s.disable()
        # Verify result is always a boolean
        result = bool(s)
        assert isinstance(result, bool)
        assert result is (s.value is True)

    @given(st.booleans())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_stopper_check_always_resets_value_to_false(self, enabled):
        """Test that after check(), value is always False (regardless of initial state)."""
        s = mod_stopper.Stopper()
        if enabled:
            s.enable()

        with contextlib.suppress(mod_stopper.ForceQuitError):
            s.check()

        # After check(), value must always be False
        assert s.value is False

    @given(st.lists(st.booleans(), min_size=1, max_size=10))
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_stopper_state_transitions_hypothesis(self, operations):
        """Test stopper with random sequences of enable/disable operations."""
        s = mod_stopper.Stopper()
        for op in operations:
            if op:
                s.enable()
            else:
                s.disable()

        # After operations, value should match the last operation
        expected_value = operations[-1] if operations else False
        assert s.value is expected_value
        assert bool(s) is expected_value
