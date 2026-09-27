"""Data schemas and domain models for wellbore and surface hydraulics."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


@dataclass
class WellboreGeometry:
    """Tubing and wellbore structural dimensions."""
    depth_m: float = 600.0                   # True vertical depth to pump intake (m)
    tubing_id_in: float = 2.441              # Tubing inside diameter (inches, 2-7/8" EUE)
    roughness_m: float = 0.0000457           # Commercial steel pipe roughness (m ≈ 0.0018 in)
    choke_nominal_id_in: float = 1.0         # Full-open choke orifice diameter (inches)


@dataclass
class HydraulicsFluidProperties:
    """Fluid PVT and physical properties."""
    oil_density_kg_m3: float = 960.0         # Extra-heavy crude density (~15-16 deg API)
    oil_viscosity_cp: float = 1500.0         # Oil dynamic viscosity (cP)
    water_density_kg_m3: float = 1000.0      # Produced water density (kg/m^3)
    water_viscosity_cp: float = 1.0          # Water viscosity (cP)
    gas_specific_gravity: float = 0.65       # Hydrocarbon gas gravity relative to air


@dataclass
class PressureDropComponents:
    """Individual physical components of pressure gradient/drop along the wellbore."""
    hydrostatic_bar: float = 0.0             # Hydrostatic / gravitational head (bar)
    friction_bar: float = 0.0                # Frictional resistance drop (bar)
    acceleration_bar: float = 0.0            # Kinetic / acceleration drop (bar)
    total_tubing_bar: float = 0.0            # Total wellbore tubing pressure drop (bar)
    choke_bar: float = 0.0                   # Surface choke pressure drop (bar)


@dataclass
class HydraulicsResult:
    """Output wellbore and surface pressure profile."""
    pump_intake_pressure_bar: float
    wellhead_pressure_bar: float
    downstream_choke_pressure_bar: float
    pressure_drop_components: PressureDropComponents
    choke_pressure_drop_bar: float
    flow_regime: str
    reynolds_number: float
    mixture_velocity_m_s: float
    liquid_holdup: float
    model_type: str                          # "BEGGS_BRILL_MULTIPHASE_SIMPLIFIED" or "SINGLE_PHASE_HEAVY_OIL_REDUCED"
    simplification_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pump_intake_pressure_bar": round(self.pump_intake_pressure_bar, 2),
            "wellhead_pressure_bar": round(self.wellhead_pressure_bar, 2),
            "downstream_choke_pressure_bar": round(self.downstream_choke_pressure_bar, 2),
            "pressure_drop_components": {
                "hydrostatic_bar": round(self.pressure_drop_components.hydrostatic_bar, 3),
                "friction_bar": round(self.pressure_drop_components.friction_bar, 3),
                "acceleration_bar": round(self.pressure_drop_components.acceleration_bar, 4),
                "total_tubing_bar": round(self.pressure_drop_components.total_tubing_bar, 3),
                "choke_bar": round(self.pressure_drop_components.choke_bar, 3),
            },
            "choke_pressure_drop_bar": round(self.choke_pressure_drop_bar, 3),
            "flow_regime": self.flow_regime,
            "reynolds_number": round(self.reynolds_number, 1),
            "mixture_velocity_m_s": round(self.mixture_velocity_m_s, 4),
            "liquid_holdup": round(self.liquid_holdup, 4),
            "model_type": self.model_type,
            "simplification_note": self.simplification_note,
        }
