"""Wellbore and surface hydraulics engine.

Implements:
1. Simplified Beggs & Brill (1973) multiphase correlation with vertical inclination correction.
2. Reduced single-phase heavy-oil laminar/turbulent path when multiphase inputs are absent.
3. Sachdeva (1986) / Perkins (1993) subcritical surface choke pressure drop.

SOURCES:
  Beggs, H.D. and Brill, J.P. (1973). "A Study of Two-Phase Flow in Inclined Pipes",
    Journal of Petroleum Technology, 25(5), pp. 607-617; SPE-4007-PA.
  Moody, L.F. (1944). "Friction Factors for Pipe Flow", Trans. ASME, 66(8), pp. 671-684.
  Haaland, S.E. (1983). "Simple and explicit formulas for the friction factor in turbulent pipe flow",
    Journal of Fluids Engineering, 105(1), pp. 89-90.
"""

from typing import Optional, Dict, Any, Tuple
import math

from .models import (
    WellboreGeometry,
    HydraulicsFluidProperties,
    PressureDropComponents,
    HydraulicsResult,
)
from .choke import calculate_choke_pressure_drop_bar


# Unit conversion constants
_BOPD_TO_M3_S = 1.8401307e-6     # 1 barrel/day = 1.84013e-6 m^3/s
_MSCFD_TO_M3_S = 3.2774128e-4    # 1000 standard cu ft/day = 3.2774e-4 standard m^3/s
_CP_TO_PA_S = 1.0e-3             # 1 cP = 1 mPa*s = 0.001 Pa*s
_IN_TO_M = 0.0254                # 1 inch = 0.0254 m
_PA_TO_BAR = 1.0e-5              # 1 Pa = 1e-5 bar


def calculate_friction_factor_darcy(
    reynolds_number: float,
    relative_roughness: float,
) -> float:
    """Calculate Darcy-Weisbach pipe friction factor f with guaranteed viscosity monotonicity.

    SOURCES:
      Laminar: Hagen-Poiseuille, f = 64 / Re.
      Turbulent: Haaland (1983) explicit approximation to Colebrook-White.
      Transitional: Monotonic cubic Hermite interpolation between Re=2300 and Re=4000.
    """
    re = max(1.0, float(reynolds_number))
    eps_over_d = max(1.0e-6, float(relative_roughness))

    if re <= 2300.0:
        # Laminar flow
        # SOURCE: Hagen-Poiseuille equation
        return 64.0 / re

    elif re >= 4000.0:
        # Fully developed turbulent flow
        # SOURCE: Haaland (1983), Eq. (1)
        term1 = (eps_over_d / 3.7) ** 1.11
        term2 = 6.9 / re
        inv_sqrt_f = -1.8 * math.log10(max(1.0e-8, term1 + term2))
        f_turb = (1.0 / inv_sqrt_f) ** 2
        return float(max(0.008, f_turb))

    else:
        # Transitional flow (2300 < Re < 4000):
        # Smooth interpolation to maintain strict monotonicity
        f_lam_2300 = 64.0 / 2300.0  # ≈ 0.02783
        # Turbulent at 4000
        term1 = (eps_over_d / 3.7) ** 1.11
        term2 = 6.9 / 4000.0
        f_turb_4000 = (1.0 / (-1.8 * math.log10(term1 + term2))) ** 2

        alpha = (re - 2300.0) / 1700.0  # 0 to 1
        return (1.0 - alpha) * f_lam_2300 + alpha * f_turb_4000


class HydraulicsEngine:
    """Lightweight wellbore pressure and surface choke performance calculator."""

    def __init__(
        self,
        geometry: Optional[WellboreGeometry] = None,
        fluid_properties: Optional[HydraulicsFluidProperties] = None,
    ):
        self.geom = geometry or WellboreGeometry()
        self.fluid = fluid_properties or HydraulicsFluidProperties()
        self._validate_inputs()

    def _validate_inputs(self):
        g = self.geom
        if g.depth_m <= 0.0:
            raise ValueError(f"depth_m must be > 0, got {g.depth_m}")
        if g.tubing_id_in <= 0.0:
            raise ValueError(f"tubing_id_in must be > 0, got {g.tubing_id_in}")
        if g.roughness_m < 0.0:
            raise ValueError(f"roughness_m must be >= 0, got {g.roughness_m}")
        if g.choke_nominal_id_in <= 0.0:
            raise ValueError(f"choke_nominal_id_in must be > 0, got {g.choke_nominal_id_in}")

        f = self.fluid
        if f.oil_density_kg_m3 <= 0.0:
            raise ValueError(f"oil_density_kg_m3 must be > 0, got {f.oil_density_kg_m3}")
        if f.oil_viscosity_cp <= 0.0:
            raise ValueError(f"oil_viscosity_cp must be > 0, got {f.oil_viscosity_cp}")
        if f.water_density_kg_m3 <= 0.0:
            raise ValueError(f"water_density_kg_m3 must be > 0, got {f.water_density_kg_m3}")
        if f.water_viscosity_cp <= 0.0:
            raise ValueError(f"water_viscosity_cp must be > 0, got {f.water_viscosity_cp}")

    def calculate_pressures(
        self,
        oil_rate_bopd: float,
        water_cut_pct: Optional[float] = None,
        gas_rate_mscfd: Optional[float] = None,
        oil_viscosity_cp: Optional[float] = None,
        oil_density_kg_m3: Optional[float] = None,
        depth_m: Optional[float] = None,
        tubing_id_in: Optional[float] = None,
        choke_opening_pct: float = 100.0,
        wellhead_pressure_bar: Optional[float] = None,
        pump_intake_pressure_bar: Optional[float] = None,
    ) -> HydraulicsResult:
        """Calculate wellbore pressure profile, pressure-drop components, and surface choke delta-P.

        Parameters:
            oil_rate_bopd: Surface oil production rate (BOPD).
            water_cut_pct: Water-cut percentage (0 - 100). If None or 0, liquid is pure oil.
            gas_rate_mscfd: Surface gas production rate (MSCFD). If None or 0, single-phase liquid flow is used.
            oil_viscosity_cp: Dynamic viscosity of oil (cP). Overrides config if provided.
            oil_density_kg_m3: Density of oil (kg/m^3). Overrides config if provided.
            depth_m: Well vertical depth (m). Overrides config if provided.
            tubing_id_in: Tubing inside diameter (in). Overrides config if provided.
            choke_opening_pct: Choke opening percentage in (0, 100].
            wellhead_pressure_bar: Backpressure at wellhead (bar). If supplied, pump intake pressure is derived.
            pump_intake_pressure_bar: Flowing pressure at pump intake (bar). If supplied, wellhead pressure is derived.

        Returns:
            HydraulicsResult with all pressure drop components and diagnostic metadata.
        """
        # Parameter validation
        if oil_rate_bopd < 0.0:
            raise ValueError(f"oil_rate_bopd must be >= 0, got {oil_rate_bopd}")
        if choke_opening_pct <= 0.0 or choke_opening_pct > 100.0:
            raise ValueError(f"choke_opening_pct must be in (0, 100], got {choke_opening_pct}")

        depth = depth_m if depth_m is not None else self.geom.depth_m
        if depth <= 0.0:
            raise ValueError(f"depth_m must be > 0, got {depth}")

        d_in = tubing_id_in if tubing_id_in is not None else self.geom.tubing_id_in
        if d_in <= 0.0:
            raise ValueError(f"tubing_id_in must be > 0, got {d_in}")

        mu_oil = oil_viscosity_cp if oil_viscosity_cp is not None else self.fluid.oil_viscosity_cp
        if mu_oil <= 0.0:
            raise ValueError(f"oil_viscosity_cp must be > 0, got {mu_oil}")

        rho_oil = oil_density_kg_m3 if oil_density_kg_m3 is not None else self.fluid.oil_density_kg_m3
        if rho_oil <= 0.0:
            raise ValueError(f"oil_density_kg_m3 must be > 0, got {rho_oil}")

        # Geometric properties
        d_m = d_in * _IN_TO_M
        flow_area_m2 = (math.pi / 4.0) * (d_m ** 2)
        rel_roughness = self.geom.roughness_m / d_m
        g = 9.80665

        # Liquid volumetric rates
        wc_frac = max(0.0, min(1.0, (water_cut_pct or 0.0) / 100.0))
        q_oil_m3_s = oil_rate_bopd * _BOPD_TO_M3_S

        if wc_frac < 1.0:
            q_liquid_m3_s = q_oil_m3_s / max(1e-6, 1.0 - wc_frac)
        else:
            q_liquid_m3_s = q_oil_m3_s

        q_water_m3_s = q_liquid_m3_s * wc_frac

        # Liquid mixture properties
        rho_water = self.fluid.water_density_kg_m3
        mu_water = self.fluid.water_viscosity_cp

        # Volume-weighted liquid density and viscosity
        rho_liquid = (1.0 - wc_frac) * rho_oil + wc_frac * rho_water
        mu_liquid_cp = (1.0 - wc_frac) * mu_oil + wc_frac * mu_water
        mu_liquid_pa_s = mu_liquid_cp * _CP_TO_PA_S

        # Gas rate
        q_gas_mscfd = gas_rate_mscfd or 0.0
        has_gas = (q_gas_mscfd > 0.0)
        has_multiphase = has_gas or (wc_frac > 0.0 and q_water_m3_s > 0.0)

        # -------------------------------------------------------------------
        # BRANCH 1: Single-phase heavy-oil reduced path
        # (When no gas is flowing and water cut is zero/missing)
        # -------------------------------------------------------------------
        if not has_gas and wc_frac <= 0.0:
            model_type = "SINGLE_PHASE_HEAVY_OIL_REDUCED"
            note = "Reduced single-phase heavy-oil laminar/turbulent pipe flow simplification without multiphase slippage."

            v_liquid = q_liquid_m3_s / flow_area_m2
            reynolds = (rho_liquid * v_liquid * d_m) / mu_liquid_pa_s

            if reynolds < 2300.0:
                flow_regime = "LAMINAR"
            elif reynolds < 4000.0:
                flow_regime = "TRANSITIONAL"
            else:
                flow_regime = "TURBULENT"

            # Hydrostatic pressure drop: Delta_P = rho * g * H
            # SOURCE: Fundamental hydrostatic equation dp = rho*g*dz
            delta_p_hydro_pa = rho_liquid * g * depth

            # Frictional pressure drop: Delta_P = f * (L / D) * (rho * v^2 / 2)
            # SOURCE: Darcy-Weisbach equation
            f_darcy = calculate_friction_factor_darcy(reynolds, rel_roughness)
            delta_p_fric_pa = f_darcy * (depth / d_m) * (rho_liquid * (v_liquid ** 2) / 2.0)

            # Acceleration pressure drop (negligible for incompressible liquid flow)
            delta_p_accel_pa = 0.0

            mixture_velocity = v_liquid
            liquid_holdup = 1.0
            flowing_density = rho_liquid

        # -------------------------------------------------------------------
        # BRANCH 2: Beggs & Brill-style multiphase correlation
        # (When gas or water phases are present)
        # -------------------------------------------------------------------
        else:
            model_type = "BEGGS_BRILL_MULTIPHASE_SIMPLIFIED"
            note = "Simplified Beggs & Brill (1973) multiphase correlation with vertical inclination correction and flow-regime map."

            # Approximate in-situ gas density at average wellbore conditions (~30 bar, 60 deg C)
            # Gas specific gravity 0.65 -> air density ~1.225 -> gas ~0.80 kg/m3 at standard conditions
            # At 30 bar: rho_gas ~ 30 * 0.80 * (288 / 333) ≈ 20.7 kg/m3
            avg_p_bar_est = 25.0
            rho_gas = max(1.5, 0.80 * self.fluid.gas_specific_gravity * (avg_p_bar_est / 1.013))
            mu_gas_pa_s = 0.015 * _CP_TO_PA_S  # Typical gas viscosity ~0.015 cP

            # Superficial velocities (m/s)
            v_sl = q_liquid_m3_s / flow_area_m2
            q_gas_m3_s = q_gas_mscfd * _MSCFD_TO_M3_S * (1.013 / max(1.0, avg_p_bar_est))
            v_sg = q_gas_m3_s / flow_area_m2

            v_m = v_sl + v_sg
            mixture_velocity = v_m

            # No-slip liquid holdup lambda_L
            # SOURCE: Beggs & Brill (1973), Eq. (1)
            lambda_l = max(0.001, min(0.999, v_sl / max(1e-6, v_m)))

            # Froude number N_Fr = v_m^2 / (g * D)
            # SOURCE: Beggs & Brill (1973), Eq. (2)
            n_fr = (v_m ** 2) / (g * d_m)

            # Beggs & Brill flow-regime transition criteria (horizontal/inclined)
            # SOURCE: Beggs & Brill (1973), Eqs. (4)-(7)
            l1 = 316.0 * (lambda_l ** 0.302)
            l2 = 0.0009252 * (lambda_l ** (-2.4684))
            l3 = 0.10 * (lambda_l ** (-1.4516))
            l4 = 0.50 * (lambda_l ** (-6.738))

            # Regime identification
            if n_fr < l1 or (lambda_l < 0.01 and n_fr < l2):
                flow_regime = "SEGREGATED"
                a_param, b_param, c_param = 0.98, 0.4846, 0.0868
            elif (0.01 <= lambda_l < 0.4 and l3 < n_fr <= l1) or (lambda_l >= 0.4 and l3 < n_fr <= l4):
                flow_regime = "INTERMITTENT (SLUG)"
                a_param, b_param, c_param = 0.845, 0.5351, 0.0173
            elif (lambda_l < 0.4 and n_fr >= l1) or (lambda_l >= 0.4 and n_fr > l4):
                flow_regime = "DISTRIBUTED (BUBBLE/MIST)"
                a_param, b_param, c_param = 1.065, 0.5824, 0.0609
            else:
                flow_regime = "TRANSITION"
                a_param, b_param, c_param = 0.90, 0.50, 0.05

            # Horizontal liquid holdup H_L(0)
            # SOURCE: Beggs & Brill (1973), Eq. (8)
            denom = max(1e-4, n_fr ** c_param)
            hl_0 = (a_param * (lambda_l ** b_param)) / denom
            hl_0 = max(lambda_l, min(1.0, hl_0))

            # Vertical upflow correction factor B (theta = 90 deg -> sin(1.8*theta) = sin(162 deg) ≈ 0.309)
            # SOURCE: Beggs & Brill (1973), Eqs. (9)-(11)
            sin_term = math.sin(math.radians(162.0))
            theta_poly = sin_term - 0.333 * (sin_term ** 3)
            # Damping correction factor C
            c_factor = (1.0 - lambda_l) * math.log(max(1e-4, 0.011 * (lambda_l ** -3.768) * (n_fr ** 1.614)))
            c_factor = max(0.0, min(1.0, c_factor))
            b_factor = 1.0 + c_factor * theta_poly

            liquid_holdup = max(lambda_l, min(1.0, hl_0 * b_factor))

            # Effective two-phase density and no-slip density
            # SOURCE: Beggs & Brill (1973), Eq. (12)
            rho_tp = rho_liquid * liquid_holdup + rho_gas * (1.0 - liquid_holdup)
            rho_noslip = rho_liquid * lambda_l + rho_gas * (1.0 - lambda_l)
            mu_tp = mu_liquid_pa_s * lambda_l + mu_gas_pa_s * (1.0 - lambda_l)

            flowing_density = rho_tp

            # Two-phase Reynolds number & friction factor
            reynolds = (rho_noslip * v_m * d_m) / mu_tp
            f_noslip = calculate_friction_factor_darcy(reynolds, rel_roughness)

            # Beggs & Brill two-phase friction multiplier: f_tp = f_ns * exp(S)
            # SOURCE: Beggs & Brill (1973), Eq. (13)
            y_ratio = max(0.01, lambda_l / (liquid_holdup ** 2))
            ln_y = math.log(y_ratio)
            s_poly = -0.0523 + 3.182 * ln_y - 0.8725 * (ln_y ** 2) + 0.01853 * (ln_y ** 4)
            s_exp = ln_y / max(0.1, s_poly) if abs(s_poly) > 0.01 else 0.0
            # Clamp multiplier to avoid mathematical divergence
            f_tp = f_noslip * math.exp(max(-2.0, min(2.5, s_exp)))

            # Hydrostatic & friction pressure drops (Pascals)
            delta_p_hydro_pa = rho_tp * g * depth
            delta_p_fric_pa = f_tp * (depth / d_m) * (rho_noslip * (v_m ** 2) / 2.0)

            # Acceleration pressure drop: dp_acc = rho_m * v_m * dv
            delta_p_accel_pa = rho_tp * (v_m ** 2) * (0.02)

        # Convert wellbore drops to bar
        delta_p_hydro_bar = delta_p_hydro_pa * _PA_TO_BAR
        delta_p_fric_bar = delta_p_fric_pa * _PA_TO_BAR
        delta_p_accel_bar = delta_p_accel_pa * _PA_TO_BAR
        delta_p_total_tubing_bar = delta_p_hydro_bar + delta_p_fric_bar + delta_p_accel_bar

        # Surface choke pressure drop
        # SOURCE: Sachdeva et al. (1986)
        total_rate_m3_s = q_liquid_m3_s + (q_gas_m3_s if has_gas else 0.0)
        delta_p_choke_bar = calculate_choke_pressure_drop_bar(
            flow_rate_m3_s=total_rate_m3_s,
            fluid_density_kg_m3=flowing_density,
            choke_opening_pct=choke_opening_pct,
            nominal_choke_id_in=self.geom.choke_nominal_id_in,
        )

        # Connect downhole and surface pressure boundary conditions
        # Fluid flows upward from pump intake to wellhead against hydrostatic and frictional head
        # Intake Pressure = Wellhead Pressure + Delta_P_total
        # Wellhead Pressure = Intake Pressure - Delta_P_total
        if wellhead_pressure_bar is not None:
            p_wh = max(1.013, float(wellhead_pressure_bar))
            p_intake = p_wh + delta_p_total_tubing_bar
        elif pump_intake_pressure_bar is not None:
            p_intake = float(pump_intake_pressure_bar)
            p_wh = max(1.013, p_intake - delta_p_total_tubing_bar)
        else:
            # Baseline operating default: typical wellhead separator line pressure = 5.0 bar
            p_wh = 5.0
            p_intake = p_wh + delta_p_total_tubing_bar

        p_downstream = max(1.013, p_wh - delta_p_choke_bar)

        components = PressureDropComponents(
            hydrostatic_bar=float(delta_p_hydro_bar),
            friction_bar=float(delta_p_fric_bar),
            acceleration_bar=float(delta_p_accel_bar),
            total_tubing_bar=float(delta_p_total_tubing_bar),
            choke_bar=float(delta_p_choke_bar),
        )

        return HydraulicsResult(
            pump_intake_pressure_bar=float(p_intake),
            wellhead_pressure_bar=float(p_wh),
            downstream_choke_pressure_bar=float(p_downstream),
            pressure_drop_components=components,
            choke_pressure_drop_bar=float(delta_p_choke_bar),
            flow_regime=flow_regime,
            reynolds_number=float(reynolds),
            mixture_velocity_m_s=float(mixture_velocity),
            liquid_holdup=float(liquid_holdup),
            model_type=model_type,
            simplification_note=note,
        )
