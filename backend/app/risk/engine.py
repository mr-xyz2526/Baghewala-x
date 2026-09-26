"""Risk and anomaly detection for CSS well operations.

Uses rule-based thresholds + a lightweight statistical z-score layer.
No GPU or external API required.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import math


class AnomalyClass(str, Enum):
    NORMAL = "NORMAL"
    ROD_FLOATING = "ROD_FLOATING"
    GAS_INTERFERENCE = "GAS_INTERFERENCE"
    PUMP_WORN = "PUMP_WORN"
    SCALE_BUILDUP = "SCALE_BUILDUP"
    OVERLOAD = "OVERLOAD"
    LOW_FILLAGE = "LOW_FILLAGE"
    THERMAL_DECLINE = "THERMAL_DECLINE"
    UNKNOWN = "UNKNOWN"


@dataclass
class RiskThresholds:
    """Configurable operational limits and alarm thresholds."""
    # Rod floating / fluid pound
    min_fillage_pct_rod_float: float = 30.0        # Below this → rod floating risk
    # Gas interference
    fillage_drop_for_gas: float = 20.0             # Sudden drop in fillage
    # Pump wear
    pump_wear_min_rod_load_ratio: float = 0.10     # MPRL/PPRL < this → likely worn/standing valve
    # Overload
    rod_stress_overload: float = 0.90              # rod_stress_indicator > this → overload
    # Thermal decline
    temp_decline_rate_c_per_day: float = 2.0       # Faster decline than this is abnormal
    # Low fillage
    critical_low_fillage_pct: float = 50.0


@dataclass
class RiskScore:
    """Output risk/anomaly assessment for a single operating state."""
    anomaly_class: AnomalyClass
    anomaly_probability: float               # 0.0 – 1.0
    rod_floating_risk: float                 # 0.0 – 1.0
    impact_risk: float                       # 0.0 – 1.0 (high load / impact)
    equipment_risk: float                    # 0.0 – 1.0 (pump wear / overstress)
    flags: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


class RiskEngine:
    """Analytical rule-based + statistical risk / anomaly scoring engine."""

    def __init__(self, thresholds: RiskThresholds = None):
        self.thr = thresholds or RiskThresholds()

    def score_srp_state(
        self,
        pump_fillage_pct: float,
        peak_rod_load_lbf: float,
        min_rod_load_lbf: float,
        rod_stress_indicator: float,
        motor_power_kw: float,
        oil_rate_bopd: float,
        prev_fillage_pct: Optional[float] = None,
    ) -> RiskScore:
        """Evaluate SRP operating risk from the current sensor-equivalent state."""
        thr = self.thr
        flags: List[str] = []
        recommendations: List[str] = []

        # -------------------------------------------------------------------
        # Rod floating / fluid pound risk
        # -------------------------------------------------------------------
        if pump_fillage_pct < thr.min_fillage_pct_rod_float:
            rod_float_risk = _clamp01(1.0 - pump_fillage_pct / thr.min_fillage_pct_rod_float)
            flags.append(f"Low fillage ({pump_fillage_pct:.1f}%) – rod floating risk")
            recommendations.append("Reduce SPM or reduce drawdown to improve fillage.")
        else:
            rod_float_risk = 0.0

        # -------------------------------------------------------------------
        # Gas interference (sudden fillage drop)
        # -------------------------------------------------------------------
        if prev_fillage_pct is not None:
            drop = prev_fillage_pct - pump_fillage_pct
            if drop > thr.fillage_drop_for_gas:
                flags.append(f"Fillage dropped {drop:.1f}% – possible gas interference")
                recommendations.append("Check for gas breakthrough; consider casing-gas venting.")

        # -------------------------------------------------------------------
        # High rod load / overload risk
        # -------------------------------------------------------------------
        impact_risk = _clamp01(rod_stress_indicator / thr.rod_stress_overload)
        if rod_stress_indicator > thr.rod_stress_overload:
            flags.append(f"Rod stress indicator {rod_stress_indicator:.2f} – approaching yield")
            recommendations.append("Reduce stroke speed or drawdown to lower rod load.")

        # -------------------------------------------------------------------
        # Equipment / pump wear risk
        # -------------------------------------------------------------------
        load_ratio = min_rod_load_lbf / max(peak_rod_load_lbf, 1.0)
        if load_ratio < thr.pump_wear_min_rod_load_ratio:
            equipment_risk = _clamp01(1.0 - load_ratio / thr.pump_wear_min_rod_load_ratio)
            flags.append("Low MPRL/PPRL ratio – possible standing/travelling valve wear")
            recommendations.append("Inspect pump valves; consider workover if sustained.")
        else:
            equipment_risk = 0.0

        # Low fillage itself contributes to equipment risk
        if pump_fillage_pct < thr.critical_low_fillage_pct:
            equipment_risk = max(equipment_risk, _clamp01(1.0 - pump_fillage_pct / thr.critical_low_fillage_pct))

        # -------------------------------------------------------------------
        # Classify dominant anomaly
        # -------------------------------------------------------------------
        anomaly_probability = max(rod_float_risk, impact_risk, equipment_risk)
        if anomaly_probability < 0.15:
            anomaly_class = AnomalyClass.NORMAL
        elif rod_float_risk >= impact_risk and rod_float_risk >= equipment_risk:
            anomaly_class = AnomalyClass.ROD_FLOATING if pump_fillage_pct < thr.min_fillage_pct_rod_float else AnomalyClass.LOW_FILLAGE
        elif rod_stress_indicator > thr.rod_stress_overload:
            anomaly_class = AnomalyClass.OVERLOAD
        elif equipment_risk > 0.5:
            anomaly_class = AnomalyClass.PUMP_WORN
        else:
            anomaly_class = AnomalyClass.UNKNOWN

        return RiskScore(
            anomaly_class=anomaly_class,
            anomaly_probability=_clamp01(anomaly_probability),
            rod_floating_risk=rod_float_risk,
            impact_risk=impact_risk,
            equipment_risk=equipment_risk,
            flags=flags,
            recommendations=recommendations,
        )

    def score_thermal_state(
        self,
        current_temp_c: float,
        base_temp_c: float,
        days_in_production: int,
        expected_end_temp_c: Optional[float] = None,
    ) -> RiskScore:
        """Evaluate thermal / production anomaly in CSS production phase."""
        thr = self.thr
        flags: List[str] = []
        recommendations: List[str] = []

        delta = current_temp_c - base_temp_c
        max_possible_delta = 250.0  # Rough max steam-to-reservoir temperature difference

        # Thermal decline too fast (abnormal)
        if days_in_production > 1 and expected_end_temp_c is not None:
            predicted_decline_rate = (current_temp_c - base_temp_c) / max(days_in_production, 1)
            expected_delta_end = expected_end_temp_c - base_temp_c
            if expected_delta_end > 0:
                decline_ratio = 1.0 - (delta / max(expected_delta_end * days_in_production, 1e-6))
            else:
                decline_ratio = 0.0

            if predicted_decline_rate > thr.temp_decline_rate_c_per_day * 1.5:
                flags.append(f"Fast thermal decline rate: {predicted_decline_rate:.2f} °C/day")
                recommendations.append("Consider earlier restimulation or increased drawdown monitoring.")
                thermal_risk = _clamp01(predicted_decline_rate / (thr.temp_decline_rate_c_per_day * 3.0))
            else:
                thermal_risk = 0.0
        else:
            thermal_risk = 0.0

        anomaly_probability = thermal_risk
        anomaly_class = AnomalyClass.THERMAL_DECLINE if thermal_risk > 0.4 else AnomalyClass.NORMAL

        return RiskScore(
            anomaly_class=anomaly_class,
            anomaly_probability=_clamp01(anomaly_probability),
            rod_floating_risk=0.0,
            impact_risk=0.0,
            equipment_risk=thermal_risk,
            flags=flags,
            recommendations=recommendations,
        )
