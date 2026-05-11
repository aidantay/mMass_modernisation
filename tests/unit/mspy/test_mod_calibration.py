import hypothesis.strategies as st
import numpy as np
import pytest
from hypothesis import given, settings

from mmass.mspy import mod_calibration


class TestDerivVar:
    """Tests for _DerivVar initialization and basic operations."""

    @pytest.mark.parametrize(
        ("index", "expected_deriv"),
        [
            (0, [1]),
            (1, [0, 1]),
            (2, [0, 0, 1]),
        ],
        ids=["index_0", "index_1", "index_2"]
    )
    def test_init_with_index(self, index, expected_deriv):
        """Test _DerivVar initialization with integer index."""
        # Arrange
        value = 10.0

        # Act
        dv = mod_calibration._DerivVar(value, index)

        # Assert
        assert dv.value == value
        assert dv.deriv == expected_deriv

    def test_init_with_list(self):
        """Test _DerivVar initialization with explicit derivative list."""
        dv = mod_calibration._DerivVar(10.0, [1, 2, 3])
        assert dv.value == 10.0
        assert dv.deriv == [1, 2, 3]

    def test_mapderiv(self):
        """Test internal _mapderiv method."""
        dv = mod_calibration._DerivVar(1.0, 0)
        # [1, 2] and [3, 4, 5] -> [1+3, 2+4, 0+5] = [4, 6, 5]
        res = dv._mapderiv(lambda a, b: a + b, [1, 2], [3, 4, 5])
        assert res == [4, 6, 5]

    def test_getitem(self):
        """Test _DerivVar __getitem__ (index access)."""
        dv = mod_calibration._DerivVar(10.0, [1, 2])
        assert dv[0] == 10.0
        assert dv[1] == [1, 2]
        with pytest.raises(IndexError):
            _ = dv[2]

    def test_cmp(self):
        """Test _DerivVar __cmp__ (comparisons)."""
        dv1 = mod_calibration._DerivVar(10.0, 0)
        dv2 = mod_calibration._DerivVar(20.0, 0)
        dv3 = mod_calibration._DerivVar(10.0, 1)

        assert dv1 < dv2
        assert dv1 <= dv2
        assert dv2 > dv1
        assert dv2 >= dv1
        assert dv1 == dv3
        assert dv1 != dv2

        # compare with scalar
        assert dv1 < 15.0
        assert dv1 == 10.0
        assert dv2 > 15.0

    def test_abs(self):
        """Test _DerivVar __abs__."""
        dv = mod_calibration._DerivVar(-10.0, [1, 2])
        # abs(-10) = 10
        # d/dx(abs(x)) = x/abs(x) = -10/10 = -1
        # deriv = [-1*1, -1*2] = [-1, -2]
        res = abs(dv)
        assert res.value == 10.0
        assert res.deriv == [-1.0, -2.0]

        dv2 = mod_calibration._DerivVar(10.0, [1, 2])
        # d/dx(abs(x)) = 10/10 = 1
        # deriv = [1*1, 1*2] = [1, 2]
        res2 = abs(dv2)
        assert res2.value == 10.0
        assert res2.deriv == [1.0, 2.0]


class TestDerivVarArithmetic:
    """Tests for _DerivVar arithmetic operations."""

    def test_add_derivvar(self):
        """Test _DerivVar __add__ with another _DerivVar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])
        dv2 = mod_calibration._DerivVar(20.0, [0, 1])

        # Act
        res = dv1 + dv2

        # Assert
        assert res.value == 30.0
        assert res.deriv == [1, 1]
        assert res is not dv1  # should be new object
        assert res is not dv2

    def test_add_scalar(self):
        """Test _DerivVar __add__ with a scalar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])

        # Act
        res = dv1 + 5.0

        # Assert
        assert res.value == 15.0
        assert res.deriv == [1, 0]

    def test_radd_inplace(self):
        """Test _DerivVar __radd__ which is unexpectedly IN-PLACE."""
        dv = mod_calibration._DerivVar(10.0, [1, 0])
        # 5.0 + dv should call dv.__radd__(5.0)
        res = 5.0 + dv
        assert res.value == 15.0
        assert res.deriv == [1, 0]
        assert res is dv  # IN-PLACE modification confirmed
        assert dv.value == 15.0

        # dv1 + dv2 usually calls dv1.__add__(dv2)
        # but if dv1.__add__ is not available or returns NotImplemented...
        # Let's test dv + dv in __radd__ specifically
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])
        dv2 = mod_calibration._DerivVar(20.0, [0, 1])
        res2 = dv1.__radd__(dv2)
        assert res2 is dv1
        assert dv1.value == 30.0
        assert dv1.deriv == [1, 1]

    def test_sub_derivvar(self):
        """Test _DerivVar __sub__ with another _DerivVar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(30.0, [1, 0])
        dv2 = mod_calibration._DerivVar(10.0, [0, 1])

        # Act
        res = dv1 - dv2

        # Assert
        assert res.value == 20.0
        assert res.deriv == [1, -1]

    def test_sub_scalar(self):
        """Test _DerivVar __sub__ with a scalar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(30.0, [1, 0])

        # Act
        res = dv1 - 5.0

        # Assert
        assert res.value == 25.0
        assert res.deriv == [1, 0]

    def test_rsub_inplace_bug(self):
        """Test _DerivVar __rsub__ which is IN-PLACE and has a REVERSE SUBTRACTION BUG."""
        dv = mod_calibration._DerivVar(10.0, [1, 0])
        # 30.0 - dv should call dv.__rsub__(30.0)
        # Expected: 30.0 - 10.0 = 20.0
        # Implementation: self.value -= other => 10.0 - 30.0 = -20.0
        res = 30.0 - dv
        assert res is dv
        assert dv.value == -20.0  # Confirming the bug
        assert dv.deriv == [1, 0]

        # dv1.__rsub__(dv2)
        dv1 = mod_calibration._DerivVar(30.0, [1, 0])
        dv2 = mod_calibration._DerivVar(10.0, [0, 1])
        res2 = dv1.__rsub__(dv2)
        assert res2 is dv1
        assert dv1.value == 20.0
        assert dv1.deriv == [1, -1]

    def test_mul_derivvar(self):
        """Test _DerivVar __mul__ with another _DerivVar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])
        dv2 = mod_calibration._DerivVar(5.0, [0, 1])

        # Act
        res = dv1 * dv2

        # Assert
        assert res.value == 50.0
        assert res.deriv == [5, 10]

    def test_mul_scalar(self):
        """Test _DerivVar __mul__ with a scalar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])

        # Act
        res = dv1 * 2.0

        # Assert
        assert res.value == 20.0
        assert res.deriv == [2, 0]

    def test_div_derivvar(self):
        """Test _DerivVar __div__ with another _DerivVar."""
        # Arrange
        dv1 = mod_calibration._DerivVar(10.0, [1, 0])
        dv2 = mod_calibration._DerivVar(5.0, [0, 1])

        # Act
        res = dv1 / dv2

        # Assert
        assert res.value == 2.0
        assert res.deriv == [0.2, -0.4]

    def test_div_scalar_bug(self):
        """Test _DerivVar __div__ and the NameError bug for scalar divisor."""
        # Arrange
        dv = mod_calibration._DerivVar(10.0, [1, 0])

        # Act
        res = dv / 2.0

        # Assert
        assert res == 5.0

    def test_pow(self):
        """Test _DerivVar __pow__."""
        dv = mod_calibration._DerivVar(3.0, [1, 0])
        # x^2
        # d/dx(x^2) = 2x
        # value = 3^2 = 9
        # deriv = [2*3 * 1, 2*3 * 0] = [6, 0]
        res = dv**2
        assert res.value == 9.0
        assert res.deriv == [6.0, 0.0]

        # x^3
        # d/dx(x^3) = 3x^2
        # value = 3^3 = 27
        # deriv = [3*3^2 * 1, 3*3^2 * 0] = [27, 0]
        res2 = dv**3
        assert res2.value == 27.0
        assert res2.deriv == [27.0, 0.0]


class TestModels:
    """Tests for linear and quadratic model functions."""

    @pytest.mark.parametrize(
        ("params", "x", "expected"),
        [
            ((1.0, 0.0), 10.0, 10.0),  # y = 1*x + 0
            ((2.0, 5.0), 10.0, 25.0),  # y = 2*x + 5
            ((0.5, -2.0), 4.0, 0.0),   # y = 0.5*x - 2
        ],
    )
    def test_linear_model_math(self, params, x, expected):
        """Verify linear model calculation."""
        # Arrange
        # Handled by parametrize
        
        # Act
        res = mod_calibration._linearModel(params, x)
        
        # Assert
        assert res == expected

    @pytest.mark.parametrize(
        ("params", "x", "expected"),
        [
            ((1.0, 0.0, 0.0), 10.0, 100.0),  # y = 1*x^2 + 0*x + 0
            ((1.0, 2.0, 3.0), 2.0, 11.0),    # y = 1*2^2 + 2*2 + 3 = 4 + 4 + 3 = 11
            ((0.5, -1.0, 5.0), 4.0, 9.0),    # y = 0.5*4^2 - 1*4 + 5 = 8 - 4 + 5 = 9
        ],
    )
    def test_quadratic_model_math(self, params, x, expected):
        """Verify quadratic model calculation."""
        # Arrange
        # Handled by parametrize
        
        # Act
        res = mod_calibration._quadraticModel(params, x)
        
        # Assert
        assert res == expected

    def test_models_with_derivvar(self):
        """Verify models work with _DerivVar for automatic differentiation."""
        # Arrange
        params = (mod_calibration._DerivVar(2.0, 0), mod_calibration._DerivVar(5.0, 1))
        
        # Act
        res = mod_calibration._linearModel(params, 10.0)
        
        # Assert
        assert res.value == 25.0
        assert res.deriv == [10.0, 1.0]

        # Arrange (Quadratic)
        params_q = (
            mod_calibration._DerivVar(1.0, 0),
            mod_calibration._DerivVar(2.0, 1),
            mod_calibration._DerivVar(3.0, 2),
        )
        
        # Act
        res_q = mod_calibration._quadraticModel(params_q, 2.0)
        
        # Assert
        assert res_q.value == 11.0
        assert res_q.deriv == [4.0, 2.0, 1.0]


class TestFitting:
    """Tests for chi-square calculation and least-squares fitting."""

    def test_chi_square_basic(self):
        """Test _chiSquare calculation with simple data."""
        params = (
            mod_calibration._DerivVar(2.0, 0),
            mod_calibration._DerivVar(5.0, 1)
        )
        data = [(10.0, 25.0)]
        chi_sq, alpha = mod_calibration._chiSquare(
            mod_calibration._linearModel, params, data
        )

        assert chi_sq.value == 0.0
        assert chi_sq.deriv == [0.0, 0.0]
        assert np.allclose(alpha, [[100.0, 10.0], [10.0, 1.0]])

        # Another point with error: y_ref = 26, y_calc = 2*10+5 = 25
        # diff = y_calc - y_ref = -1
        # chi_sq = (-1)^2 = 1
        # d(chi_sq)/da = 2*diff * df/da = 2*(-1) * 10 = -20
        # d(chi_sq)/db = 2*diff * df/db = 2*(-1) * 1 = -2
        data2 = [(10.0, 26.0)]
        chi_sq2, alpha2 = mod_calibration._chiSquare(
            mod_calibration._linearModel, params, data2
        )
        assert chi_sq2.value == 1.0
        assert chi_sq2.deriv == [-20.0, -2.0]
        assert np.allclose(alpha2, [[100.0, 10.0], [10.0, 1.0]])

    def test_least_squares_fit_convergence(self):
        """Test _leastSquaresFit convergence on a simple linear dataset."""
        # Data: y = 2x + 5
        data = [(0.0, 5.0), (1.0, 7.0), (2.0, 9.0)]
        initials = (1.0, 0.0)  # Start away from (2, 5)

        params, chi_sq = mod_calibration._leastSquaresFit(
            mod_calibration._linearModel, initials, data
        )

        assert params[0] == pytest.approx(2.0)
        assert params[1] == pytest.approx(5.0)
        assert chi_sq == pytest.approx(0.0)

    def test_least_squares_fit_branches(self, mocker):
        """Test _leastSquaresFit branches: increased damping and convergence."""
        data = [(1.0, 1.0)]
        initials = (1.0, 1.0)
        base_alpha = np.array([[10.0, 0.0], [0.0, 10.0]])

        # We need to control _chiSquare returns to force branches
        initial_chi_sq = mod_calibration._DerivVar(100.0, [10.0, 1.0])          # Initial call to _chiSquare (before loop)
        higher_chi_sq = mod_calibration._DerivVar(110.0, [5.0, 0.5])            # 1st loop call to _chiSquare: next_chi_sq > chi_sq (trigger dampin increase)
        better_chi_sq = mod_calibration._DerivVar(90.0, [2.0, 0.2])             # 2nd loop all to _chiSquare: next_chi_sq < chi_sq, difference > limit (trigger success branch)
        converged_chi_sq = mod_calibration._DerivVar(89.99999999, [0.1, 0.01])  # 3rd loop call to _chiSquare: next_chi_sq < better_chi_sq, difference < limit (trigger convergence break)

        mock_chi_sq = mocker.patch("mmass.mspy.mod_calibration._chiSquare")
        mock_chi_sq.side_effect = [
            (initial_chi_sq, base_alpha),    # Before loop
            (higher_chi_sq, base_alpha),     # 1st iteration: 110 > 100 -> l *= 10
            (better_chi_sq, base_alpha),     # 2nd iteration: 90 < 100 -> l *= 0.1, chi_sq = 90
            (converged_chi_sq, base_alpha),  # 3rd iteration: 90 - 89.999... < limit -> break
        ]

        _params, chi_sq_val = mod_calibration._leastSquaresFit(
            mod_calibration._linearModel, initials, data
        )

        assert mock_chi_sq.call_count == 4
        assert chi_sq_val == 89.99999999

    def test_least_squares_fit_max_iterations(self, mocker):
        """Test _leastSquaresFit maxIterations break."""
        data = [(1.0, 1.0)]
        initials = (1.0, 1.0)

        # Simple side effect that avoids convergence
        def side_effect(model, p, data):
            val = getattr(side_effect, "val", 100.0)
            side_effect.val = val - 1.0
            return (mod_calibration._DerivVar(val, [1.0, 1.0]), np.identity(2))

        mock_chi_sq = mocker.patch("mmass.mspy.mod_calibration._chiSquare")
        mock_chi_sq.side_effect = side_effect

        # maxIterations=2
        _params, _chi_sq_val = mod_calibration._leastSquaresFit(
            mod_calibration._linearModel, initials, data, maxIterations=2
        )

        # Called once before loop, and twice in loop (niter=1, niter=2)
        assert mock_chi_sq.call_count == 3


class TestCalibration:
    """Integration tests for the calibration high-level function."""

    def test_calibration_single_point(self):
        """Test single-point linear calibration bypass."""
        # Arrange
        data = [(100.0, 100.5)]

        # Act
        model_fn, params, chi_sq = mod_calibration.calibration(data, model="linear")

        # Assert
        assert model_fn == mod_calibration._linearModel
        assert params == (1.0, 0.5)
        assert chi_sq == 1.0

    def test_calibration_linear_multi(self):
        """Test multi-point linear calibration."""
        # Arrange
        data = [(100.0, 101.0), (200.0, 201.0)]
        
        # Act
        model_fn, params, chi_sq = mod_calibration.calibration(data, model="linear")

        # Assert
        assert model_fn == mod_calibration._linearModel
        assert params[0] == pytest.approx(1.0)
        assert params[1] == pytest.approx(1.0)
        assert chi_sq < 1e-7

    def test_calibration_quadratic(self):
        """Test multi-point quadratic calibration."""
        # Arrange
        def f(x):
            return 0.5 * x * x + 2 * x + 10

        data = [(0.0, f(0.0)), (1.0, f(1.0)), (2.0, f(2.0)), (3.0, f(3.0))]

        # Act
        model_fn, params, chi_sq = mod_calibration.calibration(data, model="quadratic")

        # Assert
        assert model_fn == mod_calibration._quadraticModel
        assert params[0] == pytest.approx(0.5)
        assert params[1] == pytest.approx(2.0)
        assert params[2] == pytest.approx(10.0)
        assert chi_sq < 1e-7

    def test_calibration_invalid_model_error(self):
        """Test invalid model string triggers UnboundLocalError."""
        # Arrange
        data = [(100.0, 101.0), (200.0, 201.0)]

        # Act / Assert
        with pytest.raises(UnboundLocalError):
            mod_calibration.calibration(data, model="cubic")


@pytest.mark.slow
class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @settings(deadline=500)
    @given(
        v1=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
        d1=st.lists(
            st.floats(
                min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
        v2=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
        d2=st.lists(
            st.floats(
                min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
    )
    def test_add_fuzz(self, v1, d1, v2, d2):
        """Fuzz _DerivVar addition."""
        dv1 = mod_calibration._DerivVar(v1, d1)
        dv2 = mod_calibration._DerivVar(v2, d2)
        res = dv1 + dv2
        assert res.value == v1 + v2
        nvars = max(len(d1), len(d2))
        for i in range(nvars):
            val1 = d1[i] if i < len(d1) else 0.0
            val2 = d2[i] if i < len(d2) else 0.0
            assert res.deriv[i] == val1 + val2

    @settings(deadline=500)
    @given(
        v1=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
        d1=st.lists(
            st.floats(
                min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
        v2=st.floats(
            min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
        ),
        d2=st.lists(
            st.floats(
                min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
    )
    def test_sub_fuzz(self, v1, d1, v2, d2):
        """Fuzz _DerivVar subtraction."""
        dv1 = mod_calibration._DerivVar(v1, d1)
        dv2 = mod_calibration._DerivVar(v2, d2)
        res = dv1 - dv2
        assert res.value == v1 - v2
        nvars = max(len(d1), len(d2))
        for i in range(nvars):
            val1 = d1[i] if i < len(d1) else 0.0
            val2 = d2[i] if i < len(d2) else 0.0
            assert res.deriv[i] == val1 - val2

    @settings(deadline=500)
    @given(
        v1=st.floats(
            min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False
        ),
        d1=st.lists(
            st.floats(
                min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
        v2=st.floats(
            min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False
        ),
        d2=st.lists(
            st.floats(
                min_value=-1e5, max_value=1e5, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=3,
        ),
    )
    def test_mul_fuzz(self, v1, d1, v2, d2):
        """Fuzz _DerivVar multiplication."""
        dv1 = mod_calibration._DerivVar(v1, d1)
        dv2 = mod_calibration._DerivVar(v2, d2)
        res = dv1 * dv2
        assert res.value == v1 * v2
        nvars = max(len(d1), len(d2))
        for i in range(nvars):
            val1 = d1[i] if i < len(d1) else 0.0
            val2 = d2[i] if i < len(d2) else 0.0
            expected_deriv = val1 * v2 + v1 * val2
            assert res.deriv[i] == pytest.approx(expected_deriv)

