# MODEL CARD: Thermal Recovery & CSS Cycle Simulator

## 1. Overview & Purpose
This model implements an analytical digital twin for **Cyclic Steam Stimulation (CSS)** under Problem Statement **SIH26120** (BAGHEWALA-X). It models multi-phase steam injection, shut-in soak, and stimulated heavy oil production using two rigorous analytical physics layers:

- **Layer A**: Marx–Langenheim-style thermal-balance and heated-zone expansion model during steam injection.
- **Layer B**: Boberg–Lantz-style post-injection vertical/radial conductive heat loss, convective fluid cooling, and composite Hawkins-type stimulated inflow performance during soak and production.
- **Viscosity Layer**: Andrade/Arrhenius temperature-dependent viscosity relationship with an exposed sensitivity parameter.

> **Status Notice**: All default parameters are synthetic literature analogues for extra-heavy oil/bitumen reservoirs. **No claim of field calibration** is made for the Baghewala field or any specific asset.

---

## 2. Primary Citations & Scholarly References

1. **Marx, J.W. and Langenheim, R.H. (1961)**  
   *Reservoir Heating by Hot Fluid Injection*  
   Transactions of the AIME, 222, pp. 312–320.  
   `SOURCE: Marx and Langenheim (1961), Eqs. 1, 5, 6, 7, 8`

2. **Boberg, T.C. and Lantz, R.B. (1966)**  
   *Calculation of the Production Rate of a Chronically Stimulated Well*  
   Journal of Petroleum Technology, 18(12), pp. 1613–1623; SPE-1578-PA.  
   `SOURCE: Boberg and Lantz (1966), Eqs. 1, 4, 5, 6, 7, 8`

3. **Hawkins, M.F. (1956)**  
   *A Note on the Skin Effect*  
   Transactions of the AIME, 207, pp. 356–357.  
   `SOURCE: Hawkins (1956), Eq. 4`

4. **Andrade, E.N. da C. (1930)**  
   *The Viscosity of Liquids*  
   Nature, 125, pp. 309–310.  
   `SOURCE: Andrade (1930)`

5. **Prats, M. (1982)**  
   *Thermal Recovery*  
   SPE Monograph Series, Vol. 7, Society of Petroleum Engineers, Richardson, TX.

6. **Butler, R.M. (1991)**  
   *Thermal Recovery of Oil and Bitumen*  
   Prentice Hall, Englewood Cliffs, NJ, Chapter 2 (Viscosity & Thermal Properties).

---

## 3. Mathematical Formulations & Notation

### 3.1 Layer A: Marx–Langenheim Injection Model
For constant-rate mass injection $\dot{m}_{st}$ (kg/s) of saturated steam at sandface temperature $T_{st}$ and vapor quality $f_s$:

1. **Heat Injection Rate ($H_0$)**:
   $$\Delta h = c_w (T_{st} - T_R) + f_s L_v(T_{st})$$
   $$H_0 = \dot{m}_{st} \cdot \Delta h \quad [\text{W}]$$
   *Latent heat correlation:* $L_v(T_{st}) \approx 10^3 \cdot (2500.8 - 2.36 \cdot T_{st})$ J/kg.

2. **Dimensionless Time ($t_D$)**:
   $$t_D = \frac{4 k_{ob} M_{ob} t}{M_R^2 h_{pay}^2} = \frac{4 \alpha_{ob} M_{ob}^2 t}{M_R^2 h_{pay}^2}$$
   where $M_R = (\rho C)_R$ is reservoir volumetric heat capacity, $M_{ob} = (\rho C)_{ob}$ is overburden heat capacity, $k_{ob}$ is thermal conductivity, $\alpha_{ob} = k_{ob} / M_{ob}$, and $h_{pay}$ is pay thickness.

3. **Auxiliary Function ($F_1(t_D)$)**:
   $$F_1(t_D) = e^{t_D} \operatorname{erfc}(\sqrt{t_D}) + 2 \sqrt{\frac{t_D}{\pi}} - 1 = \operatorname{erfcx}(\sqrt{t_D}) + 2 \sqrt{\frac{t_D}{\pi}} - 1$$
   *(Evaluated stably using Faddeeva / scaled complementary error function `scipy.special.erfcx` to prevent floating-point overflow).*

4. **Heated Area & Radius**:
   $$A(t) = \frac{H_0 M_R h_{pay}}{4 k_{ob} M_{ob} (T_{st} - T_R)} F_1(t_D) \quad [\text{m}^2]$$
   $$r_h(t) = \sqrt{\frac{A(t)}{\pi}} \quad [\text{m}]$$

5. **Thermal Efficiency Indicator ($E_{hs}$)**:
   $$E_{hs}(t) = \frac{F_1(t_D)}{t_D}$$

---

### 3.2 Layer B: Boberg–Lantz Post-Injection Cooling & Inflow
During shut-in soak and active production, the heated volume loses heat vertically into over/underburden, radially into cold formation, and convectively via produced fluids.

1. **Vertical Conduction Cooling ($\bar{V}_z$)**:
   $$\tau_z = \frac{\alpha_{ob} \Delta t}{h_{pay}^2}$$
   $$\bar{V}_z(\Delta t) = \operatorname{erf}\left(\frac{1}{2\sqrt{\tau_z}}\right) - \frac{2\sqrt{\tau_z}}{\sqrt{\pi}} \left[ 1 - \exp\left(-\frac{1}{4\tau_z}\right) \right]$$

2. **Radial Conduction Cooling ($\bar{V}_r$)**:
   $$\tau_r = \frac{\alpha_R \Delta t}{r_h^2}$$
   $$\bar{V}_r(\Delta t) = \frac{1}{1 + 2 \sqrt{\tau_r / \pi}}$$

3. **Convective Cooling by Produced Fluids ($F_{conv}$)**:
   $$\dot{Q}_{prod} = \left[ q_o \rho_o c_o + q_w \rho_w c_w \right] (\bar{T} - T_R)$$
   $$F_{conv}(\Delta t) = \exp\left( - \int_0^{\Delta t_{prod}} \frac{q_o \rho_o c_o + q_w \rho_w c_w}{C_{heated}} d\tau \right)$$
   where $C_{heated} = \pi r_h^2 h_{pay} M_R$ is total heat capacity of the steam-invaded cylinder.

4. **Average Heated Zone Temperature**:
   $$\bar{T}(\Delta t) = T_R + (T_{st} - T_R) \cdot \left[ \bar{V}_z(\Delta t) \cdot \bar{V}_r(\Delta t) \cdot F_{conv}(\Delta t) \right]$$

5. **Stimulated Well Inflow Performance (Hawkins composite radial flow)**:
   $$\frac{J(t)}{J_c} = \frac{\ln(r_e / r_w) + s}{\frac{\mu_h(t)}{\mu_c} \ln(r_h / r_w) + \ln(r_e / r_h) + s \frac{\mu_h(t)}{\mu_c}}$$
   $$q_o(t) = J_c \cdot \frac{J(t)}{J_c} \cdot \Delta p_{drawdown}$$

---

### 3.3 Viscosity Model
Modified Andrade/Arrhenius formulation with explicit sensitivity scaling:
$$\mu(T) = \mu_{ref} \cdot \exp\left( B \cdot s_{sens} \cdot \left[ \frac{1}{T(^\circ\text{C}) + 273.15} - \frac{1}{T_{ref}(^\circ\text{C}) + 273.15} \right] \right)$$
- $\mu_{ref} = 10,000$ cP at $T_{ref} = 50.0^\circ\text{C}$ (synthetic baseline).
- $B = 4500.0$ K (apparent activation energy constant).
- $s_{sens}$: Dimensionless multiplier (default $1.0$) for parametric sensitivity analysis in the absence of laboratory crude PVT data.

---

## 4. Key Assumptions & Boundary Conditions
1. Uniform cylindrical heated zone around vertical wellbore.
2. Homogeneous, isotropic thermal conductivity and volumetric heat capacities.
3. Overburden and underburden possess identical semi-infinite thermal properties.
4. Single-phase Darcy inflow approximation for composite inner heated / outer cold zones.
5. Latent heat completely released inside the heated volume.
6. Zero fluid production during shut-in soak phase ($q = 0$).
