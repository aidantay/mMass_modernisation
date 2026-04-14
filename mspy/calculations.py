import numpy as np
import scipy.ndimage


def signal_median(inarr: np.ndarray) -> float:
    """Calculate the median of an array."""
    if inarr.size == 0:
        return 0.0
    return float(np.median(inarr))


def signal_interpolate_x(x1: float, y1: float, x2: float, y2: float, y: float) -> float:
    """Linearly interpolate the x-value given y."""
    if x1 == x2:
        return float(x1)
    dy = y2 - y1
    if dy == 0:
        return float('inf')
    a = dy / (x2 - x1)
    if a == 0:
        return float('inf')
    b = y1 - a * x1
    return float((y - b) / a)


def signal_interpolate_y(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """Linearly interpolate the y-value given x."""
    if y1 == y2:
        return float(y1)
    dx = x2 - x1
    if dx == 0:
        return float('nan')
    a = (y2 - y1) / dx
    b = y1 - a * x1
    return float(a * x + b)


def signal_locate_x(p_signal: np.ndarray, x: float) -> int:
    """Find the array index for insertion such that elements to the left are <= x."""
    if p_signal.size == 0:
        return 0
    return int(np.searchsorted(p_signal[:, 0], x, side='right'))


def signal_locate_max_y(p_signal: np.ndarray) -> int:
    """Return the index of the maximum y-value."""
    if p_signal is None or not isinstance(p_signal, np.ndarray):
        raise TypeError("Input must be a numpy array")
    if p_signal.size == 0:
        return 0
    return int(np.argmax(p_signal[:, -1]))


def signal_box(p_signal: np.ndarray) -> tuple[float, float, float, float]:
    """Return the bounding box of the signal as (min_x, min_y, max_x, max_y)."""
    if p_signal.size == 0:
        return (0.0, 0.0, 0.0, 0.0)
    min_x = float(p_signal[0, 0])
    max_x = float(p_signal[-1, 0])
    min_y = float(np.min(p_signal[:, 1]))
    max_y = float(np.max(p_signal[:, 1]))
    return (min_x, min_y, max_x, max_y)


def signal_intensity(p_signal: np.ndarray, x: float) -> float:
    """Return the interpolated y-value at a given x."""
    if p_signal.size == 0:
        return 0.0
    idx = signal_locate_x(p_signal, x)
    if idx == 0 or idx == p_signal.shape[0]:
        return 0.0
    x1, y1 = p_signal[idx - 1]
    x2, y2 = p_signal[idx]
    return signal_interpolate_y(float(x1), float(y1), float(x2), float(y2), float(x))


def signal_centroid(p_signal: np.ndarray, x: float, height: float) -> float:
    """Calculates the centroid x-value of a peak at a specified height."""
    idx = signal_locate_x(p_signal, x)
    if idx == 0 or idx == p_signal.shape[0]:
        return 0.0

    y_left = p_signal[:idx, 1]
    below_height_left = np.nonzero(y_left <= height)[0]
    if below_height_left.size > 0:
        ileft = below_height_left[-1]
    else:
        ileft = 0

    y_right = p_signal[idx:, 1]
    below_height_right = np.nonzero(y_right <= height)[0]
    if below_height_right.size > 0:
        iright = idx + below_height_right[0]
    else:
        iright = p_signal.shape[0] - 1

    if ileft == iright:
        return float(p_signal[ileft, 0])

    xleft = signal_interpolate_x(
        float(p_signal[ileft, 0]), float(p_signal[ileft, 1]),
        float(p_signal[ileft + 1, 0]), float(p_signal[ileft + 1, 1]),
        height
    )
    xright = signal_interpolate_x(
        float(p_signal[iright - 1, 0]), float(p_signal[iright - 1, 1]),
        float(p_signal[iright, 0]), float(p_signal[iright, 1]),
        height
    )

    return (xleft + xright) / 2.0


def signal_width(p_signal: np.ndarray, x: float, height: float) -> float:
    """Computes the width of a peak at a specified height."""
    idx = signal_locate_x(p_signal, x)
    if idx == 0 or idx == p_signal.shape[0]:
        return 0.0

    y_left = p_signal[:idx, 1]
    below_height_left = np.nonzero(y_left <= height)[0]
    if below_height_left.size > 0:
        ileft = below_height_left[-1]
    else:
        ileft = 0

    y_right = p_signal[idx:, 1]
    below_height_right = np.nonzero(y_right <= height)[0]
    if below_height_right.size > 0:
        iright = idx + below_height_right[0]
    else:
        iright = p_signal.shape[0] - 1

    if ileft == iright:
        return 0.0

    xleft = signal_interpolate_x(
        float(p_signal[ileft, 0]), float(p_signal[ileft, 1]),
        float(p_signal[ileft + 1, 0]), float(p_signal[ileft + 1, 1]),
        height
    )
    xright = signal_interpolate_x(
        float(p_signal[iright - 1, 0]), float(p_signal[iright - 1, 1]),
        float(p_signal[iright, 0]), float(p_signal[iright, 1]),
        height
    )

    return abs(xright - xleft)


def signal_area(p_signal: np.ndarray) -> float:
    """Calculates the total area under the signal curve using trapezoidal integration."""
    if p_signal.shape[0] < 2:
        return 0.0
    dx = np.diff(p_signal[:, 0])
    y1 = p_signal[:-1, 1]
    y2 = p_signal[1:, 1]
    area = np.sum((y1 * dx) + ((y2 - y1) * dx / 2.0))
    return float(area)


def signal_noise(p_signal: np.ndarray) -> tuple[float, float]:
    """Estimates baseline noise level and width."""
    if p_signal.size == 0:
        return 0.0, 0.0
    y = p_signal[:, 1]
    level = signal_median(y)
    width = signal_median(np.abs(y - level)) * 2.0
    return float(level), float(width)


def signal_local_maxima(p_signal: np.ndarray) -> np.ndarray:
    """Finds local peaks, strictly enforcing an initial rise, and robustly handles plateaus."""
    if p_signal.shape[0] < 3:
        return np.empty((0, 2), dtype=np.double)

    dy = np.diff(p_signal[:, 1])
    non_zero_idx = np.nonzero(dy)[0]
    if non_zero_idx.size < 2:
        return np.empty((0, 2), dtype=np.double)

    non_zero_dy = dy[non_zero_idx]
    is_peak = (non_zero_dy[:-1] > 0) & (non_zero_dy[1:] < 0)
    peak_indices = non_zero_idx[1:][is_peak]

    return np.ascontiguousarray(p_signal[peak_indices], dtype=np.double)


def signal_crop(p_signal: np.ndarray, minX: float, maxX: float) -> np.ndarray:
    """Extracts a sub-region of a signal between minX and maxX."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)

    idx1 = signal_locate_x(p_signal, minX)
    idx2 = signal_locate_x(p_signal, maxX)

    n_points = p_signal.shape[0]
    result = []

    # Left boundary
    if 0 < idx1 < n_points:
        y = signal_interpolate_y(
            float(p_signal[idx1-1, 0]), float(p_signal[idx1-1, 1]),
            float(p_signal[idx1, 0]), float(p_signal[idx1, 1]),
            minX
        )
        result.append([minX, y])
    elif idx1 == n_points and p_signal[-1, 0] == minX:
        result.append(p_signal[-1])

    # Inner points
    if idx1 < idx2:
        result.extend(p_signal[idx1:idx2])

    # Right boundary
    if 0 < idx2 < n_points and p_signal[idx2-1, 0] != maxX:
        y = signal_interpolate_y(
            float(p_signal[idx2-1, 0]), float(p_signal[idx2-1, 1]),
            float(p_signal[idx2, 0]), float(p_signal[idx2, 1]),
            maxX
        )
        result.append([maxX, y])

    if not result:
        return np.empty((0, 2), dtype=np.double)

    return np.ascontiguousarray(result, dtype=np.double)


def signal_offset(p_signal: np.ndarray, x: float, y: float) -> np.ndarray:
    """Applies a constant offset to all X and Y coordinates."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)
    return p_signal + np.array([x, y], dtype=np.double)


def signal_multiply(p_signal: np.ndarray, x: float, y: float) -> np.ndarray:
    """Scales all X and Y coordinates by a constant multiplier."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)
    return p_signal * np.array([x, y], dtype=np.double)


def signal_normalize(p_signal: np.ndarray) -> np.ndarray:
    """Divides all Y coordinates by the global maximum Y value."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)

    max_y = np.max(p_signal[:, 1])
    if max_y == 0:
        return np.copy(p_signal)

    result = np.copy(p_signal)
    result[:, 1] /= max_y
    return result


def signal_smooth_ma(p_signal: np.ndarray, window: int, cycles: int) -> np.ndarray:
    """Applies an unweighted moving average filter."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)

    n_points = p_signal.shape[0]
    window = min(window, n_points)
    if window % 2 != 0:
        window -= 1

    if window < 1 or cycles < 1:
        return np.copy(p_signal)

    result = np.copy(p_signal)
    y_vals = result[:, 1]

    ksize = window + 1
    weights = np.ones(ksize) / float(ksize)

    for _ in range(cycles):
        y_vals = scipy.ndimage.convolve1d(y_vals, weights, mode='reflect')

    result[:, 1] = y_vals
    return result


def signal_smooth_ga(p_signal: np.ndarray, window: int, cycles: int) -> np.ndarray:
    """Applies a Gaussian blur filter."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)

    n_points = p_signal.shape[0]
    window = min(window, n_points)
    if window % 2 != 0:
        window -= 1

    if window < 1 or cycles < 1:
        return np.copy(p_signal)

    result = np.copy(p_signal)
    y_vals = result[:, 1]

    ksize = window + 1
    r = np.arange(ksize) - (ksize - 1) / 2.0
    weights = np.exp(-(r**2) / ((ksize**2) / 16.0))
    weights /= np.sum(weights)

    for _ in range(cycles):
        y_vals = scipy.ndimage.convolve1d(y_vals, weights, mode='reflect')

    result[:, 1] = y_vals
    return result


def signal_combine(p_signalA: np.ndarray, p_signalB: np.ndarray) -> np.ndarray:
    """Merges two profile signals by summing intensities at the union of X-coordinates."""
    if p_signalA.size == 0 and p_signalB.size == 0:
        return np.empty((0, 2), dtype=np.double)
    if p_signalA.size == 0:
        return p_signalB.copy()
    if p_signalB.size == 0:
        return p_signalA.copy()

    x_union = np.union1d(p_signalA[:, 0], p_signalB[:, 0])
    yA = np.interp(x_union, p_signalA[:, 0], p_signalA[:, 1], left=0.0, right=0.0)
    yB = np.interp(x_union, p_signalB[:, 0], p_signalB[:, 1], left=0.0, right=0.0)

    result = np.empty((x_union.size, 2), dtype=np.double)
    result[:, 0] = x_union
    result[:, 1] = yA + yB
    return result


def signal_overlay(p_signalA: np.ndarray, p_signalB: np.ndarray) -> np.ndarray:
    """Computes the bounding envelope (maximum intensity) of two signals."""
    if p_signalA.size == 0 and p_signalB.size == 0:
        return np.empty((0, 2), dtype=np.double)
    if p_signalA.size == 0:
        return p_signalB.copy()
    if p_signalB.size == 0:
        return p_signalA.copy()

    x_union = np.union1d(p_signalA[:, 0], p_signalB[:, 0])
    yA = np.interp(x_union, p_signalA[:, 0], p_signalA[:, 1], left=0.0, right=0.0)
    yB = np.interp(x_union, p_signalB[:, 0], p_signalB[:, 1], left=0.0, right=0.0)

    result = np.empty((x_union.size, 2), dtype=np.double)
    result[:, 0] = x_union
    result[:, 1] = np.maximum(yA, yB)
    return result


def signal_subtract(p_signalA: np.ndarray, p_signalB: np.ndarray) -> np.ndarray:
    """Subtracts signal B from signal A (yA - yB) at the union of X-coordinates."""
    if p_signalA.size == 0 and p_signalB.size == 0:
        return np.empty((0, 2), dtype=np.double)
    if p_signalA.size == 0:
        result = p_signalB.copy()
        result[:, 1] = -result[:, 1]
        return result
    if p_signalB.size == 0:
        return p_signalA.copy()

    x_union = np.union1d(p_signalA[:, 0], p_signalB[:, 0])
    yA = np.interp(x_union, p_signalA[:, 0], p_signalA[:, 1], left=0.0, right=0.0)
    yB = np.interp(x_union, p_signalB[:, 0], p_signalB[:, 1], left=0.0, right=0.0)

    result = np.empty((x_union.size, 2), dtype=np.double)
    result[:, 0] = x_union
    result[:, 1] = yA - yB
    return result


def signal_subbase(p_signal: np.ndarray, p_baseline: np.ndarray) -> np.ndarray:
    """Subtracts a baseline from a signal, with linear extrapolation at boundaries."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)
    if p_baseline.size == 0:
        return p_signal.copy()

    result = p_signal.copy()
    if p_baseline.shape[0] == 1:
        result[:, 1] -= p_baseline[0, 1]
    else:
        # Evaluate baseline at signal X-coordinates using linear interpolation
        baseline_y = np.interp(p_signal[:, 0], p_baseline[:, 0], p_baseline[:, 1])

        # Manual linear extrapolation for boundaries (matching C-extension behavior)
        # Left boundary
        left_mask = p_signal[:, 0] < p_baseline[0, 0]
        if np.any(left_mask):
            x1, y1 = p_baseline[0]
            x2, y2 = p_baseline[1]
            dx = x2 - x1
            if dx != 0:
                slope = (y2 - y1) / dx
                baseline_y[left_mask] = y1 + slope * (p_signal[left_mask, 0] - x1)

        # Right boundary
        right_mask = p_signal[:, 0] > p_baseline[-1, 0]
        if np.any(right_mask):
            x1, y1 = p_baseline[-2]
            x2, y2 = p_baseline[-1]
            dx = x2 - x1
            if dx != 0:
                slope = (y2 - y1) / dx
                baseline_y[right_mask] = y2 + slope * (p_signal[right_mask, 0] - x2)

        result[:, 1] -= baseline_y

    # Clip negative intensities to 0.0
    np.clip(result[:, 1], a_min=0.0, a_max=None, out=result[:, 1])
    return result


def signal_rescale(p_signal: np.ndarray, scaleX: float, scaleY: float, shiftX: float, shiftY: float) -> np.ndarray:
    """Applies a linear scaling and translation transformation to an MS signal and rounds the results to integer boundaries."""
    if p_signal.size == 0:
        return np.empty((0, 2), dtype=np.double)

    x_val = p_signal[:, 0] * scaleX + shiftX
    y_val = p_signal[:, 1] * scaleY + shiftY

    result = np.empty(p_signal.shape, dtype=np.double)
    result[:, 0] = np.where(x_val >= 0, np.floor(x_val + 0.5), np.ceil(x_val - 0.5))
    result[:, 1] = np.where(y_val >= 0, np.floor(y_val + 0.5), np.ceil(y_val - 0.5))

    return result


def signal_filter(p_signal: np.ndarray, resol: float) -> np.ndarray:
    """Downsamples an MS signal to a target X-axis resolution, preserving local minima and maxima."""
    if p_signal.shape[0] <= 1 or resol <= 0:
        return p_signal.copy()

    n_points = p_signal.shape[0]
    # Buffer to store result points. Each input point can result in up to 4 points.
    p_buff = np.empty((4 * n_points, 2), dtype=np.double)

    # Add first point
    p_buff[0] = p_signal[0]
    lastX = previousX = float(p_signal[0, 0])
    minY = maxY = previousY = float(p_signal[0, 1])
    count = 1

    for i in range(1, n_points):
        currentX = float(p_signal[i, 0])
        currentY = float(p_signal[i, 1])

        # If difference between current and last x-value is higher than resolution,
        # or it is the last point, save previous point and its minimum and maximum.
        if (currentX - lastX) >= resol or i == (n_points - 1):
            # Add minimum in range
            if p_buff[count - 1, 0] != lastX or p_buff[count - 1, 1] != minY:
                p_buff[count, 0] = lastX
                p_buff[count, 1] = minY
                count += 1

            # Add maximum in range
            if maxY != minY:
                p_buff[count, 0] = lastX
                p_buff[count, 1] = maxY
                count += 1

            # Add last point in range
            if previousY != maxY:
                p_buff[count, 0] = previousX
                p_buff[count, 1] = previousY
                count += 1

            # Add current point
            p_buff[count, 0] = currentX
            p_buff[count, 1] = currentY
            count += 1

            lastX = previousX = currentX
            maxY = minY = previousY = currentY
        else:
            # If difference is lower than resolution, remember minimum and maximum
            if currentY < minY:
                minY = currentY
            if currentY > maxY:
                maxY = currentY
            previousX = currentX
            previousY = currentY

    return np.ascontiguousarray(p_buff[:count], dtype=np.double)


def signal_gaussian(x: float, minY: float, maxY: float, fwhm: float, points: int) -> np.ndarray:
    """Models a Gaussian peak over points."""
    minX = x - 5.0 * fwhm
    maxX = x + 5.0 * fwhm
    current_x = np.linspace(minX, maxX, points, endpoint=False, dtype=np.double)
    
    amplitude = maxY - minY
    f = (fwhm / 1.66) ** 2
    y = minY + amplitude * np.exp(-((current_x - x) ** 2) / f)
    
    return np.column_stack((current_x, y)).astype(np.double)


def signal_lorentzian(x: float, minY: float, maxY: float, fwhm: float, points: int) -> np.ndarray:
    """Models a Lorentzian peak over points."""
    minX = x - 10.0 * fwhm
    maxX = x + 10.0 * fwhm
    current_x = np.linspace(minX, maxX, points, endpoint=False, dtype=np.double)
    
    amplitude = maxY - minY
    f = (fwhm / 2.0) ** 2
    y = minY + amplitude / (1.0 + ((current_x - x) ** 2) / f)
    
    return np.column_stack((current_x, y)).astype(np.double)


def signal_gausslorentzian(x: float, minY: float, maxY: float, fwhm: float, points: int) -> np.ndarray:
    """Models a hybrid peak (Gaussian on the left, Lorentzian on the right)."""
    minX = x - 5.0 * fwhm
    maxX = x + 10.0 * fwhm
    current_x = np.linspace(minX, maxX, points, endpoint=False, dtype=np.double)
    
    amplitude = maxY - minY
    f_gauss = (fwhm / 1.66) ** 2
    f_lorentz = (fwhm / 2.0) ** 2
    
    y_gauss = minY + amplitude * np.exp(-((current_x - x) ** 2) / f_gauss)
    y_lorentz = minY + amplitude / (1.0 + ((current_x - x) ** 2) / f_lorentz)
    
    y = np.where(current_x < x, y_gauss, y_lorentz)
    
    return np.column_stack((current_x, y)).astype(np.double)


def signal_profile_raster(p_peaks: np.ndarray, points: int) -> np.ndarray:
    """Dynamically generates a geometric sequence of x-values optimized for a set of peaks."""
    if p_peaks.size == 0:
        return np.empty(0, dtype=np.double)
    
    minX = np.min(p_peaks[:, 0])
    maxX = np.max(p_peaks[:, 0])
    minFwhm = np.min(p_peaks[:, 2])
    maxFwhm = np.max(p_peaks[:, 2])
    
    minX -= 5.0 * maxFwhm
    maxX += 5.0 * maxFwhm
    
    # Gradient calculation matching C-extension logic
    range_x = maxX - minX
    if range_x == 0:
        return np.array([minX], dtype=np.double)
        
    a = (maxFwhm / points - minFwhm / points) / range_x
    b = minFwhm / points - a * minX
    
    # Recurrence: x_next = (1+a)*x + b
    # Formula: x_n = (minX + b/a)*(1+a)**n - b/a
    if abs(a) < 1e-12:
        # Linear case (arithmetic sequence)
        n = int(np.ceil((maxX - minX) / b))
        return minX + np.arange(n) * b
    else:
        # Geometric case
        offset = b / a
        start_val = minX + offset
        end_val = maxX + offset
        
        # (1+a)**n = end_val / start_val
        n = int(np.ceil(np.log(end_val / start_val) / np.log(1.0 + a)))
        return start_val * (1.0 + a) ** np.arange(n) - offset


def signal_profile_to_raster(p_peaks: np.ndarray, p_raster: np.ndarray, noise: float, shape: int) -> np.ndarray:
    """Maps modeled peak shapes onto an established raster grid and optionally adds noise."""
    if p_peaks.size == 0 or p_raster.size == 0:
        return np.empty((0, 2), dtype=np.double)
    
    intensities = np.zeros(p_raster.size, dtype=np.double)
    # Helper for signal_locate_x (expects (N, 2) array)
    dummy_signal = np.column_stack((p_raster, intensities))
    
    for i in range(p_peaks.shape[0]):
        mz, intens, fwhm = p_peaks[i]
        
        if shape == 0: # Gaussian
            minX, maxX = mz - 5.0 * fwhm, mz + 5.0 * fwhm
            f = (fwhm / 1.66) ** 2
            idx1 = signal_locate_x(dummy_signal, minX)
            idx2 = signal_locate_x(dummy_signal, maxX)
            x_slice = p_raster[idx1:idx2]
            intensities[idx1:idx2] += intens * np.exp(-((x_slice - mz) ** 2) / f)
            
        elif shape == 1: # Lorentzian
            minX, maxX = mz - 10.0 * fwhm, mz + 10.0 * fwhm
            f = (fwhm / 2.0) ** 2
            idx1 = signal_locate_x(dummy_signal, minX)
            idx2 = signal_locate_x(dummy_signal, maxX)
            x_slice = p_raster[idx1:idx2]
            intensities[idx1:idx2] += intens / (1.0 + ((x_slice - mz) ** 2) / f)
            
        elif shape == 2: # Gauss-Lorentzian
            minX, maxX = mz - 5.0 * fwhm, mz + 10.0 * fwhm
            idx1 = signal_locate_x(dummy_signal, minX)
            idx2 = signal_locate_x(dummy_signal, maxX)
            x_slice = p_raster[idx1:idx2]
            
            f_gauss = (fwhm / 1.66) ** 2
            f_lorentz = (fwhm / 2.0) ** 2
            y_gauss = intens * np.exp(-((x_slice - mz) ** 2) / f_gauss)
            y_lorentz = intens / (1.0 + ((x_slice - mz) ** 2) / f_lorentz)
            intensities[idx1:idx2] += np.where(x_slice < mz, y_gauss, y_lorentz)
            
    if noise != 0:
        intensities += np.random.uniform(-noise/2.0, noise/2.0, size=intensities.size)
        
    return np.column_stack((p_raster, intensities)).astype(np.double)


def signal_profile(p_peaks: np.ndarray, points: int, noise: float, shape: int) -> np.ndarray:
    """Orchestrates the rasterization and profile modeling functions."""
    p_raster = signal_profile_raster(p_peaks, points)
    return signal_profile_to_raster(p_peaks, p_raster, noise, shape)


def _formula_generator(current_comp: list[int], maximum: tuple[int, ...], masses: tuple[float, ...], lo_mass: float, hi_mass: float, limit: int, pos: int, results: list[list[int]]) -> None:
    """
    Recursive helper to generate chemical compositions within a mass range.
    Matches logic in calculations.c.
    """
    elcount = len(current_comp)

    # Calculate current mass
    current_mass = 0.0
    for i in range(elcount):
        current_mass += current_comp[i] * masses[i]

    # Recursion end reached
    if pos == elcount:
        if lo_mass <= current_mass <= hi_mass and len(results) < limit:
            results.append(list(current_comp))
        return

    # Main recursion loop
    original_val = current_comp[pos]
    while current_comp[pos] <= maximum[pos]:
        # Check high mass and stored items limits
        if current_mass > hi_mass or len(results) >= limit:
            break

        # Do next recursion
        _formula_generator(current_comp, maximum, masses, lo_mass, hi_mass, limit, pos + 1, results)

        # Increment current position and mass
        current_comp[pos] += 1
        current_mass += masses[pos]

    # Backtrack
    current_comp[pos] = original_val


def formula_composition(minimum: tuple[int, ...], maximum: tuple[int, ...], masses: tuple[float, ...], lo_mass: float, hi_mass: float, limit: int) -> list[list[int]]:
    """
    Generate chemical compositions within a given mass range.
    Matches logic in calculations.c.
    """
    results: list[list[int]] = []
    current_comp = list(minimum)
    _formula_generator(current_comp, maximum, masses, float(lo_mass), float(hi_mass), int(limit), 0, results)
    return results
