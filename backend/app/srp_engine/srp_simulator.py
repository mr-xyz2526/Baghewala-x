"""SRP (Surface Rod Pump) analytical simulator.

Models pump fillage, rod loading, downhole stroke, and motor power
using classic beam-pump geometry and Gibbs (1963) rod-mechanics references.

SOURCES:
  Gibbs, S.G. (1963). "Predicting the Behavior of Sucker-Rod Pumping Systems."
    JPT (July 1963), pp. 769-778. SPE-588-PA.
  American Petroleum Institute (API) Specification 11E (latest edition):
    "Specification for Pumping Units."
  Takacs, G. (2015). "Sucker-Rod Pumping Handbook", Elsevier.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
import math


@dataclass
class SRPConfig:
    """Mechanical geometry and fluid properties for an SRP installation.

    Defaults are representative for a mid-size heavy-oil beam pump.
    """
    rod_od_in: float = 0.875           # Rod OD (inches)
    plunger_diameter_in: float = 2.0   # Plunger/barrel diameter (inches)
    pump_depth_m: float = 500.0        # Measured pump depth (m)
    tubing_id_in: float = 2.441        # Tubing ID (inches)  (2-7/8" EUE)
    structural_stroke_in: float = 72.0 # Surface stroke length S (inches)
    gear_reducer_efficiency: float = 0.92   # Mechanical efficiency
    surface_unit_rating_klb: float = 40.0   # Peak polished-rod rating (1000 lbf)
    max_spm: float = 12.0              # Maximum strokes per minute
    min_spm: float = 2.0               # Minimum strokes per minute
    fluid_density_kg_m3: float = 900.0 # Produced fluid density (kg/m^3)
    rod_density_kg_m3: float = 7850.0  # Steel rod density (kg/m^3)


@dataclass
class SRPOperatingPoint:
    """Per-stroke-rate operating point output."""
    spm: float                     # Strokes per minute
    stroke_length_in: float        # Surface stroke length (in)
    plunger_stroke_in: float       # Effective downhole plunger stroke (in)
    pump_fillage_pct: float        # Pump fillage (%)
    theoretical_fluid_bpd: float   # Theoretical volumetric rate (bbl/day)
    peak_rod_load_lbf: float       # Peak (upstroke) polished-rod load (lbf)
    min_rod_load_lbf: float        # Min (downstroke) polished-rod load (lbf)
    rod_stress_indicator: float    # Approximate peak rod stress (fraction of yield)
    motor_power_kw: float          # Estimated motor shaft power (kW)
    torque_indicator_ft_lbf: float # Peak torque at gearbox (ft·lbf)
    fluid_load_lbf: float          # Net fluid load (lbf)
    oil_rate_bopd: float           # Estimated oil rate (BOPD) adjusted for fillage


class SRPSimulator:
    """Analytical beam-pump SRP simulator.

    Implements classic static rod-load equations (Gibbs 1963) and
    standard API geometry relations.
    """

    # Unit conversion constants
    _IN_TO_M = 0.0254
    _FT_TO_M = 0.3048
    _LBF_TO_N = 4.44822
    _LB_TO_KG = 0.453592
    _M3_TO_BBL = 6.28981      # 1 m^3 = 6.28981 bbl (API petroleum barrel)
    _KG_TO_LBF = 2.20462 / 1.0  # kg → lbf divide by 0.453592 * g

    def __init__(self, config: SRPConfig = None):
        self.config = config or SRPConfig()
        self._validate()

    def _validate(self):
        cfg = self.config
        if cfg.rod_od_in <= 0:
            raise ValueError("rod_od_in must be > 0")
        if cfg.plunger_diameter_in <= 0:
            raise ValueError("plunger_diameter_in must be > 0")
        if cfg.pump_depth_m <= 0:
            raise ValueError("pump_depth_m must be > 0")
        if cfg.structural_stroke_in <= 0:
            raise ValueError("structural_stroke_in must be > 0")
        if cfg.gear_reducer_efficiency <= 0 or cfg.gear_reducer_efficiency > 1:
            raise ValueError("gear_reducer_efficiency must be in (0, 1]")

    # -----------------------------------------------------------------------
    # Derived geometric helpers
    # -----------------------------------------------------------------------
    @property
    def plunger_area_m2(self) -> float:
        """Plunger cross-sectional area (m^2)."""
        r = (self.config.plunger_diameter_in * self._IN_TO_M) / 2.0
        return math.pi * r ** 2

    @property
    def rod_area_m2(self) -> float:
        """Rod cross-sectional area (m^2)."""
        r = (self.config.rod_od_in * self._IN_TO_M) / 2.0
        return math.pi * r ** 2

    @property
    def rod_weight_per_m_n(self) -> float:
        """Rod linear weight in N/m."""
        return self.rod_area_m2 * self.config.rod_density_kg_m3 * 9.80665

    @property
    def rod_elastic_constant_m_per_n(self) -> float:
        """Elastic stretch constant for the rod string (m/N).
        E_steel ≈ 200 GPa.
        SOURCE: Gibbs (1963), rod-stretch correction.
        """
        E_steel = 200.0e9  # Pa
        return self.config.pump_depth_m / (E_steel * self.rod_area_m2)

    # -----------------------------------------------------------------------
    # Load calculations
    # -----------------------------------------------------------------------
    def _fluid_load_n(self) -> float:
        """Net fluid (buoyancy-corrected differential pressure) load on plunger (N).

        SOURCE: Gibbs (1963), Eq. (2): Fluid load = gamma_f * D * A_p
        where gamma_f = produced fluid specific weight (N/m^3), D = pump depth.
        """
        gamma_f = self.config.fluid_density_kg_m3 * 9.80665  # N/m^3
        return gamma_f * self.config.pump_depth_m * self.plunger_area_m2

    def _rod_weight_n(self) -> float:
        """Total rod string weight in air (N)."""
        return self.rod_weight_per_m_n * self.config.pump_depth_m

    def _buoyancy_force_n(self) -> float:
        """Buoyancy force on submerged rod string (N).

        SOURCE: Takacs (2015), Chapter 4 – rod buoyancy correction.
        """
        gamma_f = self.config.fluid_density_kg_m3 * 9.80665
        return gamma_f * self.rod_area_m2 * self.config.pump_depth_m

    def _rod_weight_in_fluid_n(self) -> float:
        """Buoyancy-corrected rod weight (N)."""
        return self._rod_weight_n() - self._buoyancy_force_n()

    def _dynamic_factor(self, spm: float) -> float:
        """Approximate dynamic force factor based on Gibbs inertia approximation.

        SOURCE: Gibbs (1963), Eq. (6): F_dyn ≈ (S * n^2) / 70500 * W_rod
        (in API field units where S is stroke in inches, n is strokes/min).
        """
        S = self.config.structural_stroke_in
        return (S * spm ** 2) / 70500.0

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def compute_operating_point(
        self,
        spm: float,
        fillage_pct: float = 100.0,
        water_cut_pct: float = 30.0,
        oil_gravity_api: float = 13.0,
    ) -> SRPOperatingPoint:
        """Compute SRP operating point for the given SPM and pump fillage.

        Parameters:
            spm:          Strokes per minute (must be in [min_spm, max_spm]).
            fillage_pct:  Pump fillage percentage (0 – 100). 100 = fully loaded.
            water_cut_pct: Water-cut (%).
            oil_gravity_api: Oil API gravity (for BOPD split).

        Returns:
            SRPOperatingPoint dataclass.
        """
        if spm <= 0:
            raise ValueError(f"SPM must be positive, got {spm}")
        if not 0.0 <= fillage_pct <= 100.0:
            raise ValueError(f"fillage_pct must be 0–100, got {fillage_pct}")

        cfg = self.config
        stroke_m = cfg.structural_stroke_in * self._IN_TO_M

        # Rod elastic stretch reduces effective plunger stroke:
        # SOURCE: Gibbs (1963) – rod-pump interaction, stretch correction
        fluid_load_n = self._fluid_load_n()
        elastic_stretch_m = fluid_load_n * self.rod_elastic_constant_m_per_n
        plunger_stroke_m = max(0.0, stroke_m - 2.0 * elastic_stretch_m)
        plunger_stroke_in = plunger_stroke_m / self._IN_TO_M

        # Theoretical production rate (m^3/day) at 100% fillage:
        # SOURCE: API 11E – pump displacement formula
        pump_displacement_m3_per_stroke = self.plunger_area_m2 * plunger_stroke_m
        theoretical_m3_day = pump_displacement_m3_per_stroke * spm * 60.0 * 24.0
        theoretical_bpd = theoretical_m3_day * self._M3_TO_BBL

        # Actual fluid BPD adjusted for fillage
        actual_fluid_bpd = theoretical_bpd * (fillage_pct / 100.0)

        # Split into oil / water
        oil_fraction = max(0.0, (100.0 - water_cut_pct) / 100.0)
        oil_rate_bopd = actual_fluid_bpd * oil_fraction

        # -----------------------------------------------------------------------
        # Static rod loads (polished-rod load analysis):
        # SOURCE: Gibbs (1963), static approximation for upstroke/downstroke
        # Peak (upstroke) load: PPRL = W_rod_fluid + F_L + F_dyn
        # Min (downstroke) load: MPRL = W_rod_fluid - F_L - F_dyn (can be ~0)
        # -----------------------------------------------------------------------
        rod_wt_fluid_n = self._rod_weight_in_fluid_n()
        dyn_frac = self._dynamic_factor(spm)

        # Fluid load proportioned to fillage
        active_fluid_load_n = fluid_load_n * (fillage_pct / 100.0)

        pprl_n = rod_wt_fluid_n + active_fluid_load_n * (1.0 + dyn_frac)
        mprl_n = rod_wt_fluid_n - active_fluid_load_n * (1.0 + dyn_frac)

        pprl_lbf = pprl_n / self._LBF_TO_N
        mprl_lbf = max(0.0, mprl_n / self._LBF_TO_N)

        # Rod stress indicator (fraction of typical API Grade D yield ~100,000 psi)
        rod_area_in2 = (math.pi / 4.0) * (cfg.rod_od_in ** 2)
        peak_stress_psi = pprl_lbf / rod_area_in2
        rod_stress_indicator = peak_stress_psi / 100_000.0  # Grade D ~100 kpsi

        # -----------------------------------------------------------------------
        # Torque estimate: SOURCE: API 11E – gearbox torque
        # Peak Torque ≈ Net Torque Factor × (PPRL - rod_counterbalance)
        # Simplified as: T_peak ≈ (PPRL - MPRL)/2 × (S/2) [ft·lbf]
        # -----------------------------------------------------------------------
        S_ft = cfg.structural_stroke_in / 12.0
        torque_ft_lbf = ((pprl_lbf - mprl_lbf) / 2.0) * (S_ft / 2.0)

        # Motor power:
        # SOURCE: Takacs (2015), Chapter 5
        # P = (PPRL + MPRL) / 2 × S × N / (33,000 × eff) [HP]
        avg_load_lbf = (pprl_lbf + mprl_lbf) / 2.0
        power_hp = (avg_load_lbf * S_ft * spm) / (33_000.0 * cfg.gear_reducer_efficiency)
        power_kw = power_hp * 0.745699872

        return SRPOperatingPoint(
            spm=spm,
            stroke_length_in=cfg.structural_stroke_in,
            plunger_stroke_in=plunger_stroke_in,
            pump_fillage_pct=fillage_pct,
            theoretical_fluid_bpd=theoretical_bpd,
            peak_rod_load_lbf=pprl_lbf,
            min_rod_load_lbf=mprl_lbf,
            rod_stress_indicator=rod_stress_indicator,
            motor_power_kw=power_kw,
            torque_indicator_ft_lbf=torque_ft_lbf,
            fluid_load_lbf=active_fluid_load_n / self._LBF_TO_N,
            oil_rate_bopd=oil_rate_bopd,
        )

    def vfd_hz_to_spm(self, hz: float, rated_hz: float = 60.0) -> float:
        """Convert VFD frequency to strokes/minute (proportional to motor speed).

        SOURCE: Takacs (2015) – VFD-controlled beam pumps.
        """
        if rated_hz <= 0 or hz < 0:
            raise ValueError("rated_hz must be > 0 and hz >= 0")
        spm_ratio = hz / rated_hz
        return max(self.config.min_spm, min(self.config.max_spm, spm_ratio * self.config.max_spm))

    def optimize_spm_for_rate(
        self,
        target_rate_bopd: float,
        fillage_pct: float = 100.0,
        water_cut_pct: float = 30.0,
    ) -> SRPOperatingPoint:
        """Find the SPM that approximately meets the target oil production rate.

        Uses bisection search between min_spm and max_spm.
        """
        lo, hi = self.config.min_spm, self.config.max_spm
        for _ in range(64):
            mid = (lo + hi) / 2.0
            rate = self.compute_operating_point(mid, fillage_pct, water_cut_pct).oil_rate_bopd
            if rate < target_rate_bopd:
                lo = mid
            else:
                hi = mid
        return self.compute_operating_point((lo + hi) / 2.0, fillage_pct, water_cut_pct)
