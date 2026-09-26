"""Marx-Langenheim heated-zone / thermal-balance model for steam injection.

SOURCE: Marx, J.W. and Langenheim, R.H. (1961),
"Reservoir Heating by Hot Fluid Injection",
Transactions of the AIME, 222, 312-320.
"""

from dataclasses import dataclass
import math
import numpy as np
from scipy.special import erfcx


@dataclass
class MarxLangenheimConfig:
    """Reservoir and overburden thermal properties for steam injection.

    All units are SI (m, kg, s, J, W, K) unless otherwise specified.
    Representative literature values for sandstone / heavy oil reservoirs.
    """
    pay_thickness_m: float = 15.0               # Net pay thickness h (m)
    m_reservoir_j_per_m3_k: float = 2.3e6       # Reservoir volumetric heat capacity M_R = (rho*C)_R (J/(m^3*K))
    m_overburden_j_per_m3_k: float = 2.1e6      # Overburden volumetric heat capacity M_ob (J/(m^3*K))
    k_overburden_w_per_m_k: float = 1.8         # Overburden thermal conductivity k_ob (W/(m*K))
    base_reservoir_temp_c: float = 50.0         # Initial reservoir temperature T_R (deg C)
    water_heat_capacity_j_per_kg_k: float = 4186.0  # Specific heat capacity of liquid water c_w (J/(kg*K))


@dataclass
class InjectionResult:
    """Output metrics from steam injection phase."""
    heated_radius_m: float
    heated_area_m2: float
    total_heat_mj: float
    thermal_efficiency_indicator: float


class MarxLangenheimModel:
    """Analytical thermal-balance model for constant-rate steam injection."""

    def __init__(self, config: MarxLangenheimConfig = None):
        self.config = config or MarxLangenheimConfig()
        if self.config.pay_thickness_m <= 0:
            raise ValueError(f"Pay thickness must be > 0, got {self.config.pay_thickness_m}")
        if self.config.m_reservoir_j_per_m3_k <= 0:
            raise ValueError(f"Reservoir volumetric heat capacity must be > 0, got {self.config.m_reservoir_j_per_m3_k}")
        if self.config.k_overburden_w_per_m_k <= 0:
            raise ValueError(f"Overburden thermal conductivity must be > 0, got {self.config.k_overburden_w_per_m_k}")

    @staticmethod
    def latent_heat_of_vaporization(steam_temp_c: float) -> float:
        """Estimate latent heat of vaporization of saturated water/steam L_v (J/kg).

        Correlated from standard steam tables for 100 to 350 deg C:
            L_v(T) = 1000 * (2500.8 - 2.36 * T)  [J/kg]
        SOURCE: Prats, M. (1982), 'Thermal Recovery', SPE Monograph Vol. 7, Appendix A.
        """
        if steam_temp_c < 100.0 or steam_temp_c > 370.0:
            # Allow reasonable extrapolation, but protect physics
            pass
        # SOURCE: Empirical correlation for saturated water latent heat (Prats 1982)
        lv = 1000.0 * (2500.8 - 2.36 * steam_temp_c)
        return max(lv, 1.0e5)

    def calculate_injection(
        self,
        steam_rate_tpd: float,
        steam_temp_c: float,
        injection_days: float,
        steam_quality: float,
    ) -> InjectionResult:
        """Calculate heated area, radius, heat injected, and thermal efficiency.

        Parameters:
            steam_rate_tpd: Steam injection rate (tonnes per day, CWE). Must be > 0.
            steam_temp_c: Steam temperature at sandface (deg C). Must be > base_reservoir_temp_c.
            injection_days: Duration of injection (days). Must be > 0.
            steam_quality: Vapour mass fraction (0.0 to 1.0).

        Returns:
            InjectionResult containing heated_radius_m, heated_area_m2, total_heat_mj,
            and thermal_efficiency_indicator.
        """
        if steam_rate_tpd <= 0:
            raise ValueError(f"Steam injection rate must be strictly positive, got {steam_rate_tpd}")
        if injection_days <= 0:
            raise ValueError(f"Injection duration must be strictly positive, got {injection_days}")
        if steam_quality < 0.0 or steam_quality > 1.0:
            raise ValueError(f"Steam quality must be in range [0, 1], got {steam_quality}")
        if steam_temp_c <= self.config.base_reservoir_temp_c:
            raise ValueError(
                f"Steam temperature ({steam_temp_c} C) must exceed reservoir temperature "
                f"({self.config.base_reservoir_temp_c} C)"
            )

        # Mass injection rate in kg/s
        # 1 tonne = 1000 kg, 1 day = 86400 s
        m_dot = (steam_rate_tpd * 1000.0) / 86400.0  # kg/s

        # Specific enthalpy of injected steam relative to base reservoir temperature T_R
        delta_t = steam_temp_c - self.config.base_reservoir_temp_c
        c_w = self.config.water_heat_capacity_j_per_kg_k
        l_v = self.latent_heat_of_vaporization(steam_temp_c)

        # SOURCE: Marx and Langenheim (1961), Eq. 1: Injected fluid specific heat enthalpy
        h_inj = c_w * delta_t + steam_quality * l_v  # J/kg

        # Heat injection rate H_0 in Watts (J/s)
        h_0 = m_dot * h_inj  # W

        # Injection time in seconds
        t_sec = injection_days * 86400.0  # s

        # Total heat injected in Joules and MegaJoules
        total_heat_j = h_0 * t_sec
        total_heat_mj = total_heat_j / 1.0e6

        # Overburden thermal diffusivity alpha_ob = k_ob / M_ob (m^2/s)
        alpha_ob = self.config.k_overburden_w_per_m_k / self.config.m_overburden_j_per_m3_k

        # Dimensionless time t_D:
        # SOURCE: Marx and Langenheim (1961), Eq. 5
        # t_D = (4 * k_ob * M_ob * t) / (M_R^2 * h^2)
        h_pay = self.config.pay_thickness_m
        m_r = self.config.m_reservoir_j_per_m3_k
        k_ob = self.config.k_overburden_w_per_m_k
        m_ob = self.config.m_overburden_j_per_m3_k

        t_d = (4.0 * k_ob * m_ob * t_sec) / ((m_r ** 2) * (h_pay ** 2))

        # Auxiliary function F_1(t_D):
        # SOURCE: Marx and Langenheim (1961), Eq. 6:
        # F_1(t_D) = exp(t_D) * erfc(sqrt(t_D)) + 2 * sqrt(t_D / pi) - 1
        # Using erfcx(x) = exp(x^2) * erfc(x) for complete numerical stability:
        sqrt_td = math.sqrt(t_d)
        f_1 = float(erfcx(sqrt_td) + 2.0 * (sqrt_td / math.sqrt(math.pi)) - 1.0)

        # Heated area A(t) in m^2:
        # SOURCE: Marx and Langenheim (1961), Eq. 7
        # A(t) = [H_0 * M_R * h / (4 * k_ob * M_ob * (T_st - T_R))] * F_1(t_D)
        area_scale = (h_0 * m_r * h_pay) / (4.0 * k_ob * m_ob * delta_t)
        heated_area_m2 = max(0.0, area_scale * f_1)

        # Heated radius r_h assuming radial cylindrical expansion:
        heated_radius_m = math.sqrt(heated_area_m2 / math.pi)

        # Thermal efficiency E_hs(t):
        # SOURCE: Marx and Langenheim (1961), Eq. 8:
        # E_hs = F_1(t_D) / t_D
        if t_d > 1e-12:
            thermal_efficiency = min(1.0, max(0.0, f_1 / t_d))
        else:
            thermal_efficiency = 1.0

        return InjectionResult(
            heated_radius_m=heated_radius_m,
            heated_area_m2=heated_area_m2,
            total_heat_mj=total_heat_mj,
            thermal_efficiency_indicator=thermal_efficiency,
        )
