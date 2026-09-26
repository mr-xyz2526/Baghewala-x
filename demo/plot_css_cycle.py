"""Standalone script to simulate and plot a sample CSS (Cyclic Steam Stimulation) cycle.

Usage:
    python demo/plot_css_cycle.py

Outputs:
    demo/sample_css_cycle.png
"""

import os
import sys

# Ensure backend package can be imported from root directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np

from backend.app.css_engine import (
    CSSCycleSimulator,
    CSSCycleParams,
    ProductivityParams,
)


def run_sample_plot():
    print("Initializing CSSCycleSimulator...")
    simulator = CSSCycleSimulator()

    params = CSSCycleParams(
        steam_rate_tpd=850.0,
        steam_temp_c=260.0,
        injection_days=18,
        steam_quality=0.8,
        soak_days=4,
        production_days=70,
        productivity_params=ProductivityParams(
            base_drawdown_bar=25.0,
            base_productivity_index_bopd_per_bar=1.2,
            water_cut_pct=35.0,
            max_oil_rate_bopd=1200.0,
        ),
    )

    print(f"Running simulation: {params.injection_days}d injection, {params.soak_days}d soak, {params.production_days}d production...")
    result = simulator.run_cycle(params)

    print("\n--- Simulation Summary ---")
    print(f"Heated Radius:           {result.injection_summary.heated_radius_m:.2f} m")
    print(f"Heated Area:             {result.injection_summary.heated_area_m2:.1f} m^2")
    print(f"Thermal Efficiency:      {result.injection_summary.thermal_efficiency_indicator * 100:.1f} %")
    print(f"Total Steam Injected:    {result.cycle_steam:,.1f} tonnes")
    print(f"Total Oil Produced:      {result.cycle_oil:,.1f} bbl")
    print(f"Steam-to-Oil Ratio (SOR):{result.SOR:.2f} t steam / bbl oil")
    print(f"Volumetric SOR (CWE):    {result.sor_cwe_bbl_per_bbl:.2f} bbl steam / bbl oil")

    # Extract timeline arrays
    days = [r.day for r in result.full_cycle_timeline]
    temps = [r.temperature_c for r in result.full_cycle_timeline]
    viscs = [r.viscosity_cp for r in result.full_cycle_timeline]
    rates = [r.oil_rate_bopd for r in result.full_cycle_timeline]
    cum_oils = [r.cumulative_oil_bbl for r in result.full_cycle_timeline]

    inj_end = params.injection_days
    soak_end = inj_end + params.soak_days
    total_days = days[-1]

    # Create 3-panel figure
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    plt.subplots_adjust(hspace=0.25)

    # Shading phase regions
    for ax in (ax1, ax2, ax3):
        ax.axvspan(1, inj_end, color="#ffdddd", alpha=0.5, label="Injection" if ax == ax1 else "")
        ax.axvspan(inj_end, soak_end, color="#fff2cc", alpha=0.6, label="Soaking" if ax == ax1 else "")
        ax.axvspan(soak_end, total_days, color="#d9ead3", alpha=0.5, label="Production" if ax == ax1 else "")
        ax.grid(True, linestyle="--", alpha=0.5)

    # Panel 1: Temperature & Viscosity
    color_temp = "#d9534f"
    ax1.set_ylabel("Reservoir Temp (°C)", color=color_temp, fontsize=11, fontweight="bold")
    line1 = ax1.plot(days, temps, color=color_temp, linewidth=2.2, label="Temperature (°C)")
    ax1.tick_params(axis="y", labelcolor=color_temp)

    ax1_twin = ax1.twinx()
    color_visc = "#337ab7"
    ax1_twin.set_ylabel("Oil Viscosity (cP, log scale)", color=color_visc, fontsize=11, fontweight="bold")
    line2 = ax1_twin.semilogy(days, viscs, color=color_visc, linewidth=2.0, linestyle="--", label="Viscosity (cP)")
    ax1_twin.tick_params(axis="y", labelcolor=color_visc)
    ax1.set_title("BAGHEWALA-X: Analytical CSS Cycle Simulation (Marx-Langenheim & Boberg-Lantz)", fontsize=13, fontweight="bold")

    # Panel 2: Oil Rate & Cumulative Oil
    color_rate = "#2e7d32"
    ax2.set_ylabel("Oil Rate (BOPD)", color=color_rate, fontsize=11, fontweight="bold")
    ax2.plot(days, rates, color=color_rate, linewidth=2.2, label="Oil Rate (BOPD)")
    ax2.tick_params(axis="y", labelcolor=color_rate)

    ax2_twin = ax2.twinx()
    color_cum = "#e67e22"
    ax2_twin.set_ylabel("Cumulative Oil (bbl)", color=color_cum, fontsize=11, fontweight="bold")
    ax2_twin.plot(days, cum_oils, color=color_cum, linewidth=2.0, linestyle=":", label="Cumulative Oil")
    ax2_twin.tick_params(axis="y", labelcolor=color_cum)

    # Panel 3: Injected Steam Profile & Metrics
    steam_rates = [r.steam_rate_tpd for r in result.full_cycle_timeline]
    ax3.step(days, steam_rates, where="mid", color="#8e44ad", linewidth=2.0, label="Steam Injection Rate (t/d)")
    ax3.set_ylabel("Steam Rate (t/d)", color="#8e44ad", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Cycle Time (Days)", fontsize=11, fontweight="bold")

    # Summary text box on Panel 3
    summary_txt = (
        f"Cycle Metrics:\n"
        f"• Steam Injected: {result.cycle_steam:,.0f} t\n"
        f"• Oil Produced: {result.cycle_oil:,.0f} bbl\n"
        f"• Heated Radius: {result.injection_summary.heated_radius_m:.1f} m\n"
        f"• Thermal Eff: {result.injection_summary.thermal_efficiency_indicator * 100:.1f}%\n"
        f"• Volumetric SOR: {result.sor_cwe_bbl_per_bbl:.2f} bbl/bbl"
    )
    ax3.text(
        0.73, 0.50, summary_txt,
        transform=ax3.transAxes,
        fontsize=9.5,
        verticalalignment="center",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#888", alpha=0.9),
    )

    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_css_cycle.png")
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(f"\nSuccessfully generated plot: {out_path}")
    return out_path


if __name__ == "__main__":
    run_sample_plot()
