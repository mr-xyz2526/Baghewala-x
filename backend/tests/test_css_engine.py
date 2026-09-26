import math
import pytest
import numpy as np

from backend.app.css_engine import (
    ViscosityModel,
    ViscosityConfig,
    MarxLangenheimModel,
    MarxLangenheimConfig,
    BobergLantzModel,
    BobergLantzConfig,
    CSSCycleSimulator,
    CSSCycleParams,
    ProductivityParams,
)


@pytest.fixture
def simulator():
    return CSSCycleSimulator()


def test_heated_radius_monotonicity_with_injection_duration(simulator):
    """Verify heated radius strictly increases with injection days under fixed conditions."""
    rate = 800.0
    temp = 260.0
    quality = 0.8

    res_10 = simulator.inject(rate, temp, injection_days=10, steam_quality=quality)
    res_20 = simulator.inject(rate, temp, injection_days=20, steam_quality=quality)
    res_30 = simulator.inject(rate, temp, injection_days=30, steam_quality=quality)

    r10 = res_10["heated_radius_m"]
    r20 = res_20["heated_radius_m"]
    r30 = res_30["heated_radius_m"]

    assert 0 < r10 < r20 < r30
    assert 0 < res_10["heated_area_m2"] < res_20["heated_area_m2"] < res_30["heated_area_m2"]


def test_sensible_dependence_on_steam_rate(simulator):
    """Verify higher steam injection rate yields larger heated area and radius."""
    temp = 260.0
    days = 15
    quality = 0.8

    res_low = simulator.inject(steam_rate_tpd=400.0, steam_temp_c=temp, injection_days=days, steam_quality=quality)
    res_high = simulator.inject(steam_rate_tpd=1200.0, steam_temp_c=temp, injection_days=days, steam_quality=quality)

    assert res_low["heated_radius_m"] < res_high["heated_radius_m"]
    assert res_low["heated_area_m2"] < res_high["heated_area_m2"]
    assert res_low["total_heat_mj"] < res_high["total_heat_mj"]


def test_temperature_rises_during_injection(simulator):
    """Verify temperature in the heated zone rises from base temp toward steam temp during injection."""
    params = CSSCycleParams(
        steam_rate_tpd=800.0,
        steam_temp_c=260.0,
        injection_days=15,
        steam_quality=0.8,
        soak_days=3,
        production_days=30,
    )
    res = simulator.run_cycle(params)

    inj_records = [r for r in res.full_cycle_timeline if r.phase == "INJECTION"]
    assert len(inj_records) == 15

    # Base reservoir temperature
    t_base = simulator.ml_config.base_reservoir_temp_c

    # Temperature at all injection days should exceed cold base temp
    for r in inj_records:
        assert r.temperature_c > t_base

    # Temperature profile during injection should be monotonically non-decreasing
    temps = [r.temperature_c for r in inj_records]
    for i in range(len(temps) - 1):
        assert temps[i] <= temps[i + 1]

    # At the end of injection, temperature should reach the steam temperature
    assert math.isclose(temps[-1], 260.0, rel_tol=1e-3)


def test_temperature_decays_during_soak_and_production(simulator):
    """Verify temperature strictly decays during soak and continues decaying during production."""
    params = CSSCycleParams(
        steam_rate_tpd=800.0,
        steam_temp_c=260.0,
        injection_days=10,
        soak_days=5,
        production_days=30,
    )
    res = simulator.run_cycle(params)

    soak_records = [r for r in res.full_cycle_timeline if r.phase == "SOAKING"]
    prod_records = [r for r in res.full_cycle_timeline if r.phase == "PRODUCTION"]

    assert len(soak_records) == 5
    assert len(prod_records) == 30

    # Temperature strictly decreases during soak
    soak_temps = [r.temperature_c for r in soak_records]
    for i in range(len(soak_temps) - 1):
        assert soak_temps[i] > soak_temps[i + 1]

    # Temperature at start of production is <= end of soak
    assert prod_records[0].temperature_c <= soak_temps[-1]

    # Temperature generally decreases during production
    prod_temps = [r.temperature_c for r in prod_records]
    for i in range(len(prod_temps) - 1):
        assert prod_temps[i] >= prod_temps[i + 1]

    assert prod_temps[-1] < prod_temps[0]


def test_viscosity_decreases_as_temperature_increases():
    """Verify heavy oil viscosity is strictly monotonically decreasing with temperature."""
    visc_model = ViscosityModel()
    temps = [30.0, 50.0, 80.0, 120.0, 180.0, 240.0, 300.0]
    viscosities = [visc_model.calculate_viscosity(t) for t in temps]

    for i in range(len(viscosities) - 1):
        assert viscosities[i] > viscosities[i + 1]

    # Reference viscosity check at T_ref = 50 C
    assert math.isclose(visc_model.calculate_viscosity(50.0), 10000.0, rel_tol=1e-3)


def test_viscosity_sensitivity_parameter():
    """Verify sensitivity_factor scales the temperature-viscosity slope."""
    model_low_sens = ViscosityModel(ViscosityConfig(sensitivity_factor=0.8))
    model_high_sens = ViscosityModel(ViscosityConfig(sensitivity_factor=1.2))

    # At higher temperature (e.g. 150 C), higher sensitivity should produce lower viscosity
    v_low = model_low_sens.calculate_viscosity(150.0)
    v_high = model_high_sens.calculate_viscosity(150.0)
    assert v_high < v_low


def test_cumulative_oil_and_sor_are_finite_and_non_negative(simulator):
    """Verify cumulative oil and SOR are finite and non-negative."""
    params = CSSCycleParams(
        steam_rate_tpd=600.0,
        steam_temp_c=250.0,
        injection_days=14,
        steam_quality=0.75,
        soak_days=4,
        production_days=60,
    )
    result = simulator.run_cycle(params)

    assert result.cycle_oil > 0.0
    assert math.isfinite(result.cycle_oil)

    assert result.cycle_steam > 0.0
    assert math.isfinite(result.cycle_steam)

    assert result.SOR > 0.0
    assert math.isfinite(result.SOR)
    assert result.sor_cwe_bbl_per_bbl > 0.0
    assert math.isfinite(result.sor_cwe_bbl_per_bbl)

    # Check phase boundaries
    pb = result.phase_boundaries
    assert pb["injection"]["start_day"] == 1
    assert pb["injection"]["end_day"] == 14
    assert pb["soak"]["start_day"] == 15
    assert pb["soak"]["end_day"] == 18
    assert pb["production"]["start_day"] == 19
    assert pb["production"]["end_day"] == 78


def test_zero_or_invalid_steam_inputs_are_rejected(simulator):
    """Verify simulator rejects physically invalid or zero steam parameters."""
    # Zero or negative steam rate
    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=0.0, steam_temp_c=250.0, injection_days=10, steam_quality=0.8)

    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=-100.0, steam_temp_c=250.0, injection_days=10, steam_quality=0.8)

    # Zero or negative injection days
    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=500.0, steam_temp_c=250.0, injection_days=0, steam_quality=0.8)

    # Invalid steam quality (<0 or >1)
    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=500.0, steam_temp_c=250.0, injection_days=10, steam_quality=1.2)

    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=500.0, steam_temp_c=250.0, injection_days=10, steam_quality=-0.1)

    # Steam colder than or equal to initial reservoir temperature
    with pytest.raises(ValueError):
        simulator.inject(steam_rate_tpd=500.0, steam_temp_c=50.0, injection_days=10, steam_quality=0.8)

    # Negative soak days
    with pytest.raises(ValueError):
        simulator.soak(soak_days=-2)

    # Negative production days
    with pytest.raises(ValueError):
        simulator.produce(production_days=-10)


def test_sequential_api(simulator):
    """Verify inject(), soak(), produce() sequential invocation works smoothly."""
    inj = simulator.inject(steam_rate_tpd=700.0, steam_temp_c=260.0, injection_days=12, steam_quality=0.85)
    assert inj["heated_radius_m"] > 0.0
    assert inj["thermal_efficiency_indicator"] > 0.0

    soak_res = simulator.soak(soak_days=4)
    assert len(soak_res["temperature_time_series"]) == 4
    assert soak_res["end_soak_temperature"] < 260.0

    prod_res = simulator.produce(production_days=20)
    assert len(prod_res) == 20
    assert prod_res[0]["cumulative_oil"] > 0.0
    assert prod_res[-1]["cumulative_oil"] > prod_res[0]["cumulative_oil"]
