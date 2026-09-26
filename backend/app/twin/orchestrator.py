"""Digital Twin Orchestrator.

Wires together:
  - CSSCycleSimulator (thermal physics)
  - SRPSimulator (pump mechanics)
  - RiskEngine (anomaly scoring)
  - EconomicsEngine (NPV / cash flow)
  - TwinStateStore (state persistence)

Produces an integrated, per-day simulation result that populates WellTwinState fields.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..css_engine import CSSCycleSimulator, CSSCycleParams, ProductivityParams
from ..srp_engine import SRPSimulator, SRPConfig
from ..economics import EconomicsEngine, EconomicsConfig
from ..risk import RiskEngine, RiskThresholds
from ..models.well_state import WellTwinState, Phase, Mode
from ..services.twin_state_store import TwinStateStore


@dataclass
class TwinRunParams:
    """Top-level parameters for a single twin simulation run."""
    well_id: str = "demo-well-001"
    well_name: str = "Baghewala Demo Well"
    field_name: str = "Demo Field"

    # CSS
    steam_rate_tpd: float = 800.0
    steam_temp_c: float = 260.0
    injection_days: int = 18
    steam_quality: float = 0.80
    soak_days: int = 4
    production_days: int = 70

    # SRP
    spm: float = 6.0
    vfd_hz: float = 36.0
    water_cut_pct: float = 30.0

    # Economics
    oil_price_usd_bbl: float = 60.0
    steam_cost_usd_tonne: float = 12.0

    # Metadata
    mode: str = "SIMULATED_DEMO"
    source_notes: Optional[str] = "Run by TwinOrchestrator"


class TwinOrchestrator:
    """Runs a full CSS twin simulation and populates WellTwinState records."""

    def __init__(
        self,
        css_simulator: Optional[CSSCycleSimulator] = None,
        srp_simulator: Optional[SRPSimulator] = None,
        risk_engine: Optional[RiskEngine] = None,
        economics_engine: Optional[EconomicsEngine] = None,
        store: Optional[TwinStateStore] = None,
    ):
        self.css = css_simulator or CSSCycleSimulator()
        self.srp = srp_simulator or SRPSimulator()
        self.risk = risk_engine or RiskEngine()
        self.econ = economics_engine or EconomicsEngine()
        self.store = store or TwinStateStore()

    def run(self, params: TwinRunParams) -> Dict[str, Any]:
        """Execute a full CSS twin cycle and return integrated results.

        Returns a dict with:
            - 'well_id'
            - 'cycle_result'       (from CSSCycleSimulator)
            - 'economics'          (from EconomicsEngine)
            - 'srp_point'          (from SRPSimulator at current SPM)
            - 'risk_score'         (from RiskEngine)
            - 'final_well_state'   (WellTwinState)
            - 'history'            (list of WellTwinState)
        """
        # -------------------------------------------------------------------
        # Step 1: Run CSS cycle
        # -------------------------------------------------------------------
        css_params = CSSCycleParams(
            steam_rate_tpd=params.steam_rate_tpd,
            steam_temp_c=params.steam_temp_c,
            injection_days=params.injection_days,
            steam_quality=params.steam_quality,
            soak_days=params.soak_days,
            production_days=params.production_days,
            productivity_params=ProductivityParams(
                water_cut_pct=params.water_cut_pct,
            ),
        )
        cycle_result = self.css.run_cycle(css_params)

        # -------------------------------------------------------------------
        # Step 2: SRP operating point at the given SPM
        # -------------------------------------------------------------------
        srp_point = self.srp.compute_operating_point(
            spm=params.spm,
            fillage_pct=75.0,  # Representative mid-production fillage
            water_cut_pct=params.water_cut_pct,
        )

        # -------------------------------------------------------------------
        # Step 3: Economics
        # -------------------------------------------------------------------
        econ_cfg = EconomicsConfig(
            oil_price_usd_bbl=params.oil_price_usd_bbl,
            steam_cost_usd_tonne=params.steam_cost_usd_tonne,
        )
        econ_engine = EconomicsEngine(econ_cfg)
        timeline_dicts = [
            {
                "day": r.day,
                "oil_rate_bopd": r.oil_rate_bopd,
                "steam_rate_tpd": r.steam_rate_tpd,
            }
            for r in cycle_result.full_cycle_timeline
        ]
        econ_summary = econ_engine.analyse_cycle(timeline_dicts)

        # -------------------------------------------------------------------
        # Step 4: Risk scoring on final production state
        # -------------------------------------------------------------------
        prod_records = [r for r in cycle_result.full_cycle_timeline if r.phase == "PRODUCTION"]
        last_prod = prod_records[-1] if prod_records else None
        risk_score = self.risk.score_srp_state(
            pump_fillage_pct=srp_point.pump_fillage_pct,
            peak_rod_load_lbf=srp_point.peak_rod_load_lbf,
            min_rod_load_lbf=srp_point.min_rod_load_lbf,
            rod_stress_indicator=srp_point.rod_stress_indicator,
            motor_power_kw=srp_point.motor_power_kw,
            oil_rate_bopd=last_prod.oil_rate_bopd if last_prod else 0.0,
        )

        # -------------------------------------------------------------------
        # Step 5: Populate WellTwinState and store it
        # -------------------------------------------------------------------
        self.store.reset_demo_state(params.well_id)
        base_reservoir_temp = self.css.ml_config.base_reservoir_temp_c

        state_patch = dict(
            well_name=params.well_name,
            field=params.field_name,
            cycle_number=1,
            phase=Phase.PRODUCTION,
            days_in_phase=params.production_days,
            reservoir_temperature_c=float(last_prod.temperature_c if last_prod else base_reservoir_temp),
            base_reservoir_temperature_c=float(base_reservoir_temp),
            reservoir_pressure_bar=30.0,
            steam_rate_tpd=0.0,  # production phase — no steam
            steam_pressure_bar=1.01,
            steam_quality=0.0,
            injection_duration_days=params.injection_days,
            soak_duration_days=params.soak_days,
            production_cutoff_days=params.production_days,
            cumulative_steam_t=float(cycle_result.cycle_steam),
            cumulative_oil_bbl=float(cycle_result.cycle_oil),
            heated_radius_m=float(cycle_result.injection_summary.heated_radius_m),
            oil_viscosity_cp=float(last_prod.viscosity_cp if last_prod else 10000.0),
            spm=float(params.spm),
            stroke_length_in=float(srp_point.stroke_length_in),
            vfd_hz=float(params.vfd_hz),
            pump_fillage_pct=float(srp_point.pump_fillage_pct),
            peak_rod_load=float(srp_point.peak_rod_load_lbf),
            min_rod_load=float(srp_point.min_rod_load_lbf),
            rod_stress_indicator=float(srp_point.rod_stress_indicator),
            motor_power_kw=float(srp_point.motor_power_kw),
            torque_indicator=float(srp_point.torque_indicator_ft_lbf),
            wellhead_pressure_bar=5.0,
            pump_intake_pressure_bar=15.0,
            choke_pct=100.0,
            oil_rate_bopd=float(last_prod.oil_rate_bopd if last_prod else 0.0),
            water_cut_pct=float(params.water_cut_pct),
            anomaly_class=risk_score.anomaly_class.value,
            anomaly_probability=float(risk_score.anomaly_probability),
            rod_floating_risk=float(risk_score.rod_floating_risk),
            impact_risk=float(risk_score.impact_risk),
            equipment_risk=float(risk_score.equipment_risk),
            model_confidence_pct=85.0,
            state_residual_score=0.0,
            data_quality_score=100.0,
            last_update_timestamp=datetime.now(timezone.utc),
            mode=Mode(params.mode),
            source_notes=params.source_notes,
        )

        final_state = self.store.update_state(params.well_id, state_patch)
        history = self.store.history(params.well_id)

        return {
            "well_id": params.well_id,
            "cycle_result": cycle_result.to_dict(),
            "economics": {
                "total_oil_bbl": econ_summary.total_oil_bbl,
                "total_steam_t": econ_summary.total_steam_t,
                "sor_t_per_bbl": econ_summary.sor_t_per_bbl,
                "gross_revenue_usd": econ_summary.gross_revenue_usd,
                "net_cash_flow_usd": econ_summary.net_cash_flow_usd,
                "npv_usd": econ_summary.npv_usd,
                "payout_day": econ_summary.payout_day,
                "unit_cost_usd_bbl": econ_summary.unit_cost_usd_bbl,
                "is_economic": econ_summary.is_economic(),
            },
            "srp_point": asdict(srp_point),
            "risk_score": {
                "anomaly_class": risk_score.anomaly_class.value,
                "anomaly_probability": risk_score.anomaly_probability,
                "rod_floating_risk": risk_score.rod_floating_risk,
                "impact_risk": risk_score.impact_risk,
                "equipment_risk": risk_score.equipment_risk,
                "flags": risk_score.flags,
                "recommendations": risk_score.recommendations,
            },
            "final_well_state": final_state.model_dump(),
            "history_count": len(history),
        }
