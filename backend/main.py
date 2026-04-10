"""FastAPI application entry point for Agent Town backend."""
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

import backend.config as cfg
from backend.routers import health, ws, llm, agents
from backend.simulation.engine import SimulationEngine
from backend.simulation.connection_manager import ConnectionManager
from backend.simulation.map_generator import generate_town_map
from backend.simulation.world import Maze
from backend.agents.loader import load_all_agents
from backend.schemas import WSMessage

logger = logging.getLogger(__name__)

OLLAMA_PROBE_TIMEOUT = 3.0  # seconds — T-01-03: prevent startup hang


def _make_broadcast_callback(manager: ConnectionManager):
    """Create a broadcast callback that wraps engine data in a WSMessage.

    The SimulationEngine calls this callback with a raw dict containing "type"
    and other payload fields. This helper wraps it into a validated WSMessage
    and broadcasts the JSON to all connected WebSocket clients.

    Args:
        manager: The ConnectionManager to broadcast to.

    Returns:
        An async callable suitable for engine._broadcast_callback.
    """
    async def callback(data: dict) -> None:
        msg = WSMessage(
            type=data["type"],
            payload={k: v for k, v in data.items() if k != "type"},
            timestamp=time.time(),
        )
        await manager.broadcast(msg.model_dump_json())
    return callback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize simulation on startup; cancel cleanly on shutdown.

    Startup sequence (Pattern 4 from 04-RESEARCH.md):
    1. Probe Ollama availability (non-blocking — D-06)
    2. Create ConnectionManager for WebSocket multi-client broadcast
    3. Load town map config and construct Maze
    4. Load all agent configs from disk
    5. Create SimulationEngine with maze, agents, and a generated simulation_id
    6. Wire broadcast callback (engine -> ConnectionManager -> all WS clients)
    7. Store engine and manager on app.state for ws.py and health endpoints
    8. Initialize engine (resets ChromaDB, generates daily schedules)
    9. Start simulation loop as asyncio background task

    Shutdown:
    1. Cancel background simulation task
    2. Await CancelledError to let the task clean up
    """
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

    # Initialize ConnectionManager (no external dependencies)
    connection_manager = ConnectionManager()

    # Load town map and build Maze
    map_config = generate_town_map()
    maze = Maze(map_config)

    # Load all agent configs from disk (raises FileNotFoundError if missing)
    agents = load_all_agents()

    # Generate a unique simulation ID for this run
    simulation_id = str(uuid.uuid4())

    # Create SimulationEngine with maze, agents, and a unique run ID.
    # WR-03: broadcast_callback is passed as a constructor argument so the
    # dependency is explicit and callers never write to the private attribute.
    engine = SimulationEngine(
        maze=maze,
        agents=agents,
        simulation_id=simulation_id,
        broadcast_callback=_make_broadcast_callback(connection_manager),
    )

    # Expose on app.state so ws.py and other routes can access them
    app.state.engine = engine
    app.state.connection_manager = connection_manager

    # Initialize engine: reset ChromaDB, create AgentStates, generate schedules
    await engine.initialize()
    logger.info(
        "Simulation initialized: %s with %d agents",
        simulation_id,
        len(agents),
    )

    # Start the simulation loop as a background asyncio task
    sim_task = asyncio.create_task(engine.run())
    logger.info("Simulation loop started (task_id=%s)", id(sim_task))

    yield

    # Shutdown: cancel the background simulation loop cleanly (T-04-07)
    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass  # Expected — tick loop exits via CancelledError

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
app.include_router(llm.router)            # POST /api/llm/test, POST /api/config
app.include_router(agents.router)         # GET /api/agents/{name}/memories
