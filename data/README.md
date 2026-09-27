# BAGHEWALA-X DATASETS

## 1. Overview & Provenance Notice
All data located in `data/` are **purely synthetic**. They are generated via mathematical and physics-based models (Gibbs 1D damped-wave equation, Marx-Langenheim thermal balance, Boberg-Lantz inflow). **No field data or proprietary asset calibration** is claimed.

---

## 2. Synthetic Dynamometer Card Dataset (`data/synthetic/`)

### Files
- **`dynamometer_cards.npz`**: Compressed NumPy archive containing:
  - `surface_cards`: Array of shape `(N, 100, 2)` containing physical surface cards `(position_in, load_lbf)`.
  - `downhole_cards`: Array of shape `(N, 100, 2)` containing downhole pump cards `(position_in, load_lbf)`.
  - `normalized_cards`: Array of shape `(N, 100, 2)` containing min-max normalized coordinates `[0, 1] x [0, 1]` for machine-learning feature vectors.
  - `labels`: Array of shape `(N,)` containing the string class labels.
- **`dynamometer_metadata.json`**: JSON list with complete metadata per card:
  - `card_id`: Unique identifier (e.g. `SYNTH-00001`)
  - `card_class`: One of the 5 prototype classes
  - `spm`: Pumping speed (strokes per minute)
  - `surface_stroke_in`: Surface stroke length (inches)
  - `rod_length_m`: Rod string length (meters)
  - `rod_diameter_in`: Sucker rod diameter (inches)
  - `plunger_diameter_in`: Pump plunger diameter (inches)
  - `damping_factor_s_inv`: Gibbs damping factor $c$ ($\text{s}^{-1}$)
  - `pump_fillage_pct`: Liquid fillage percentage (%)
  - `peak_load_lbf`: Peak polished rod load (lbf)
  - `min_load_lbf`: Minimum polished rod load (lbf)
  - `card_area_in_lbf`: Enclosed loop work (in·lbf)
  - `power_estimate_hp`: Hydraulic horsepower (HP)
  - `torque_indicator_ft_lbf`: Peak gearbox torque estimate (ft·lbf)

---

## 3. Literature Taxonomy Relationship Note
In petroleum production literature, dynamometer card taxonomies vary substantially:
- **Lufkin / Nabla Classic Catalog**: Identifies 16+ specific downhole patterns including unanchored tubing, delayed traveling valve closing, parted rods, gas lock, split barrel, bent pump barrel, fluid pound, and stuffing-box friction.
- **API Specification 11L**: Focuses on design calculation tables and polished rod load limits.
- **Gibbs & Neely (1966)**: Categorizes downhole pump operation into full pump, gas interference, fluid pound, traveling valve leak, and standing valve leak.

For **BAGHEWALA-X**, we implement **five prototype classes** representing the predominant thermal heavy-oil artificial lift states:
1. `NORMAL`: Full fillage (88–100%), clean rectangular downhole card, standard surface loop.
2. `GAS_INTERFERENCE`: Free gas in pump chamber; cushioned downstroke compression curve and rod-floating risk.
3. `FLUID_POUND`: Partial liquid fillage (35–75%); traveling valve hits liquid abruptly on downstroke, launching acoustic shock waves.
4. `TRAVELING_VALVE_LEAK`: Fluid slippage through traveling valve on upstroke; decaying load line.
5. `PUMP_OFF`: Severe reservoir depletion (< 22% fillage); collapsed card area, minimal work.

These five classes serve as our operational prototypes for system development and do **not** claim to represent the sole or exhaustive industry taxonomy.
