import copy
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from ..models.well_state import WellTwinState
from pydantic import ValidationError


class TwinStateStore:
    """In‑memory store for well twin states with simple history tracking.

    The store is deliberately lightweight – suitable for a demo or unit tests.
    In a production system this would be backed by a database and include
    concurrency controls.
    """

    def __init__(self):
        # current state per well_id
        self._current: Dict[str, WellTwinState] = {}
        # list of historic states per well_id (ordered oldest → newest)
        self._history: Dict[str, List[WellTwinState]] = {}
        # a deterministic demo baseline used by reset_demo_state
        self._demo_baseline: Dict[str, Any] = {
            "well_id": "demo-well-001",
            "well_name": "Demo Well",
            "timestamp": datetime.now(timezone.utc),
            "field": "Demo Field",
            "cycle_number": 0,
            "phase": "INJECTION",
            "days_in_phase": 0,
            "reservoir_temperature_c": 150.0,
            "base_reservoir_temperature_c": 150.0,
            "reservoir_pressure_bar": 30.0,
            "steam_rate_tpd": 1000.0,
            "steam_pressure_bar": 15.0,
            "steam_quality": 0.9,
            "injection_duration_days": 30,
            "soak_duration_days": 10,
            "production_cutoff_days": 60,
            "cumulative_steam_t": 0.0,
            "cumulative_oil_bbl": 0.0,
            "heated_radius_m": 0.0,
            "oil_viscosity_cp": 10.0,
            "spm": 0.0,
            "stroke_length_in": 4.0,
            "vfd_hz": 60.0,
            "pump_fillage_pct": 0.0,
            "peak_rod_load": 0.0,
            "min_rod_load": 0.0,
            "rod_stress_indicator": 0.0,
            "motor_power_kw": 100.0,
            "torque_indicator": 0.0,
            "wellhead_pressure_bar": 30.0,
            "pump_intake_pressure_bar": 28.0,
            "choke_pct": 0.0,
            "oil_rate_bopd": 0.0,
            "water_cut_pct": None,
            "anomaly_class": None,
            "anomaly_probability": None,
            "rod_floating_risk": None,
            "impact_risk": None,
            "equipment_risk": None,
            "model_confidence_pct": 100.0,
            "state_residual_score": 0.0,
            "data_quality_score": 100.0,
            "last_update_timestamp": datetime.now(timezone.utc),
            "mode": "SIMULATED_DEMO",
            "source_notes": "Initial demo state",
        }

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def get_well_state(self, well_id: str) -> Optional[WellTwinState]:
        """Return the current WellTwinState for *well_id* or ``None`` if unknown."""
        return self._current.get(well_id)

    def update_state(self, well_id: str, patch: dict) -> WellTwinState:
        """Apply *patch* (a dict of field updates) to the stored state.

        Raises:
            KeyError: if the well does not exist.
            ValidationError / ValueError: if the resulting state is invalid.
        """
        if well_id not in self._current:
            raise KeyError(f"Well '{well_id}' not found in store")
        current_state = self._current[well_id]
        try:
            new_state = current_state.copy_with_patch(patch)
        except (ValidationError, ValueError) as exc:
            # Propagate validation errors to the caller for test assertions
            raise exc
        # Persist new state and history
        self._current[well_id] = new_state
        self._history.setdefault(well_id, []).append(new_state)
        return new_state

    def history(self, well_id: str) -> List[WellTwinState]:
        """Return the ordered list of historic states for *well_id*.
        The current state is also included as the last element.
        """
        return copy.deepcopy(self._history.get(well_id, []))

    def reset_demo_state(self, well_id: str) -> WellTwinState:
        """Create a fresh demo state for *well_id* and replace any existing data.
        The history is cleared.
        """
        baseline = copy.deepcopy(self._demo_baseline)
        baseline["well_id"] = well_id
        baseline["well_name"] = f"Demo Well {well_id}"
        baseline["timestamp"] = datetime.now(timezone.utc)
        baseline["last_update_timestamp"] = datetime.now(timezone.utc)
        demo_state = WellTwinState(**baseline)
        self._current[well_id] = demo_state
        self._history[well_id] = [demo_state]
        return demo_state

    # ---------------------------------------------------------------------
    # Convenience for tests / scripts
    # ---------------------------------------------------------------------
    def ensure_well(self, well_id: str) -> WellTwinState:
        """Utility: return existing state or create a demo one if missing."""
        if well_id not in self._current:
            return self.reset_demo_state(well_id)
        return self._current[well_id]
