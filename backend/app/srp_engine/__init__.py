"""SRP (Surface Rod Pump) Engine.

Analytical and numerical beam-pumping modeling:
- Gibbs (1963) one-dimensional damped wave equation solver
- Surface and downhole dynamometer card generation
- Operating point and static load calculations (API 11E / Takacs 2015)
- Multi-class synthetic dynamometer dataset generator
"""

from .srp_simulator import SRPSimulator, SRPConfig, SRPOperatingPoint
from .models import (
    CardClass,
    RodStringParams,
    PumpParams,
    OperatingState,
    DynamometerCardResult,
)
from .wave_solver import GibbsWaveSolver, calculate_net_fluid_load_n
from .card_generator import (
    generate_dynamometer_card,
    generate_analytical_card,
    generate_synthetic_dataset,
    compute_card_area_in_lbf,
    normalize_card_points,
)

__all__ = [
    "SRPSimulator",
    "SRPConfig",
    "SRPOperatingPoint",
    "CardClass",
    "RodStringParams",
    "PumpParams",
    "OperatingState",
    "DynamometerCardResult",
    "GibbsWaveSolver",
    "calculate_net_fluid_load_n",
    "generate_dynamometer_card",
    "generate_analytical_card",
    "generate_synthetic_dataset",
    "compute_card_area_in_lbf",
    "normalize_card_points",
]
