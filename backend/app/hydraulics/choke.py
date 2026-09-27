"""Choke performance and pressure drop modeling.

SOURCES:
  Sachdeva, R., Schmidt, Z., Brill, J.P., and Blais, R.M. (1986).
    "Two-Phase Flow Through Chokes", SPE-15657-MS.
  Perkins, T.K. (1993).
    "Critical and Subcritical Flow of Multiphase Mixtures Through Chokes",
    SPE Drilling & Completion, 8(4), pp. 271-276; SPE-20633-PA.
"""

import math


def calculate_choke_pressure_drop_bar(
    flow_rate_m3_s: float,
    fluid_density_kg_m3: float,
    choke_opening_pct: float,
    nominal_choke_id_in: float = 1.0,
    discharge_coefficient: float = 0.84,
) -> float:
    """Calculate pressure drop across a surface production choke orifice (in bar).

    SOURCE: Sachdeva et al. (1986) / Perkins (1993) subcritical orifice flow equation:
        Delta_P = (rho / (2 * Cd^2)) * (q / A_orifice)^2

    Parameters:
        flow_rate_m3_s: Total fluid volumetric flow rate (m^3/s).
        fluid_density_kg_m3: Flowing mixture density (kg/m^3).
        choke_opening_pct: Choke opening percentage in (0, 100].
        nominal_choke_id_in: Maximum choke bore diameter at 100% open (inches).
        discharge_coefficient: Empirical orifice discharge coefficient Cd (typically 0.80 - 0.88).

    Returns:
        Pressure drop across the choke in bar.
    """
    if choke_opening_pct <= 0.0 or choke_opening_pct > 100.0:
        raise ValueError(f"choke_opening_pct must be in (0, 100], got {choke_opening_pct}")
    if nominal_choke_id_in <= 0.0:
        raise ValueError(f"nominal_choke_id_in must be > 0, got {nominal_choke_id_in}")
    if fluid_density_kg_m3 <= 0.0:
        raise ValueError(f"fluid_density_kg_m3 must be > 0, got {fluid_density_kg_m3}")
    if flow_rate_m3_s < 0.0:
        raise ValueError(f"flow_rate_m3_s must be >= 0, got {flow_rate_m3_s}")

    if flow_rate_m3_s == 0.0:
        return 0.0

    # Full orifice area
    nominal_d_m = nominal_choke_id_in * 0.0254
    full_area_m2 = (math.pi / 4.0) * (nominal_d_m ** 2)

    # Effective orifice area based on percentage opening
    # Choke bean area varies proportionally with opening fraction
    open_frac = max(0.005, choke_opening_pct / 100.0)
    effective_area_m2 = full_area_m2 * open_frac

    # Constricted throat velocity (m/s)
    throat_velocity_m_s = flow_rate_m3_s / effective_area_m2

    # Orifice pressure drop in Pascals
    # SOURCE: Sachdeva (1986), Eq. (1) subcritical orifice relation
    delta_p_pa = (fluid_density_kg_m3 / (2.0 * (discharge_coefficient ** 2))) * (throat_velocity_m_s ** 2)

    # 1 Pa = 1e-5 bar
    delta_p_bar = delta_p_pa * 1.0e-5
    return float(max(0.0, delta_p_bar))
