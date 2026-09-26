# Placeholder for API routes

from fastapi import APIRouter

router = APIRouter()

# Example endpoint (expand as needed)
@router.get("/ping")
async def ping():
    return {"message": "pong"}
