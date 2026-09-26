"""Boberg-Lantz post-injection temperature decay and productivity model.

SOURCE: Boberg, T.C. and Lantz, R.B. (1966),
"Calculation of the Production Rate of a Chronically Stimulated Well",
Journal of Petroleum Technology, 18(12), 1613-1623, SPE-1578-PA.

SOURCE: Hawkins, M.F. (1956),
"A Note on the Skin Effect",
Transactions of the AIME, 207, 356-357.
"""

from dataclasses import dataclass, field
import math
from typing import List, Dict, Any, Optional
import numpy as np

from .viscosity import ViscosityModel, ViscosityConfig


@dataclass
class BobergLantzConfig:
    """Reservoir, fluid, and geometric parameters for post-injection modeling."""
    pay_thickness_m: float = 15.0               # Formation thickness h (m)
    m_reservoir_j_per_m3_k: float = 2.3e6       # Reservoir volumetric heat capacity (J/(m^3*K))
    m_overburden_j_per_m3_k: float = 2.1e6      # Overburden volumetric heat capacity (J/(m^3*K))
    k_overburden_w_per_m_k: float = 1.8         # Overburden thermal conductivity (W/(m*K))
    k_reservoir_w_per_m_k: float = 2.0          # Reservoir thermal conductivity (W/(m*K))
    base_reservoir_temp_c: float = 50.0         # Initial cold reservoir temperature T_R (deg C)
    wellbore_radius_m: float = 0.1              # Wellbore radius r_w (m)
    drainage_radius_m: float = 150.0            # Reservoir drainage radius r_e (m)
    skin_factor: float = 0.0                    # Mechanical skin s (dimensionless)
    oil_density_kg_m3: float = 980.0            # Extra-heavy oil density (kg/m^3)
    water_density_kg_m3: float = 1000.0         # Formation water density (kg/m^3)
    oil_heat_capacity_j_kg_k: float = 2000.0    # Oil specific heat capacity c_o (J/(kg*K))
    water_heat_capacity_j_kg_k: float = 4186.0  # Water specific heat capacity c_w (J/(kg*K))


@dataclass
class ProductivityParams:
    """Inflow and drawdown operational parameters for production."""
    base_drawdown_bar: float = 20.0             # Operating drawdown (p_R - p_wf) (bar)
    base_productivity_index_bopd_per_bar: float = 1.0  # Cold oil PI: J_c (bopd/bar)
    water_cut_pct: float = 30.0                 # Water cut (percentage 0-100)
    max_oil_rate_bopd: float = 1500.0           # Physical/facility pump capacity limit


@dataclass
class ProductionDayRecord:
    """Time-step record during CSS production phase."""
    day: int
    reservoir_temperature_c: float
    viscosity_cp: float
    estimated_inflow_pi: float
    oil_rate_bopd: float
    cumulative_oil_bbl: float


class BobergLantzModel:
    """Calculates post-injection thermal cooling and composite radial inflow."""

    def __init__(
        self,
        config: BobergLantzConfig = None,
        viscosity_model: ViscosityModel = None,
    ):
        self.config = config or BobergLantzConfig()
        self.viscosity_model = viscosity_model or ViscosityModel(
            ViscosityConfig(t_ref_c=self.config.base_reservoir_temp_c)
        )

        # Thermal diffusivities
        # Overburden: alpha_ob = k_ob / M_ob (m^2/s)
        self.alpha_ob = self.config.k_overburden_w_per_m_k / self.config.m_overburden_j_per_m3_k
        # Reservoir: alpha_r = k_r / M_r (m^2/s)
        self.alpha_r = self.config.k_reservoir_w_per_m_k / self.config.m_reservoir_j_per_m3_k

    def vertical_conduction_factor(self, delta_t_sec: float) -> float:
        """Calculate vertical conductive cooling factor V_z for slab of thickness h.

        SOURCE: Boberg, T.C. and Lantz, R.B. (1966), Eq. 5 / Appendix.
        Equation:
            tau_z = (alpha_ob * delta_t) / h^2
            V_z = erf(1 / (2 * sqrt(tau_z))) - 2 * sqrt(tau_z / pi) * (1 - exp(-1 / (4 * tau_z)))
        """
        if delta_t_sec <= 0:
            return 1.0

        h = self.config.pay_thickness_m
        tau_z = (self.alpha_ob * delta_t_sec) / (h ** 2)

        if tau_z < 1e-12:
            return 1.0

        sqrt_tau = math.sqrt(tau_z)
        inv_2sqrt = 1.0 / (2.0 * sqrt_tau)

        # SOURCE: Boberg and Lantz (1966), Eq. 5
        v_z = math.erf(inv_2sqrt) - 2.0 * (sqrt_tau / math.sqrt(math.pi)) * (1.0 - math.exp(-inv_2sqrt ** 2))
        return float(min(1.0, max(0.0, v_z)))

    def radial_conduction_factor(self, delta_t_sec: float, heated_radius_m: float) -> float:
        """Calculate radial conductive cooling factor V_r from cylinder of radius r_h.

        SOURCE: Boberg, T.C. and Lantz, R.B. (1966), Eq. 6.
        Equation:
            tau_r = (alpha_r * delta_t) / r_h^2
            V_r = 1 / (1 + 2 * sqrt(tau_r / pi))
        """
        if delta_t_sec <= 0 or heated_radius_m <= 0:
            return 1.0

        tau_r = (self.alpha_r * delta_t_sec) / (heated_radius_m ** 2)
        # SOURCE: Boberg and Lantz (1966), Eq. 6
        v_r = 1.0 / (1.0 + 2.0 * math.sqrt(tau_r / math.pi))
        return float(min(1.0, max(0.0, v_r)))

    def calculate_stimulation_ratio(
        self,
        heated_radius_m: float,
        viscosity_heated_cp: float,
        viscosity_cold_cp: float,
    ) -> float:
        """Calculate Boberg-Lantz stimulation ratio (J_stimulated / J_cold).

        SOURCE: Boberg, T.C. and Lantz, R.B. (1966), Eq. 1:
        SOURCE: Hawkins, M.F. (1956), Eq. 4: Composite radial flow skin formulation.
        Equation:
            J / J_c = [ln(r_e / r_w) + s] / [ (mu_h / mu_c) * ln(r_h / r_w) + ln(r_e / r_h) + s * (mu_h / mu_c) ]
        """
        r_w = self.config.wellbore_radius_m
        r_e = self.config.drainage_radius_m
        s = self.config.skin_factor

        r_h = max(heated_radius_m, r_w * 1.01)
        r_h = min(r_h, r_e * 0.99)

        mu_ratio = max(1e-5, viscosity_heated_cp / max(1e-5, viscosity_cold_cp))

        # Numerator: cold well inflow resistance scale
        # SOURCE: Boberg and Lantz (1966), Eq. 1
        numerator = math.log(r_e / r_w) + s

        # Denominator: heated inner zone + cold outer zone + heated skin
        denominator = (mu_ratio * math.log(r_h / r_w)) + math.log(r_e / r_h) + (s * mu_ratio)

        if denominator <= 0:
            return 1.0

        return max(1.0, numerator / denominator)

    def simulate_soak(
        self,
        soak_days: int,
        steam_temp_c: float,
        heated_radius_m: float,
    ) -> Dict[str, Any]:
        """Simulate temperature decay during shut-in soak period (conduction only).

        Returns:
            Dict with 'temperature_time_series' and 'end_soak_temperature'.
        """
        if soak_days < 0:
            raise ValueError(f"Soak days must be non-negative, got {soak_days}")

        t_r = self.config.base_reservoir_temp_c
        delta_t_initial = steam_temp_c - t_r

        temps: List[float] = []

        if soak_days == 0:
            return {
                "temperature_time_series": [steam_temp_c],
                "end_soak_temperature": steam_temp_c,
            }

        for day in range(1, soak_days + 1):
            t_sec = day * 86400.0
            v_z = self.vertical_conduction_factor(t_sec)
            v_r = self.radial_conduction_factor(t_sec, heated_radius_m)

            # SOURCE: Boberg and Lantz (1966), Eq. 4: No fluid production during soak
            theta = v_z * v_r
            t_day = t_r + delta_t_initial * theta
            temps.append(float(t_day))

        return {
            "temperature_time_series": temps,
            "end_soak_temperature": temps[-1],
        }

    def simulate_production(
        self,
        production_days: int,
        start_temp_c: float,
        steam_temp_c: float,
        heated_radius_m: float,
        soak_days: int = 0,
        prod_params: Optional[ProductivityParams] = None,
    ) -> List[ProductionDayRecord]:
        """Simulate daily CSS production with conductive + convective cooling.

        Returns:
            List of ProductionDayRecord entries for each day.
        """
        if production_days < 0:
            raise ValueError(f"Production days must be non-negative, got {production_days}")

        params = prod_params or ProductivityParams()
        t_r = self.config.base_reservoir_temp_c
        mu_cold = self.viscosity_model.calculate_viscosity(t_r)

        # Thermal capacity of the heated zone C_h (J/K)
        # C_h = pi * r_h^2 * h * M_R
        vol_heated_m3 = math.pi * (max(heated_radius_m, 1.0) ** 2) * self.config.pay_thickness_m
        c_heated_j_per_k = vol_heated_m3 * self.config.m_reservoir_j_per_m3_k

        # Conversion factor: 1 bbl = 0.1589873 m^3
        bbl_to_m3 = 0.1589873

        # Convective cooling accumulator
        log_conv_decay = 0.0

        records: List[ProductionDayRecord] = []
        cum_oil = 0.0
        current_temp = start_temp_c

        for d in range(1, production_days + 1):
            # Elapsed time since end of injection includes soak and production days
            total_elapsed_days = soak_days + d
            delta_t_sec = total_elapsed_days * 86400.0

            # Conductive factors
            v_z = self.vertical_conduction_factor(delta_t_sec)
            v_r = self.radial_conduction_factor(delta_t_sec, heated_radius_m)

            # Combined dimensionless temperature rise
            # SOURCE: Boberg and Lantz (1966), Eq. 7-8: Conductive cooling + convective cooling
            f_conv = math.exp(-log_conv_decay)
            theta = v_z * v_r * f_conv
            theta = max(0.0, min(1.0, theta))

            current_temp = t_r + (steam_temp_c - t_r) * theta

            # Viscosity at current heated temperature
            mu_heated = self.viscosity_model.calculate_viscosity(current_temp)

            # Stimulation ratio
            stim_ratio = self.calculate_stimulation_ratio(
                heated_radius_m=heated_radius_m,
                viscosity_heated_cp=mu_heated,
                viscosity_cold_cp=mu_cold,
            )

            # Productive capacity
            pi_effective = params.base_productivity_index_bopd_per_bar * stim_ratio
            oil_rate = pi_effective * params.base_drawdown_bar
            oil_rate = min(oil_rate, params.max_oil_rate_bopd)
            oil_rate = max(0.0, oil_rate)

            cum_oil += oil_rate

            # Convective heat loss to update log_conv_decay for subsequent days
            # Water rate associated with oil rate
            wcut_frac = min(0.99, max(0.0, params.water_cut_pct / 100.0))
            if wcut_frac < 0.99:
                water_rate_bwpd = oil_rate * (wcut_frac / (1.0 - wcut_frac))
            else:
                water_rate_bwpd = oil_rate * 99.0

            # Daily fluid mass (kg/day)
            daily_m_oil = oil_rate * bbl_to_m3 * self.config.oil_density_kg_m3
            daily_m_water = water_rate_bwpd * bbl_to_m3 * self.config.water_density_kg_m3

            daily_fluid_heat_capacity = (
                daily_m_oil * self.config.oil_heat_capacity_j_kg_k +
                daily_m_water * self.config.water_heat_capacity_j_kg_k
            )

            # SOURCE: Boberg and Lantz (1966), Eq. 8: Daily convective enthalpy removal
            if c_heated_j_per_k > 0:
                step_conv_fraction = daily_fluid_heat_capacity / c_heated_j_per_k
                log_conv_decay += step_conv_fraction

            records.append(
                ProductionDayRecord(
                    day=d,
                    reservoir_temperature_c=float(current_temp),
                    viscosity_cp=float(mu_heated),
                    estimated_inflow_pi=float(pi_effective),
                    oil_rate_bopd=float(oil_rate),
                    cumulative_oil_bbl=float(cum_oil),
                )
            )

        return records
