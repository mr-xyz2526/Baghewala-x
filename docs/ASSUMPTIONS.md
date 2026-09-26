# ASSUMPTIONS & REPRESENTATIVE PARAMETERS TABLE

> **CRITICAL DISCLAIMER**:
> All parameters in BAGHEWALA-X are **synthetic literature/engineering baseline estimates**.
> **No field-calibrated parameters** are claimed or used. Crude assay and rock physics calibration data were not available.

| Parameter | Symbol / Key | Default Value | Source / Scholarly Reference | Unit | Allowable Physical Range | Field-Calibrated Status |
|:---|:---|:---|:---|:---|:---|:---|
| **Base Reservoir Temperature** | $T_R$ | 50.0 | Literature analogue for heavy oil reservoir | °C | 20.0 – 90.0 | Synthetic (No) |
| **Reservoir Pressure** | $p_R$ | 30.0 | Literature analogue | bar | 10.0 – 150.0 | Synthetic (No) |
| **Net Pay Thickness** | $h_{pay}$ | 15.0 | Typical CSS pay thickness | m | 3.0 – 60.0 | Synthetic (No) |
| **Reservoir Volumetric Heat Capacity** | $M_R$ | $2.3 \times 10^6$ | Prats (1982), SPE Monograph Vol. 7 | $\text{J}/(\text{m}^3\cdot\text{K})$ | $1.5\times 10^6$ – $3.5\times 10^6$ | Synthetic (No) |
| **Overburden Volumetric Heat Capacity** | $M_{ob}$ | $2.1 \times 10^6$ | Marx & Langenheim (1961), Trans. AIME | $\text{J}/(\text{m}^3\cdot\text{K})$ | $1.5\times 10^6$ – $3.0\times 10^6$ | Synthetic (No) |
| **Overburden Thermal Conductivity** | $k_{ob}$ | 1.8 | Marx & Langenheim (1961), Trans. AIME | $\text{W}/(\text{m}\cdot\text{K})$ | 1.0 – 3.5 | Synthetic (No) |
| **Reservoir Thermal Conductivity** | $k_R$ | 2.0 | Prats (1982) | $\text{W}/(\text{m}\cdot\text{K})$ | 1.0 – 3.5 | Synthetic (No) |
| **Steam Injection Rate** | $\dot{m}_{st}$ | 800.0 | Representative high-rate steam generator | t/day | 50.0 – 2500.0 | Synthetic (No) |
| **Steam Sandface Temperature** | $T_{st}$ | 260.0 | Saturated steam @ ~47 bar | °C | 150.0 – 330.0 | Synthetic (No) |
| **Steam Quality** | $f_s$ | 0.80 | Standard surface boiler steam quality | fraction | 0.0 – 1.0 | Synthetic (No) |
| **Liquid Water Heat Capacity** | $c_w$ | 4186.0 | Standard thermodynamic reference | $\text{J}/(\text{kg}\cdot\text{K})$ | 4180 – 4220 | Standard physical constant |
| **Cold Reference Viscosity** | $\mu_{ref}$ | 10,000.0 | Extra-heavy oil literature analogue | cP | 500 – 100,000 | Synthetic (No) |
| **Reference Viscosity Temp** | $T_{ref}$ | 50.0 | Baseline reservoir temperature | °C | 20.0 – 90.0 | Synthetic (No) |
| **Viscosity Activation Constant** | $B$ | 4500.0 | Andrade (1930) / Butler (1991) | K | 2500 – 7500 | Synthetic (No) |
| **Viscosity Sensitivity Factor** | $s_{sens}$ | 1.0 | Configurable multiplier for uncertainty | dimensionless | 0.2 – 3.0 | Synthetic (No) |
| **Wellbore Radius** | $r_w$ | 0.10 | Standard 7-inch casing / 8.5-inch bit | m | 0.05 – 0.25 | Standard engineering |
| **Reservoir Drainage Radius** | $r_e$ | 150.0 | 5-acre to 10-acre well spacing | m | 50.0 – 500.0 | Synthetic (No) |
| **Mechanical Skin Factor** | $s$ | 0.0 | Hawkins (1956) formulation | dimensionless | -3.0 – +20.0 | Synthetic (No) |
| **Base Productivity Index (Cold)** | $J_c$ | 1.0 | Cold heavy oil unstimulated rate | bopd/bar | 0.05 – 10.0 | Synthetic (No) |
| **Operating Drawdown** | $\Delta p$ | 20.0 | Bottomhole pumping drawdown | bar | 2.0 – 80.0 | Synthetic (No) |
| **Water Cut** | $f_w$ | 30.0 | Early/mid cycle water cut | % | 0.0 – 98.0 | Synthetic (No) |
| **Heavy Oil Density** | $\rho_o$ | 980.0 | Extra-heavy crude (~13° API) | $\text{kg}/\text{m}^3$ | 940 – 1020 | Synthetic (No) |
| **Formation Water Density** | $\rho_w$ | 1000.0 | Standard water density | $\text{kg}/\text{m}^3$ | 990 – 1080 | Standard physical constant |
| **Oil Specific Heat Capacity** | $c_o$ | 2000.0 | Petroleum literature (Speight, 2006) | $\text{J}/(\text{kg}\cdot\text{K})$ | 1700 – 2300 | Synthetic (No) |
