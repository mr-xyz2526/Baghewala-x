"""Gibbs 1D Damped Wave Equation Finite-Difference Solver.

SOURCE:
  Gibbs, S.G. (1963). "Predicting the Behavior of Sucker-Rod Pumping Systems."
    Journal of Petroleum Technology, 15(7), pp. 769-778. SPE-588-PA.
  Gibbs, S.G. and Neely, A.B. (1966). "Computer Diagnosis of Down-Hole Conditions
    in Sucker Rod Pumping Wells." Journal of Petroleum Technology, 18(1), pp. 91-98.
"""

from typing import List, Tuple, Dict, Any, Optional
import math
import numpy as np

from .models import RodStringParams, PumpParams, OperatingState, CardClass


def calculate_net_fluid_load_n(
    rod_params: RodStringParams,
    pump_params: PumpParams,
    fluid_level_m: Optional[float] = None,
) -> float:
    """Calculate net fluid load on the pump plunger (N).

    SOURCE: Gibbs (1963), Eq. (2):
        F_fluid = gamma_f * D * A_p
    """
    g = 9.80665
    rho_f = pump_params.tubing_fluid_density_kg_m3
    d_m = fluid_level_m if fluid_level_m is not None else rod_params.length_m
    f_fluid_n = rho_f * g * d_m * pump_params.plunger_area_m2
    return float(max(1000.0, f_fluid_n))


class GibbsWaveSolver:
    """Solves the one-dimensional damped wave equation for a sucker rod string.

    Governing Equation:
        d^2 u / dt^2 = a^2 * d^2 u / dx^2 - c * du / dt
    SOURCE: Gibbs (1963), Eq. (1)
    """

    def __init__(
        self,
        rod_params: RodStringParams,
        pump_params: PumpParams,
        num_spatial_nodes: int = 41,  # Configurable spatial discretization
        cfl_target: float = 0.90,     # CFL stability number (must be <= 1.0)
    ):
        self.rod = rod_params
        self.pump = pump_params
        self.nx = max(11, num_spatial_nodes)
        self.cfl_target = min(0.95, max(0.50, cfl_target))

    def compute_pump_load(
        self,
        plunger_pos_norm: float,
        plunger_vel_m_s: float,
        fluid_load_n: float,
        card_class: CardClass,
        fillage_frac: float,
        prev_load_n: float = 0.0,
    ) -> float:
        """Evaluate downhole pump boundary resistance F_pump(u, v) based on card class and valve states.

        Returns load in Newtons (tension applied to rod at pump boundary).
        """
        f_o = fluid_load_n
        s = max(0.0, min(1.0, plunger_pos_norm))
        is_upstroke = (plunger_vel_m_s >= 0.0)

        # Baseline friction on plunger
        friction_n = self.pump.plunger_friction_n * (1.0 if is_upstroke else -1.0)

        if card_class == CardClass.NORMAL:
            # Traveling valve closes immediately at bottom stroke, holds load through upstroke;
            # opens at top stroke, load transfers to zero through downstroke.
            # Small transition smoothing prevents artificial shock singularity.
            if is_upstroke:
                # Load pick-up at bottom of stroke
                load = f_o * (1.0 - math.exp(-s * 25.0))
            else:
                # Load release at top of stroke
                load = f_o * math.exp(-(1.0 - s) * 25.0)

        elif card_class == CardClass.FLUID_POUND:
            # Liquid fillage is partial (e.g. 40-70%). On downstroke, traveling valve stays closed
            # while passing through vapor void, until plunger impacts liquid surface at s_impact = fillage.
            if is_upstroke:
                load = f_o * (1.0 - math.exp(-s * 20.0))
            else:
                # Downstroke:
                impact_s = max(0.05, min(0.95, fillage_frac))
                if s > impact_s:
                    # Still in void: traveling valve has not opened, carrying remaining fluid column
                    load = f_o * 0.90
                else:
                    # Plunger has impacted liquid: sharp drop with impact reaction
                    load = f_o * 0.05 * math.exp(-((impact_s - s) * 10.0))

        elif card_class == CardClass.GAS_INTERFERENCE:
            # Free gas in chamber: on downstroke, traveling valve cannot open until gas is compressed.
            # Load decays gradually following polytropic curve (s^1.4).
            if is_upstroke:
                load = f_o * (1.0 - math.exp(-s * 15.0))
            else:
                # Delayed valve opening due to gas cushion
                load = f_o * (s ** 1.35)

        elif card_class == CardClass.TRAVELING_VALVE_LEAK:
            # Traveling valve leaks: fluid slips through on upstroke, causing load to decay with stroke.
            if is_upstroke:
                leak_factor = 0.50
                load = f_o * (1.0 - leak_factor * s)
            else:
                load = f_o * math.exp(-(1.0 - s) * 20.0)

        elif card_class == CardClass.PUMP_OFF:
            # Severe underfill (< 20%): minimal liquid intake, card loop collapses.
            if is_upstroke:
                load = f_o * 0.25 * (1.0 - math.exp(-s * 10.0))
            else:
                load = f_o * 0.05 * math.exp(-(1.0 - s) * 10.0)

        else:
            load = f_o if is_upstroke else 0.0

        total_load = max(0.0, load + friction_n)
        return float(total_load)

    def solve(
        self,
        operating_state: OperatingState,
        cycles_to_run: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """Integrate Gibbs damped wave equation and extract steady-state dynamometer card.

        Returns:
            Dict with surface & downhole stroke/load points, or None if instability detected.
        """
        # Physical constants & grid setup
        l_rod = self.rod.length_m
        a = self.rod.acoustic_velocity_m_s
        c = self.rod.damping_factor_s_inv
        ea = self.rod.elastic_modulus_pa * self.rod.area_m2
        w_rod_air = self.rod.total_weight_in_air_n

        # Buoyant rod weight
        rho_fluid = self.pump.tubing_fluid_density_kg_m3
        v_rod = self.rod.area_m2 * l_rod
        f_buoyant = rho_fluid * 9.80665 * v_rod
        w_rod_fluid = max(100.0, w_rod_air - f_buoyant)

        # Spatial discretization
        dx = l_rod / (self.nx - 1)

        # Time discretization (CFL condition)
        # SOURCE: Courant-Friedrichs-Lewy stability criterion for hyperbolic wave equation
        omega = 2.0 * math.pi * (operating_state.spm / 60.0)
        t_period = 60.0 / max(0.5, operating_state.spm)

        dt_cfl = (self.cfl_target * dx) / a
        steps_per_period = max(80, int(math.ceil(t_period / dt_cfl)))
        dt = t_period / steps_per_period
        courant = (a * dt) / dx

        if courant > 1.0:
            # CFL violation - cannot be numerically stable
            return None

        gamma = (c * dt) / 2.0
        denom = 1.0 + gamma
        c_sq = courant ** 2

        stroke_m = operating_state.surface_stroke_in * 0.0254

        # Net fluid load
        if operating_state.net_fluid_load_n is not None:
            f_fluid = operating_state.net_fluid_load_n
        else:
            f_fluid = calculate_net_fluid_load_n(
                self.rod, self.pump, operating_state.fluid_level_m
            )

        # Total simulation time steps across cycles
        total_steps = steps_per_period * max(2, cycles_to_run)

        # Displacement state arrays: u_prev (t - dt), u_curr (t), u_next (t + dt)
        u_prev = np.zeros(self.nx, dtype=np.float64)
        u_curr = np.zeros(self.nx, dtype=np.float64)
        u_next = np.zeros(self.nx, dtype=np.float64)

        # Static stretch initialization along depth
        # At surface, rod supports rod weight + fluid load; at bottom, plunger supports fluid load
        stretch_slope = (f_fluid + w_rod_fluid) / ea
        for j in range(self.nx):
            u_prev[j] = stretch_slope * (j * dx)
            u_curr[j] = u_prev[j]

        # Recording arrays for the final periodic cycle
        final_start_step = total_steps - steps_per_period
        surface_disp: List[float] = []
        surface_load_lbf: List[float] = []
        downhole_disp: List[float] = []
        downhole_load_lbf: List[float] = []

        plunger_stroke_est = stroke_m * 0.85
        fillage_frac = max(0.05, min(1.0, operating_state.pump_fillage_pct / 100.0))
        last_down_load_n = 0.0

        # Time integration loop
        for step in range(total_steps):
            t = step * dt

            # Surface motion input: u(0, t) = S/2 * (1 - cos(omega * t))
            # SOURCE: API Specification 11E kinematic surface stroke input
            u_next[0] = (stroke_m / 2.0) * (1.0 - math.cos(omega * (t + dt)))

            # Interior nodes finite-difference wave equation update
            # SOURCE: Gibbs (1963), Eq. (1) discrete central difference
            u_next[1:-1] = (
                2.0 * u_curr[1:-1]
                - (1.0 - gamma) * u_prev[1:-1]
                + c_sq * (u_curr[2:] - 2.0 * u_curr[1:-1] + u_curr[:-2])
            ) / denom

            # Downhole plunger velocity and normalized position estimate
            v_down = (u_curr[-1] - u_prev[-1]) / dt
            plunger_pos_norm = max(0.0, min(1.0, u_curr[-1] / max(plunger_stroke_est, 0.01)))

            # Evaluate pump boundary load F_pump
            f_pump_n = self.compute_pump_load(
                plunger_pos_norm=plunger_pos_norm,
                plunger_vel_m_s=v_down,
                fluid_load_n=f_fluid,
                card_class=operating_state.card_class,
                fillage_frac=fillage_frac,
                prev_load_n=last_down_load_n,
            )
            last_down_load_n = f_pump_n

            # Downhole boundary update using ghost-node formulation
            # SOURCE: Gibbs (1963), downhole force boundary condition E*A * du/dx(L) = -F_pump
            u_next[-1] = (
                2.0 * u_curr[-1]
                - (1.0 - gamma) * u_prev[-1]
                + 2.0 * c_sq * (u_curr[-2] - u_curr[-1])
                - (2.0 * c_sq * dx / ea) * f_pump_n
            ) / denom

            # Check numerical stability (divergence / NaN guard)
            if not np.all(np.isfinite(u_next)) or np.max(np.abs(u_next)) > (stroke_m * 10.0 + 10.0):
                # Unstable! Trigger analytical fallback
                return None

            # Record final steady-state cycle
            if step >= final_start_step:
                # Surface dynamic load: W_rod + E*A * (u_1 - u_0)/dx
                # Inward tension convention: dynamic tension pulls down on surface
                dynamic_strain = (u_curr[1] - u_curr[0]) / dx
                # Dynamic load in N
                f_surf_n = w_rod_fluid + ea * dynamic_strain
                # Add surface mechanical stuffing-box friction
                surf_vel = (u_curr[0] - u_prev[0]) / dt
                f_surf_n += 200.0 * math.tanh(surf_vel * 5.0)

                # Convert to inches and lbf
                pos_in = u_curr[0] / 0.0254
                load_lbf = f_surf_n / 4.44822

                pos_down_in = u_curr[-1] / 0.0254
                down_lbf = f_pump_n / 4.44822

                surface_disp.append(pos_in)
                surface_load_lbf.append(load_lbf)
                downhole_disp.append(pos_down_in)
                downhole_load_lbf.append(down_lbf)

            # Shift time levels
            u_prev[:] = u_curr
            u_curr[:] = u_next

        # Ensure non-empty
        if not surface_disp:
            return None

        # Assemble closed card points: append first point to end if loop not perfectly closed
        surface_points = list(zip(surface_disp, surface_load_lbf))
        downhole_points = list(zip(downhole_disp, downhole_load_lbf))

        if surface_points:
            surface_points.append(surface_points[0])
        if downhole_points:
            downhole_points.append(downhole_points[0])

        return {
            "surface_points": surface_points,
            "downhole_points": downhole_points,
            "solver_mode": "NUMERICAL_WAVE",
        }
