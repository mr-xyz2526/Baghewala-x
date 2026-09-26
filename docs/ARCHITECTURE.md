# Architecture Overview

The **BAGHEWALA‑X** system is split into three logical layers:

1. **Backend (FastAPI)** – Core simulation, ML, optimization and economics services.
   * `twin/` – deterministic physics‑based well model.
   * `ml/` – scikit‑learn/XGBoost models trained on synthetic data.
   * `optimization/` – hybrid optimizer (grid + gradient).
   * `economics/` – cash‑flow, NPV, IRR calculations.
   * `risk/` – simple anomaly scoring.
   * All services expose REST endpoints under `/api/…`.
2. **Frontend (React + Vite)** – UI for visualizing the digital twin.
   * Components for well view, optimizer UI, economic dashboard, risk panel, and run‑history.
   * Light charting with `recharts` (or `plotly.js` if preferred).
3. **Data Layer** – SQLite for persistence, accessed via a service‑layer interface (`backend/app/services/database.py`).

```
baghewala-x/
├─ backend/   # Python services
│  └─ app/
│     ├─ api/          # FastAPI routers
│     ├─ services/     # DB, business‑logic services
│     └─ ...
├─ frontend/  # React UI
│  └─ src/
│     ├─ components/
│     ├─ pages/
│     └─ ...
├─ data/      # Synthetic data assets
├─ docs/      # Design docs
└─ Dockerfile # Container build
```

The architecture is deliberately modular so that each layer can be swapped (e.g., replace SQLite with PostgreSQL) without affecting the others.
