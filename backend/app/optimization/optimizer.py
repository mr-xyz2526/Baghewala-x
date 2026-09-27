"""CSSOptimizer: Multi-objective optimization for Cyclic Steam Stimulation.

Implements:
1. Baseline Transparent Grid Search (SciPy-friendly discretization).
2. Lightweight NSGA-II Evolutionary Search (pure Python + NumPy, deterministic with seed).
3. Non-dominated Pareto Filtering and Compromise Programming Selection.
4. Comprehensive Trade-off Analysis & Alternatives Table.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import random
import numpy as np

from ..css_engine import CSSCycleSimulator, CSSCycleParams, ProductivityParams
from .models import (
    OptimizationBounds,
    CandidatePlan,
    SelectionRuleConfig,
    OptimizationResult,
)
from .pareto import (
    extract_pareto_front,
    select_compromise_plan,
    dominates,
)


def saturation_temp_from_pressure_bar(pressure_bar: float) -> float:
    """Calculate saturated steam temperature (deg C) from absolute pressure (bar) via Antoine correlation.

    Antoine formula for H2O:
        log10(P_bar) = 5.40221 - 1838.675 / (T_C + 241.263)
        T_C = 1838.675 / (5.40221 - log10(P_bar)) - 241.263
    SOURCE: Standard chemical thermodynamics Antoine coefficients for water (100 - 374 deg C).
    """
    p_safe = max(1.05, min(150.0, pressure_bar))
    log_p = math.log10(p_safe)
    denom = 5.40221 - log_p
    if denom <= 0.01:
        return 350.0
    t_c = (1838.675 / denom) - 241.263
    return float(max(100.0, min(360.0, t_c)))


class CSSOptimizer:
    """Multi-objective optimizer for CSS operational decision variables."""

    def __init__(
        self,
        bounds: Optional[OptimizationBounds] = None,
        simulator: Optional[CSSCycleSimulator] = None,
        random_seed: Optional[int] = 42,
    ):
        self.bounds = bounds or OptimizationBounds()
        self.simulator = simulator or CSSCycleSimulator()
        self.random_seed = random_seed
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

    def evaluate_candidate(
        self,
        plan_id: str,
        steam_rate_tpd: float,
        steam_pressure_bar: float,
        injection_days: int,
        soak_days: int,
        production_days: int,
    ) -> CandidatePlan:
        """Evaluate a decision variable combination using CSSCycleSimulator and test constraints."""
        b = self.bounds
        violations: List[str] = []

        # Pressure and temperature check
        if steam_pressure_bar > b.max_steam_pressure_bar:
            violations.append(f"Steam pressure {steam_pressure_bar:.1f} bar exceeds limit {b.max_steam_pressure_bar:.1f} bar")
        if steam_pressure_bar < b.min_steam_pressure_bar:
            violations.append(f"Steam pressure {steam_pressure_bar:.1f} bar below minimum {b.min_steam_pressure_bar:.1f} bar")

        steam_temp_c = saturation_temp_from_pressure_bar(steam_pressure_bar)
        if steam_temp_c > b.max_steam_temp_c:
            violations.append(f"Steam temperature {steam_temp_c:.1f} °C exceeds thermal limit {b.max_steam_temp_c:.1f} °C")

        # Rate and duration bound checks
        if not (b.min_steam_rate_tpd <= steam_rate_tpd <= b.max_steam_rate_tpd):
            violations.append(f"Steam rate {steam_rate_tpd:.0f} t/d outside [{b.min_steam_rate_tpd}, {b.max_steam_rate_tpd}]")
        if not (b.min_injection_days <= injection_days <= b.max_injection_days):
            violations.append(f"Injection duration {injection_days}d outside [{b.min_injection_days}, {b.max_injection_days}]")
        if not (b.min_soak_days <= soak_days <= b.max_soak_days):
            violations.append(f"Soak duration {soak_days}d outside [{b.min_soak_days}, {b.max_soak_days}]")
        if not (b.min_production_days <= production_days <= b.max_production_days):
            violations.append(f"Production duration {production_days}d outside [{b.min_production_days}, {b.max_production_days}]")

        cum_steam = steam_rate_tpd * injection_days
        if cum_steam > b.max_cumulative_steam_t:
            violations.append(f"Cumulative steam {cum_steam:,.0f} t exceeds limit {b.max_cumulative_steam_t:,.0f} t")

        # Run simulation if basic inputs are physically sensible
        cum_oil = 0.0
        sor = 0.0
        r_h = 0.0
        eff = 0.0
        final_rate = 0.0

        try:
            params = CSSCycleParams(
                steam_rate_tpd=steam_rate_tpd,
                steam_temp_c=steam_temp_c,
                injection_days=int(injection_days),
                steam_quality=b.fixed_steam_quality,
                soak_days=int(soak_days),
                production_days=int(production_days),
            )
            sim_res = self.simulator.run_cycle(params)
            cum_oil = sim_res.cycle_oil
            sor = sim_res.SOR
            r_h = sim_res.injection_summary.heated_radius_m
            eff = sim_res.injection_summary.thermal_efficiency_indicator

            prod_timeline = [r for r in sim_res.full_cycle_timeline if r.phase == "PRODUCTION"]
            final_rate = prod_timeline[-1].oil_rate_bopd if prod_timeline else 0.0

            # Economic & performance thresholds
            if cum_oil < b.min_cumulative_oil_bbl:
                violations.append(f"Cumulative oil {cum_oil:,.0f} bbl below minimum viable threshold {b.min_cumulative_oil_bbl:,.0f} bbl")
            if final_rate < b.min_economic_oil_rate_bopd:
                violations.append(f"End production rate {final_rate:.1f} BOPD below cutoff {b.min_economic_oil_rate_bopd:.1f} BOPD")

        except Exception as e:
            violations.append(f"Simulation failed: {str(e)}")

        is_feasible = (len(violations) == 0)

        return CandidatePlan(
            plan_id=plan_id,
            steam_rate_tpd=float(steam_rate_tpd),
            steam_pressure_bar=float(steam_pressure_bar),
            steam_temp_c=float(steam_temp_c),
            injection_days=int(injection_days),
            soak_days=int(soak_days),
            production_days=int(production_days),
            cumulative_oil_bbl=float(cum_oil),
            sor_t_per_bbl=float(sor),
            cumulative_steam_t=float(cum_steam),
            heated_radius_m=float(r_h),
            thermal_efficiency=float(eff),
            final_oil_rate_bopd=float(final_rate),
            is_feasible=is_feasible,
            constraint_violations=violations,
        )

    def grid_search(
        self,
        rate_steps: int = 3,
        pressure_steps: int = 3,
        inj_steps: int = 3,
        soak_steps: int = 2,
        prod_steps: int = 3,
    ) -> List[CandidatePlan]:
        """Perform systematic baseline exploration over a discrete parameter grid."""
        b = self.bounds
        rates = np.linspace(b.min_steam_rate_tpd, b.max_steam_rate_tpd, rate_steps)
        pressures = np.linspace(b.min_steam_pressure_bar, b.max_steam_pressure_bar, pressure_steps)
        injs = np.linspace(b.min_injection_days, b.max_injection_days, inj_steps, dtype=int)
        soaks = np.linspace(b.min_soak_days, b.max_soak_days, soak_steps, dtype=int)
        prods = np.linspace(b.min_production_days, b.max_production_days, prod_steps, dtype=int)

        candidates: List[CandidatePlan] = []
        idx = 1
        for r in rates:
            for p in pressures:
                for inj in injs:
                    for s in soaks:
                        for pr in prods:
                            cand = self.evaluate_candidate(
                                plan_id=f"GRID-{idx:03d}",
                                steam_rate_tpd=float(r),
                                steam_pressure_bar=float(p),
                                injection_days=int(inj),
                                soak_days=int(s),
                                production_days=int(pr),
                            )
                            candidates.append(cand)
                            idx += 1
        return candidates

    def nsga2_search(
        self,
        population_size: int = 20,
        generations: int = 4,
        seed: Optional[int] = None,
    ) -> List[CandidatePlan]:
        """Perform lightweight, zero-dependency evolutionary multi-objective search (NSGA-II inspired)."""
        rng = random.Random(seed if seed is not None else self.random_seed)
        b = self.bounds

        def sample_individual(pid: str) -> CandidatePlan:
            r = rng.uniform(b.min_steam_rate_tpd, b.max_steam_rate_tpd)
            p = rng.uniform(b.min_steam_pressure_bar, b.max_steam_pressure_bar)
            inj = rng.randint(b.min_injection_days, b.max_injection_days)
            soak = rng.randint(b.min_soak_days, b.max_soak_days)
            prod = rng.randint(b.min_production_days, b.max_production_days)
            return self.evaluate_candidate(pid, r, p, inj, soak, prod)

        # Initial population
        population: List[CandidatePlan] = [sample_individual(f"NSGA-0-{i:02d}") for i in range(population_size)]
        all_evaluated: List[CandidatePlan] = list(population)

        # Generation iterations
        for gen in range(1, generations + 1):
            offspring: List[CandidatePlan] = []
            for i in range(population_size // 2):
                # Tournament selection
                p1, p2 = rng.sample(population, 2)
                parent1 = p1 if (p1.is_feasible and not p2.is_feasible) or (dominates(p1, p2)) else p2
                p3, p4 = rng.sample(population, 2)
                parent2 = p3 if (p3.is_feasible and not p4.is_feasible) or (dominates(p3, p4)) else p4

                # Crossover
                alpha = rng.random()
                child_r = alpha * parent1.steam_rate_tpd + (1 - alpha) * parent2.steam_rate_tpd
                child_p = alpha * parent1.steam_pressure_bar + (1 - alpha) * parent2.steam_pressure_bar
                child_inj = int(round(alpha * parent1.injection_days + (1 - alpha) * parent2.injection_days))
                child_soak = int(round(alpha * parent1.soak_days + (1 - alpha) * parent2.soak_days))
                child_prod = int(round(alpha * parent1.production_days + (1 - alpha) * parent2.production_days))

                # Mutation
                if rng.random() < 0.3:
                    child_r += rng.uniform(-100, 100)
                if rng.random() < 0.3:
                    child_p += rng.uniform(-5, 5)
                if rng.random() < 0.3:
                    child_inj += rng.randint(-2, 2)

                # Clamp to bounds
                child_r = max(b.min_steam_rate_tpd, min(b.max_steam_rate_tpd, child_r))
                child_p = max(b.min_steam_pressure_bar, min(b.max_steam_pressure_bar, child_p))
                child_inj = max(b.min_injection_days, min(b.max_injection_days, child_inj))
                child_soak = max(b.min_soak_days, min(b.max_soak_days, child_soak))
                child_prod = max(b.min_production_days, min(b.max_production_days, child_prod))

                child = self.evaluate_candidate(
                    f"NSGA-{gen}-{i:02d}", child_r, child_p, child_inj, child_soak, child_prod
                )
                offspring.append(child)
                all_evaluated.append(child)

            # Combine and truncate to population_size
            combined = population + offspring
            # Feasible candidates prioritized, sorted by dominance rank
            feasible = [c for c in combined if c.is_feasible]
            infeasible = [c for c in combined if not c.is_feasible]

            if feasible:
                from .pareto import fast_non_dominated_sort, assign_crowding_distance
                fronts = fast_non_dominated_sort(feasible)
                survivors: List[CandidatePlan] = []
                for front in fronts:
                    assign_crowding_distance(front)
                    front.sort(key=lambda c: c.crowding_distance, reverse=True)
                    for c in front:
                        if len(survivors) < population_size:
                            survivors.append(c)
                population = survivors
            else:
                population = infeasible[:population_size]

        return all_evaluated

    def optimize(
        self,
        current_plan_params: Optional[Dict[str, Any]] = None,
        selection_rule: Optional[SelectionRuleConfig] = None,
        use_nsga2: bool = True,
    ) -> OptimizationResult:
        """Run full CSS optimization with grid search + NSGA-II, Pareto analysis, and trade-off summary."""
        # 1. Evaluate current plan baseline
        curr = current_plan_params or {
            "steam_rate_tpd": 800.0,
            "steam_pressure_bar": 47.0,
            "injection_days": 18,
            "soak_days": 4,
            "production_days": 70,
        }
        current_candidate = self.evaluate_candidate(
            plan_id="CURRENT-PLAN",
            steam_rate_tpd=curr["steam_rate_tpd"],
            steam_pressure_bar=curr.get("steam_pressure_bar", 47.0),
            injection_days=int(curr["injection_days"]),
            soak_days=int(curr["soak_days"]),
            production_days=int(curr["production_days"]),
        )

        # 2. Explore search space
        # Fast 3x2x3x2x2 grid search (72 points)
        grid_candidates = self.grid_search(rate_steps=3, pressure_steps=2, inj_steps=3, soak_steps=2, prod_steps=2)

        all_candidates = [current_candidate] + grid_candidates

        # Optional NSGA-II refinement
        if use_nsga2:
            nsga_candidates = self.nsga2_search(population_size=16, generations=3, seed=self.random_seed)
            all_candidates.extend(nsga_candidates)

        # 3. Extract Pareto Front (feasible, non-dominated)
        pareto_front = extract_pareto_front(all_candidates)

        # If pareto_front is empty (e.g. strict constraints violated everywhere), relax and fallback to best feasible
        feasible = [c for c in all_candidates if c.is_feasible]
        if not pareto_front and feasible:
            pareto_front = [max(feasible, key=lambda c: c.cumulative_oil_bbl)]
        elif not pareto_front:
            # Fallback if zero feasible
            pareto_front = [current_candidate]

        # 4. Multi-criteria selection of representative plan
        rule_cfg = selection_rule or SelectionRuleConfig()
        selected_candidate, rule_desc = select_compromise_plan(pareto_front, rule_cfg)

        # 5. Build Alternatives Table
        # Max Oil candidate
        max_oil_cand = max(pareto_front, key=lambda c: c.cumulative_oil_bbl)
        # Min SOR candidate
        min_sor_cand = min(pareto_front, key=lambda c: c.sor_t_per_bbl)
        # Min Steam candidate
        min_steam_cand = min(pareto_front, key=lambda c: c.cumulative_steam_t)

        def make_alt_row(name: str, c: CandidatePlan) -> Dict[str, Any]:
            oil_delta = c.cumulative_oil_bbl - current_candidate.cumulative_oil_bbl
            sor_delta = c.sor_t_per_bbl - current_candidate.sor_t_per_bbl
            steam_delta = c.cumulative_steam_t - current_candidate.cumulative_steam_t
            return {
                "strategy": name,
                "plan_id": c.plan_id,
                "steam_rate_tpd": round(c.steam_rate_tpd, 0),
                "steam_pressure_bar": round(c.steam_pressure_bar, 1),
                "injection_days": c.injection_days,
                "soak_days": c.soak_days,
                "production_days": c.production_days,
                "cumulative_oil_bbl": round(c.cumulative_oil_bbl, 1),
                "sor_t_per_bbl": round(c.sor_t_per_bbl, 3),
                "cumulative_steam_t": round(c.cumulative_steam_t, 1),
                "heated_radius_m": round(c.heated_radius_m, 2),
                "oil_delta_vs_current_bbl": round(oil_delta, 1),
                "sor_delta_vs_current": round(sor_delta, 3),
                "steam_delta_vs_current_t": round(steam_delta, 1),
            }

        alternatives = [
            make_alt_row("Current Baseline Plan", current_candidate),
            make_alt_row("Selected Compromise Plan", selected_candidate),
            make_alt_row("Maximum Oil Strategy", max_oil_cand),
            make_alt_row("Minimum SOR (High Efficiency) Strategy", min_sor_cand),
            make_alt_row("Steam Conservation Strategy", min_steam_cand),
        ]

        # 6. Generate Trade-Off Narrative
        trade_offs = self._generate_trade_off_explanation(
            current=current_candidate,
            selected=selected_candidate,
            max_oil=max_oil_cand,
            min_sor=min_sor_cand,
            min_steam=min_steam_cand,
            rule_desc=rule_desc,
        )

        # 7. Summary metrics
        total_eval = len(all_candidates)
        feasible_count = len(feasible)
        infeasible_count = total_eval - feasible_count

        return OptimizationResult(
            pareto_candidates=pareto_front,
            current_plan=current_candidate,
            selected_plan=selected_candidate,
            selection_rule_description=rule_desc,
            objective_values={
                "current_plan": {
                    "cumulative_oil_bbl": current_candidate.cumulative_oil_bbl,
                    "sor_t_per_bbl": current_candidate.sor_t_per_bbl,
                    "cumulative_steam_t": current_candidate.cumulative_steam_t,
                },
                "selected_plan": {
                    "cumulative_oil_bbl": selected_candidate.cumulative_oil_bbl,
                    "sor_t_per_bbl": selected_candidate.sor_t_per_bbl,
                    "cumulative_steam_t": selected_candidate.cumulative_steam_t,
                },
                "pareto_front_size": len(pareto_front),
            },
            constraints_summary={
                "total_evaluated": total_eval,
                "feasible_candidates": feasible_count,
                "infeasible_candidates": infeasible_count,
                "feasibility_rate_pct": round((feasible_count / max(1, total_eval)) * 100.0, 1),
            },
            alternatives_table=alternatives,
            explanation_of_trade_offs=trade_offs,
            all_evaluated_candidates=all_candidates,
        )

    def _generate_trade_off_explanation(
        self,
        current: CandidatePlan,
        selected: CandidatePlan,
        max_oil: CandidatePlan,
        min_sor: CandidatePlan,
        min_steam: CandidatePlan,
        rule_desc: str,
    ) -> str:
        """Synthesize a structured trade-off narrative."""
        oil_gain = selected.cumulative_oil_bbl - current.cumulative_oil_bbl
        oil_gain_pct = (oil_gain / max(current.cumulative_oil_bbl, 1.0)) * 100.0
        sor_diff = selected.sor_t_per_bbl - current.sor_t_per_bbl
        steam_diff = selected.cumulative_steam_t - current.cumulative_steam_t

        lines = [
            "### Trade-Off Analysis & Plan Comparison",
            f"**Selection Context**: {rule_desc}",
            "",
            "#### 1. Selected Plan vs. Current Baseline",
            f"- **Cumulative Oil Production**: The selected plan yields **{selected.cumulative_oil_bbl:,.0f} bbl** "
            f"compared to **{current.cumulative_oil_bbl:,.0f} bbl** for the current baseline "
            f"({'gain of +' if oil_gain >= 0 else 'decrease of '}{oil_gain:,.0f} bbl, {oil_gain_pct:+.1f}%).",
            f"- **Steam-to-Oil Ratio (SOR)**: Shifted from **{current.sor_t_per_bbl:.2f}** to **{selected.sor_t_per_bbl:.2f} t/bbl** "
            f"({'increase of +' if sor_diff >= 0 else 'improvement of '}{sor_diff:+.2f}).",
            f"- **Steam Volume Consumption**: Required **{selected.cumulative_steam_t:,.0f} tonnes** vs **{current.cumulative_steam_t:,.0f} tonnes** "
            f"({'increase of +' if steam_diff >= 0 else 'saving of '}{steam_diff:,.0f} t).",
            "",
            "#### 2. Pareto Extremes & Opportunity Cost",
            f"- **Maximum Oil Strategy ({max_oil.plan_id})**: Can reach up to **{max_oil.cumulative_oil_bbl:,.0f} bbl**, but requires "
            f"**{max_oil.cumulative_steam_t:,.0f} tonnes** of steam, driving the SOR to **{max_oil.sor_t_per_bbl:.2f} t/bbl**.",
            f"- **Efficiency Strategy ({min_sor.plan_id})**: Minimizes SOR down to **{min_sor.sor_t_per_bbl:.2f} t/bbl**, but caps oil output at "
            f"**{min_sor.cumulative_oil_bbl:,.0f} bbl** due to conservative steam volume ({min_sor.cumulative_steam_t:,.0f} t).",
            f"- **Steam Conservation Strategy ({min_steam.plan_id})**: Uses the least steam (**{min_steam.cumulative_steam_t:,.0f} t**), suitable for "
            f"boiler capacity or water supply bottlenecks, yielding **{min_steam.cumulative_oil_bbl:,.0f} bbl** oil.",
            "",
            "#### 3. Recommendation Summary",
            "The selected plan balances thermal reservoir energy delivery against steam generation cost. "
            "If boiler fuel costs or emissions quotas rise, shifting towards the Minimum SOR candidate is advised. "
            "Conversely, under high crude price scenarios, migrating towards the Maximum Oil point captures additional revenue.",
        ]
        return "\n".join(lines)
