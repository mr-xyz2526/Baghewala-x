"""Tests for CSSOptimizer and Pareto multi-objective optimization."""

import pytest
import math
from backend.app.optimization import (
    CSSOptimizer,
    OptimizationBounds,
    CandidatePlan,
    SelectionRuleConfig,
    dominates,
    extract_pareto_front,
    select_compromise_plan,
)


def test_dominated_candidates_are_removed_from_pareto_set():
    """Verify that any candidate dominated by another is excluded from the Pareto set."""
    # Candidate A: high oil (10,000), low SOR (1.2), low steam (12,000)
    cand_a = CandidatePlan(
        plan_id="A",
        steam_rate_tpd=800,
        steam_pressure_bar=40,
        steam_temp_c=250,
        injection_days=15,
        soak_days=4,
        production_days=60,
        cumulative_oil_bbl=10000.0,
        sor_t_per_bbl=1.2,
        cumulative_steam_t=12000.0,
        is_feasible=True,
    )

    # Candidate B: strictly worse in all 3 objectives -> dominated by A
    cand_b = CandidatePlan(
        plan_id="B",
        steam_rate_tpd=900,
        steam_pressure_bar=40,
        steam_temp_c=250,
        injection_days=16,
        soak_days=4,
        production_days=60,
        cumulative_oil_bbl=8000.0,     # Worse (lower)
        sor_t_per_bbl=1.8,             # Worse (higher)
        cumulative_steam_t=14400.0,    # Worse (higher)
        is_feasible=True,
    )

    # Candidate C: trade-off (higher oil 12,000, but higher steam 18,000 and higher SOR 1.5) -> mutually non-dominated with A
    cand_c = CandidatePlan(
        plan_id="C",
        steam_rate_tpd=1000,
        steam_pressure_bar=45,
        steam_temp_c=257,
        injection_days=18,
        soak_days=4,
        production_days=70,
        cumulative_oil_bbl=12000.0,
        sor_t_per_bbl=1.5,
        cumulative_steam_t=18000.0,
        is_feasible=True,
    )

    assert dominates(cand_a, cand_b)
    assert not dominates(cand_b, cand_a)
    assert not dominates(cand_a, cand_c)
    assert not dominates(cand_c, cand_a)

    pareto_set = extract_pareto_front([cand_a, cand_b, cand_c])
    pareto_ids = {c.plan_id for c in pareto_set}

    # B must be removed, A and C must be retained
    assert "B" not in pareto_ids
    assert "A" in pareto_ids
    assert "C" in pareto_ids


def test_infeasible_candidates_are_excluded():
    """Verify that candidates with constraint violations are excluded from the Pareto front."""
    # Feasible candidate
    cand_feasible = CandidatePlan(
        plan_id="FEASIBLE",
        steam_rate_tpd=800,
        steam_pressure_bar=40,
        steam_temp_c=250,
        injection_days=15,
        soak_days=4,
        production_days=60,
        cumulative_oil_bbl=9000.0,
        sor_t_per_bbl=1.33,
        cumulative_steam_t=12000.0,
        is_feasible=True,
    )

    # Infeasible candidate due to pressure limit violation
    cand_infeasible = CandidatePlan(
        plan_id="INFEASIBLE_PRESSURE",
        steam_rate_tpd=800,
        steam_pressure_bar=85,         # Way above 65 bar limit
        steam_temp_c=300,
        injection_days=15,
        soak_days=4,
        production_days=60,
        cumulative_oil_bbl=15000.0,    # High oil, but invalid
        sor_t_per_bbl=0.8,
        cumulative_steam_t=12000.0,
        is_feasible=False,
        constraint_violations=["Pressure exceeds limit"],
    )

    pareto_set = extract_pareto_front([cand_feasible, cand_infeasible])
    pareto_ids = {c.plan_id for c in pareto_set}

    assert "INFEASIBLE_PRESSURE" not in pareto_ids
    assert "FEASIBLE" in pareto_ids


def test_optimizer_is_deterministic_with_fixed_seed():
    """Verify running the optimizer with identical seed yields identical results."""
    opt1 = CSSOptimizer(random_seed=123)
    opt2 = CSSOptimizer(random_seed=123)

    # Use a small grid for fast test execution
    res1 = opt1.optimize(use_nsga2=True)
    res2 = opt2.optimize(use_nsga2=True)

    assert len(res1.pareto_candidates) == len(res2.pareto_candidates)
    assert res1.selected_plan.plan_id == res2.selected_plan.plan_id
    assert math.isclose(res1.selected_plan.cumulative_oil_bbl, res2.selected_plan.cumulative_oil_bbl, rel_tol=1e-5)
    assert math.isclose(res1.selected_plan.sor_t_per_bbl, res2.selected_plan.sor_t_per_bbl, rel_tol=1e-5)
    assert math.isclose(res1.selected_plan.cumulative_steam_t, res2.selected_plan.cumulative_steam_t, rel_tol=1e-5)


def test_at_least_one_candidate_returned_on_standard_demo_config():
    """Verify standard demo configuration returns non-empty Pareto set and valid selected plan."""
    opt = CSSOptimizer(random_seed=42)
    res = opt.optimize(use_nsga2=False)  # Grid search only for quick run

    assert len(res.pareto_candidates) >= 1
    assert res.selected_plan is not None
    assert res.selected_plan.is_feasible
    assert res.selected_plan.cumulative_oil_bbl > 0
    assert res.selected_plan.sor_t_per_bbl > 0

    # Ensure selected plan description mentions weighting / selection rule
    assert "Compromise Programming" in res.selection_rule_description or "weights" in res.selection_rule_description.lower()
    assert "not an unconditional" in res.selection_rule_description.lower() or "preference" in res.selection_rule_description.lower()

    # Ensure alternatives table has rows
    assert len(res.alternatives_table) >= 4
    strategies = {row["strategy"] for row in res.alternatives_table}
    assert "Current Baseline Plan" in strategies
    assert "Selected Compromise Plan" in strategies
    assert "Maximum Oil Strategy" in strategies
    assert "Minimum SOR (High Efficiency) Strategy" in strategies


def test_custom_selection_rule_weighting():
    """Verify changing weights alters plan selection towards the prioritized objective."""
    pareto_candidates = [
        # Candidate 1: High Oil, high steam, high SOR
        CandidatePlan(
            plan_id="OIL_MAX",
            steam_rate_tpd=1200, steam_pressure_bar=50, steam_temp_c=263,
            injection_days=20, soak_days=4, production_days=80,
            cumulative_oil_bbl=15000.0, sor_t_per_bbl=1.6, cumulative_steam_t=24000.0,
            is_feasible=True,
        ),
        # Candidate 2: Low SOR, low steam, moderate oil
        CandidatePlan(
            plan_id="EFF_MAX",
            steam_rate_tpd=600, steam_pressure_bar=35, steam_temp_c=242,
            injection_days=10, soak_days=4, production_days=60,
            cumulative_oil_bbl=6000.0, sor_t_per_bbl=1.0, cumulative_steam_t=6000.0,
            is_feasible=True,
        ),
    ]

    # Priority on Oil
    rule_oil = SelectionRuleConfig(rule_name="max_oil", weight_oil=0.9, weight_sor=0.05, weight_steam=0.05)
    sel_oil, _ = select_compromise_plan(pareto_candidates, rule_oil)
    assert sel_oil.plan_id == "OIL_MAX"

    # Priority on Efficiency (Min SOR)
    rule_eff = SelectionRuleConfig(rule_name="min_sor", weight_oil=0.05, weight_sor=0.9, weight_steam=0.05)
    sel_eff, _ = select_compromise_plan(pareto_candidates, rule_eff)
    assert sel_eff.plan_id == "EFF_MAX"
