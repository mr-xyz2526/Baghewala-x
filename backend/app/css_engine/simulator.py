"""Cyclic Steam Stimulation (CSS) Cycle Simulator.

Combines:
Layer A: Marx-Langenheim (1961) thermal-balance injection model.
Layer B: Boberg-Lantz (1966) / Hawkins (1956) post-injection soak and production model.
Viscosity: Temperature-dependent Andrade/Arrhenius model with explicit sensitivity.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
import numpy as np

from .viscosity import ViscosityModel, ViscosityConfig
from .marx_langenheim import (
    MarxLangenheimModel,
    MarxLangenheimConfig,
    InjectionResult,
)
from .boberg_lantz import (
    BobergLantzModel,
    BobergLantzConfig,
    ProductivityParams,
    ProductionDayRecord,
)


@dataclass
class CSSCycleParams:
    """Input parameters for a complete CSS cycle."""
    steam_rate_tpd: float = 800.0           # Steam injection rate (t/d CWE)
    steam_temp_c: float = 260.0             # Steam temperature (deg C)
    injection_days: int = 20                # Injection duration (days)
    steam_quality: float = 0.8              # Steam quality fraction (0 to 1)
    soak_days: int = 5                      # Soak duration (days)
    production_days: int = 90               # Production duration (days)
    productivity_params: Optional[ProductivityParams] = None


@dataclass
class CycleTimelineRecord:
    """Daily record across the entire CSS cycle."""
    day: int
    phase: str                              # "INJECTION" | "SOAKING" | "PRODUCTION"
    temperature_c: float
    viscosity_cp: float
    oil_rate_bopd: float
    cumulative_oil_bbl: float
    steam_rate_tpd: float
    cumulative_steam_t: float


@dataclass
class CycleResult:
    """Comprehensive result of running a full CSS cycle."""
    full_cycle_timeline: List[CycleTimelineRecord]
    cycle_oil: float                        # Cumulative oil produced (bbl)
    cycle_steam: float                      # Cumulative steam injected (tonnes)
    SOR: float                              # Steam-to-oil ratio (t steam / bbl oil)
    sor_cwe_bbl_per_bbl: float              # Volumetric SOR (bbl CWE steam / bbl oil)
    temperature_history: List[float]
    viscosity_history: List[float]
    phase_boundaries: Dict[str, Any]
    injection_summary: InjectionResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_cycle_timeline": [asdict(r) for r in self.full_cycle_timeline],
            "cycle_oil": self.cycle_oil,
            "cycle_steam": self.cycle_steam,
            "SOR": self.SOR,
            "sor_cwe_bbl_per_bbl": self.sor_cwe_bbl_per_bbl,
            "temperature_history": self.temperature_history,
            "viscosity_history": self.viscosity_history,
            "phase_boundaries": self.phase_boundaries,
            "injection_summary": asdict(self.injection_summary),
        }


class CSSCycleSimulator:
    """Simulator for Cyclic Steam Stimulation cycles using analytical physics layers.

    Architecture:
    - Layer A (Marx-Langenheim 1961): heated zone area, heated radius, heat balance.
    - Layer B (Boberg-Lantz 1966): post-injection vertical and radial conduction +
      convective fluid cooling + Hawkins (1956) composite radial inflow.
    - Viscosity (Andrade 1930 / Butler 1991): explicit sensitivity factor.
    """

    def __init__(
        self,
        ml_config: Optional[MarxLangenheimConfig] = None,
        bl_config: Optional[BobergLantzConfig] = None,
        viscosity_config: Optional[ViscosityConfig] = None,
    ):
        self.ml_config = ml_config or MarxLangenheimConfig()
        self.bl_config = bl_config or BobergLantzConfig(
            pay_thickness_m=self.ml_config.pay_thickness_m,
            m_reservoir_j_per_m3_k=self.ml_config.m_reservoir_j_per_m3_k,
            m_overburden_j_per_m3_k=self.ml_config.m_overburden_j_per_m3_k,
            k_overburden_w_per_m_k=self.ml_config.k_overburden_w_per_m_k,
            base_reservoir_temp_c=self.ml_config.base_reservoir_temp_c,
        )
        self.viscosity_config = viscosity_config or ViscosityConfig(
            t_ref_c=self.ml_config.base_reservoir_temp_c
        )

        self.viscosity_model = ViscosityModel(self.viscosity_config)
        self.ml_model = MarxLangenheimModel(self.ml_config)
        self.bl_model = BobergLantzModel(self.bl_config, self.viscosity_model)

        # Retained state from last injection/soak step if invoked sequentially
        self._last_injection_result: Optional[InjectionResult] = None
        self._last_steam_temp_c: float = 260.0
        self._last_soak_result: Optional[Dict[str, Any]] = None

    def inject(
        self,
        steam_rate_tpd: float,
        steam_temp_c: float,
        injection_days: float,
        steam_quality: float,
    ) -> Dict[str, Any]:
        """Perform Layer A injection calculation.

        Returns:
            Dict containing:
            - 'heated_radius_m': float
            - 'heated_area_m2': float
            - 'total_heat_mj': float
            - 'thermal_efficiency_indicator': float
        """
        res = self.ml_model.calculate_injection(
            steam_rate_tpd=steam_rate_tpd,
            steam_temp_c=steam_temp_c,
            injection_days=injection_days,
            steam_quality=steam_quality,
        )
        self._last_injection_result = res
        self._last_steam_temp_c = steam_temp_c

        return {
            "heated_radius_m": res.heated_radius_m,
            "heated_area_m2": res.heated_area_m2,
            "total_heat_mj": res.total_heat_mj,
            "thermal_efficiency_indicator": res.thermal_efficiency_indicator,
        }

    def soak(
        self,
        soak_days: int,
        steam_temp_c: Optional[float] = None,
        heated_radius_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Perform Layer B soak calculation (conductive cooling).

        Returns:
            Dict containing:
            - 'temperature_time_series': List[float]
            - 'end_soak_temperature': float
        """
        st_temp = steam_temp_c if steam_temp_c is not None else self._last_steam_temp_c
        if heated_radius_m is not None:
            r_h = heated_radius_m
        elif self._last_injection_result is not None:
            r_h = self._last_injection_result.heated_radius_m
        else:
            r_h = 10.0  # sensible default if called standalone

        res = self.bl_model.simulate_soak(
            soak_days=soak_days,
            steam_temp_c=st_temp,
            heated_radius_m=r_h,
        )
        self._last_soak_result = res
        return res

    def produce(
        self,
        production_days: int,
        productivity_params: Optional[Union[ProductivityParams, Dict[str, Any]]] = None,
        start_temp_c: Optional[float] = None,
        steam_temp_c: Optional[float] = None,
        heated_radius_m: Optional[float] = None,
        soak_days: int = 0,
    ) -> List[Dict[str, Any]]:
        """Perform Layer B production simulation.

        Returns a time series of dicts with:
        - 'day': int
        - 'reservoir_temperature': float
        - 'viscosity': float
        - 'estimated_inflow': float (productivity index)
        - 'oil_rate': float (bopd)
        - 'cumulative_oil': float (bbl)
        """
        if isinstance(productivity_params, dict):
            p_params = ProductivityParams(**productivity_params)
        else:
            p_params = productivity_params or ProductivityParams()

        st_temp = steam_temp_c if steam_temp_c is not None else self._last_steam_temp_c
        if start_temp_c is not None:
            t_start = start_temp_c
        elif self._last_soak_result is not None:
            t_start = self._last_soak_result["end_soak_temperature"]
        else:
            t_start = st_temp

        if heated_radius_m is not None:
            r_h = heated_radius_m
        elif self._last_injection_result is not None:
            r_h = self._last_injection_result.heated_radius_m
        else:
            r_h = 10.0

        records = self.bl_model.simulate_production(
            production_days=production_days,
            start_temp_c=t_start,
            steam_temp_c=st_temp,
            heated_radius_m=r_h,
            soak_days=soak_days,
            prod_params=p_params,
        )

        return [
            {
                "day": r.day,
                "reservoir_temperature": r.reservoir_temperature_c,
                "viscosity": r.viscosity_cp,
                "estimated_inflow": r.estimated_inflow_pi,
                "oil_rate": r.oil_rate_bopd,
                "cumulative_oil": r.cumulative_oil_bbl,
            }
            for r in records
        ]

    def run_cycle(self, params: Union[CSSCycleParams, Dict[str, Any]]) -> CycleResult:
        """Execute an integrated end-to-end CSS cycle simulation.

        Parameters:
            params: CSSCycleParams or dict matching its fields.

        Returns:
            CycleResult containing full_cycle_timeline, cycle_oil, cycle_steam,
            SOR, temperature_history, viscosity_history, and phase_boundaries.
        """
        if isinstance(params, dict):
            c_params = CSSCycleParams(**params)
        else:
            c_params = params

        t_base = self.ml_config.base_reservoir_temp_c
        t_steam = c_params.steam_temp_c

        # Step 1: Injection
        inj_dict = self.inject(
            steam_rate_tpd=c_params.steam_rate_tpd,
            steam_temp_c=c_params.steam_temp_c,
            injection_days=c_params.injection_days,
            steam_quality=c_params.steam_quality,
        )
        inj_res = self._last_injection_result

        # Step 2: Soak
        soak_dict = self.soak(
            soak_days=c_params.soak_days,
            steam_temp_c=t_steam,
            heated_radius_m=inj_res.heated_radius_m,
        )

        # Step 3: Production
        prod_list = self.produce(
            production_days=c_params.production_days,
            productivity_params=c_params.productivity_params,
            start_temp_c=soak_dict["end_soak_temperature"],
            steam_temp_c=t_steam,
            heated_radius_m=inj_res.heated_radius_m,
            soak_days=c_params.soak_days,
        )

        # Build full cycle timeline
        timeline: List[CycleTimelineRecord] = []
        temp_history: List[float] = []
        visc_history: List[float] = []

        total_cum_steam = 0.0
        current_cum_oil = 0.0
        day_counter = 1

        # Injection phase timeline:
        # Temperature rises monotonically towards steam temperature
        for d in range(1, c_params.injection_days + 1):
            total_cum_steam += c_params.steam_rate_tpd
            # Smooth rising profile during heating:
            # At d=1: T rises above baseline; at end: T reaches steam temperature
            frac = d / c_params.injection_days
            # Square root growth characteristic of thermal diffusion front:
            t_day = t_base + (t_steam - t_base) * (frac ** 0.5)
            mu_day = self.viscosity_model.calculate_viscosity(t_day)

            record = CycleTimelineRecord(
                day=day_counter,
                phase="INJECTION",
                temperature_c=float(t_day),
                viscosity_cp=float(mu_day),
                oil_rate_bopd=0.0,
                cumulative_oil_bbl=0.0,
                steam_rate_tpd=float(c_params.steam_rate_tpd),
                cumulative_steam_t=float(total_cum_steam),
            )
            timeline.append(record)
            temp_history.append(float(t_day))
            visc_history.append(float(mu_day))
            day_counter += 1

        # Soak phase timeline:
        # Temperature decays conductively from t_steam
        for d in range(1, c_params.soak_days + 1):
            t_day = soak_dict["temperature_time_series"][d - 1]
            mu_day = self.viscosity_model.calculate_viscosity(t_day)

            record = CycleTimelineRecord(
                day=day_counter,
                phase="SOAKING",
                temperature_c=float(t_day),
                viscosity_cp=float(mu_day),
                oil_rate_bopd=0.0,
                cumulative_oil_bbl=0.0,
                steam_rate_tpd=0.0,
                cumulative_steam_t=float(total_cum_steam),
            )
            timeline.append(record)
            temp_history.append(float(t_day))
            visc_history.append(float(mu_day))
            day_counter += 1

        # Production phase timeline:
        # Oil produced, temperature decays conductively + convectively
        for p_rec in prod_list:
            t_day = p_rec["reservoir_temperature"]
            mu_day = p_rec["viscosity"]
            oil_rate = p_rec["oil_rate"]
            current_cum_oil = p_rec["cumulative_oil"]

            record = CycleTimelineRecord(
                day=day_counter,
                phase="PRODUCTION",
                temperature_c=float(t_day),
                viscosity_cp=float(mu_day),
                oil_rate_bopd=float(oil_rate),
                cumulative_oil_bbl=float(current_cum_oil),
                steam_rate_tpd=0.0,
                cumulative_steam_t=float(total_cum_steam),
            )
            timeline.append(record)
            temp_history.append(float(t_day))
            visc_history.append(float(mu_day))
            day_counter += 1

        cycle_oil = current_cum_oil
        cycle_steam = total_cum_steam

        # Steam-to-Oil Ratio (tonne steam / bbl oil)
        if cycle_oil > 1e-6:
            sor_t_bbl = cycle_steam / cycle_oil
            # 1 tonne water = 1 m^3 = 6.2898 bbl (Cold Water Equivalent CWE)
            sor_cwe_bbl_bbl = (cycle_steam * 6.2898) / cycle_oil
        else:
            sor_t_bbl = 0.0
            sor_cwe_bbl_bbl = 0.0

        inj_end = c_params.injection_days
        soak_end = inj_end + c_params.soak_days
        prod_end = soak_end + c_params.production_days

        phase_boundaries = {
            "injection": {"start_day": 1, "end_day": inj_end},
            "soak": {"start_day": inj_end + 1, "end_day": soak_end},
            "production": {"start_day": soak_end + 1, "end_day": prod_end},
        }

        return CycleResult(
            full_cycle_timeline=timeline,
            cycle_oil=float(cycle_oil),
            cycle_steam=float(cycle_steam),
            SOR=float(sor_t_bbl),
            sor_cwe_bbl_per_bbl=float(sor_cwe_bbl_bbl),
            temperature_history=temp_history,
            viscosity_history=visc_history,
            phase_boundaries=phase_boundaries,
            injection_summary=inj_res,
        )
