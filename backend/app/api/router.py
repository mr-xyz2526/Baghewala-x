"""FastAPI routes for the Baghewala-X twin backend."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..css_engine import CSSCycleSimulator, CSSCycleParams, ProductivityParams
from ..srp_engine import SRPSimulator, SRPConfig
from ..economics import EconomicsEngine, EconomicsConfig
from ..risk import RiskEngine
from ..twin import TwinOrchestrator, TwinRunParams
from ..services.twin_state_store import TwinStateStore
from ..optimization import CSSOptimizer, OptimizationBounds, SelectionRuleConfig

router = APIRouter()

# Module-level singletons (stateless per-request, store is shared)
_store = TwinStateStore()
_css = CSSCycleSimulator()
_srp = SRPSimulator()
_risk = RiskEngine()
_econ = EconomicsEngine()
_orchestrator = TwinOrchestrator(
    css_simulator=_css,
    srp_simulator=_srp,
    risk_engine=_risk,
    economics_engine=_econ,
    store=_store,
)


# ── Health / smoke ──────────────────────────────────────────────────────────

@router.get("/ping")
async def ping():
    return {"message": "pong", "service": "baghewala-x"}


# ── CSS Engine ──────────────────────────────────────────────────────────────

class CSSRunRequest(BaseModel):
    steam_rate_tpd: float = 800.0
    steam_temp_c: float = 260.0
    injection_days: int = 18
    steam_quality: float = 0.80
    soak_days: int = 4
    production_days: int = 70
    base_drawdown_bar: float = 20.0
    base_productivity_index_bopd_per_bar: float = 1.0
    water_cut_pct: float = 30.0


@router.post("/css/run")
async def css_run(req: CSSRunRequest):
    """Run a full CSS cycle (inject → soak → produce) and return time series."""
    try:
        sim = CSSCycleSimulator()
        params = CSSCycleParams(
            steam_rate_tpd=req.steam_rate_tpd,
            steam_temp_c=req.steam_temp_c,
            injection_days=req.injection_days,
            steam_quality=req.steam_quality,
            soak_days=req.soak_days,
            production_days=req.production_days,
            productivity_params=ProductivityParams(
                base_drawdown_bar=req.base_drawdown_bar,
                base_productivity_index_bopd_per_bar=req.base_productivity_index_bopd_per_bar,
                water_cut_pct=req.water_cut_pct,
            ),
        )
        result = sim.run_cycle(params)
        return result.to_dict()
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/css/inject")
async def css_inject(
    steam_rate_tpd: float = 800.0,
    steam_temp_c: float = 260.0,
    injection_days: int = 18,
    steam_quality: float = 0.80,
):
    """Run only the injection phase and return heated zone metrics."""
    try:
        sim = CSSCycleSimulator()
        return sim.inject(steam_rate_tpd, steam_temp_c, injection_days, steam_quality)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── SRP Engine ──────────────────────────────────────────────────────────────

class SRPRequest(BaseModel):
    spm: float = 6.0
    fillage_pct: float = 80.0
    water_cut_pct: float = 30.0
    pump_depth_m: float = 500.0
    structural_stroke_in: float = 72.0


@router.post("/srp/compute")
async def srp_compute(req: SRPRequest):
    """Compute SRP operating point at the given SPM and pump fillage."""
    try:
        cfg = SRPConfig(
            pump_depth_m=req.pump_depth_m,
            structural_stroke_in=req.structural_stroke_in,
        )
        sim = SRPSimulator(cfg)
        point = sim.compute_operating_point(
            spm=req.spm,
            fillage_pct=req.fillage_pct,
            water_cut_pct=req.water_cut_pct,
        )
        from dataclasses import asdict
        return asdict(point)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Economics ───────────────────────────────────────────────────────────────

class EconomicsRequest(BaseModel):
    oil_price_usd_bbl: float = 60.0
    steam_cost_usd_tonne: float = 12.0
    opex_usd_day: float = 800.0
    # The caller supplies the CSS timeline as list of records
    timeline: List[Dict[str, Any]]


@router.post("/economics/analyse")
async def economics_analyse(req: EconomicsRequest):
    """Run DCF cash-flow analysis over a supplied CSS timeline."""
    try:
        cfg = EconomicsConfig(
            oil_price_usd_bbl=req.oil_price_usd_bbl,
            steam_cost_usd_tonne=req.steam_cost_usd_tonne,
            opex_usd_day=req.opex_usd_day,
        )
        eng = EconomicsEngine(cfg)
        summary = eng.analyse_cycle(req.timeline)
        return {
            "total_oil_bbl": summary.total_oil_bbl,
            "total_steam_t": summary.total_steam_t,
            "sor_t_per_bbl": summary.sor_t_per_bbl,
            "gross_revenue_usd": summary.gross_revenue_usd,
            "total_steam_cost_usd": summary.total_steam_cost_usd,
            "total_opex_usd": summary.total_opex_usd,
            "net_cash_flow_usd": summary.net_cash_flow_usd,
            "npv_usd": summary.npv_usd,
            "payout_day": summary.payout_day,
            "unit_cost_usd_bbl": summary.unit_cost_usd_bbl,
            "is_economic": summary.is_economic(),
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Risk ────────────────────────────────────────────────────────────────────

class RiskRequest(BaseModel):
    pump_fillage_pct: float = 80.0
    peak_rod_load_lbf: float = 10000.0
    min_rod_load_lbf: float = 3000.0
    rod_stress_indicator: float = 0.3
    motor_power_kw: float = 30.0
    oil_rate_bopd: float = 200.0
    prev_fillage_pct: Optional[float] = None


@router.post("/risk/score")
async def risk_score(req: RiskRequest):
    """Score SRP operating risk from current sensor-equivalent state."""
    risk = RiskEngine()
    score = risk.score_srp_state(
        pump_fillage_pct=req.pump_fillage_pct,
        peak_rod_load_lbf=req.peak_rod_load_lbf,
        min_rod_load_lbf=req.min_rod_load_lbf,
        rod_stress_indicator=req.rod_stress_indicator,
        motor_power_kw=req.motor_power_kw,
        oil_rate_bopd=req.oil_rate_bopd,
        prev_fillage_pct=req.prev_fillage_pct,
    )
    return {
        "anomaly_class": score.anomaly_class.value,
        "anomaly_probability": score.anomaly_probability,
        "rod_floating_risk": score.rod_floating_risk,
        "impact_risk": score.impact_risk,
        "equipment_risk": score.equipment_risk,
        "flags": score.flags,
        "recommendations": score.recommendations,
    }


# ── Twin Orchestrator ───────────────────────────────────────────────────────

class TwinRunRequest(BaseModel):
    well_id: str = "demo-well-001"
    well_name: str = "Baghewala Demo Well"
    field_name: str = "Demo Field"
    steam_rate_tpd: float = 800.0
    steam_temp_c: float = 260.0
    injection_days: int = 18
    steam_quality: float = 0.80
    soak_days: int = 4
    production_days: int = 70
    spm: float = 6.0
    vfd_hz: float = 36.0
    water_cut_pct: float = 30.0
    oil_price_usd_bbl: float = 60.0
    steam_cost_usd_tonne: float = 12.0
    mode: str = "SIMULATED_DEMO"
    source_notes: Optional[str] = None


@router.post("/twin/run")
async def twin_run(req: TwinRunRequest):
    """Run a complete digital twin cycle: CSS + SRP + economics + risk."""
    try:
        run_params = TwinRunParams(**req.model_dump())
        return _orchestrator.run(run_params)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Well State Store ─────────────────────────────────────────────────────────

@router.get("/wells/{well_id}/state")
async def get_well_state(well_id: str):
    """Return the current WellTwinState for a well."""
    state = _store.get_well_state(well_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Well '{well_id}' not found")
    return state.model_dump()


@router.get("/wells/{well_id}/history")
async def get_well_history(well_id: str):
    """Return state history for a well."""
    history = _store.history(well_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"No history for well '{well_id}'")
    return [s.model_dump() for s in history]


@router.post("/wells/{well_id}/reset")
async def reset_well(well_id: str):
    """Reset a well to its demo baseline state."""
    state = _store.reset_demo_state(well_id)
    return state.model_dump()


# ── CSS Optimizer ───────────────────────────────────────────────────────────

class OptimizerRequest(BaseModel):
    current_plan: Optional[Dict[str, Any]] = None
    bounds: Optional[Dict[str, Any]] = None
    selection_rule: Optional[Dict[str, Any]] = None
    use_nsga2: bool = True
    random_seed: Optional[int] = 42


@router.post("/optimizer/optimize")
async def optimize_css(req: OptimizerRequest):
    """Run multi-objective optimization (Pareto front, trade-offs, compromise selection)."""
    try:
        bounds_obj = OptimizationBounds(**req.bounds) if req.bounds else OptimizationBounds()
        rule_obj = SelectionRuleConfig(**req.selection_rule) if req.selection_rule else SelectionRuleConfig()
        opt = CSSOptimizer(bounds=bounds_obj, random_seed=req.random_seed)
        res = opt.optimize(
            current_plan_params=req.current_plan,
            selection_rule=rule_obj,
            use_nsga2=req.use_nsga2,
        )
        return res.to_dict()
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

