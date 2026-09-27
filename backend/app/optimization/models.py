"""Domain models and schemas for CSS optimization."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import math


@dataclass
class OptimizationBounds:
    """Configurable parameter ranges and physical operational limits."""
    # Decision variable bounds
    min_steam_rate_tpd: float = 400.0
    max_steam_rate_tpd: float = 1400.0
    min_steam_pressure_bar: float = 20.0
    max_steam_pressure_bar: float = 65.0       # Formation integrity / fracture margin limit
    min_injection_days: int = 8
    max_injection_days: int = 30
    min_soak_days: int = 2
    max_soak_days: int = 10
    min_production_days: int = 30
    max_production_days: int = 120

    # Operational & Physical Constraints
    max_cumulative_steam_t: float = 25000.0    # Boiler / allocation constraint
    max_steam_temp_c: float = 300.0            # Metallurgical / casing thermal limit
    min_cumulative_oil_bbl: float = 1500.0     # Minimum viable cycle oil threshold
    min_economic_oil_rate_bopd: float = 10.0   # Minimum viable final production rate
    fixed_steam_quality: float = 0.80          # Typical surface boiler quality


@dataclass
class CandidatePlan:
    """A single evaluation point in the optimization decision space."""
    plan_id: str
    steam_rate_tpd: float
    steam_pressure_bar: float
    steam_temp_c: float
    injection_days: int
    soak_days: int
    production_days: int

    # Evaluated Objectives
    cumulative_oil_bbl: float = 0.0
    sor_t_per_bbl: float = 0.0
    cumulative_steam_t: float = 0.0
    heated_radius_m: float = 0.0
    thermal_efficiency: float = 0.0
    final_oil_rate_bopd: float = 0.0

    # Constraint Status
    is_feasible: bool = True
    constraint_violations: List[str] = field(default_factory=list)

    # Pareto Ranking metadata
    pareto_rank: int = 0
    crowding_distance: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["cumulative_oil_bbl"] = round(self.cumulative_oil_bbl, 1)
        d["sor_t_per_bbl"] = round(self.sor_t_per_bbl, 3)
        d["cumulative_steam_t"] = round(self.cumulative_steam_t, 1)
        d["heated_radius_m"] = round(self.heated_radius_m, 2)
        d["thermal_efficiency"] = round(self.thermal_efficiency, 3)
        if math.isinf(self.crowding_distance) or math.isnan(self.crowding_distance):
            d["crowding_distance"] = 999999.0
        else:
            d["crowding_distance"] = round(self.crowding_distance, 4)
        return d


@dataclass
class SelectionRuleConfig:
    """Configurable weights and preference rule for choosing a plan from the Pareto set."""
    rule_name: str = "balanced_compromise"  # "balanced_compromise" | "max_oil_priority" | "efficiency_priority" | "steam_conservation"
    weight_oil: float = 0.45                # Importance of maximizing oil
    weight_sor: float = 0.35                # Importance of minimizing SOR
    weight_steam: float = 0.20              # Importance of minimizing steam


@dataclass
class OptimizationResult:
    """Comprehensive output of CSS multi-objective optimization."""
    pareto_candidates: List[CandidatePlan]
    current_plan: CandidatePlan
    selected_plan: CandidatePlan
    selection_rule_description: str
    objective_values: Dict[str, Any]
    constraints_summary: Dict[str, Any]
    alternatives_table: List[Dict[str, Any]]
    explanation_of_trade_offs: str
    all_evaluated_candidates: List[CandidatePlan]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pareto_candidates": [c.to_dict() for c in self.pareto_candidates],
            "current_plan": self.current_plan.to_dict(),
            "selected_plan": self.selected_plan.to_dict(),
            "selection_rule_description": self.selection_rule_description,
            "objective_values": self.objective_values,
            "constraints_summary": self.constraints_summary,
            "alternatives_table": self.alternatives_table,
            "explanation_of_trade_offs": self.explanation_of_trade_offs,
            "all_evaluated_candidates": [c.to_dict() for c in self.all_evaluated_candidates],
        }
