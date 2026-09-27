"""Fast Non-Dominated Sorting and Pareto analysis algorithms.

REFERENCE:
  Deb, K., Pratap, A., Agarwal, S., and Meyarivan, T. (2002).
  "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II",
  IEEE Transactions on Evolutionary Computation, 6(2), pp. 182-197.
"""

from typing import List, Tuple, Dict, Any, Optional
import math
from .models import CandidatePlan, SelectionRuleConfig


def dominates(a: CandidatePlan, b: CandidatePlan) -> bool:
    """Check if candidate A Pareto-dominates candidate B.

    Objectives:
      1. Maximize Cumulative Oil: a.cumulative_oil_bbl >= b.cumulative_oil_bbl
      2. Minimize SOR:            a.sor_t_per_bbl <= b.sor_t_per_bbl
      3. Minimize Steam Use:      a.cumulative_steam_t <= b.cumulative_steam_t

    Dominance requires being no worse in all 3 objectives and strictly better in at least one.
    """
    no_worse = (
        (a.cumulative_oil_bbl >= b.cumulative_oil_bbl) and
        (a.sor_t_per_bbl <= b.sor_t_per_bbl) and
        (a.cumulative_steam_t <= b.cumulative_steam_t)
    )
    strictly_better = (
        (a.cumulative_oil_bbl > b.cumulative_oil_bbl) or
        (a.sor_t_per_bbl < b.sor_t_per_bbl) or
        (a.cumulative_steam_t < b.cumulative_steam_t)
    )
    return no_worse and strictly_better


def fast_non_dominated_sort(candidates: List[CandidatePlan]) -> List[List[CandidatePlan]]:
    """Perform Deb's Fast Non-Dominated Sort on candidate plans.

    Returns:
      List of Pareto fronts [F_1, F_2, ...], where F_1 is the non-dominated front.
    """
    if not candidates:
        return []

    domination_count: Dict[int, int] = {}
    dominated_set: Dict[int, List[int]] = {}
    fronts: List[List[int]] = [[]]

    for p in range(len(candidates)):
        domination_count[p] = 0
        dominated_set[p] = []
        for q in range(len(candidates)):
            if p == q:
                continue
            if dominates(candidates[p], candidates[q]):
                dominated_set[p].append(q)
            elif dominates(candidates[q], candidates[p]):
                domination_count[p] += 1

        if domination_count[p] == 0:
            candidates[p].pareto_rank = 1
            fronts[0].append(p)

    i = 0
    while i < len(fronts) and fronts[i]:
        next_front: List[int] = []
        for p in fronts[i]:
            for q in dominated_set[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    candidates[q].pareto_rank = i + 2
                    next_front.append(q)
        i += 1
        if next_front:
            fronts.append(next_front)

    return [[candidates[idx] for idx in front] for front in fronts if front]


def assign_crowding_distance(front: List[CandidatePlan]) -> None:
    """Compute Deb's crowding distance metric for diversity preservation."""
    n = len(front)
    if n == 0:
        return
    for c in front:
        c.crowding_distance = 0.0

    if n <= 2:
        for c in front:
            c.crowding_distance = float("inf")
        return

    # Objectives to evaluate diversity along:
    # 1. Cumulative oil (maximize)
    # 2. SOR (minimize)
    # 3. Steam use (minimize)
    objectives = [
        lambda c: c.cumulative_oil_bbl,
        lambda c: c.sor_t_per_bbl,
        lambda c: c.cumulative_steam_t,
    ]

    for obj in objectives:
        front.sort(key=obj)
        front[0].crowding_distance = float("inf")
        front[-1].crowding_distance = float("inf")
        val_range = obj(front[-1]) - obj(front[0])
        if abs(val_range) < 1e-9:
            continue
        for i in range(1, n - 1):
            if front[i].crowding_distance != float("inf"):
                dist = (obj(front[i + 1]) - obj(front[i - 1])) / val_range
                front[i].crowding_distance += dist


def extract_pareto_front(candidates: List[CandidatePlan]) -> List[CandidatePlan]:
    """Filter candidates to keep only the feasible, non-dominated Pareto front (Rank 1)."""
    feasible = [c for c in candidates if c.is_feasible]
    if not feasible:
        return []

    fronts = fast_non_dominated_sort(feasible)
    if not fronts:
        return []

    rank1 = fronts[0]
    assign_crowding_distance(rank1)

    # Sort primarily by cumulative oil descending
    rank1.sort(key=lambda c: c.cumulative_oil_bbl, reverse=True)
    return rank1


def select_compromise_plan(
    pareto_candidates: List[CandidatePlan],
    config: Optional[SelectionRuleConfig] = None,
) -> Tuple[CandidatePlan, str]:
    """Select a representative plan from the Pareto set using multi-criteria compromise.

    NOTE: The returned plan is an optimal trade-off according to the specified
    objective weighting, NOT an unconditional 'mathematically best plan'.
    """
    if not pareto_candidates:
        raise ValueError("Cannot select a plan from an empty Pareto candidate set")

    rule_cfg = config or SelectionRuleConfig()

    if len(pareto_candidates) == 1:
        desc = (
            f"Selected sole Pareto candidate under rule '{rule_cfg.rule_name}'. "
            f"Weights: oil={rule_cfg.weight_oil:.2f}, SOR={rule_cfg.weight_sor:.2f}, steam={rule_cfg.weight_steam:.2f}."
        )
        return pareto_candidates[0], desc

    # Normalization bounds across the Pareto front:
    min_oil = min(c.cumulative_oil_bbl for c in pareto_candidates)
    max_oil = max(c.cumulative_oil_bbl for c in pareto_candidates)
    range_oil = max(max_oil - min_oil, 1e-5)

    min_sor = min(c.sor_t_per_bbl for c in pareto_candidates)
    max_sor = max(c.sor_t_per_bbl for c in pareto_candidates)
    range_sor = max(max_sor - min_sor, 1e-5)

    min_steam = min(c.cumulative_steam_t for c in pareto_candidates)
    max_steam = max(c.cumulative_steam_t for c in pareto_candidates)
    range_steam = max(max_steam - min_steam, 1e-5)

    # Weights normalized to sum to 1.0
    w_sum = rule_cfg.weight_oil + rule_cfg.weight_sor + rule_cfg.weight_steam
    w_oil = rule_cfg.weight_oil / w_sum
    w_sor = rule_cfg.weight_sor / w_sum
    w_steam = rule_cfg.weight_steam / w_sum

    best_score = float("inf")
    best_candidate = pareto_candidates[0]

    # Compromise Programming: minimize weighted normalized Euclidean distance to Utopian point
    # Utopian point: max_oil, min_sor, min_steam
    for c in pareto_candidates:
        d_oil = (max_oil - c.cumulative_oil_bbl) / range_oil
        d_sor = (c.sor_t_per_bbl - min_sor) / range_sor
        d_steam = (c.cumulative_steam_t - min_steam) / range_steam

        dist_sq = (w_oil * (d_oil ** 2)) + (w_sor * (d_sor ** 2)) + (w_steam * (d_steam ** 2))
        score = math.sqrt(dist_sq)

        if score < best_score:
            best_score = score
            best_candidate = c

    rule_desc = (
        f"Selected plan using Compromise Programming (weighted Euclidean distance to utopian point) "
        f"under preference rule '{rule_cfg.rule_name}'. "
        f"Assigned objective weights: Cumulative Oil = {w_oil * 100:.1f}%, "
        f"SOR Minimization = {w_sor * 100:.1f}%, Steam Minimization = {w_steam * 100:.1f}%. "
        f"(Note: This selection reflects the stated objective weighting and is not an unconditional "
        f"universal best plan)."
    )

    return best_candidate, rule_desc
