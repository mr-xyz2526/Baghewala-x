# BAGHEWALA‑X

## Project purpose

BAGHEWALA‑X is a **synthetic‑data, digital‑twin prototype** for multi‑well oil‑field operations. It demonstrates end‑to‑end simulation, optimization, economic evaluation, and risk/anomaly visualization without requiring any cloud credentials, external APIs, GPUs, or paid services.

- **PS ID**: SIH26120
- **Status**: Prototype using synthetic data only (no field‑calibrated parameters).

## Architecture overview

```
baghewala-x/
├─ backend/   # FastAPI + Python services
├─ frontend/  # React + TypeScript UI (Vite)
├─ data/      # Synthetic and processed data
├─ docs/      # Design docs, assumptions, prior art, etc.
└─ demo/      # Demo scripts / notebooks
```

* **Backend** – Python 3.11+, FastAPI, SQLite (service‑layer DB abstraction). Core modules under `backend/app/` include:
  * `twin/` – deterministic physics‑based simulator.
  * `ml/` – ML models (trained on synthetic data).
  * `optimization/` – hybrid optimizer (heuristic + gradient‑based).
  * `economics/` – cash‑flow & NPV calculations.
  * `risk/` – anomaly/risk scoring.
* **Frontend** – React + TypeScript, Vite dev server, lightweight charting (e.g., `recharts`). UI components for well‑view, optimizer UI, economic dashboards, risk panels, and run‑history.
* **Data** – `synthetic/` (generated well logs, production curves) and `processed/` (derived features).

## Local development

```bash
# Clone repository (already in workspace)
cd baghewala-x

# Backend – create virtual environment & install deps
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r requirements-dev.txt
uvicorn backend/app/main:app --reload

# Frontend – install Node deps & run dev server
cd frontend
npm ci
npm run dev   # Vite dev server at http://localhost:5173
```

## Testing

```bash
# Backend tests (pytest)
pytest backend/tests

# Frontend unit tests (if added)
# npm test
```

## Demo

A simple demo script is provided under `demo/`. Run it after the backend is up:

```bash
python demo/run_demo.py
```

## License

MIT License – feel free to adapt and extend.
