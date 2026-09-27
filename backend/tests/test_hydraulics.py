"""Tests for the wellbore and surface hydraulics module."""

import pytest
import math

from backend.app.hydraulics import (
    WellboreGeometry,
    HydraulicsFluidProperties,
    HydraulicsEngine,
    calculate_choke_pressure_drop_bar,
    calculate_friction_factor_darcy,
)


def test_pressure_drop_sign_is_physically_sensible():
    """Verify all pressure drop components and pressure gradient directions are physically sensible."""
    engine = HydraulicsEngine(
        geometry=WellboreGeometry(depth_m=600.0, tubing_id_in=2.441),
        fluid_properties=HydraulicsFluidProperties(oil_density_kg_m3=960.0, oil_viscosity_cp=1200.0),
    )

    # 1. Single-phase heavy oil
    res = engine.calculate_pressures(
        oil_rate_bopd=200.0,
        wellhead_pressure_bar=5.0,
        choke_opening_pct=80.0,
    )

    # Hydrostatic head must be strictly positive (rho * g * H)
    assert res.pressure_drop_components.hydrostatic_bar > 0.0
    # Frictional resistance must be strictly positive
    assert res.pressure_drop_components.friction_bar > 0.0
    # Total wellbore tubing pressure drop must be positive
    assert res.pressure_drop_components.total_tubing_bar > 0.0
    # Choke drop must be positive
    assert res.choke_pressure_drop_bar > 0.0

    # Downhole pump intake pressure must exceed surface wellhead pressure to lift fluid
    assert res.pump_intake_pressure_bar > res.wellhead_pressure_bar
    # Expected hydrostatic alone for 600m of ~960 kg/m^3 is 960*9.81*600*1e-5 ≈ 56.5 bar
    assert math.isclose(res.pressure_drop_components.hydrostatic_bar, 56.486, rel_tol=0.05)

    # Downstream separator pressure after choke must be <= wellhead pressure
    assert res.downstream_choke_pressure_bar <= res.wellhead_pressure_bar

    # 2. Multiphase Beggs & Brill
    res_mp = engine.calculate_pressures(
        oil_rate_bopd=200.0,
        water_cut_pct=30.0,
        gas_rate_mscfd=50.0,
        wellhead_pressure_bar=5.0,
        choke_opening_pct=75.0,
    )
    assert res_mp.pressure_drop_components.hydrostatic_bar > 0.0
    assert res_mp.pressure_drop_components.friction_bar > 0.0
    assert res_mp.pump_intake_pressure_bar > res_mp.wellhead_pressure_bar
    assert res_mp.model_type == "BEGGS_BRILL_MULTIPHASE_SIMPLIFIED"


def test_increasing_viscosity_does_not_reduce_frictional_pressure_drop():
    """Verify monotonicity: increasing viscosity never reduces frictional pressure drop under fixed flow."""
    engine = HydraulicsEngine(
        geometry=WellboreGeometry(depth_m=500.0, tubing_id_in=2.441),
    )

    # Monotonic progression across 4 orders of magnitude: 10 cP -> 50 cP -> 250 cP -> 1,000 cP -> 10,000 cP
    viscosities = [10.0, 50.0, 200.0, 1000.0, 5000.0, 20000.0]
    frictional_drops = []

    for mu in viscosities:
        res = engine.calculate_pressures(
            oil_rate_bopd=150.0,
            oil_viscosity_cp=mu,
            wellhead_pressure_bar=5.0,
            choke_opening_pct=100.0,
        )
        frictional_drops.append(res.pressure_drop_components.friction_bar)

    # Verify strictly non-decreasing sequence: d(Delta_P_fric) / d(mu) >= 0
    for i in range(len(frictional_drops) - 1):
        assert frictional_drops[i + 1] >= frictional_drops[i], (
            f"Friction drop decreased from {frictional_drops[i]:.4f} to {frictional_drops[i+1]:.4f} "
            f"when viscosity increased from {viscosities[i]} to {viscosities[i+1]} cP"
        )


def test_invalid_geometry_and_physics_are_rejected():
    """Verify engine raises ValueError on invalid physical or geometric parameters."""
    engine = HydraulicsEngine()

    # Invalid tubing ID
    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, tubing_id_in=0.0)

    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, tubing_id_in=-2.5)

    # Invalid depth
    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, depth_m=0.0)

    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, depth_m=-500.0)

    # Invalid choke opening percentage (must be in (0, 100])
    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, choke_opening_pct=0.0)

    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, choke_opening_pct=105.0)

    # Negative oil rate
    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=-50.0)

    # Invalid fluid properties
    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, oil_viscosity_cp=0.0)

    with pytest.raises(ValueError):
        engine.calculate_pressures(oil_rate_bopd=100.0, oil_density_kg_m3=-900.0)


def test_single_phase_reduced_path_simplification_label():
    """Verify single-phase path explicitly labels the simplification when multiphase inputs are absent."""
    engine = HydraulicsEngine()
    res = engine.calculate_pressures(
        oil_rate_bopd=180.0,
        water_cut_pct=0.0,
        gas_rate_mscfd=0.0,
    )
    assert res.model_type == "SINGLE_PHASE_HEAVY_OIL_REDUCED"
    assert "Reduced single-phase heavy-oil" in res.simplification_note
    assert res.liquid_holdup == 1.0
    assert res.flow_regime in ["LAMINAR", "TRANSITIONAL", "TURBULENT"]


def test_choke_pressure_drop_response():
    """Verify constricting choke increases choke pressure drop."""
    q_m3_s = 200.0 * 1.84013e-6
    rho = 950.0

    dp_wide = calculate_choke_pressure_drop_bar(flow_rate_m3_s=q_m3_s, fluid_density_kg_m3=rho, choke_opening_pct=100.0)
    dp_constricted = calculate_choke_pressure_drop_bar(flow_rate_m3_s=q_m3_s, fluid_density_kg_m3=rho, choke_opening_pct=25.0)

    assert dp_constricted > dp_wide > 0.0
    # Because area is 1/4, velocity is 4x, Delta_P should scale by ~16x
    assert math.isclose(dp_constricted / dp_wide, 16.0, rel_tol=0.10)
