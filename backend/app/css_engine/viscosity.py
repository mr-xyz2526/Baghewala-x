"""Heavy oil viscosity model for thermal recovery calculations.

NOTE ON CALIBRATION:
The default coefficients in this module are representative literature-based
synthetic values for extra-heavy crude/bitumen analogues.
They are NOT calibrated against field crude assay data from Baghewala or any
specific reservoir. A sensitivity_factor parameter is explicitly exposed to
allow parametric uncertainty analysis.
"""

from dataclasses import dataclass
import math
from typing import Union
import numpy as np


@dataclass
class ViscosityConfig:
    """Explicit configuration parameters for temperature-viscosity relationship.

    Attributes:
        mu_ref_cp: Cold oil dynamic viscosity at reference temperature (cP).
            Default: 10,000 cP (synthetic heavy oil analogue, NOT field-calibrated).
        t_ref_c: Reference temperature for mu_ref_cp (deg C). Default: 50.0 deg C.
        b_activation_k: Apparent thermal activation constant B = E_a / R (Kelvin).
            Default: 4500.0 K (literature representative value).
        sensitivity_factor: Multiplier on temperature sensitivity (dimensionless).
            Default: 1.0 (permits sensitivity sweeps when crude assay data are absent).
        min_viscosity_cp: Physical floor for high-temperature asymptotic limit (cP).
            Default: 0.5 cP.
    """
    mu_ref_cp: float = 10000.0
    t_ref_c: float = 50.0
    b_activation_k: float = 4500.0
    sensitivity_factor: float = 1.0
    min_viscosity_cp: float = 0.5


class ViscosityModel:
    """Temperature-dependent dynamic viscosity model for heavy oil/bitumen.

    Uses the classic Andrade/Arrhenius formulation relating dynamic viscosity
    to absolute temperature, with an explicit sensitivity parameter.
    """

    def __init__(self, config: ViscosityConfig = None):
        self.config = config or ViscosityConfig()
        if self.config.mu_ref_cp <= 0:
            raise ValueError(f"Reference viscosity must be positive, got {self.config.mu_ref_cp}")
        if self.config.b_activation_k <= 0:
            raise ValueError(f"Activation constant B must be positive, got {self.config.b_activation_k}")
        if self.config.sensitivity_factor <= 0:
            raise ValueError(f"Sensitivity factor must be positive, got {self.config.sensitivity_factor}")

    def calculate_viscosity(self, temperature_c: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Compute oil dynamic viscosity (cP) at the given temperature(s) (deg C).

        Equation:
            mu(T) = mu_ref * exp( B * s * ( 1 / (T + 273.15) - 1 / (T_ref + 273.15) ) )
        SOURCE: Andrade, E.N. da C. (1930), 'The Viscosity of Liquids', Nature, 125, 309-310.
        SOURCE: Butler, R.M. (1991), 'Thermal Recovery of Oil and Bitumen', Prentice Hall, Eq. 2.1-2.4.
        """
        is_scalar = isinstance(temperature_c, (int, float))
        t_arr = np.asarray(temperature_c, dtype=float)

        t_k = t_arr + 273.15
        if np.any(t_k <= 0):
            raise ValueError("Temperature in Kelvin must be strictly positive (> -273.15 deg C)")

        t_ref_k = self.config.t_ref_c + 273.15
        b_eff = self.config.b_activation_k * self.config.sensitivity_factor

        # SOURCE: Andrade (1930) / Butler (1991) temperature-viscosity relationship
        ln_ratio = b_eff * (1.0 / t_k - 1.0 / t_ref_k)
        visc = self.config.mu_ref_cp * np.exp(ln_ratio)
        visc = np.maximum(visc, self.config.min_viscosity_cp)

        if is_scalar:
            return float(visc.item())
        return visc

    def __call__(self, temperature_c: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        return self.calculate_viscosity(temperature_c)
