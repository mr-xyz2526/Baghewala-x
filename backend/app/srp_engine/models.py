"""Domain models and data schemas for SRP dynamometer card modeling.

TAXONOMY NOTE:
Published petroleum industry literature uses varying classifications for downhole
dynamometer cards. For instance, classic Lufkin/Nabla systems catalog 16+ specific
patterns (e.g. unanchored tubing, delayed traveling valve closing, parted rods,
gas lock, split barrel, bent pump).
For BAGHEWALA-X, five representative prototype classes are selected to model the
predominant thermal heavy-oil pumping phenomena:
  1. NORMAL: full pump fillage, standard traveling/standing valve seating.
  2. GAS_INTERFERENCE: high gas-to-oil ratio causing cushioned downstroke load decay
     and rod floating risk.
  3. FLUID_POUND: liquid fillage deficit causing high-velocity impact on liquid surface.
  4. TRAVELING_VALVE_LEAK: worn valve or cut seat with fluid slippage on upstroke.
  5. PUMP_OFF: severe reservoir depletion with minimal liquid inflow and small card loop.
These five classes are our operational prototypes and do NOT claim to represent the
sole or exhaustive industry taxonomy.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Tuple, Dict, Any, Optional
import math


class CardClass(str, Enum):
    """Representative prototype classes for sucker rod dynamometer cards."""
    NORMAL = "NORMAL"
    GAS_INTERFERENCE = "GAS_INTERFERENCE"
    FLUID_POUND = "FLUID_POUND"
    TRAVELING_VALVE_LEAK = "TRAVELING_VALVE_LEAK"
    PUMP_OFF = "PUMP_OFF"


@dataclass
class RodStringParams:
    """Mechanical and material properties of the sucker rod string.

    SOURCE: API Specification 11B (Specification for Sucker Rods) and
    Gibbs, S.G. (1963), 'Predicting the Behavior of Sucker-Rod Pumping Systems'.
    """
    length_m: float = 600.0              # Total rod length L (m)
    diameter_in: float = 0.875           # Rod outside diameter (inches, 7/8" standard)
    elastic_modulus_pa: float = 2.0e11   # Steel Young's modulus E (Pa ≈ 29-30 Mpsi)
    density_kg_m3: float = 7850.0        # Steel density rho (kg/m^3)
    damping_factor_s_inv: float = 0.8    # Gibbs viscous damping coefficient c (s^-1)

    @property
    def area_m2(self) -> float:
        """Cross-sectional area of rod string (m^2)."""
        r_m = (self.diameter_in * 0.0254) / 2.0
        return math.pi * (r_m ** 2)

    @property
    def acoustic_velocity_m_s(self) -> float:
        """Acoustic wave speed a = sqrt(E / rho) (m/s).
        Typical steel rod speed is ~5,000 - 5,100 m/s (~16,400 ft/s).
        """
        return math.sqrt(self.elastic_modulus_pa / self.density_kg_m3)

    @property
    def total_weight_in_air_n(self) -> float:
        """Weight of the rod string in air (N)."""
        return self.area_m2 * self.length_m * self.density_kg_m3 * 9.80665


@dataclass
class PumpParams:
    """Downhole subsurface sucker-rod pump dimensions and valve properties."""
    plunger_diameter_in: float = 2.0     # Pump bore / plunger diameter (inches)
    standing_valve_leak_pct: float = 0.0 # Standing valve leakage fraction
    traveling_valve_leak_pct: float = 0.0 # Traveling valve leakage fraction (higher for VALVE_LEAK)
    plunger_friction_n: float = 300.0    # Mechanical friction between plunger & barrel (N)
    tubing_fluid_density_kg_m3: float = 950.0  # Density of produced oil-water column (kg/m^3)

    @property
    def plunger_area_m2(self) -> float:
        """Plunger cross-sectional area A_p (m^2)."""
        r_m = (self.plunger_diameter_in * 0.0254) / 2.0
        return math.pi * (r_m ** 2)


@dataclass
class OperatingState:
    """Operational settings and dynamometer card generation state."""
    spm: float = 6.0                     # Pumping speed (strokes per minute)
    surface_stroke_in: float = 72.0      # Polished rod stroke length S (inches)
    pump_fillage_pct: float = 95.0       # Pump liquid fillage (0.0 to 100.0)
    card_class: CardClass = CardClass.NORMAL
    fluid_level_m: Optional[float] = None # Depth to liquid level if known
    net_fluid_load_n: Optional[float] = None # Specified fluid load or calculated from depth


@dataclass
class DynamometerCardResult:
    """Computed dynamometer card outputs for visualization and ML features."""
    card_id: str
    card_class: CardClass
    surface_card_points: List[Tuple[float, float]]     # (position_in, load_lbf)
    downhole_card_points: List[Tuple[float, float]]    # (position_in, load_lbf)
    normalized_surface_points: List[Tuple[float, float]] # (norm_pos [0, 1], norm_load [0, 1])

    peak_load_lbf: float
    min_load_lbf: float
    stroke_length_in: float
    downhole_stroke_in: float
    torque_indicator_ft_lbf: float
    power_estimate_hp: float
    fillage_estimate_pct: float
    card_area_in_lbf: float
    solver_mode: str  # "NUMERICAL_WAVE" or "ANALYTICAL_FALLBACK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "card_class": self.card_class.value,
            "surface_card_points": [
                [round(p[0], 2), round(p[1], 1)] for p in self.surface_card_points
            ],
            "downhole_card_points": [
                [round(p[0], 2), round(p[1], 1)] for p in self.downhole_card_points
            ],
            "normalized_surface_points": [
                [round(p[0], 4), round(p[1], 4)] for p in self.normalized_surface_points
            ],
            "peak_load_lbf": round(self.peak_load_lbf, 1),
            "min_load_lbf": round(self.min_load_lbf, 1),
            "stroke_length_in": round(self.stroke_length_in, 2),
            "downhole_stroke_in": round(self.downhole_stroke_in, 2),
            "torque_indicator_ft_lbf": round(self.torque_indicator_ft_lbf, 1),
            "power_estimate_hp": round(self.power_estimate_hp, 2),
            "fillage_estimate_pct": round(self.fillage_estimate_pct, 1),
            "card_area_in_lbf": round(self.card_area_in_lbf, 1),
            "solver_mode": self.solver_mode,
        }
