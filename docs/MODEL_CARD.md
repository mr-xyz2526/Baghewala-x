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

### 3.4 Sucker-Rod Pumping Mechanics: Gibbs 1D Damped-Wave Model
The sucker rod string is modeled as a continuous flexible elastic transmission line governed by the classic one-dimensional damped wave equation.

`SOURCE: Gibbs, S.G. (1963), 'Predicting the Behavior of Sucker-Rod Pumping Systems', JPT 15(7), pp. 769–778; SPE-588-PA.`
`SOURCE: Gibbs, S.G. and Neely, A.B. (1966), 'Computer Diagnosis of Down-Hole Conditions in Sucker Rod Pumping Wells', JPT 18(1), pp. 91–98; SPE-1165-PA.`

1. **Governing Wave Equation**:
   $$\frac{\partial^2 u(x, t)}{\partial t^2} = a^2 \frac{\partial^2 u(x, t)}{\partial x^2} - c \frac{\partial u(x, t)}{\partial t}$$
   where:
   - $u(x, t)$: dynamic axial displacement of rod section at depth $x$ and time $t$ [m].
   - $a = \sqrt{E / \rho}$: acoustic wave velocity in rod steel ($\approx 5,047 \text{ m/s} \approx 16,560 \text{ ft/s}$).
   - $c$: Gibbs viscous damping factor [$\text{s}^{-1}$], representing fluid drag and internal damping along the rod string.

2. **Surface Boundary Condition ($x = 0$)**:
   Imposed kinematic motion from surface beam pumping unit:
   $$u(0, t) = \frac{S}{2} (1 - \cos(\omega t))$$
   where $S$ is polished rod stroke length, $\omega = \frac{2 \pi \cdot \text{SPM}}{60}$.
   Surface polished rod load (PRL):
   $$F_{surface}(t) = W_{rod, fluid} + E A \frac{\partial u}{\partial x}(0, t) + F_{friction}(t)$$

3. **Downhole Pump Boundary Condition ($x = L$)**:
   Relates rod tension at the bottom of the string to plunger resistance force:
   $$E A \frac{\partial u}{\partial x}(L, t) = - F_{pump}(u(L, t), \dot{u}(L, t))$$
   The boundary load $F_{pump}$ is governed by traveling valve and standing valve states, fluid fillage, and gas presence.

4. **Numerical Discretization**:
   Solved via second-order explicit central finite differences under strict Courant-Friedrichs-Lewy stability:
   $$C = \frac{a \Delta t}{\Delta x} \le 0.95 < 1.0$$
   A ghost-node formulation handles the downhole force boundary. A lightweight analytical harmonic fallback is automatically engaged if numerical instability is detected.

---

## 4. Key Assumptions & Boundary Conditions
1. Uniform cylindrical heated zone around vertical wellbore.
2. Homogeneous, isotropic thermal conductivity and volumetric heat capacities.
3. Overburden and underburden possess identical semi-infinite thermal properties.
4. Single-phase Darcy inflow approximation for composite inner heated / outer cold zones.
5. Latent heat completely released inside the heated volume.
6. Zero fluid production during shut-in soak phase ($q = 0$).
7. Sucker rod transmission line assumes uniform single-taper steel rod string (multi-taper API strings represented by equivalent acoustic impedance).

---

## 5. Dynamometer Card Taxonomy & Relationship Note
In petroleum production literature, dynamometer card taxonomies vary substantially:
- **Lufkin / Nabla Classic Catalog**: Catalogs 16+ specific downhole patterns including unanchored tubing, delayed traveling valve closing, parted rods, gas lock, split barrel, bent pump barrel, fluid pound, and stuffing-box friction.
- **API Specification 11L**: Focuses on design calculation tables and polished rod load limits.
- **Gibbs & Neely (1966)**: Categorizes downhole pump operation into full pump, gas interference, fluid pound, traveling valve leak, and standing valve leak.

For **BAGHEWALA-X**, we implement **five prototype classes** representing the predominant thermal heavy-oil artificial lift states:
1. `NORMAL`: Full liquid fillage (88–100%), clean rectangular downhole card, classic surface loop.
2. `GAS_INTERFERENCE`: Free gas in pump chamber; cushioned downstroke compression curve and rod-floating risk.
3. `FLUID_POUND`: Partial liquid fillage (35–75%); traveling valve hits liquid abruptly on downstroke, launching high-frequency acoustic shock waves.
4. `TRAVELING_VALVE_LEAK`: Fluid slippage through traveling valve on upstroke; decaying load line.
5. `PUMP_OFF`: Severe reservoir depletion (< 22% fillage); collapsed card area, minimal work.

These five classes serve as our operational prototypes for system development and do **not** claim to represent the sole or exhaustive industry taxonomy.

