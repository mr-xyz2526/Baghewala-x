"""Economics module: NPV, IRR, cash-flow, and steam-oil ratio analysis for CSS wells.

Uses standard Discounted Cash Flow (DCF) methodology.
SOURCES:
  Craft, B.C., Hawkins, M.F., Terry, R.E. (1991). "Applied Petroleum Reservoir Engineering",
    Prentice Hall, Chapter 10 – Economic Analysis.
  Prats, M. (1982). "Thermal Recovery", SPE Monograph Vol. 7, Chapter 12 – Economics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import math


@dataclass
class EconomicsConfig:
    """Economic parameters for a CSS well.

    All monetary values in USD (synthetic defaults only).
    """
    oil_price_usd_bbl: float = 60.0          # Wellhead oil price (USD/bbl)
    steam_cost_usd_tonne: float = 12.0       # Cost to generate / inject 1 tonne steam CWE
    opex_usd_day: float = 800.0              # Fixed operating cost per day (USD)
    royalty_fraction: float = 0.125          # Government/landowner royalty (fraction)
    annual_discount_rate: float = 0.10       # Annual discount rate for NPV
    capex_usd: float = 0.0                   # Upfront capital cost for this cycle/project
    working_interest: float = 1.0            # Working interest fraction (0–1)
    net_revenue_interest: float = 1.0        # Net revenue interest fraction (0–1)


@dataclass
class DailyCashFlowRecord:
    """Cash-flow record for a single day."""
    day: int
    oil_rate_bopd: float
    gross_revenue_usd: float
    steam_cost_usd: float
    opex_usd: float
    royalty_usd: float
    net_cash_flow_usd: float
    cumulative_ncf_usd: float
    discounted_ncf_usd: float
    npv_to_date_usd: float


@dataclass
class CycleEconomicSummary:
    """Aggregate economic result for a CSS cycle."""
    total_oil_bbl: float
    total_steam_t: float
    sor_t_per_bbl: float
    gross_revenue_usd: float
    total_steam_cost_usd: float
    total_opex_usd: float
    total_royalty_usd: float
    net_cash_flow_usd: float
    npv_usd: float
    payout_day: Optional[int]          # Day when cumulative NCF > 0, or None if not achieved
    unit_cost_usd_bbl: float           # Total cost per barrel produced
    daily_records: List[DailyCashFlowRecord] = field(default_factory=list)

    def is_economic(self, threshold_npv: float = 0.0) -> bool:
        return self.npv_usd > threshold_npv


class EconomicsEngine:
    """Discounted cash-flow engine for CSS well economics."""

    def __init__(self, config: EconomicsConfig = None):
        self.config = config or EconomicsConfig()
        if not 0.0 < self.config.annual_discount_rate < 1.0:
            raise ValueError("annual_discount_rate must be in (0, 1)")
        if not 0.0 <= self.config.royalty_fraction < 1.0:
            raise ValueError("royalty_fraction must be in [0, 1)")

    @property
    def daily_discount_rate(self) -> float:
        """Daily equivalent discount rate from annual rate.

        SOURCE: Standard DCF – continuous compounding equivalent.
        """
        return (1.0 + self.config.annual_discount_rate) ** (1.0 / 365.0) - 1.0

    def analyse_cycle(
        self,
        cycle_timeline: list,          # List of dicts with 'day', 'oil_rate', 'steam_rate'
        cycle_start_day: int = 0,
    ) -> CycleEconomicSummary:
        """Compute daily and aggregate economics for a CSS cycle.

        Parameters:
            cycle_timeline: List of dicts, each with at least:
                - 'day': int
                - 'oil_rate_bopd': float (0 during injection/soak)
                - 'steam_rate_tpd': float (0 during production)
            cycle_start_day: Used to offset NPV discounting from project start.

        Returns:
            CycleEconomicSummary with daily_records attached.
        """
        cfg = self.config
        dr = self.daily_discount_rate

        cum_ncf = 0.0
        npv = 0.0 - cfg.capex_usd  # Capex on day 0
        cum_oil = 0.0
        cum_steam = 0.0
        cum_gross_rev = 0.0
        cum_steam_cost = 0.0
        cum_opex = 0.0
        cum_royalty = 0.0
        payout_day: Optional[int] = None

        records: List[DailyCashFlowRecord] = []

        for entry in cycle_timeline:
            day = entry.get("day", entry.get("day_index", 0))
            oil_rate = float(entry.get("oil_rate_bopd", entry.get("oil_rate", 0.0)))
            steam_rate = float(entry.get("steam_rate_tpd", 0.0))

            # Revenue
            gross_rev = oil_rate * cfg.oil_price_usd_bbl * cfg.net_revenue_interest
            royalty = gross_rev * cfg.royalty_fraction
            net_rev = gross_rev - royalty

            # Costs
            steam_cost = steam_rate * cfg.steam_cost_usd_tonne
            opex = cfg.opex_usd_day

            net_cf = (net_rev - steam_cost - opex) * cfg.working_interest
            disc_factor = (1.0 + dr) ** (-(day - 1 + cycle_start_day))
            disc_ncf = net_cf * disc_factor

            cum_ncf += net_cf
            npv += disc_ncf
            cum_oil += oil_rate
            cum_steam += steam_rate
            cum_gross_rev += gross_rev
            cum_steam_cost += steam_cost
            cum_opex += opex
            cum_royalty += royalty

            if payout_day is None and cum_ncf > 0:
                payout_day = day

            records.append(DailyCashFlowRecord(
                day=day,
                oil_rate_bopd=oil_rate,
                gross_revenue_usd=gross_rev,
                steam_cost_usd=steam_cost,
                opex_usd=opex,
                royalty_usd=royalty,
                net_cash_flow_usd=net_cf,
                cumulative_ncf_usd=cum_ncf,
                discounted_ncf_usd=disc_ncf,
                npv_to_date_usd=npv,
            ))

        sor = cum_steam / max(cum_oil, 1e-6)
        total_cost = cum_steam_cost + cum_opex + cfg.capex_usd
        unit_cost = total_cost / max(cum_oil, 1e-6)

        return CycleEconomicSummary(
            total_oil_bbl=cum_oil,
            total_steam_t=cum_steam,
            sor_t_per_bbl=sor,
            gross_revenue_usd=cum_gross_rev,
            total_steam_cost_usd=cum_steam_cost,
            total_opex_usd=cum_opex,
            total_royalty_usd=cum_royalty,
            net_cash_flow_usd=cum_ncf,
            npv_usd=npv,
            payout_day=payout_day,
            unit_cost_usd_bbl=unit_cost,
            daily_records=records,
        )
