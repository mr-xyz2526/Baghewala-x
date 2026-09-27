"""Dynamometer Card Generation and Synthetic Dataset Synthesis.

Provides:
  - generate_dynamometer_card: Primary API integrating Gibbs wave solver and analytical fallback.
  - generate_analytical_card: Physically plausible closed-loop fallback.
  - generate_synthetic_dataset: Batch synthesizer generating >= 1,000 cards with .npz and .json persistence.
"""

from typing import List, Tuple, Dict, Any, Optional
import os
import json
import math
import random
import numpy as np

from .models import (
    RodStringParams,
    PumpParams,
    OperatingState,
    CardClass,
    DynamometerCardResult,
)
from .wave_solver import GibbsWaveSolver, calculate_net_fluid_load_n


def compute_card_area_in_lbf(points: List[Tuple[float, float]]) -> float:
    """Compute enclosed area of a 2D dynamometer card loop using the Shoelace formula.

    Units: in * lbf (work per stroke in inch-pounds).
    """
    if len(points) < 3:
        return 0.0
    area = 0.0
    n = len(points)
    for i in range(n - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        area += (x1 * y2 - x2 * y1)
    # Wrap around
    x1, y1 = points[-1]
    x2, y2 = points[0]
    area += (x1 * y2 - x2 * y1)
    return float(abs(area) * 0.5)


def normalize_card_points(
    points: List[Tuple[float, float]],
    target_num_points: int = 100,
) -> List[Tuple[float, float]]:
    """Resample and normalize card points to [0, 1] x [0, 1] for ML feature extraction."""
    if not points:
        return [(0.0, 0.0)] * target_num_points

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    range_x = max(1e-5, max_x - min_x)
    range_y = max(1e-5, max_y - min_y)

    norm_pts = [((x - min_x) / range_x, (y - min_y) / range_y) for x, y in points]

    # Interpolate to fixed number of points along loop perimeter if needed
    if len(norm_pts) == target_num_points:
        return norm_pts

    # Resample evenly along arc-length
    dists = [0.0]
    for i in range(len(norm_pts) - 1):
        dx = norm_pts[i + 1][0] - norm_pts[i][0]
        dy = norm_pts[i + 1][1] - norm_pts[i][1]
        dists.append(dists[-1] + math.hypot(dx, dy))

    total_len = dists[-1]
    if total_len <= 1e-6:
        return [norm_pts[0]] * target_num_points

    target_dists = np.linspace(0.0, total_len, target_num_points)
    resampled: List[Tuple[float, float]] = []

    cur_idx = 0
    for td in target_dists:
        while cur_idx < len(dists) - 2 and dists[cur_idx + 1] < td:
            cur_idx += 1
        seg_len = dists[cur_idx + 1] - dists[cur_idx]
        if seg_len > 1e-6:
            frac = (td - dists[cur_idx]) / seg_len
            nx = norm_pts[cur_idx][0] + frac * (norm_pts[cur_idx + 1][0] - norm_pts[cur_idx][0])
            ny = norm_pts[cur_idx][1] + frac * (norm_pts[cur_idx + 1][1] - norm_pts[cur_idx][1])
        else:
            nx, ny = norm_pts[cur_idx]
        resampled.append((float(nx), float(ny)))

    return resampled


def generate_analytical_card(
    rod_params: RodStringParams,
    pump_params: PumpParams,
    operating_state: OperatingState,
    num_points: int = 100,
    noise_level: float = 0.0,
) -> Dict[str, Any]:
    """Lightweight analytical/synthetic fallback generator.

    Produces smooth, closed-loop dynamometer cards that faithfully reproduce the
    geometric signatures of the 5 prototype classes.
    """
    s_in = operating_state.surface_stroke_in
    spm = operating_state.spm
    omega = 2.0 * math.pi * (spm / 60.0)

    # Static loads in lbf
    # 1 N = 0.224809 lbf
    w_rod_n = rod_params.total_weight_in_air_n
    rho_f = pump_params.tubing_fluid_density_kg_m3
    v_rod = rod_params.area_m2 * rod_params.length_m
    f_buoyant_n = rho_f * 9.80665 * v_rod
    w_rod_fluid_lbf = max(100.0, (w_rod_n - f_buoyant_n) * 0.224809)

    f_fluid_lbf = calculate_net_fluid_load_n(rod_params, pump_params, operating_state.fluid_level_m) * 0.224809

    # Dynamic inertia / wave multiplier
    # SOURCE: Gibbs (1963) static approximation: dynamic range ~ S * spm^2 / 70500 * W_rod
    dyn_factor = (s_in * (spm ** 2)) / 70500.0
    f_dyn_lbf = w_rod_fluid_lbf * dyn_factor

    # Phase angle progression around cycle: 0 -> 2pi
    theta = np.linspace(0.0, 2.0 * math.pi, num_points, endpoint=True)

    # Surface position: s(t) = S/2 * (1 - cos(theta))
    pos_surf = (s_in / 2.0) * (1.0 - np.cos(theta))

    # Downhole effective stroke (elastic stretch reduces stroke)
    stretch_in = (f_fluid_lbf / (rod_params.elastic_modulus_pa * 0.000145038 * (math.pi / 4.0 * (rod_params.diameter_in ** 2)))) * rod_params.length_m * 39.3701
    downhole_stroke_in = max(s_in * 0.4, s_in - stretch_in * 0.5)
    pos_down = (downhole_stroke_in / 2.0) * (1.0 - np.cos(theta - 0.25))

    surf_load = np.zeros(num_points, dtype=np.float64)
    down_load = np.zeros(num_points, dtype=np.float64)

    fillage = max(0.05, min(1.0, operating_state.pump_fillage_pct / 100.0))
    cls = operating_state.card_class

    for i, th in enumerate(theta):
        # Normalised cycle parameter: 0 to pi is upstroke (sin(theta) > 0), pi to 2pi is downstroke (sin(theta) < 0)
        is_upstroke = (th <= math.pi)

        # Baseline downhole load
        if cls == CardClass.NORMAL:
            if is_upstroke:
                p_load = f_fluid_lbf
            else:
                p_load = 0.0

        elif cls == CardClass.FLUID_POUND:
            if is_upstroke:
                p_load = f_fluid_lbf
            else:
                # Downstroke: traveling valve stays closed through vapor, slams open at impact angle
                # impact occurs at downstroke progress = (1 - fillage)
                downstroke_prog = (th - math.pi) / math.pi  # 0 to 1
                if downstroke_prog < (1.0 - fillage):
                    p_load = f_fluid_lbf * 0.95
                else:
                    # Fluid pound impact step + high frequency vibration decaying
                    decay = math.exp(-(downstroke_prog - (1.0 - fillage)) * 12.0)
                    p_load = f_fluid_lbf * 0.05 + f_fluid_lbf * 0.35 * decay * math.cos((th - math.pi) * 16.0)

        elif cls == CardClass.GAS_INTERFERENCE:
            if is_upstroke:
                p_load = f_fluid_lbf
            else:
                # Polytropic rounded compression corner on downstroke
                downstroke_prog = (th - math.pi) / math.pi
                p_load = f_fluid_lbf * ((1.0 - downstroke_prog) ** 1.4)

        elif cls == CardClass.TRAVELING_VALVE_LEAK:
            if is_upstroke:
                upstroke_prog = th / math.pi
                # Load decays on upstroke as fluid slips through traveling valve
                p_load = f_fluid_lbf * (1.0 - 0.55 * upstroke_prog)
            else:
                p_load = 0.0

        elif cls == CardClass.PUMP_OFF:
            # Minimal fluid load loop (< 20% fillage)
            if is_upstroke:
                p_load = f_fluid_lbf * 0.20
            else:
                downstroke_prog = (th - math.pi) / math.pi
                if downstroke_prog < 0.85:
                    p_load = f_fluid_lbf * 0.20
                else:
                    p_load = 0.0
        else:
            p_load = f_fluid_lbf if is_upstroke else 0.0

        down_load[i] = max(0.0, p_load)

        # Surface card reflects buoyant rod weight + dynamic wave reflection + transmission phase lag
        # Wave reflection harmonic approximation:
        # Phase lag tau = 2L/a
        # Dynamic load oscillation
        wave_component = f_dyn_lbf * math.sin(th + 0.30)
        transmitted_fluid_load = down_load[i] * 0.95

        s_load = w_rod_fluid_lbf + transmitted_fluid_load + wave_component

        # Add class-specific dynamic acoustic ripples
        if cls == CardClass.FLUID_POUND and not is_upstroke:
            downstroke_prog = (th - math.pi) / math.pi
            if downstroke_prog >= (1.0 - fillage):
                s_load += f_fluid_lbf * 0.25 * math.exp(-(downstroke_prog - (1.0 - fillage)) * 8.0) * math.sin((th - math.pi) * 18.0)

        surf_load[i] = s_load

    # Optional noise
    if noise_level > 0.0:
        surf_load += np.random.normal(0.0, noise_level * f_fluid_lbf, num_points)
        down_load += np.random.normal(0.0, noise_level * f_fluid_lbf * 0.5, num_points)

    # Ensure smooth closure
    surf_load[-1] = surf_load[0]
    down_load[-1] = down_load[0]

    surface_points = list(zip(pos_surf.tolist(), surf_load.tolist()))
    downhole_points = list(zip(pos_down.tolist(), down_load.tolist()))

    return {
        "surface_points": surface_points,
        "downhole_points": downhole_points,
        "solver_mode": "ANALYTICAL_FALLBACK",
        "downhole_stroke_in": float(downhole_stroke_in),
    }


def generate_dynamometer_card(
    rod_params: Optional[RodStringParams] = None,
    pump_params: Optional[PumpParams] = None,
    operating_state: Optional[OperatingState] = None,
    prefer_numerical: bool = True,
    card_id: str = "CARD-001",
) -> DynamometerCardResult:
    """Generate surface and downhole dynamometer cards using Gibbs damped wave model with fallback.

    Parameters:
        rod_params: Sucker rod string parameters (defaults to 600m 7/8" rod).
        pump_params: Downhole pump dimensions (defaults to 2" pump).
        operating_state: Speed, stroke, fillage, and card class.
        prefer_numerical: Attempt Gibbs wave PDE solver before analytical fallback.
        card_id: Tracking identifier.

    Returns:
        DynamometerCardResult with physical and normalized points, loads, power, and area.
    """
    r_params = rod_params or RodStringParams()
    p_params = pump_params or PumpParams()
    op_state = operating_state or OperatingState()

    solver_res: Optional[Dict[str, Any]] = None

    if prefer_numerical:
        try:
            solver = GibbsWaveSolver(rod_params=r_params, pump_params=p_params)
            solver_res = solver.solve(operating_state=op_state)
        except Exception:
            solver_res = None

    if solver_res is None:
        solver_res = generate_analytical_card(
            rod_params=r_params,
            pump_params=p_params,
            operating_state=op_state,
        )

    surf_pts = solver_res["surface_points"]
    down_pts = solver_res.get("downhole_points", [])
    mode = solver_res.get("solver_mode", "ANALYTICAL_FALLBACK")

    # Metrics
    loads = [p[1] for p in surf_pts]
    peak_load = float(max(loads))
    min_load = float(min(loads))

    disps = [p[0] for p in surf_pts]
    stroke_length = float(max(disps) - min(disps))

    down_disps = [p[0] for p in down_pts] if down_pts else [0.0]
    downhole_stroke = float(max(down_disps) - min(down_disps)) if down_pts else stroke_length * 0.85

    card_area = compute_card_area_in_lbf(surf_pts)

    # Polished rod power: HP = Area * SPM / 396,000 (API 11E definition)
    power_hp = (card_area * op_state.spm) / 396000.0

    # Gearbox peak torque indicator: (PPRL - MPRL)/2 * (S/24) ft-lbf
    torque_indicator = ((peak_load - min_load) / 2.0) * (stroke_length / 24.0)

    # Resample to 100 points for normalized ML features
    normalized_pts = normalize_card_points(surf_pts, target_num_points=100)

    return DynamometerCardResult(
        card_id=card_id,
        card_class=op_state.card_class,
        surface_card_points=surf_pts,
        downhole_card_points=down_pts,
        normalized_surface_points=normalized_pts,
        peak_load_lbf=peak_load,
        min_load_lbf=min_load,
        stroke_length_in=stroke_length,
        downhole_stroke_in=downhole_stroke,
        torque_indicator_ft_lbf=torque_indicator,
        power_estimate_hp=power_hp,
        fillage_estimate_pct=float(op_state.pump_fillage_pct),
        card_area_in_lbf=card_area,
        solver_mode=mode,
    )


def generate_synthetic_dataset(
    total_samples: int = 1000,
    random_seed: int = 42,
    output_dir: str = "data/synthetic",
) -> Dict[str, Any]:
    """Generate at least 1,000 synthetic dynamometer cards and save arrays and metadata.

    Parameters:
        total_samples: Total number of cards to generate (>= 1,000).
        random_seed: Seed for deterministic repeatability.
        output_dir: Target directory under data/synthetic/.

    Outputs:
        - dynamometer_cards.npz: compressed numpy arrays of surface, downhole, normalized cards & labels
        - dynamometer_metadata.json: structured JSON list of card descriptors and metrics
    """
    total = max(1000, total_samples)
    rng = random.Random(random_seed)
    np_rng = np.random.default_rng(random_seed)

    classes = [
        CardClass.NORMAL,
        CardClass.GAS_INTERFERENCE,
        CardClass.FLUID_POUND,
        CardClass.TRAVELING_VALVE_LEAK,
        CardClass.PUMP_OFF,
    ]
    per_class = total // len(classes)
    remainder = total % len(classes)

    all_surface_cards: List[np.ndarray] = []
    all_downhole_cards: List[np.ndarray] = []
    all_normalized_cards: List[np.ndarray] = []
    all_labels: List[str] = []
    metadata_list: List[Dict[str, Any]] = []

    card_counter = 1

    for c_idx, card_class in enumerate(classes):
        n_class = per_class + (1 if c_idx < remainder else 0)

        for _ in range(n_class):
            # Vary operational and physical parameters within realistic industry bounds
            spm = rng.uniform(3.0, 9.5)
            stroke_in = rng.choice([54.0, 64.0, 72.0, 86.0, 100.0, 120.0])
            rod_len = rng.uniform(400.0, 950.0)
            rod_diam = rng.choice([0.75, 0.875, 1.0])
            plunger_diam = rng.choice([1.5, 1.75, 2.0, 2.25])
            damping = rng.uniform(0.3, 1.6)

            # Class-specific fillage ranges
            if card_class == CardClass.NORMAL:
                fillage = rng.uniform(88.0, 100.0)
            elif card_class == CardClass.GAS_INTERFERENCE:
                fillage = rng.uniform(65.0, 90.0)
            elif card_class == CardClass.FLUID_POUND:
                fillage = rng.uniform(35.0, 75.0)
            elif card_class == CardClass.TRAVELING_VALVE_LEAK:
                fillage = rng.uniform(80.0, 98.0)
            elif card_class == CardClass.PUMP_OFF:
                fillage = rng.uniform(8.0, 22.0)
            else:
                fillage = 80.0

            r_params = RodStringParams(
                length_m=rod_len,
                diameter_in=rod_diam,
                damping_factor_s_inv=damping,
            )
            p_params = PumpParams(
                plunger_diameter_in=plunger_diam,
            )
            op_state = OperatingState(
                spm=spm,
                surface_stroke_in=stroke_in,
                pump_fillage_pct=fillage,
                card_class=card_class,
            )

            card_id = f"SYNTH-{card_counter:05d}"
            # Use prefer_numerical=False for high-speed batch dataset generation;
            # numerical wave solver is verified and exercised in tests and single runs.
            res = generate_dynamometer_card(
                rod_params=r_params,
                pump_params=p_params,
                operating_state=op_state,
                prefer_numerical=False,
                card_id=card_id,
            )

            # Convert to fixed-size numpy arrays (100, 2)
            surf_arr = np.array(res.surface_card_points[:100], dtype=np.float32)
            down_arr = np.array(res.downhole_card_points[:100], dtype=np.float32)
            norm_arr = np.array(res.normalized_surface_points, dtype=np.float32)

            all_surface_cards.append(surf_arr)
            all_downhole_cards.append(down_arr)
            all_normalized_cards.append(norm_arr)
            all_labels.append(card_class.value)

            meta = {
                "card_id": card_id,
                "card_class": card_class.value,
                "spm": round(spm, 2),
                "surface_stroke_in": round(stroke_in, 1),
                "rod_length_m": round(rod_len, 1),
                "rod_diameter_in": rod_diam,
                "plunger_diameter_in": plunger_diam,
                "damping_factor_s_inv": round(damping, 2),
                "pump_fillage_pct": round(fillage, 1),
                "peak_load_lbf": round(res.peak_load_lbf, 1),
                "min_load_lbf": round(res.min_load_lbf, 1),
                "stroke_length_in": round(res.stroke_length_in, 2),
                "downhole_stroke_in": round(res.downhole_stroke_in, 2),
                "card_area_in_lbf": round(res.card_area_in_lbf, 1),
                "power_estimate_hp": round(res.power_estimate_hp, 2),
                "torque_indicator_ft_lbf": round(res.torque_indicator_ft_lbf, 1),
                "solver_mode": res.solver_mode,
            }
            metadata_list.append(meta)
            card_counter += 1

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    npz_path = os.path.join(output_dir, "dynamometer_cards.npz")
    json_path = os.path.join(output_dir, "dynamometer_metadata.json")

    # Save numpy archive
    np.savez_compressed(
        npz_path,
        surface_cards=np.array(all_surface_cards, dtype=np.float32),
        downhole_cards=np.array(all_downhole_cards, dtype=np.float32),
        normalized_cards=np.array(all_normalized_cards, dtype=np.float32),
        labels=np.array(all_labels),
    )

    # Save json metadata
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2)

    return {
        "total_generated": len(metadata_list),
        "classes": {cls.value: all_labels.count(cls.value) for cls in classes},
        "npz_file": npz_path,
        "json_file": json_path,
        "random_seed": random_seed,
    }
