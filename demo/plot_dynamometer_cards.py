"""Generate and plot sample dynamometer cards for all 5 prototype classes.

Usage:
    python demo/plot_dynamometer_cards.py

Outputs:
    demo/sample_dynamometer_cards.png
"""

import os
import sys

# Ensure backend package can be imported from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib
matplotlib.use("Agg")  # Headless non-interactive backend
import matplotlib.pyplot as plt

from backend.app.srp_engine import (
    RodStringParams,
    PumpParams,
    OperatingState,
    CardClass,
    generate_dynamometer_card,
)


def run_card_plots():
    print("Generating sample dynamometer cards for all 5 prototype classes...")

    classes = [
        (CardClass.NORMAL, 95.0, "#27ae60", "Normal (Full Fillage)"),
        (CardClass.GAS_INTERFERENCE, 80.0, "#e67e22", "Gas Interference / Rod Floating"),
        (CardClass.FLUID_POUND, 50.0, "#d35400", "Fluid Pound (Partial Fillage)"),
        (CardClass.TRAVELING_VALVE_LEAK, 90.0, "#8e44ad", "Traveling Valve Leak"),
        (CardClass.PUMP_OFF, 15.0, "#c0392b", "Pump-Off (Severe Underfill)"),
    ]

    r_params = RodStringParams(length_m=600.0, diameter_in=0.875)
    p_params = PumpParams(plunger_diameter_in=2.0)

    fig, axes = plt.subplots(1, 5, figsize=(20, 4.5), sharey=True)

    for ax, (cls, fillage, color, title) in zip(axes, classes):
        state = OperatingState(
            spm=6.0,
            surface_stroke_in=72.0,
            pump_fillage_pct=fillage,
            card_class=cls,
        )
        card = generate_dynamometer_card(r_params, p_params, state, prefer_numerical=False)

        surf_x = [p[0] for p in card.surface_card_points]
        surf_y = [p[1] for p in card.surface_card_points]

        down_x = [p[0] for p in card.downhole_card_points]
        down_y = [p[1] for p in card.downhole_card_points]

        # Surface card
        ax.plot(surf_x, surf_y, color=color, linewidth=2.0, label="Surface Card")

        # Downhole card
        if down_x:
            ax.plot(down_x, down_y, color="#2c3e50", linestyle="--", linewidth=1.5, label="Downhole Card")

        ax.set_title(f"{cls.value}\n({title})", fontsize=10, fontweight="bold", pad=8)
        ax.set_xlabel("Displacement (in)", fontsize=9.5)
        ax.grid(True, linestyle=":", alpha=0.6)

        # Annotations
        ax.text(
            0.05, 0.05,
            f"Fillage: {card.fillage_estimate_pct:.0f}%\nArea: {card.card_area_in_lbf:,.0f} in·lbf\nPower: {card.power_estimate_hp:.1f} HP",
            transform=ax.transAxes,
            fontsize=8.5,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="#ccc"),
        )

    axes[0].set_ylabel("Polished Rod Load (lbf)", fontsize=10, fontweight="bold")
    axes[0].legend(loc="upper left", fontsize=8.5)

    plt.suptitle("BAGHEWALA-X: SRP Dynamometer Prototype Card Signatures (Gibbs Damped-Wave Model)", fontsize=12, fontweight="bold", y=1.02)
    plt.tight_layout()

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "sample_dynamometer_cards.png")
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(f"Sample dynamometer cards plot saved to: {out_path}")
    return out_path


if __name__ == "__main__":
    run_card_plots()
