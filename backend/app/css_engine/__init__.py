"""Cyclic Steam Stimulation (CSS) Engine.

Analytical thermal recovery simulator:
- Marx-Langenheim (1961) thermal balance injection model
- Boberg-Lantz (1966) post-injection temperature & productivity model
- Temperature-dependent viscosity model with explicit sensitivity
"""

from .viscosity import ViscosityModel, ViscosityConfig
from .marx_langenheim import MarxLangenheimModel, MarxLangenheimConfig, InjectionResult
from .boberg_lantz import (
    BobergLantzModel,
    BobergLantzConfig,
    ProductivityParams,
    ProductionDayRecord,
)
from .simulator import (
    CSSCycleSimulator,
    CSSCycleParams,
    CycleResult,
    CycleTimelineRecord,
)

__all__ = [
    "ViscosityModel",
    "ViscosityConfig",
    "MarxLangenheimModel",
    "MarxLangenheimConfig",
    "InjectionResult",
    "BobergLantzModel",
    "BobergLantzConfig",
    "ProductivityParams",
    "ProductionDayRecord",
    "CSSCycleSimulator",
    "CSSCycleParams",
    "CycleResult",
    "CycleTimelineRecord",
]
