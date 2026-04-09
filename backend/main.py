"""FastAPI application entry point for Agent Town backend."""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

import backend.config as cfg
from backend.routers import health, ws

logger = logging.getLogger(__name__)

OLLAMA_PROBE_TIMEOUT = 3.0  # seconds — T-01-03: prevent startup hang


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: probe Ollama on startup; clean up on shutdown."""
    # Probe Ollama availability (non-blocking — D-06)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cfg.OLLAMA_BASE_URL}/",
                timeout=OLLAMA_PROBE_TIMEOUT,
            )
            if response.status_code == 200:
                cfg.state.ollama_available = True
                logger.info("Ollama detected at %s", cfg.OLLAMA_BASE_URL)
            else:
                logger.warning(
                    "Ollama probe returned status %d — running without Ollama",
                    response.status_code,
                )
    except Exception as exc:
        logger.warning(
            "Ollama not reachable at %s: %s — running without Ollama",
            cfg.OLLAMA_BASE_URL,
            type(exc).__name__,
        )

    yield

    # Shutdown cleanup (placeholder)
    logger.info("Agent Town backend shutting down")


app = FastAPI(
    title="Agent Town",
    description="Generative agents playground backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health.router)          # GET /health
app.include_router(ws.router)             # WebSocket /ws
# LLM router registered in Task 2 (backend/routers/llm.py)
