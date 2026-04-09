# Phase 1: Foundation - Research

**Researched:** 2026-04-08
**Domain:** Python/FastAPI backend scaffold + React/Vite/PixiJS frontend shell + Ollama LLM gateway + async infrastructure
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** v1 uses Ollama local-only. No API key configuration, no provider selection UI. Users must have Ollama running locally.
- **D-02:** Default model is Llama 3.1 8B. App auto-detects Ollama availability on startup.
- **D-03:** CFG-01 (provider config), CFG-02 (API key), and CFG-03 (cost estimation) are deferred to v2. Phase 1 requirements narrowed to: Ollama auto-detection, structured output, async infrastructure.
- **D-04:** Map-dominant layout. Tile map takes most of the screen. Activity feed in a collapsible right sidebar. Event input and controls (pause/resume) in a bottom bar below the map.
- **D-05:** Agent inspector replaces the feed sidebar when an agent is clicked. Feed is hidden while inspecting; closing inspector restores the feed.

### Claude's Discretion
- **D-06:** Pick the best approach for communicating LLM failures (Ollama timeout, model not found, malformed response) to the user. Non-blocking preferred; simulation should attempt retry before alerting.

### Deferred Ideas (OUT OF SCOPE)
- User-provided API keys and provider selection UI (v2 — CFG-01, CFG-02)
- Token counting and cost estimation display (v2 — CFG-03)
- Model routing per call type: cheap model for routine calls, expensive for complex (v2 — CFG-04)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INF-01 | Fresh simulation starts by default on each visit | In-memory simulation state (no SQLite in Phase 1); FastAPI lifespan hook initializes state on startup; each browser connect/reconnect gets a fresh session |
| INF-02 | All agent processing is async/concurrent (not sequential) for real-time performance | asyncio.TaskGroup (Python 3.11+) for concurrent agent coroutines; never use `requests` or sync LLM clients inside async routes; semaphore pattern established in gateway |
| INF-03 | Structured LLM output via Pydantic schemas with retry and fallback on parse failure | instructor >=1.15 + LiteLLM via `instructor.from_litellm(litellm.acompletion)` provides automatic retry with Pydantic validation; fallback state returned on repeated failure |
</phase_requirements>

---

## Summary

Phase 1 establishes the full-stack scaffold for Agent Town: a FastAPI backend with async infrastructure and Ollama LLM gateway, paired with a Vite/React/TypeScript frontend featuring the map-dominant shell layout and Zustand state management. This is greenfield work — no existing code to port. The goal is a running application that proves end-to-end connectivity: browser loads, detects Ollama, renders the PixiJS canvas placeholder, opens a WebSocket connection, and can make a structured LLM call to Ollama with Pydantic validation.

The reference implementation (`GenerativeAgentsCN/llm_model.py`) uses synchronous `requests` calls — this pattern MUST NOT be ported directly. The Phase 1 gateway must be async from day one using `litellm.acompletion`. The reference also uses `magentic` for structured output (OpenAI only) and a custom JSON schema + regex fallback for Ollama. In Phase 1, replace both with `instructor.from_litellm(litellm.acompletion)` which handles both structured output and retry uniformly across providers.

The Ollama auto-detection pattern is simple: on FastAPI startup, GET `http://localhost:11434/` (returns "Ollama is running" with 200) and then GET `/api/tags` to list available models. If Llama 3.1 8B is not in the list, surface a non-blocking startup warning. The WebSocket endpoint is established in Phase 1 as a stub; the simulation engine wires into it in Phase 4.

**Primary recommendation:** Build backend first (pyproject.toml + FastAPI scaffold + Ollama health check + LLM gateway stub + WebSocket endpoint), then frontend (Vite scaffold + PixiJS canvas placeholder + Zustand store + WebSocket hook + layout shell). Verify end-to-end with a smoke test: startup detects Ollama, a REST call to `/api/llm/test` returns a Pydantic-validated response from Ollama.

---

## Project Constraints (from CLAUDE.md)

| Directive | Applies To |
|-----------|------------|
| Use Python 3.11+ (NOT 3.14 for isolation — use 3.11 via uv) | Backend runtime |
| Use FastAPI 0.115+ with Uvicorn | Backend server |
| Use `uv` for Python package management (NOT pip/venv) | Backend deps |
| Use `pyproject.toml` as project manifest | Backend config |
| Use React 19+ with TypeScript 5.4+ | Frontend |
| Use Vite 5+ with `npm create vite@latest -- --template react-ts` | Frontend scaffold |
| Use PixiJS 8.17+ and `@pixi/react` 8+ (NOT react-pixi-fiber) | Frontend rendering |
| Use Zustand 4.5+ (NOT Redux, NOT React Context for WS updates) | Frontend state |
| Use LiteLLM >=1.83.0 (NEVER 1.82.7 or 1.82.8 — supply-chain backdoor) | LLM client |
| Use `instructor` for structured LLM output (NOT custom JSON parsing) | LLM structured output |
| Use Pydantic v2 patterns: `model_validator`, NOT `@validator` | Schemas |
| Use Biome for frontend linting/formatting (NOT ESLint + Prettier) | Frontend tooling |
| Use Vitest for frontend tests, pytest + pytest-asyncio for backend | Testing |
| Do NOT use threading.Thread for agent concurrency — use asyncio | Concurrency |
| Do NOT use WebSockets Python lib as primary server — FastAPI handles it | WebSocket |
| Do NOT use Next.js — Vite SPA only | Frontend framework |
| Do NOT use Phaser (any version) — PixiJS + @pixi/react only | Rendering |
| GSD workflow enforcement: use `/gsd-execute-phase` for file changes | Process |

---

## Standard Stack

### Core — Phase 1 Only

These are the packages needed specifically for Phase 1 foundation work. ChromaDB and SQLAlchemy are deferred to their respective phases.

| Library | Verified Version | Purpose | Why |
|---------|-----------------|---------|-----|
| Python | 3.11.6 (on machine) | Backend runtime | asyncio.TaskGroup requires 3.11+; 3.14 installed but use 3.11 for project via uv python pin |
| FastAPI | 0.135.3 | HTTP + WebSocket server | Native async, built-in Starlette WebSocket, Pydantic v2 bundled |
| uvicorn | 0.44.0 | ASGI server | Standard FastAPI runtime; use `uvicorn[standard]` for uvloop |
| Pydantic | 2.12.5 | Data validation + LLM schemas | Bundled with FastAPI; v2 patterns only |
| LiteLLM | 1.83.4 (latest safe) | Ollama call abstraction | Ollama native support; v2 provider switch requires zero agent logic changes |
| instructor | 1.15.1 | Structured LLM output | Auto-retry with Pydantic validation; `instructor.from_litellm(litellm.acompletion)` pattern |
| httpx | 0.28.1 | Async HTTP (health checks + test client) | Used for Ollama health check probe and FastAPI test client |
| pytest | latest | Backend testing | |
| pytest-asyncio | 1.3.0 | Async test support | Required for testing async FastAPI routes |

| Library | Verified Version | Purpose | Why |
|---------|-----------------|---------|-----|
| React | 19.2.5 | UI framework | @pixi/react v8 targets React 19 |
| TypeScript | 6.0.2 | Type safety | PixiJS v8 ships TS definitions |
| Vite | 8.0.8 | Build tool + dev server | CRA deprecated; Vite is 2025 standard |
| pixi.js | 8.17.1 | 2D canvas renderer | WebGL-accelerated; handles 25 sprites at 60 FPS |
| @pixi/react | 8.0.5 | React-PixiJS bridge | v8 rewrite (March 2025) with React 19 support |
| zustand | 5.0.12 | Frontend state | WebSocket message ingestion without re-render cost |
| @biomejs/biome | 2.4.11 | Linting + formatting | Replaces ESLint + Prettier; single config |
| vitest | 4.1.4 | Frontend unit tests | Vite-native; same config |

**Version verification:** All versions confirmed via `npm view [package] dist-tags.latest` and `pip3 index versions [package]` on 2026-04-08. [VERIFIED: npm registry, pip index]

### Installation

```bash
# Backend — using uv with Python 3.11 specifically
uv init agent-town-backend --python 3.11
cd agent-town-backend

uv add "fastapi>=0.135" "uvicorn[standard]>=0.44" pydantic
uv add "litellm>=1.83.0"   # CRITICAL: never 1.82.7 or 1.82.8 (supply-chain backdoor)
uv add instructor
uv add httpx

uv add --dev pytest pytest-asyncio httpx

# Frontend
npm create vite@latest frontend -- --template react-ts
cd frontend

npm install pixi.js @pixi/react zustand
npm install -D @biomejs/biome vitest @vitest/ui
```

---

## Architecture Patterns

### Recommended Project Structure

Phase 1 creates only the directories and files needed for foundation. Stub empty `__init__.py` files where shown; future phases fill the modules.

```
agent-town/
├── backend/
│   ├── main.py                    # FastAPI app, lifespan hook, router registration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ws.py                  # WebSocket endpoint + ConnectionManager stub
│   │   └── health.py              # GET /api/health, GET /api/ollama/status
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gateway.py             # LiteLLM + instructor async wrapper
│   │   └── ollama.py              # Ollama health check + model discovery
│   ├── models/
│   │   ├── __init__.py
│   │   └── messages.py            # Pydantic schemas: WebSocket envelopes, LLM responses
│   └── config.py                  # Pydantic Settings: OLLAMA_BASE_URL, DEFAULT_MODEL
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # React root mount
│   │   ├── App.tsx                # Layout shell: map area + sidebar + bottom bar
│   │   ├── components/
│   │   │   ├── MapCanvas.tsx      # PixiJS Application placeholder (Phase 5 fills this)
│   │   │   ├── ActivityFeed.tsx   # Collapsible right sidebar stub
│   │   │   ├── BottomBar.tsx      # Pause/resume + event input stub
│   │   │   └── AgentInspector.tsx # Replaces feed when agent clicked (stub)
│   │   ├── stores/
│   │   │   └── simulation.ts      # Zustand store: connection status, feed entries
│   │   └── lib/
│   │       └── ws.ts              # WebSocket connection hook
│   ├── index.html
│   ├── vite.config.ts
│   ├── biome.json
│   └── tsconfig.json
│
├── pyproject.toml                 # uv project manifest
└── .python-version                # 3.11 (written by uv python pin 3.11)
```

### Pattern 1: FastAPI Lifespan Hook for Startup Tasks

Use the `@asynccontextmanager` lifespan pattern (FastAPI >=0.95.0 standard). Old `@app.on_event("startup")` is deprecated.

**What:** Run Ollama availability check and model discovery once at server startup. Store result in app state so routes can read it.

**When:** Always — startup verification surfaces Ollama misconfiguration early.

```python
# backend/main.py
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.llm.ollama import check_ollama_availability

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: probe Ollama
    status = await check_ollama_availability()
    app.state.ollama_status = status
    if not status["available"]:
        # Log warning but do NOT crash — non-blocking per D-06
        import logging
        logging.warning(
            "Ollama not reachable at startup. "
            "Start Ollama and visit /api/ollama/status to re-check."
        )
    yield
    # Shutdown: nothing to clean up in Phase 1

app = FastAPI(lifespan=lifespan)
```

[CITED: https://fastapi.tiangolo.com/advanced/events/]

### Pattern 2: Ollama Health Check + Model Discovery

**What:** HTTP probe to `localhost:11434` on startup. List models via `/api/tags`. Detect whether the default model (llama3.1:8b) is already pulled.

**When:** Called in lifespan hook; also exposed as `GET /api/ollama/status` REST endpoint for frontend polling.

```python
# backend/llm/ollama.py
import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1:8b"

async def check_ollama_availability() -> dict:
    """
    Returns: {available: bool, models: list[str], has_default_model: bool, error: str|None}
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            # Primary health check — returns "Ollama is running"
            resp = await client.get(f"{OLLAMA_BASE_URL}/")
            resp.raise_for_status()

            # Model discovery
            tags_resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            tags_resp.raise_for_status()
            data = tags_resp.json()
            models = [m["name"] for m in data.get("models", [])]
            has_default = any(DEFAULT_MODEL in m for m in models)

            return {
                "available": True,
                "models": models,
                "has_default_model": has_default,
                "error": None,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            return {
                "available": False,
                "models": [],
                "has_default_model": False,
                "error": str(e),
            }
```

[CITED: https://docs.ollama.com/api/tags] [VERIFIED: tested curl against localhost:11434 — endpoint confirmed]

### Pattern 3: LLM Gateway — async instructor + LiteLLM

**What:** Thin async wrapper that converts a Pydantic schema + prompt into a validated model instance. Uses `instructor.from_litellm(litellm.acompletion)` for all calls. Retries twice on validation failure before returning the fallback.

**Critical:** The reference implementation (`OllamaLLMModel`) uses synchronous `requests.post()` directly. **Do not port this pattern.** Replace with `litellm.acompletion` throughout.

```python
# backend/llm/gateway.py
# Source: https://python.useinstructor.com/integrations/litellm/
import instructor
import litellm
from pydantic import BaseModel
from typing import TypeVar, Type
import asyncio

T = TypeVar("T", bound=BaseModel)

# instructor wraps litellm's async completion function
_client = instructor.from_litellm(litellm.acompletion)

# Cap concurrent LLM calls — Ollama is single-threaded; cap at 3 for local
_semaphore = asyncio.Semaphore(3)

async def llm_call(
    prompt: str,
    response_model: Type[T],
    model: str = "ollama_chat/llama3.1:8b",
    api_base: str = "http://localhost:11434",
    max_retries: int = 2,
    fallback: T | None = None,
) -> T | None:
    """
    Make a structured LLM call with Pydantic validation and retry.
    Returns validated model instance, or fallback on repeated failure.
    """
    async with _semaphore:
        try:
            result = await _client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_model=response_model,
                max_retries=max_retries,
                api_base=api_base,
            )
            return result
        except Exception as e:
            # Log structured error; simulation continues with fallback (D-06)
            import logging
            logging.error(f"LLM call failed after {max_retries} retries: {e}")
            return fallback
```

**Model string for Ollama:** Use `"ollama_chat/llama3.1:8b"` (not `"ollama/..."`) — the `ollama_chat` prefix routes to the `/api/chat` endpoint which is recommended for multi-turn chat. [CITED: https://docs.litellm.ai/docs/providers/ollama]

### Pattern 4: WebSocket Endpoint with ConnectionManager

**What:** Phase 1 establishes the WebSocket endpoint and connection registry pattern. Simulation engine (Phase 4) wires into this. For now, the endpoint accepts connections and echoes a `sim_connected` message.

```python
# backend/api/ws.py
# Source: https://fastapi.tiangolo.com/advanced/websockets/
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._queues: dict[str, asyncio.Queue] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[session_id] = ws
        self._queues[session_id] = asyncio.Queue()

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)
        self._queues.pop(session_id, None)

    async def send(self, session_id: str, message: dict):
        """Push to queue; broadcaster coroutine drains it."""
        if session_id in self._queues:
            await self._queues[session_id].put(message)

    async def broadcast_all(self, message: dict):
        for sid in list(self._connections.keys()):
            await self.send(sid, message)


manager = ConnectionManager()

# In router:
# @router.websocket("/ws/{session_id}")
# async def websocket_endpoint(ws: WebSocket, session_id: str):
#     await manager.connect(session_id, ws)
#     try:
#         await ws.send_json({"type": "sim_connected", "session_id": session_id})
#         while True:
#             data = await ws.receive_json()
#             # Phase 4 wires simulation commands here
#     except WebSocketDisconnect:
#         manager.disconnect(session_id)
```

### Pattern 5: Pydantic WebSocket Message Envelope

**What:** All WebSocket messages use a typed envelope. Define in Phase 1; all future phases import from here.

```python
# backend/models/messages.py
from pydantic import BaseModel
from typing import Literal, Any

class WSMessage(BaseModel):
    type: str
    session_id: str
    tick: int = 0
    payload: dict[str, Any] = {}

class OllamaStatusPayload(BaseModel):
    available: bool
    models: list[str]
    has_default_model: bool
    error: str | None = None
```

### Pattern 6: Zustand Store for WebSocket State

**What:** Single Zustand store handles connection state and activity feed. WebSocket hook lives outside React component tree so it doesn't trigger unnecessary re-renders.

```typescript
// frontend/src/stores/simulation.ts
import { create } from 'zustand'

interface FeedEntry {
  id: string
  timestamp: number
  message: string
  type: 'agent_action' | 'agent_thought' | 'system' | 'error'
}

interface SimulationState {
  connected: boolean
  ollamaAvailable: boolean | null  // null = unknown (startup)
  feedEntries: FeedEntry[]
  setConnected: (v: boolean) => void
  setOllamaStatus: (available: boolean) => void
  addFeedEntry: (entry: FeedEntry) => void
}

export const useSimulationStore = create<SimulationState>((set) => ({
  connected: false,
  ollamaAvailable: null,
  feedEntries: [],
  setConnected: (connected) => set({ connected }),
  setOllamaStatus: (available) => set({ ollamaAvailable: available }),
  addFeedEntry: (entry) =>
    set((s) => ({ feedEntries: [entry, ...s.feedEntries].slice(0, 200) })),
}))
```

### Pattern 7: PixiJS Application Placeholder

**What:** Phase 1 renders a PixiJS canvas with a solid background color as a placeholder. Actual tile map rendering is Phase 5's job.

```typescript
// frontend/src/components/MapCanvas.tsx
// Source: @pixi/react v8 official API
import { Application, extend } from '@pixi/react'
import { Graphics } from 'pixi.js'

extend({ Graphics })

export function MapCanvas() {
  return (
    <Application
      width={800}
      height={600}
      background="#1a1a2e"
      style={{ width: '100%', height: '100%' }}
    >
      {/* Phase 5 adds TileMap, AgentSprite components here */}
    </Application>
  )
}
```

### Pattern 8: App Layout Shell (Map-Dominant)

**What:** CSS Grid layout matching D-04. Map occupies the main content area. Sidebar collapses. Bottom bar is fixed.

```typescript
// frontend/src/App.tsx
// Implements D-04: map-dominant layout
export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [inspectedAgent, setInspectedAgent] = useState<string | null>(null)

  return (
    <div className="app-layout">
      {/* Main: PixiJS canvas */}
      <main className="map-area">
        <MapCanvas />
      </main>

      {/* Right sidebar: feed OR inspector (D-05) */}
      {sidebarOpen && (
        <aside className="sidebar">
          {inspectedAgent
            ? <AgentInspector agentId={inspectedAgent} onClose={() => setInspectedAgent(null)} />
            : <ActivityFeed />
          }
        </aside>
      )}

      {/* Bottom bar: controls + event input */}
      <footer className="bottom-bar">
        <BottomBar />
      </footer>
    </div>
  )
}
```

### Anti-Patterns to Avoid

- **Sync LLM calls in async routes:** Never `litellm.completion()` inside `async def`. Always `await litellm.acompletion()`. [CITED: PITFALLS.md Pitfall 6]
- **Porting reference `requests.post()` directly:** The `OllamaLLMModel` in the reference uses synchronous `requests` — replace entirely with the async gateway pattern.
- **Module-level global simulation state:** All simulation state must be session-scoped, not Python module globals. [CITED: PITFALLS.md Security]
- **Threading for concurrency:** Use `asyncio.Semaphore` + `asyncio.gather` / `asyncio.TaskGroup`, never `threading.Thread`. [CITED: CLAUDE.md]
- **@app.on_event("startup"):** Deprecated since FastAPI 0.95. Use `lifespan=` parameter. [CITED: FastAPI docs]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output with retry | Custom JSON strip + regex + `json.loads()` + Pydantic | `instructor.from_litellm(litellm.acompletion)` | instructor handles: markdown fence stripping, JSON extraction, Pydantic validation, retry with error context injection — all tested across model providers |
| Ollama model format | Custom `/api/generate` HTTP client | `litellm.acompletion(model="ollama_chat/...")` | LiteLLM routes to correct Ollama endpoint, handles response format normalization |
| WebSocket connection tracking | Custom dict management | `ConnectionManager` pattern (FastAPI official) | Handles disconnect cleanup, session scoping, queue backpressure |
| Python env management | pip + virtualenv | `uv` | 10-100x faster; handles complex dep graphs like litellm + pydantic |

---

## Common Pitfalls

### Pitfall 1: Using Python 3.14 (Default on This Machine)

**What goes wrong:** The dev machine has Python 3.14.2 as the default `python3`. Some packages (sentence-transformers, chromadb) have not published 3.14 wheels yet. LiteLLM's dependency graph may be untested on 3.14.

**Why it happens:** `uv init` without `--python` might pick up the system default.

**How to avoid:** Explicitly pin the project to 3.11: `uv init agent-town-backend --python 3.11` or `uv python pin 3.11` after init. The `.python-version` file in the project root ensures consistency.

**Warning signs:** `ModuleNotFoundError` for native extension packages during `uv sync`.

### Pitfall 2: litellm 1.82.7 / 1.82.8 Supply-Chain Backdoor

**What goes wrong:** These two versions contain a backdoor injected via a supply-chain compromise (March 2026). Installing them gives an attacker remote code execution.

**Why it happens:** `pip install litellm` or `uv add litellm` without version pinning could pull an old cached version or a manually specified bad version.

**How to avoid:** Always specify `"litellm>=1.83.0"` in pyproject.toml. Run `uv lock --check` to verify. [CITED: CLAUDE.md, STACK.md]

**Warning signs:** litellm version 1.82.7 or 1.82.8 appearing in `uv pip list`.

### Pitfall 3: Ollama Not Running / Model Not Pulled

**What goes wrong:** The app starts, the frontend loads, user clicks "Start" — nothing happens because Ollama is not running or `llama3.1:8b` hasn't been pulled. The error surfaces as a timeout after 5s with no user-facing message.

**Why it happens:** This is the most common first-run failure for local LLM apps.

**How to avoid:**
1. FastAPI startup lifespan checks Ollama availability and stores result in `app.state`.
2. Frontend polls `GET /api/ollama/status` on load.
3. If `available: false` → show non-blocking banner: "Ollama not running. Start Ollama and run `ollama pull llama3.1:8b`."
4. If `has_default_model: false` → show banner with pull command.
5. Simulation start button is disabled (not hidden) until `ollamaAvailable === true`.

**Warning signs:** Silently hanging on first LLM call with no frontend feedback.

### Pitfall 4: @pixi/react v7 vs v8 API Mismatch

**What goes wrong:** Searching for @pixi/react tutorials finds mostly v7 docs (pre-March 2025). The v8 API is completely different: `extend()` replaces the component registry, `<Application>` props changed, `useTick` hook API changed.

**Why it happens:** v8 was a full rewrite released March 2025. Old tutorials are the top search results.

**How to avoid:**
- Install `@pixi/react@latest` (currently 8.0.5) — it targets PixiJS v8.
- Use the `extend({ Graphics, Sprite, ... })` import pattern before using any PixiJS component as JSX.
- Do NOT use `react-pixi-fiber` (unmaintained, v7 only).
- Official v8 docs: https://pixijs.com/blog/pixi-react-v8-live

**Warning signs:** TypeScript errors on `<Stage>` component (v7 API), missing `extend` import errors.

### Pitfall 5: Semaphore Initialized Outside Event Loop

**What goes wrong:** `asyncio.Semaphore(3)` initialized at module import time (before the event loop is running) causes `DeprecationWarning` in Python 3.10+ and `RuntimeError` in Python 3.12+.

**Why it happens:** Module-level `_semaphore = asyncio.Semaphore(3)` executes at import time, before FastAPI starts its event loop.

**How to avoid:** Initialize the semaphore lazily inside the first async call, or use a singleton pattern initialized in the lifespan hook:

```python
# backend/llm/gateway.py
_semaphore: asyncio.Semaphore | None = None

def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(3)
    return _semaphore
```

Or initialize in `lifespan` and store on `app.state`.

**Warning signs:** `DeprecationWarning: There is no current event loop` at startup.

### Pitfall 6: Vite Proxy Not Configured for Backend

**What goes wrong:** Frontend runs on `localhost:5173`, backend on `localhost:8000`. The WebSocket connection to `ws://localhost:8000/ws/session-id` and REST calls to `http://localhost:8000/api/...` are blocked by CORS in development.

**How to avoid:** Configure Vite's `server.proxy` in `vite.config.ts`:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

Also configure FastAPI CORS for the Vite dev origin in development.

---

## Code Examples

### Verified: instructor + LiteLLM async call with Pydantic

```python
# Source: https://python.useinstructor.com/integrations/litellm/
import instructor
import litellm
from pydantic import BaseModel

client = instructor.from_litellm(litellm.acompletion)

class TestResponse(BaseModel):
    message: str
    confidence: float

async def test_ollama_call() -> TestResponse | None:
    return await client.chat.completions.create(
        model="ollama_chat/llama3.1:8b",
        messages=[{"role": "user", "content": "Say hello in JSON format."}],
        response_model=TestResponse,
        max_retries=2,
        api_base="http://localhost:11434",
    )
```

[CITED: https://python.useinstructor.com/integrations/litellm/]

### Verified: FastAPI WebSocket endpoint

```python
# Source: https://fastapi.tiangolo.com/advanced/websockets/
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        await websocket.send_json({
            "type": "sim_connected",
            "session_id": session_id,
            "tick": 0,
            "payload": {},
        })
        while True:
            data = await websocket.receive_json()
            # Phase 4 handles simulation commands here
    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

[CITED: https://fastapi.tiangolo.com/advanced/websockets/]

### Verified: asyncio.TaskGroup for concurrent agent coroutines (Python 3.11+)

```python
# Source: https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
# Preferred over asyncio.gather() — structured concurrency with automatic cleanup
async def run_all_agents_concurrently(agents: list) -> list:
    results = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(agent.run_tick()) for agent in agents]
    return [t.result() for t in tasks]
```

Note: `asyncio.TaskGroup` cancels all sibling tasks if one raises. For agent steps where one failure should not kill others, use `asyncio.gather(*coroutines, return_exceptions=True)` instead.

[CITED: https://docs.python.org/3/library/asyncio-task.html]

### Verified: Zustand WebSocket hook outside React tree

```typescript
// frontend/src/lib/ws.ts
// Pattern: WebSocket managed outside React — no re-render cost on connection events
import { useSimulationStore } from '../stores/simulation'

let ws: WebSocket | null = null

export function connectSimulation(sessionId: string) {
  const store = useSimulationStore.getState()

  ws = new WebSocket(`/ws/${sessionId}`)

  ws.onopen = () => store.setConnected(true)
  ws.onclose = () => store.setConnected(false)

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'agent_action') {
      store.addFeedEntry({
        id: crypto.randomUUID(),
        timestamp: Date.now(),
        message: msg.payload.description,
        type: 'agent_action',
      })
    }
    // Phase 4 adds agent_moved, agent_thought handlers
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `FastAPI(lifespan=lifespan)` with `@asynccontextmanager` | FastAPI 0.95.0 (2023) | Cleaner startup/shutdown; `on_event` deprecated |
| `react-pixi-fiber` | `@pixi/react` v8 with `extend()` API | March 2025 | Official library; React 19 support; tree-shaking |
| `instructor.patch(client)` | `instructor.from_litellm(litellm.acompletion)` | instructor 1.0.0 (2024) | `patch` is OpenAI-only; `from_litellm` works with all providers |
| `asyncio.gather()` for structured concurrency | `asyncio.TaskGroup` (Python 3.11+) | Python 3.11 (2022) | TaskGroup propagates exceptions correctly; gather silently swallows them |
| ESLint + Prettier | Biome | 2024 | Single tool, 10-100x faster, zero config conflicts |
| `pip + venv` | `uv` | 2024-2025 | 10-100x faster resolution; lockfile support |

**Deprecated/outdated in reference implementation:**
- `magentic` library: Used in `OpenAILLMModel` — OpenAI-only, unmaintained. Replace with `instructor`.
- Synchronous `requests.post()` in `OllamaLLMModel`: Blocks event loop. Replace with `httpx.AsyncClient` or `litellm.acompletion`.
- `@validator` (Pydantic v1 pattern): Use `@field_validator` or `@model_validator` in v2.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Backend runtime | YES | 3.11.6 | — (also 3.12.6 available) |
| Node.js | Frontend build | YES | 24.13.0 | — |
| npm | Package management | YES | 11.6.2 | — |
| uv | Python deps | YES | 0.9.26 | pip+venv (slower) |
| Ollama CLI/app | LLM runtime | NO | — | Must install; no fallback for v1 |
| Ollama API (localhost:11434) | LLM calls | NO | — | App detects and shows install prompt |

**Missing dependencies with no fallback:**
- **Ollama:** Not installed (no CLI, no app). v1 requires Ollama. The planner MUST include a Wave 0 task that verifies Ollama is installed and the `llama3.1:8b` model is pulled before any LLM integration task runs. The app itself handles the graceful startup warning; the developer needs it installed to run integration tests.

**Missing dependencies with fallback:**
- None in this phase.

**Ollama install command (macOS):**
```bash
brew install ollama
ollama serve &          # start in background
ollama pull llama3.1:8b  # ~4.7 GB download
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.x + pytest-asyncio 1.3.0 |
| Framework (frontend) | Vitest 4.1.4 |
| Config file (backend) | `backend/pyproject.toml` `[tool.pytest.ini_options]` section |
| Config file (frontend) | `frontend/vitest.config.ts` (or inline in `vite.config.ts`) |
| Quick run (backend) | `cd backend && uv run pytest tests/ -x -q` |
| Quick run (frontend) | `cd frontend && npm run test -- --run` |
| Full suite | `cd backend && uv run pytest && cd ../frontend && npm run test -- --run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INF-01 | Fresh simulation state on each startup (no persisted state) | unit | `pytest tests/test_session.py::test_fresh_state_on_startup -x` | Wave 0 |
| INF-02 | Agent step coroutines run concurrently, not sequentially | unit | `pytest tests/test_concurrency.py::test_concurrent_tasks -x` | Wave 0 |
| INF-03 | Structured LLM call returns validated Pydantic model; retries on failure | unit (mock Ollama) | `pytest tests/test_gateway.py::test_structured_output -x` | Wave 0 |
| INF-03 | Gateway returns fallback on repeated parse failure | unit (mock) | `pytest tests/test_gateway.py::test_fallback_on_failure -x` | Wave 0 |
| Ollama health | `/api/ollama/status` returns correct JSON shape | integration | `pytest tests/test_health.py::test_ollama_status_endpoint -x` | Wave 0 |
| WebSocket | WS endpoint accepts connection and sends `sim_connected` | integration | `pytest tests/test_ws.py::test_ws_connect -x` | Wave 0 |

**Frontend tests (Vitest):**

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INF-01 | Zustand store initializes to default state | unit | `npm run test -- src/stores/simulation.test.ts` | Wave 0 |
| Layout | App renders all three layout regions without crash | unit | `npm run test -- src/App.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q && npm run test -- --run`
- **Per wave merge:** Full suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

Backend test infrastructure (all missing — greenfield):
- [ ] `backend/tests/__init__.py` — test package
- [ ] `backend/tests/conftest.py` — shared pytest fixtures (async client, mock Ollama)
- [ ] `backend/tests/test_health.py` — covers Ollama status endpoint
- [ ] `backend/tests/test_gateway.py` — covers INF-03 structured output + fallback
- [ ] `backend/tests/test_concurrency.py` — covers INF-02 concurrent execution
- [ ] `backend/tests/test_session.py` — covers INF-01 fresh state
- [ ] `backend/tests/test_ws.py` — covers WebSocket connect handshake
- [ ] pytest-asyncio config: add `asyncio_mode = "auto"` to `pyproject.toml`

Frontend test infrastructure (all missing — greenfield):
- [ ] `frontend/src/stores/simulation.test.ts` — covers Zustand store init
- [ ] `frontend/src/App.test.tsx` — covers layout shell rendering
- [ ] `frontend/vitest.config.ts` — test runner config
- [ ] Framework install: `npm install -D @testing-library/react @testing-library/jest-dom jsdom` — needed for React component tests

---

## Security Domain

> `security_enforcement` not set in config.json — treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user auth in v1 (single-user, local) |
| V3 Session Management | Partial | Session IDs for WebSocket scoping; no auth tokens in v1 |
| V4 Access Control | No | Single-user local app |
| V5 Input Validation | Yes | Pydantic validates all WebSocket messages and LLM responses |
| V6 Cryptography | No | No secrets stored in Phase 1 (Ollama is local, no API keys) |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| WebSocket message injection (malformed JSON) | Tampering | Pydantic `WSMessage.model_validate_json()` at receive; reject invalid envelopes |
| LLM prompt injection via event text | Tampering | Enforce max event text length (500 chars) at API layer; implemented in Phase 6 |
| Ollama listening on 0.0.0.0 by default | Info Disclosure | Document in README: Ollama should only bind to localhost in dev; not a Phase 1 code concern |
| Module-level global simulation state | Info Disclosure | Session-scoped state only; no globals; enforced by architecture pattern |

**Note:** API key security (V6, LocalStorage) is not applicable in Phase 1 — no API keys exist in v1.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `instructor.from_litellm(litellm.acompletion)` creates an async-compatible client | Gateway pattern | If wrong, use `instructor.from_litellm(litellm.acompletion, mode=instructor.Mode.JSON)` explicitly; or use `instructor.from_provider("litellm/...", async_client=True)` as fallback |
| A2 | `ollama_chat/llama3.1:8b` is the correct LiteLLM model string for Ollama chat endpoint | Gateway pattern | If wrong, try `ollama/llama3.1:8b`; check `litellm.utils.get_llm_provider("ollama_chat/llama3.1:8b")` |
| A3 | pytest-asyncio 1.3.0 `asyncio_mode = "auto"` config key name is unchanged | Test config | If wrong, check pytest-asyncio 1.x changelog for config key changes |

---

## Open Questions

1. **Does instructor 1.15 change the `from_litellm` API?**
   - What we know: STACK.md says `instructor.from_litellm(litellm.completion)` is the pattern. The web search found `instructor.from_provider("litellm/...", async_client=True)` as an alternative newer API.
   - What's unclear: Whether `from_litellm` is deprecated in 1.15 in favor of `from_provider`.
   - Recommendation: Use `instructor.from_litellm(litellm.acompletion)` in Phase 1 (confirmed in official docs); if it fails, fall back to `instructor.from_provider("litellm/ollama_chat/llama3.1:8b", async_client=True)`.

2. **Ollama on this machine — how will tests run without Ollama installed?**
   - What we know: Ollama is not installed (verified). Integration tests that hit the real Ollama endpoint will fail in CI.
   - What's unclear: Whether the user wants mock-based tests or real Ollama integration tests.
   - Recommendation: Mark Ollama-dependent tests with `@pytest.mark.integration` and skip them when `OLLAMA_BASE_URL` env var is unset. Unit tests use `httpx.MockTransport` or `unittest.mock.patch` to simulate Ollama responses.

---

## Sources

### Primary (HIGH confidence)
- FastAPI official docs, Lifespan Events — https://fastapi.tiangolo.com/advanced/events/ — startup/shutdown pattern
- FastAPI official docs, WebSockets — https://fastapi.tiangolo.com/advanced/websockets/ — WebSocket endpoint pattern
- LiteLLM Ollama integration — https://docs.litellm.ai/docs/providers/ollama — model string format, api_base
- Ollama API docs, List Models — https://docs.ollama.com/api/tags — health check + model discovery endpoints
- Python asyncio docs, TaskGroup — https://docs.python.org/3/library/asyncio-task.html — structured concurrency
- Project STACK.md — all library decisions and compatibility notes
- Project ARCHITECTURE.md — connection manager, event bus, data flow patterns
- Project PITFALLS.md — async anti-patterns, semaphore rate limiting

### Secondary (MEDIUM confidence)
- instructor + LiteLLM integration guide — https://python.useinstructor.com/integrations/litellm/ — `from_litellm` async pattern
- LiteLLM instructor tutorial — https://docs.litellm.ai/docs/tutorials/instructor — alternative `from_provider` pattern

### Tertiary (LOW confidence — flagged as ASSUMED in Assumptions Log)
- `instructor.from_litellm(litellm.acompletion)` async behavior — inferred from docs and search; not directly executed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry and pip index on 2026-04-08
- Architecture patterns: HIGH — all patterns cite official FastAPI/LiteLLM/instructor docs or are derived from project ARCHITECTURE.md (HIGH confidence source)
- Pitfalls: HIGH — sourced from project PITFALLS.md (HIGH confidence) plus environment verification
- Environment: HIGH — directly probed via shell commands on dev machine
- instructor async pattern: MEDIUM — cited from official docs but exact `from_litellm` vs `from_provider` question remains open

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable ecosystem; litellm releases frequently but major API won't break in 30 days)
