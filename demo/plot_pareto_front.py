"""Standalone script to run CSSOptimizer and plot the Pareto Frontier.

Usage:
    python demo/plot_pareto_front.py

Outputs:
    demo/sample_pareto_front.png
"""

import os
import sys

# Ensure backend package can be imported from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt

from backend.app.optimization import (
    CSSOptimizer,
    OptimizationBounds,
    SelectionRuleConfig,
)


def run_pareto_plot():
    print("Initializing CSSOptimizer...")
    opt = CSSOptimizer(random_seed=42)

    print("Running multi-objective optimization (Grid Search + NSGA-II)...")
    rule = SelectionRuleConfig(
        rule_name="balanced_compromise",
        weight_oil=0.45,
        weight_sor=0.35,
        weight_steam=0.20,
    )
    result = opt.optimize(selection_rule=rule, use_nsga2=True)

    print(f"\nOptimization complete:")
    print(f"Total Evaluated: {result.constraints_summary['total_evaluated']}")
    print(f"Feasible:        {result.constraints_summary['feasible_candidates']}")
    print(f"Pareto Front:    {len(result.pareto_candidates)} non-dominated candidates")
    print(f"\n{result.selection_rule_description}")
    print(f"Current Plan:    Oil={result.current_plan.cumulative_oil_bbl:,.0f} bbl, SOR={result.current_plan.sor_t_per_bbl:.2f} t/bbl, Steam={result.current_plan.cumulative_steam_t:,.0f} t")
    print(f"Selected Plan:   Oil={result.selected_plan.cumulative_oil_bbl:,.0f} bbl, SOR={result.selected_plan.sor_t_per_bbl:.2f} t/bbl, Steam={result.selected_plan.cumulative_steam_t:,.0f} t")

    # Extract points for plotting
    feasible_candidates = [c for c in result.all_evaluated_candidates if c.is_feasible]
    pareto_ids = {c.plan_id for c in result.pareto_candidates}

    other_x = [c.sor_t_per_bbl for c in feasible_candidates if c.plan_id not in pareto_ids and c.plan_id != result.current_plan.plan_id]
    other_y = [c.cumulative_oil_bbl for c in feasible_candidates if c.plan_id not in pareto_ids and c.plan_id != result.current_plan.plan_id]

    pareto_x = [c.sor_t_per_bbl for c in result.pareto_candidates if c.plan_id != result.selected_plan.plan_id]
    pareto_y = [c.cumulative_oil_bbl for c in result.pareto_candidates if c.plan_id != result.selected_plan.plan_id]

    curr_x = result.current_plan.sor_t_per_bbl
    curr_y = result.current_plan.cumulative_oil_bbl

    sel_x = result.selected_plan.sor_t_per_bbl
    sel_y = result.selected_plan.cumulative_oil_bbl

    # Create figure
    plt.figure(figsize=(10, 7))
    plt.grid(True, linestyle="--", alpha=0.5)

    # 1. Feasible non-Pareto points
    if other_x:
        plt.scatter(other_x, other_y, color="#a0aec0", alpha=0.45, s=40, label="Feasible Candidates")

    # 2. Pareto Optimal Front
    if pareto_x:
        plt.scatter(pareto_x, pareto_y, color="#0984e3", alpha=0.9, s=70, edgecolors="#074b83", linewidth=1.2, label="Pareto Front Candidates")

    # 3. Current Operating Plan
    plt.scatter([curr_x], [curr_y], color="#e74c3c", s=180, marker="^", edgecolors="#900", linewidth=1.8, label=f"Current Baseline Plan ({result.current_plan.plan_id})", zorder=5)

    # 4. Selected Plan
    plt.scatter([sel_x], [sel_y], color="#00b894", s=220, marker="*", edgecolors="#005a48", linewidth=1.8, label=f"Selected Compromise Plan ({result.selected_plan.plan_id})", zorder=6)

    # Label selected and current plans
    plt.annotate(
        f"Selected ({sel_y:,.0f} bbl, {sel_x:.2f} SOR)",
        xy=(sel_x, sel_y),
        xytext=(sel_x + 0.08, sel_y + 400),
        arrowprops=dict(facecolor="#00b894", shrink=0.08, width=1.5, headwidth=6),
        fontweight="bold",
        fontsize=9.5,
        color="#005a48",
    )
    plt.annotate(
        f"Current ({curr_y:,.0f} bbl, {curr_x:.2f} SOR)",
        xy=(curr_x, curr_y),
        xytext=(curr_x - 0.25, curr_y - 800),
        arrowprops=dict(facecolor="#e74c3c", shrink=0.08, width=1.5, headwidth=6),
        fontweight="bold",
        fontsize=9.5,
        color="#900",
    )

    plt.title("BAGHEWALA-X: CSS Multi-Objective Optimization (Pareto Frontier)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Steam-to-Oil Ratio (t steam / bbl oil) — [Lower is Better]", fontsize=11, fontweight="bold")
    plt.ylabel("Cumulative Oil Production (bbl) — [Higher is Better]", fontsize=11, fontweight="bold")
    plt.legend(loc="best", framealpha=0.9, fontsize=10)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "sample_pareto_front.png")
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(f"\nSuccessfully generated Pareto plot: {out_path}")
    return out_path


if __name__ == "__main__":
    run_pareto_plot()
