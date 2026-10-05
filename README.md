# BAGHEWALA-X

A synthetic-data digital twin platform for multi-well oilfield operations, designed to demonstrate simulation, optimization, economics, and risk analysis in a self-contained local environment.

- PS ID: SIH26120
- Project status: Prototype / demo-ready
- Data model: Synthetic only, no external cloud dependency

## Overview

BAGHEWALA-X is a full-stack prototype that brings together:

- a Python FastAPI backend for simulation logic and analytics,
- a React + TypeScript frontend for operational dashboards,
- synthetic well and field datasets for reproducible experiments,
- optimization and risk workflows for decision support.

The goal is to provide a compact but realistic digital twin experience for oil and gas operations without requiring paid services, cloud credentials, or GPUs.

## Key capabilities

- Multi-well operational simulation
- Production / hydraulic behavior analysis
- Optimization workflows for operating decisions
- Economic evaluation and cash-flow assessment
- Risk and anomaly visibility
- Interactive web dashboard interface
- Test-backed backend validation

## Architecture

```text
baghewala-x/
├── backend/        # FastAPI backend and domain modules
├── frontend/       # React + TypeScript UI
├── data/           # Synthetic datasets and metadata
├── docs/           # Design, assumptions, and architecture notes
├── demo/           # Example scripts and visualizations
├── Dockerfile      # Container configuration
├── requirements-dev.txt
├── pytest.ini
├── README.md
└── .gitignore
```

### Backend
The backend is built with Python and FastAPI. It contains modular services for simulation, optimization, economics, risk, ML, and twin-state orchestration.

### Frontend
The frontend is a Vite-based React application with a dashboard-style interface for operational views, optimization panels, and analysis screens.

### Data layer
Synthetic datasets support demonstration use cases without requiring field integration or calibration data.

## Tech stack

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- NumPy / SciPy / Pandas
- scikit-learn
- XGBoost
- React
- TypeScript
- Vite

## Local setup

### 1. Backend

```bash
cd d:\SIH_IMP\baghewala-x
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt -r requirements-dev.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:

- http://127.0.0.1:8000
- health endpoint: http://127.0.0.1:8000/health

### 2. Frontend

```bash
cd d:\SIH_IMP\baghewala-x\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The UI will be available at:

- http://127.0.0.1:5173

## Testing

```bash
cd d:\SIH_IMP\baghewala-x
pytest backend/tests -q
```

Verified status:

- Backend test suite passes successfully
- 40 tests passed in the current project validation run

## Build verification

Frontend production build:

```bash
cd d:\SIH_IMP\baghewala-x\frontend
npm run build
```

The project was validated successfully with a production build and backend startup checks.

## Demo usage

A demo workflow is included under the demo folder for visualization and inspection tasks. This project is designed to be easy to run locally for showcase and evaluation purposes.

## Project goals

This prototype aims to demonstrate:

- operational intelligence for oilfield management,
- data-driven digital twin decision support,
- simulation-guided optimization,
- economic and risk interpretation in a compact stack.

## License

This project is provided for educational, prototype, and evaluation use.

## Repository

- GitHub: https://github.com/mr-xyz2526/Baghewala-x

## Summary

BAGHEWALA-X is a complete prototype for a synthetic digital-twin platform covering simulation, optimization, economics, risk scoring, and operational visualization. It is functional, test-validated, and ready for local demo use.
