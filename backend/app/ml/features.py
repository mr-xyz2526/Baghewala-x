"""Geometric Feature Extraction & Elliptic Fourier Descriptors for Dynamometer Cards.

SOURCE:
  Kuhl, F.P. and Giardina, C.R. (1982). "Elliptic Fourier features of a closed contour."
  Computer Graphics and Image Processing, 18(3), pp. 236-258.
"""

from typing import List, Tuple, Dict, Any, Optional
import math
import numpy as np


def resample_card_points(
    points: List[Tuple[float, float]],
    target_num_points: int = 100,
) -> np.ndarray:
    """Resample closed-curve card points evenly along cumulative perimeter arc length.

    Returns:
        np.ndarray of shape (target_num_points, 2).
    """
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 3:
        raise ValueError("At least 3 points are required to define a dynamometer card loop.")

    # Ensure loop closure
    if not np.allclose(pts[0], pts[-1], atol=1e-3):
        pts = np.vstack([pts, pts[0]])

    # Cumulative arc length
    diffs = np.diff(pts, axis=0)
    seg_lengths = np.hypot(diffs[:, 0], diffs[:, 1])
    cum_dist = np.insert(np.cumsum(seg_lengths), 0, 0.0)
    total_len = cum_dist[-1]

    if total_len < 1e-6:
        return np.repeat(pts[:1], target_num_points, axis=0)

    target_dists = np.linspace(0.0, total_len, target_num_points, endpoint=False)
    resampled_x = np.interp(target_dists, cum_dist, pts[:, 0])
    resampled_y = np.interp(target_dists, cum_dist, pts[:, 1])
    return np.column_stack([resampled_x, resampled_y])


def normalize_card_points(points: np.ndarray) -> np.ndarray:
    """Min-max normalize card coordinates to [0, 1] x [0, 1]."""
    min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
    min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])

    range_x = max(1e-5, max_x - min_x)
    range_y = max(1e-5, max_y - min_y)

    norm = np.zeros_like(points)
    norm[:, 0] = (points[:, 0] - min_x) / range_x
    norm[:, 1] = (points[:, 1] - min_y) / range_y
    return norm


def elliptic_fourier_descriptors(
    points: np.ndarray,
    num_harmonics: int = 10,
    normalize_invariance: bool = True,
) -> np.ndarray:
    """Compute Elliptic Fourier Descriptors (EFD) for a closed contour.

    SOURCE: Kuhl & Giardina (1982), Eqs. (4)-(7).
    Calculates four coefficients (a_n, b_n, c_n, d_n) for each harmonic n.

    Parameters:
        points: Array of shape (K, 2) defining ordered contour vertices.
        num_harmonics: Number of Fourier harmonics to extract (default: 10).
        normalize_invariance: Whether to standardize scale/rotation invariant amplitudes.

    Returns:
        1D np.ndarray of Fourier descriptors.
    """
    pts = np.asarray(points, dtype=np.float64)
    # Ensure closed
    if not np.allclose(pts[0], pts[-1], atol=1e-3):
        pts = np.vstack([pts, pts[0]])

    k = len(pts) - 1
    dxy = np.diff(pts, axis=0)
    dt = np.hypot(dxy[:, 0], dxy[:, 1])

    # Handle zero-length steps
    dt[dt < 1e-9] = 1e-9

    t = np.insert(np.cumsum(dt), 0, 0.0)
    T = t[-1]

    two_pi_over_T = 2.0 * math.pi / T
    two_pi_sq = 2.0 * (math.pi ** 2)

    a = np.zeros(num_harmonics, dtype=np.float64)
    b = np.zeros(num_harmonics, dtype=np.float64)
    c = np.zeros(num_harmonics, dtype=np.float64)
    d = np.zeros(num_harmonics, dtype=np.float64)

    for n in range(1, num_harmonics + 1):
        n_fact = T / (two_pi_sq * (n ** 2))
        arg1 = n * two_pi_over_T * t[1:]
        arg0 = n * two_pi_over_T * t[:-1]

        cos_diff = np.cos(arg1) - np.cos(arg0)
        sin_diff = np.sin(arg1) - np.sin(arg0)

        dx_over_dt = dxy[:, 0] / dt
        dy_over_dt = dxy[:, 1] / dt

        a[n - 1] = n_fact * np.sum(dx_over_dt * cos_diff)
        b[n - 1] = n_fact * np.sum(dx_over_dt * sin_diff)
        c[n - 1] = n_fact * np.sum(dy_over_dt * cos_diff)
        d[n - 1] = n_fact * np.sum(dy_over_dt * sin_diff)

    if normalize_invariance:
        # Scale-invariant harmonic amplitudes:
        # Fundamental semi-major axis A_0 for normalization:
        e1 = math.sqrt(a[0] ** 2 + c[0] ** 2)
        scale = max(1e-6, e1)

        # Invariant harmonic amplitudes for each harmonic: sqrt(a_n^2 + b_n^2) + sqrt(c_n^2 + d_n^2)
        descriptors = []
        for i in range(num_harmonics):
            amp_x = math.hypot(a[i], b[i]) / scale
            amp_y = math.hypot(c[i], d[i]) / scale
            descriptors.extend([a[i] / scale, b[i] / scale, c[i] / scale, d[i] / scale, amp_x, amp_y])
        return np.array(descriptors, dtype=np.float64)
    else:
        return np.column_stack([a, b, c, d]).flatten()


def extract_interpretable_features(
    raw_points: np.ndarray,
    norm_points: np.ndarray,
) -> Dict[str, float]:
    """Calculate interpretable engineered geometric descriptors."""
    xs_raw = raw_points[:, 0]
    ys_raw = raw_points[:, 1]
    xs_norm = norm_points[:, 0]
    ys_norm = norm_points[:, 1]

    # 1. Extents & Dimensions
    width_in = float(np.max(xs_raw) - np.min(xs_raw))
    height_lbf = float(np.max(ys_raw) - np.min(ys_raw))
    aspect_ratio = width_in / max(1e-4, height_lbf)

    # 2. Loads
    peak_load = float(np.max(ys_raw))
    min_load = float(np.min(ys_raw))
    load_range = peak_load - min_load
    avg_load = float(np.mean(ys_raw))
    load_ratio = min_load / max(1.0, peak_load)

    # 3. Card Area via Shoelace Formula
    # Area in physical units (in * lbf) and normalized units ([0, 1]^2)
    def shoelace(pts):
        x = pts[:, 0]
        y = pts[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    raw_area = float(shoelace(raw_points))
    norm_area = float(shoelace(norm_points))

    # 4. Rectangular fullness proxy (card area / bounding box area)
    bounding_box_area = width_in * height_lbf
    fullness_ratio = raw_area / max(1e-4, bounding_box_area)

    # 5. Upstroke and Downstroke Slope Indicators
    # Separate upstroke (dx/dt > 0) and downstroke (dx/dt < 0)
    n = len(raw_points)
    half = n // 2
    # In standardized resampling: 0 to half is upstroke, half to n is downstroke
    up_x = xs_norm[:half]
    up_y = ys_norm[:half]
    down_x = xs_norm[half:]
    down_y = ys_norm[half:]

    def safe_poly_slope(x, y):
        if len(x) < 3 or (np.max(x) - np.min(x)) < 1e-4:
            return 0.0
        p = np.polyfit(x, y, 1)
        return float(p[0])

    upstroke_slope = safe_poly_slope(up_x, up_y)
    downstroke_slope = safe_poly_slope(down_x, down_y)

    # 6. Curvature & Rounded Corner Indicators
    # Compute angles between consecutive edge vectors
    diffs = np.diff(norm_points, axis=0)
    angles = np.arctan2(diffs[:, 1], diffs[:, 0])
    angle_diffs = np.abs(np.diff(angles))
    # Wrap angles into [0, pi]
    angle_diffs = np.minimum(angle_diffs, 2.0 * math.pi - angle_diffs)
    curvature_mean = float(np.mean(angle_diffs))
    curvature_var = float(np.var(angle_diffs))
    curvature_max = float(np.max(angle_diffs)) if len(angle_diffs) > 0 else 0.0

    # 7. Fillage Proxy:
    # Measure fraction of downstroke where load is dropped to baseline
    mid_load = min_load + 0.40 * load_range
    down_load_fraction = float(np.mean(down_y < 0.35))
    fillage_proxy = 1.0 - down_load_fraction

    return {
        "card_area_in_lbf": raw_area,
        "norm_area": norm_area,
        "width_in": width_in,
        "height_lbf": height_lbf,
        "aspect_ratio": aspect_ratio,
        "peak_load_lbf": peak_load,
        "min_load_lbf": min_load,
        "load_range_lbf": load_range,
        "avg_load_lbf": avg_load,
        "load_ratio": load_ratio,
        "fullness_ratio": fullness_ratio,
        "upstroke_slope": upstroke_slope,
        "downstroke_slope": downstroke_slope,
        "curvature_mean": curvature_mean,
        "curvature_var": curvature_var,
        "curvature_max": curvature_max,
        "fillage_proxy": fillage_proxy,
    }


def extract_card_features(
    card_points: List[Tuple[float, float]],
    target_num_points: int = 100,
    num_harmonics: int = 10,
) -> Tuple[np.ndarray, Dict[str, float], List[str]]:
    """Complete feature extraction pipeline: raw points -> resampling -> EFD + interpretable features.

    Returns:
        feature_vector: 1D np.ndarray of shape (D,)
        interpretable_dict: Dictionary of named human-interpretable features
        feature_names: List of all feature names corresponding to feature_vector
    """
    # 1. Resample to fixed number of points
    resampled_raw = resample_card_points(card_points, target_num_points=target_num_points)

    # 2. Coordinate normalization
    resampled_norm = normalize_card_points(resampled_raw)

    # 3. Primary descriptor: Elliptic Fourier Descriptors
    efd_features = elliptic_fourier_descriptors(resampled_norm, num_harmonics=num_harmonics)
    efd_names = [f"efd_{i}" for i in range(len(efd_features))]

    # 4. Interpretable engineered features
    interp_dict = extract_interpretable_features(resampled_raw, resampled_norm)
    interp_names = list(interp_dict.keys())
    interp_values = [interp_dict[k] for k in interp_names]

    # Combine into single feature vector
    feature_vector = np.concatenate([efd_features, np.array(interp_values, dtype=np.float64)])
    all_feature_names = efd_names + interp_names

    return feature_vector, interp_dict, all_feature_names


def explain_geometric_reasons(
    interp_features: Dict[str, float],
    predicted_class: str,
) -> List[str]:
    """Generate human-interpretable technical explanations for the predicted card classification."""
    reasons: List[str] = []
    area = interp_features.get("card_area_in_lbf", 0.0)
    fullness = interp_features.get("fullness_ratio", 0.0)
    up_slope = interp_features.get("upstroke_slope", 0.0)
    down_slope = interp_features.get("downstroke_slope", 0.0)
    curv_var = interp_features.get("curvature_var", 0.0)
    curv_max = interp_features.get("curvature_max", 0.0)
    fillage = interp_features.get("fillage_proxy", 0.0)
    load_range = interp_features.get("load_range_lbf", 0.0)

    if predicted_class == "NORMAL":
        reasons.append(f"Fullness ratio is high ({fullness:.2f}), reflecting complete pump barrel liquid fillage.")
        reasons.append(f"Card area ({area:,.0f} in·lbf) indicates strong hydraulic work per stroke with stable valve seating.")
        reasons.append(f"Upstroke slope ({up_slope:+.2f}) is stable with minimal fluid slippage.")

    elif predicted_class == "PUMP_OFF":
        reasons.append(f"Card area is severely depressed ({area:,.0f} in·lbf), showing collapsed pump work.")
        reasons.append(f"Fullness ratio ({fullness:.2f}) is minimal, indicating depleted reservoir inflow and liquid underfill.")
        reasons.append(f"Fillage proxy estimate ({fillage * 100:.1f}%) is well below operational baseline.")

    elif predicted_class == "FLUID_POUND":
        reasons.append(f"Peak directional curvature ({curv_max:.2f} rad) and variance ({curv_var:.3f}) reveal a sharp impact transition on downstroke.")
        reasons.append(f"Partial fillage proxy ({fillage * 100:.1f}%) indicates plunger drops through vapor void before slamming into liquid.")
        reasons.append("Abrupt downward load drop midway through stroke produces characteristic fluid pound notch.")

    elif predicted_class == "GAS_INTERFERENCE":
        reasons.append(f"Downstroke slope ({down_slope:+.2f}) shows a rounded polytropic compression tail rather than an abrupt valve opening.")
        reasons.append("Free casing/formation gas cushions the plunger descent, delaying traveling valve pressure equilibrium.")
        reasons.append("Downstroke resistance poses elevated rod-floating risk during high-viscosity or high-GOR cycles.")

    elif predicted_class == "TRAVELING_VALVE_LEAK":
        reasons.append(f"Negative upstroke slope ({up_slope:+.2f}) confirms steady load decay as fluid slips past the traveling valve.")
        reasons.append(f"Top load line tilts downward with stroke progression, indicating eroded ball/seat or seal bypass.")
        reasons.append(f"Fullness ratio ({fullness:.2f}) is reduced from nominal due to slippage loss.")

    else:
        reasons.append(f"Card exhibits area of {area:,.0f} in·lbf with load range {load_range:,.0f} lbf.")

    return reasons
