from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import Settings
from .api.router import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load settings on startup
    Settings.load_env()
    yield

app = FastAPI(title="Baghewala‑X Backend", version="0.1.0", lifespan=lifespan)

@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api")
