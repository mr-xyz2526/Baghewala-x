"""Tests for the SRP Gibbs damped-wave dynamometer module."""

import pytest
import math
import numpy as np

from backend.app.srp_engine import (
    RodStringParams,
    PumpParams,
    OperatingState,
    CardClass,
    GibbsWaveSolver,
    generate_dynamometer_card,
    generate_analytical_card,
    generate_synthetic_dataset,
    compute_card_area_in_lbf,
)


def test_cards_are_finite_and_non_empty():
    """Verify generated surface and downhole cards are non-empty, finite, and closed loops."""
    r_params = RodStringParams(length_m=500.0, diameter_in=0.875)
    p_params = PumpParams(plunger_diameter_in=2.0)
    op_state = OperatingState(spm=6.0, surface_stroke_in=72.0, card_class=CardClass.NORMAL)

    # Test both numerical wave solver and fallback
    for prefer_num in [True, False]:
        card = generate_dynamometer_card(
            rod_params=r_params,
            pump_params=p_params,
            operating_state=op_state,
            prefer_numerical=prefer_num,
        )

        assert len(card.surface_card_points) >= 50
        assert len(card.downhole_card_points) >= 50
        assert len(card.normalized_surface_points) == 100

        # Check all coordinates are finite
        for pos, load in card.surface_card_points:
            assert math.isfinite(pos)
            assert math.isfinite(load)

        for pos, load in card.downhole_card_points:
            assert math.isfinite(pos)
            assert math.isfinite(load)

        for norm_pos, norm_load in card.normalized_surface_points:
            assert 0.0 <= norm_pos <= 1.0001
            assert 0.0 <= norm_load <= 1.0001

        # Check closed loop: first point matches last point within numerical tolerance
        first_pt = card.surface_card_points[0]
        last_pt = card.surface_card_points[-1]
        assert math.isclose(first_pt[0], last_pt[0], abs_tol=1e-2)
        assert math.isclose(first_pt[1], last_pt[1], abs_tol=1e-1)


def test_displacement_span_is_positive():
    """Verify that stroke displacement span is strictly positive and bounded by structural stroke."""
    card = generate_dynamometer_card(
        operating_state=OperatingState(surface_stroke_in=84.0),
        prefer_numerical=False,
    )
    assert card.stroke_length_in > 0.0
    assert card.downhole_stroke_in > 0.0
    assert math.isclose(card.stroke_length_in, 84.0, rel_tol=0.05)
    assert card.peak_load_lbf > card.min_load_lbf > 0.0


def test_class_generation_is_deterministic_with_fixed_seed():
    """Verify dataset and card generation produces identical output with a fixed seed."""
    seed = 12345
    ds1 = generate_synthetic_dataset(total_samples=25, random_seed=seed, output_dir="data/synthetic_test")
    ds2 = generate_synthetic_dataset(total_samples=25, random_seed=seed, output_dir="data/synthetic_test")

    # Load arrays
    npz1 = np.load(ds1["npz_file"])
    npz2 = np.load(ds2["npz_file"])

    np.testing.assert_allclose(npz1["surface_cards"], npz2["surface_cards"])
    np.testing.assert_allclose(npz1["normalized_cards"], npz2["normalized_cards"])
    assert list(npz1["labels"]) == list(npz2["labels"])

    # Clean up test dir
    import shutil
    shutil.rmtree("data/synthetic_test", ignore_errors=True)


def test_average_geometric_features_differ_by_class():
    """Verify that the 5 prototype classes exhibit statistically distinguishable geometric features."""
    r_params = RodStringParams(length_m=600.0)
    p_params = PumpParams(plunger_diameter_in=2.0)

    class_metrics = {}
    for cls in CardClass:
        areas = []
        load_ratios = []
        for i in range(10):
            state = OperatingState(
                spm=5.0 + i * 0.3,
                surface_stroke_in=72.0,
                card_class=cls,
                pump_fillage_pct=15.0 if cls == CardClass.PUMP_OFF else 50.0 if cls == CardClass.FLUID_POUND else 90.0,
            )
            card = generate_dynamometer_card(r_params, p_params, state, prefer_numerical=False)
            areas.append(card.card_area_in_lbf)
            load_ratios.append(card.min_load_lbf / card.peak_load_lbf)

        class_metrics[cls] = {
            "mean_area": np.mean(areas),
            "mean_ratio": np.mean(load_ratios),
        }

    # Normal should have significantly higher work/area than pump-off
    assert class_metrics[CardClass.NORMAL]["mean_area"] > 3.0 * class_metrics[CardClass.PUMP_OFF]["mean_area"]

    # All 5 classes should have distinct mean areas
    mean_areas = [class_metrics[cls]["mean_area"] for cls in CardClass]
    assert len(set(mean_areas)) == len(CardClass)


def test_normal_cards_have_larger_cleaner_filled_shape_than_pump_off():
    """Verify NORMAL cards enclose significantly more loop area and higher fillage than PUMP_OFF cards."""
    r_params = RodStringParams(length_m=500.0)
    p_params = PumpParams(plunger_diameter_in=2.0)

    normal_state = OperatingState(spm=6.0, surface_stroke_in=72.0, card_class=CardClass.NORMAL, pump_fillage_pct=95.0)
    pumpoff_state = OperatingState(spm=6.0, surface_stroke_in=72.0, card_class=CardClass.PUMP_OFF, pump_fillage_pct=12.0)

    normal_card = generate_dynamometer_card(r_params, p_params, normal_state, prefer_numerical=False)
    pumpoff_card = generate_dynamometer_card(r_params, p_params, pumpoff_state, prefer_numerical=False)

    # Area check
    assert normal_card.card_area_in_lbf > 0.0
    assert pumpoff_card.card_area_in_lbf > 0.0
    assert normal_card.card_area_in_lbf > 4.0 * pumpoff_card.card_area_in_lbf

    # Power check
    assert normal_card.power_estimate_hp > pumpoff_card.power_estimate_hp

    # Fillage check
    assert normal_card.fillage_estimate_pct > 80.0
    assert pumpoff_card.fillage_estimate_pct < 25.0


def test_gibbs_wave_solver_numerical_execution():
    """Directly test the finite-difference GibbsWaveSolver on a standard well configuration."""
    r_params = RodStringParams(length_m=500.0, diameter_in=0.875)
    p_params = PumpParams(plunger_diameter_in=2.0)
    state = OperatingState(spm=6.0, surface_stroke_in=72.0, card_class=CardClass.NORMAL)

    solver = GibbsWaveSolver(rod_params=r_params, pump_params=p_params, num_spatial_nodes=31)
    res = solver.solve(operating_state=state, cycles_to_run=2)

    assert res is not None
    assert res["solver_mode"] == "NUMERICAL_WAVE"
    assert len(res["surface_points"]) > 0
    assert len(res["downhole_points"]) > 0

    # Ensure finite loads and positions
    for p in res["surface_points"]:
        assert math.isfinite(p[0])
        assert math.isfinite(p[1])
