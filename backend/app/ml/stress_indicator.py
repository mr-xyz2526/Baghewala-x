"""Simplified Rod-Load Stress Screening Indicator.

DISCLAIMER & SCOPE NOTE:
This module provides a SIMPLIFIED SCREENING INDICATOR for rapid operational monitoring
and digital twin anomaly detection. It evaluates peak tensile stress, cyclic range,
and rod compression/floating risk against configurable operational thresholds.
It is NOT a full API Spec 11B / Modified Goodman diagram design calculation, and should
not be used as a substitute for certified sucker-rod string engineering design.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import math


@dataclass
class RodStressConfig:
    """Configurable operational screening thresholds."""
    rod_diameter_in: float = 0.875              # Standard 7/8" rod string
    max_allowable_stress_psi: float = 35000.0   # API Grade D operational upper bound
    warning_stress_psi: float = 28000.0         # Preventive maintenance threshold
    max_cyclic_range_psi: float = 22000.0       # Fatigue range screening threshold
    min_load_warning_lbf: float = 800.0         # Below this -> rod floating/compression warning
    rod_yield_strength_psi: float = 100000.0    # Approximate Grade D steel yield


@dataclass
class RodStressScreeningResult:
    """Screening assessment outputs."""
    peak_load_lbf: float
    min_load_lbf: float
    rod_diameter_in: float
    rod_area_in2: float
    peak_stress_psi: float
    min_stress_psi: float
    stress_range_psi: float
    stress_utilization_pct: float
    status: str  # "ACCEPTABLE" | "WARNING" | "EXCEEDED"
    flags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    screening_type: str = "Simplified screening indicator, not a full API/Goodman design calculation."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_load_lbf": round(self.peak_load_lbf, 1),
            "min_load_lbf": round(self.min_load_lbf, 1),
            "rod_diameter_in": self.rod_diameter_in,
            "rod_area_in2": round(self.rod_area_in2, 4),
            "peak_stress_psi": round(self.peak_stress_psi, 1),
            "min_stress_psi": round(self.min_stress_psi, 1),
            "stress_range_psi": round(self.stress_range_psi, 1),
            "stress_utilization_pct": round(self.stress_utilization_pct, 1),
            "status": self.status,
            "flags": self.flags,
            "recommendations": self.recommendations,
            "screening_type": self.screening_type,
        }


def evaluate_rod_stress_screening(
    peak_load_lbf: float,
    min_load_lbf: float,
    config: Optional[RodStressConfig] = None,
) -> RodStressScreeningResult:
    """Evaluate simplified rod stress screening metrics against configurable limits."""
    cfg = config or RodStressConfig()

    area_in2 = (math.pi / 4.0) * (cfg.rod_diameter_in ** 2)
    peak_stress = peak_load_lbf / max(1e-4, area_in2)
    min_stress = max(0.0, min_load_lbf / max(1e-4, area_in2))
    stress_range = peak_stress - min_stress

    utilization_pct = (peak_stress / cfg.max_allowable_stress_psi) * 100.0

    flags: List[str] = []
    recommendations: List[str] = []
    status = "ACCEPTABLE"

    # 1. Peak stress checks
    if peak_stress >= cfg.max_allowable_stress_psi:
        status = "EXCEEDED"
        flags.append(f"Peak stress ({peak_stress:,.0f} psi) exceeds allowable limit ({cfg.max_allowable_stress_psi:,.0f} psi).")
        recommendations.append("Reduce pumping speed (SPM) or stroke length immediately to relieve rod tension.")
    elif peak_stress >= cfg.warning_stress_psi:
        if status != "EXCEEDED":
            status = "WARNING"
        flags.append(f"Peak stress ({peak_stress:,.0f} psi) is in preventive warning band (>= {cfg.warning_stress_psi:,.0f} psi).")
        recommendations.append("Monitor rod fatigue cycle accumulation; evaluate tapered rod string upgrade.")

    # 2. Cyclic stress range (fatigue screening)
    if stress_range >= cfg.max_cyclic_range_psi:
        if status != "EXCEEDED":
            status = "WARNING"
        flags.append(f"High cyclic stress range ({stress_range:,.0f} psi) elevates long-term fatigue failure risk.")
        recommendations.append("Assess pump counterbalance and investigate fluid pound damping.")

    # 3. Minimum load / rod floating risk
    if min_load_lbf < cfg.min_load_warning_lbf:
        if status != "EXCEEDED":
            status = "WARNING"
        flags.append(f"Low minimum load ({min_load_lbf:,.0f} lbf < {cfg.min_load_warning_lbf:,.0f} lbf) indicates potential rod floating / downstroke compression.")
        recommendations.append("Check fluid level and oil viscosity; consider sinker bars above pump if rod float persists.")

    return RodStressScreeningResult(
        peak_load_lbf=float(peak_load_lbf),
        min_load_lbf=float(min_load_lbf),
        rod_diameter_in=float(cfg.rod_diameter_in),
        rod_area_in2=float(area_in2),
        peak_stress_psi=float(peak_stress),
        min_stress_psi=float(min_stress),
        stress_range_psi=float(stress_range),
        stress_utilization_pct=float(utilization_pct),
        status=status,
        flags=flags,
        recommendations=recommendations,
    )
