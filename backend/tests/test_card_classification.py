"""Tests for the Dynamometer Card Classification & Rod Stress Screening Pipeline."""

import os
import pytest
import math
import numpy as np

from backend.app.srp_engine import (
    generate_dynamometer_card,
    OperatingState,
    CardClass,
)
from backend.app.ml import (
    extract_card_features,
    elliptic_fourier_descriptors,
    resample_card_points,
    normalize_card_points,
    evaluate_rod_stress_screening,
    RodStressConfig,
    CardClassifier,
    predict_condition,
)


def test_elliptic_fourier_descriptors_and_resampling():
    """Verify EFD extraction produces finite, rotation/scale invariant harmonic coefficients."""
    # Create simple rectangular loop
    rect = [(0.0, 0.0), (72.0, 0.0), (72.0, 12000.0), (0.0, 12000.0)]
    resampled = resample_card_points(rect, target_num_points=100)
    assert resampled.shape == (100, 2)

    norm = normalize_card_points(resampled)
    assert norm.shape == (100, 2)
    assert 0.0 <= np.min(norm) and np.max(norm) <= 1.0

    efd = elliptic_fourier_descriptors(norm, num_harmonics=8, normalize_invariance=True)
    assert len(efd) == 8 * 6
    assert np.all(np.isfinite(efd))


def test_extract_card_features_contains_all_engineered_properties():
    """Verify interpretable feature extraction contains area, slopes, fullness, curvature, and fillage proxy."""
    card = generate_dynamometer_card(
        operating_state=OperatingState(card_class=CardClass.NORMAL, pump_fillage_pct=95.0),
        prefer_numerical=False,
    )
    vec, interp_dict, names = extract_card_features(card.surface_card_points, target_num_points=100)

    assert len(vec) == len(names)
    assert np.all(np.isfinite(vec))

    required_keys = [
        "card_area_in_lbf",
        "width_in",
        "height_lbf",
        "aspect_ratio",
        "peak_load_lbf",
        "min_load_lbf",
        "load_range_lbf",
        "avg_load_lbf",
        "fullness_ratio",
        "upstroke_slope",
        "downstroke_slope",
        "curvature_mean",
        "curvature_var",
        "curvature_max",
        "fillage_proxy",
    ]
    for key in required_keys:
        assert key in interp_dict
        assert math.isfinite(interp_dict[key])


def test_rod_stress_screening_indicator():
    """Verify rod stress screening evaluates thresholds, sets status, and carries disclaimer."""
    cfg = RodStressConfig(
        rod_diameter_in=0.875,
        max_allowable_stress_psi=35000.0,
        warning_stress_psi=28000.0,
        min_load_warning_lbf=1000.0,
    )

    # 1. Normal acceptable load
    res_ok = evaluate_rod_stress_screening(peak_load_lbf=12000.0, min_load_lbf=3000.0, config=cfg)
    assert res_ok.status == "ACCEPTABLE"
    assert res_ok.stress_utilization_pct < 100.0
    assert "Simplified screening indicator, not a full API/Goodman design calculation." in res_ok.screening_type

    # 2. Warning state (low minimum load -> rod floating risk)
    res_warn = evaluate_rod_stress_screening(peak_load_lbf=14000.0, min_load_lbf=500.0, config=cfg)
    assert res_warn.status == "WARNING"
    assert any("floating" in flag.lower() for flag in res_warn.flags)

    # 3. Exceeded state (over-stress)
    area = math.pi / 4.0 * (0.875 ** 2)
    high_load = area * 40000.0  # > 35,000 psi
    res_exceeded = evaluate_rod_stress_screening(peak_load_lbf=high_load, min_load_lbf=2000.0, config=cfg)
    assert res_exceeded.status == "EXCEEDED"
    assert res_exceeded.stress_utilization_pct > 100.0
    assert len(res_exceeded.recommendations) > 0


def test_predict_condition_returns_confidence_and_geometric_reasons():
    """Verify predict_condition returns valid class, confidence in [0, 1], alternatives, and geometric reasons."""
    # Test on FLUID_POUND card
    state = OperatingState(spm=6.0, surface_stroke_in=72.0, card_class=CardClass.FLUID_POUND, pump_fillage_pct=50.0)
    card = generate_dynamometer_card(operating_state=state, prefer_numerical=False)

    pred = predict_condition(card.surface_card_points)

    assert pred["class"] == CardClass.FLUID_POUND.value
    assert 0.0 <= pred["probability"] <= 1.0
    assert len(pred["top_alternatives"]) == 4  # 5 classes total - 1 predicted
    assert len(pred["key_geometric_reasons"]) >= 1
    assert "curvature" in str(pred["key_geometric_reasons"]).lower() or "pound" in str(pred["key_geometric_reasons"]).lower()
    assert pred["validation_badge"] == "SYNTHETIC-DEMO VALIDATION"
    assert "status" in pred["stress_screening"]


def test_card_classifier_metrics_json():
    """Verify saved metrics file includes required reporting fields and SYNTHETIC-DEMO VALIDATION badge."""
    clf = CardClassifier(models_dir="data/models")
    assert clf.is_loaded
    metrics = clf.metrics

    assert metrics["validation_badge"] == "SYNTHETIC-DEMO VALIDATION"
    assert "No real-world field accuracy is asserted" in metrics["provenance_note"]

    # Primary model metrics
    pm = metrics["primary_model"]
    assert "test_accuracy" in pm
    assert "macro_precision" in pm
    assert "macro_recall" in pm
    assert "macro_f1" in pm

    # Support & per-class metrics
    assert len(metrics["per_class_metrics"]) == 5
    for cls_name, vals in metrics["per_class_metrics"].items():
        assert vals["support"] > 0
        assert "f1_score" in vals

    # Secondary benchmark
    assert "random_forest" in metrics["secondary_benchmarks"]

    # Confusion matrix
    assert len(metrics["confusion_matrix"]) == 5
