"""Health check endpoint for Agent Town backend."""
from fastapi import APIRouter
import backend.config as cfg

router = APIRouter()


@router.get("/api/health")
async def health_check():
    """Returns application health status and provider availability."""
    return {
        "status": "ok",
        "provider_status": {
            "ollama": cfg.state.ollama_available,
            "openrouter": cfg.state.openrouter_configured,
        },
    }
