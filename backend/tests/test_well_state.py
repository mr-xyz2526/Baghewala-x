import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.app.models.well_state import WellTwinState, Phase, Mode
from backend.app.services.twin_state_store import TwinStateStore


@pytest.fixture
def store():
    return TwinStateStore()


def test_valid_state_serialization():
    now = datetime.now(timezone.utc)
    state = WellTwinState(
        well_id="well-001",
        well_name="Test Well",
        timestamp=now,
        field="Test Field",
        cycle_number=0,
        phase=Phase.INJECTION,
        days_in_phase=0,
        reservoir_temperature_c=150.0,
        base_reservoir_temperature_c=150.0,
        reservoir_pressure_bar=30.0,
        steam_rate_tpd=1000.0,
        steam_pressure_bar=15.0,
        steam_quality=0.9,
        injection_duration_days=30,
        soak_duration_days=10,
        production_cutoff_days=60,
        cumulative_steam_t=0.0,
        cumulative_oil_bbl=0.0,
        heated_radius_m=0.0,
        oil_viscosity_cp=10.0,
        spm=0.0,
        stroke_length_in=4.0,
        vfd_hz=60.0,
        pump_fillage_pct=0.0,
        peak_rod_load=0.0,
        min_rod_load=0.0,
        rod_stress_indicator=0.0,
        motor_power_kw=100.0,
        torque_indicator=0.0,
        wellhead_pressure_bar=30.0,
        pump_intake_pressure_bar=28.0,
        choke_pct=0.0,
        oil_rate_bopd=0.0,
        water_cut_pct=None,
        anomaly_class=None,
        anomaly_probability=None,
        rod_floating_risk=None,
        impact_risk=None,
        equipment_risk=None,
        model_confidence_pct=100.0,
        state_residual_score=0.0,
        data_quality_score=100.0,
        last_update_timestamp=now,
        mode=Mode.SIMULATED_DEMO,
        source_notes="test",
    )
    # Serialize to JSON and deserialize back
    json_str = state.model_dump_json()
    restored = WellTwinState.model_validate_json(json_str)
    assert restored == state


def test_invalid_units_ranges():
    now = datetime.now(timezone.utc)
    # Temperature out of allowed range
    with pytest.raises(ValidationError):
        WellTwinState(
            well_id="well-002",
            well_name="Bad Temp",
            timestamp=now,
            field="Field",
            cycle_number=0,
            phase=Phase.INJECTION,
            days_in_phase=0,
            reservoir_temperature_c=450.0,  # invalid (>370, physically impossible steam temp)
            base_reservoir_temperature_c=150.0,
            reservoir_pressure_bar=30.0,
            steam_rate_tpd=1000.0,
            steam_pressure_bar=15.0,
            steam_quality=0.9,
            injection_duration_days=30,
            soak_duration_days=10,
            production_cutoff_days=60,
            cumulative_steam_t=0.0,
            cumulative_oil_bbl=0.0,
            heated_radius_m=0.0,
            oil_viscosity_cp=10.0,
            spm=0.0,
            stroke_length_in=4.0,
            vfd_hz=60.0,
            pump_fillage_pct=0.0,
            peak_rod_load=0.0,
            min_rod_load=0.0,
            rod_stress_indicator=0.0,
            motor_power_kw=100.0,
            torque_indicator=0.0,
            wellhead_pressure_bar=30.0,
            pump_intake_pressure_bar=28.0,
            choke_pct=0.0,
            oil_rate_bopd=0.0,
            water_cut_pct=None,
            anomaly_class=None,
            anomaly_probability=None,
            rod_floating_risk=None,
            impact_risk=None,
            equipment_risk=None,
            model_confidence_pct=100.0,
            state_residual_score=0.0,
            data_quality_score=100.0,
            last_update_timestamp=now,
            mode=Mode.SIMULATED_DEMO,
            source_notes="bad",
        )

    # Percentage out of range
    with pytest.raises(ValidationError):
        WellTwinState(
            well_id="well-003",
            well_name="Bad Percent",
            timestamp=now,
            field="Field",
            cycle_number=0,
            phase=Phase.INJECTION,
            days_in_phase=0,
            reservoir_temperature_c=150.0,
            base_reservoir_temperature_c=150.0,
            reservoir_pressure_bar=30.0,
            steam_rate_tpd=1000.0,
            steam_pressure_bar=15.0,
            steam_quality=1.5,  # invalid (>1)
            injection_duration_days=30,
            soak_duration_days=10,
            production_cutoff_days=60,
            cumulative_steam_t=0.0,
            cumulative_oil_bbl=0.0,
            heated_radius_m=0.0,
            oil_viscosity_cp=10.0,
            spm=0.0,
            stroke_length_in=4.0,
            vfd_hz=60.0,
            pump_fillage_pct=0.0,
            peak_rod_load=0.0,
            min_rod_load=0.0,
            rod_stress_indicator=0.0,
            motor_power_kw=100.0,
            torque_indicator=0.0,
            wellhead_pressure_bar=30.0,
            pump_intake_pressure_bar=28.0,
            choke_pct=0.0,
            oil_rate_bopd=0.0,
            water_cut_pct=None,
            anomaly_class=None,
            anomaly_probability=None,
            rod_floating_risk=None,
            impact_risk=None,
            equipment_risk=None,
            model_confidence_pct=100.0,
            state_residual_score=0.0,
            data_quality_score=100.0,
            last_update_timestamp=now,
            mode=Mode.SIMULATED_DEMO,
            source_notes="bad",
        )


def test_phase_transition_rules(store):
    # Create a demo well in INJECTION phase
    state = store.reset_demo_state("test-well")
    assert state.phase == Phase.INJECTION
    # Attempt to exceed injection duration -> should raise ValueError via model validator
    with pytest.raises(ValueError):
        store.update_state("test-well", {"days_in_phase": state.injection_duration_days + 1})
    # Advance to the last valid injection day
    state = store.update_state("test-well", {"days_in_phase": state.injection_duration_days})
    assert state.days_in_phase == state.injection_duration_days
    # Transition to SOAKING phase (allowed once injection period is complete)
    state = store.update_state("test-well", {"phase": Phase.SOAKING, "days_in_phase": 0})
    assert state.phase == Phase.SOAKING
    # Exceed soak duration should raise
    with pytest.raises(ValueError):
        store.update_state("test-well", {"days_in_phase": state.soak_duration_days + 1})


def test_state_history(store):
    store.reset_demo_state("hist-well")
    # Apply a few updates
    store.update_state("hist-well", {"oil_rate_bopd": 10.0})
    store.update_state("hist-well", {"oil_rate_bopd": 20.0})
    store.update_state("hist-well", {"oil_rate_bopd": 30.0})
    hist = store.history("hist-well")
    # History should include the initial state + three updates (total 4)
    assert len(hist) == 4
    # Verify ordering and values
    assert hist[0].oil_rate_bopd == 0.0
    assert hist[1].oil_rate_bopd == 10.0
    assert hist[2].oil_rate_bopd == 20.0
    assert hist[3].oil_rate_bopd == 30.0
