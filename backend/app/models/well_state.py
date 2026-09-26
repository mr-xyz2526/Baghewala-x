import enum
from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, model_validator


class Phase(str, enum.Enum):
    INJECTION = "INJECTION"
    SOAKING = "SOAKING"
    PRODUCTION = "PRODUCTION"


class Mode(str, enum.Enum):
    SIMULATED_DEMO = "SIMULATED_DEMO"
    HISTORICAL = "HISTORICAL"
    FIELD_VALIDATED = "FIELD_VALIDATED"


class WellTwinState(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    # Identity
    well_id: str = Field(..., description="Unique identifier for the well")
    well_name: str = Field(..., description="Human‑readable name")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="State timestamp")
    field: str = Field(..., description="Field/region name")

    # Reservoir / CSS
    cycle_number: int = Field(..., ge=0)
    phase: Phase = Field(...)
    days_in_phase: int = Field(..., ge=0)
    reservoir_temperature_c: float = Field(..., ge=-50, le=370)
    base_reservoir_temperature_c: float = Field(..., ge=-50, le=370)
    reservoir_pressure_bar: float = Field(..., gt=0)
    steam_rate_tpd: float = Field(..., ge=0)
    steam_pressure_bar: float = Field(..., gt=0)
    steam_quality: float = Field(..., ge=0, le=1)
    injection_duration_days: int = Field(..., ge=0)
    soak_duration_days: int = Field(..., ge=0)
    production_cutoff_days: int = Field(..., ge=0)
    cumulative_steam_t: float = Field(..., ge=0)
    cumulative_oil_bbl: float = Field(..., ge=0)
    heated_radius_m: float = Field(..., ge=0)
    oil_viscosity_cp: float = Field(..., ge=0)

    # SRP (Surface Rod Pump)
    spm: float = Field(..., ge=0)
    stroke_length_in: float = Field(..., gt=0)
    vfd_hz: float = Field(..., gt=0)
    pump_fillage_pct: float = Field(..., ge=0, le=100)
    peak_rod_load: float = Field(..., ge=0)
    min_rod_load: float = Field(..., ge=0)
    rod_stress_indicator: float = Field(..., ge=0)
    motor_power_kw: float = Field(..., gt=0)
    torque_indicator: float = Field(..., ge=0)

    # Hydraulics / surface
    wellhead_pressure_bar: float = Field(..., gt=0)
    pump_intake_pressure_bar: float = Field(..., gt=0)
    choke_pct: float = Field(..., ge=0, le=100)
    oil_rate_bopd: float = Field(..., ge=0)
    water_cut_pct: Optional[float] = Field(None, ge=0, le=100)

    # Risk
    anomaly_class: Optional[str] = None
    anomaly_probability: Optional[float] = Field(None, ge=0, le=1)
    rod_floating_risk: Optional[float] = Field(None, ge=0, le=1)
    impact_risk: Optional[float] = Field(None, ge=0, le=1)
    equipment_risk: Optional[float] = Field(None, ge=0, le=1)

    # Twin health
    model_confidence_pct: float = Field(..., ge=0, le=100)
    state_residual_score: float = Field(..., ge=0, le=100)
    data_quality_score: float = Field(..., ge=0, le=100)
    last_update_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Provenance
    mode: Mode = Field(...)
    source_notes: Optional[str] = None

    @model_validator(mode="after")
    def _phase_duration_consistency(self) -> "WellTwinState":
        if self.phase == Phase.INJECTION and self.days_in_phase > self.injection_duration_days:
            raise ValueError("days_in_phase cannot exceed injection_duration_days during INJECTION phase")
        if self.phase == Phase.SOAKING and self.days_in_phase > self.soak_duration_days:
            raise ValueError("days_in_phase cannot exceed soak_duration_days during SOAKING phase")
        if self.phase == Phase.PRODUCTION and self.days_in_phase > self.production_cutoff_days:
            raise ValueError("days_in_phase cannot exceed production_cutoff_days during PRODUCTION phase")
        return self

    def copy_with_patch(self, patch: dict) -> "WellTwinState":
        """Return a new WellTwinState with the supplied patch applied and re-validated."""
        data = self.model_dump()
        data.update(patch)
        return WellTwinState.model_validate(data)
