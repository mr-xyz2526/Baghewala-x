from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.router import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks (DB init etc.) can go here
    yield


app = FastAPI(
    title="Baghewala‑X Backend",
    description="Analytical CSS digital twin simulator — PS SIH26120. Synthetic data only.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow frontend dev server at localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_class=JSONResponse, tags=["Health"])
async def health():
    return {"status": "ok", "project": "baghewala-x", "ps_id": "SIH26120"}


app.include_router(api_router, prefix="/api", tags=["API"])
