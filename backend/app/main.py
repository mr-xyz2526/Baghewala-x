import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import Settings
from .api import router as api_router

app = FastAPI(title="Baghewala‑X Backend", version="0.1.0")

@app.on_event("startup")
async def startup_event():
    # Load settings (e.g., from .env) – placeholder
    Settings.load_env()

@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api")
