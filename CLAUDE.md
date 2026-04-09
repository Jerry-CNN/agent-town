<!-- GSD:project-start source:PROJECT.md -->
## Project

**Agent Town**

A web-based generative agents playground where users watch AI-powered characters live their daily lives in a 2D tile-map town. Users inject events — "a stock is going up," "there's a wedding tomorrow" — and watch agents react in real-time: heading to the trading hall, getting dressed for the ceremony, gossiping about the news. Built as an interactive reimplementation of the Generative Agents paper (reference: `~/projects/GenerativeAgentsCN/`), designed for the browser.

**Core Value:** Users can type any event and immediately see AI agents respond to it in a living, breathing town — the magic is watching emergent behavior unfold.

### Constraints

- **LLM Cost**: Each agent makes 5-20 LLM calls per step — design must support cheap models (GPT-4o-mini, Haiku) for routine calls and reserve expensive models for complex reasoning
- **Real-time UX**: Agents must appear to act fluidly — backend processes asynchronously, frontend interpolates movement
- **Single-user architecture**: No shared state between sessions, but avoid designs that would prevent future multiplayer
- **Browser rendering**: 2D tile map must run smoothly with 5-25 agents on a standard laptop
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|----------------|
| Python | 3.11+ | Backend runtime | 3.11 gives 10-60% perf gains over 3.10; required for modern asyncio patterns. 3.12 is fine too but 3.11 is the widest-supported baseline in 2025 containers. |
| FastAPI | 0.115+ | HTTP + WebSocket API server | Native async, first-class WebSocket support, Pydantic v2 built-in, Starlette 1.0 compatibility. The reference agent logic is Python — FastAPI is the lowest-friction web layer. Do not use Flask/Django; they lack async-first WebSocket handling. |
| Uvicorn | 0.30+ | ASGI server | Paired with FastAPI as the standard runtime. Use `uvicorn[standard]` (includes `uvloop` and `httptools`) for production-grade performance. |
| React | 19+ | UI framework | Official @pixi/react v8 targets React 19. Ecosystem standard. Use with TypeScript. |
| TypeScript | 5.4+ | Frontend type safety | PixiJS v8 and @pixi/react v8 ship TypeScript definitions. Saves debugging time at the agent-state schema boundary. |
| Vite | 5+ | Frontend build tool | CRA is deprecated. Vite is the 2025 standard: instant HMR, native ESM, SWC for TS compilation. `npm create vite@latest -- --template react-ts` is the canonical starting point. |
| PixiJS | 8.17+ | 2D tile rendering engine | WebGL/WebGPU renderer with Canvas fallback. Fastest 2D rendering library for browser (47 FPS benchmark vs. Phaser 3's 43 FPS on sprite stress tests). Does NOT impose a game structure — plugs cleanly into React. Tiled JSON map support via `pixi-tiledmap`. |
| @pixi/react | 8+ | React-PixiJS bridge | Official v8 (March 2025 rewrite) with TypeScript, React 19 support, `extend` API for tree-shaking. Renders PixiJS scene graph as JSX. This is the standard — do not use the older `react-pixi-fiber`. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| LiteLLM | 1.83+ | Unified LLM provider client | Single Python API for OpenAI, Anthropic, Ollama, OpenRouter, Bedrock. Abstracts away SDK differences so agent logic never changes when the user switches providers. Pin to >=1.83.0 — avoid 1.82.7/1.82.8 (supply-chain compromise, March 2026, both removed from PyPI). |
| instructor | 1.8+ | Structured LLM output with Pydantic | Forces LLM responses into typed Pydantic models with automatic retry on validation failure. Use for every agent cognition call: schedule generation, reaction decisions, conversation turns. Works with any provider via `instructor.from_litellm()`. |
| Pydantic | 2.7+ | Data validation / schema | Bundled with FastAPI. Use for agent state models, LLM response schemas, WebSocket message contracts. Do not mix v1 and v2 patterns — use `model_validator`, not `@validator`. |
| ChromaDB | 0.6+ | Vector store for agent memory | Embedded SQLite-backed store, zero infrastructure. `PersistentClient(path=...)` survives restarts for save/load. Bundles `all-MiniLM-L6-v2` embeddings by default. Right choice for single-user, per-simulation instances. Do NOT use Qdrant/Weaviate — they require separate server processes. |
| sentence-transformers | 3.x | Local embedding model | Used by ChromaDB's default embedding function. `all-MiniLM-L6-v2` is 80MB, runs on CPU, fast enough for memory retrieval (<50ms per embed). No API key required — critical since the memory system runs on every agent step. |
| SQLAlchemy | 2.0+ | Simulation state persistence | For optional save/load: serialize agent state (schedule, memory refs, position) to SQLite. Use async SQLAlchemy (`asyncpg` or `aiosqlite`) to avoid blocking the event loop. |
| aiosqlite | 0.20+ | Async SQLite driver | Pairs with SQLAlchemy for non-blocking SQLite I/O in the FastAPI async context. |
| Zustand | 4.5+ | Frontend global state | Minimal boilerplate, excellent performance, works outside React context for WebSocket message ingestion. Use for agent state store (positions, activity, conversation). Do not use Redux — overkill. Do not use React Context for high-frequency WebSocket updates (re-render cost). |
| pixi-tiledmap | latest | Tiled JSON map loader for PixiJS v8 | Ground-up PixiJS v8 rewrite with full layer support and typed API. Parses Tiled JSON exported from the Tiled map editor. Use Tiled to design the town map, export JSON, load at runtime. |
| websockets (Python) | 12+ | WebSocket protocol (dev only) | FastAPI/Starlette handles WebSocket protocol natively via `starlette.websockets`. You don't need this as a direct dependency unless writing standalone WS test clients. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package and venv management | Replaces pip + virtualenv. 10-100x faster than pip. Install with `curl -LsSf https://astral.sh/uv/install.sh \| sh`. Use `uv sync` to install from `pyproject.toml`. |
| pyproject.toml | Python project manifest | Standard since PEP 517. Replaces setup.py, requirements.txt. Works with uv natively. |
| Vitest | Frontend unit testing | Vite-native, same config. Test agent state reducers and WebSocket message parsers. |
| pytest + pytest-asyncio | Backend testing | Essential for async FastAPI routes and agent simulation step tests. |
| Tiled Map Editor | Town map authoring | Open-source desktop app. Design the tile grid, export to JSON, load in browser at runtime. One-time tool, not a runtime dependency. |
| Biome | Frontend linting + formatting | Replaces ESLint + Prettier. Rust-based, 10-100x faster. Single config file. |
## Installation
# --- Backend ---
# Requires Python 3.11+, uv installed
# --- Frontend ---
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| 2D Rendering | PixiJS + @pixi/react | Phaser 4 | Phaser imposes a full game loop and scene manager that conflicts with React's render cycle. Phaser 4 is in RC as of April 2025 — production risk. PixiJS integrates cleanly as a React canvas child. |
| 2D Rendering | PixiJS | HTML5 Canvas API | Canvas requires manual sprite sheet management, no WebGL acceleration by default, quadratic performance degradation with agent count. |
| 2D Rendering | PixiJS | Three.js | 3D engine with 2D support is overkill. Adds 600KB+ to bundle for no benefit. |
| LLM Abstraction | LiteLLM | Direct OpenAI SDK | OpenAI SDK only covers OpenAI and Azure. Users require Anthropic, Ollama, OpenRouter support. LiteLLM provides a single interface to all. |
| LLM Abstraction | LiteLLM | LangChain | LangChain is too opinionated for agent architecture that matches the paper's design. LiteLLM is a pure provider abstraction — no chain/agent framework lock-in. |
| Structured Output | instructor | OpenAI `response_format` | `response_format` only works with OpenAI. instructor works across all LiteLLM-supported providers with the same Pydantic schema. |
| Vector Store | ChromaDB | Qdrant | Qdrant runs as a separate server process. Single-user, local simulation does not need distributed vector search. ChromaDB is embedded and zero-ops. |
| Vector Store | ChromaDB | FAISS | FAISS lacks metadata filtering — can't filter memories by agent ID or time window without external logic. ChromaDB handles both. |
| Vector Store | ChromaDB | pgvector | PostgreSQL server dependency is too heavy for a local single-user simulation tool. |
| State Management | Zustand | Redux Toolkit | Redux requires 5x more boilerplate. Zustand's `subscribe` API is better suited for ingesting high-frequency WebSocket messages without triggering unnecessary re-renders. |
| State Management | Zustand | React Context | Context re-renders all consumers on every update. With 5-25 agents emitting updates every few seconds, this causes visible frame drops. |
| Frontend Build | Vite | Create React App | CRA is deprecated and unmaintained since 2023. Vite is the community standard. |
| Backend Server | FastAPI + Uvicorn | Django Channels | Django adds ORM, migrations, and admin overhead irrelevant to agent simulation. FastAPI is async-native and lightweight. |
| Python Deps | uv | pip + venv | uv is 10-100x faster and handles lockfiles correctly. pip's resolver has known issues with complex dependency graphs (e.g., torch + sentence-transformers). |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Phaser 4 (in production, April 2026) | RC4 released May 2025 — stable release may be out by April 2026, but the React integration story is weaker than PixiJS. The full game loop (scenes, physics engine, audio) adds complexity you don't need. | PixiJS 8 + @pixi/react 8 |
| Kaboom / Kaplay | 3 FPS in sprite stress benchmarks. Built for game jams, not production simulations. | PixiJS |
| LangChain as agent framework | LangChain abstractions don't map to the Generative Agents paper's architecture (memory stream, reflection, planning). Using it means fighting the framework. Use it only as a last resort for a specific integration. | Direct LiteLLM + instructor + custom agent classes |
| litellm 1.82.7 or 1.82.8 | Supply-chain compromise discovered March 2026. Both versions backdoored and removed from PyPI. | litellm >=1.83.0 |
| threading.Thread for agent concurrency | Python GIL limits true parallelism. For I/O-bound LLM calls, asyncio with `asyncio.Semaphore` is correct. | asyncio.gather + asyncio.Semaphore |
| WebSockets library (Python) as primary server | FastAPI's built-in Starlette WebSocket handling is already production-grade. Adding `websockets` as a server creates a second event loop conflict. | FastAPI WebSocket endpoints |
| Next.js | SSR adds complexity for a simulation UI that is purely client-side dynamic content. No SEO needed. | Vite + React (SPA) |
| SQLite WAL mode with multiple processes | Agent simulation will write/read state frequently from Python. Multi-process SQLite access causes lock contention. Keep simulation in a single process. | Single-process FastAPI + aiosqlite |
## Stack Patterns by Variant
### If LLM calls are too slow for real-time feel
### If users want Ollama (local LLM)
### If vector memory retrieval is slow
### If tile map requires animation (NPC walking cycles)
### If save/load is deferred (MVP)
## Version Compatibility
| Pair | Compatibility Note |
|------|--------------------|
| FastAPI 0.115+ + Starlette 1.0+ | FastAPI >=0.115 requires Starlette >=1.0. Starlette 1.0 dropped several deprecated APIs — do not use `starlette.requests.Request.receive` directly. |
| @pixi/react v8 + PixiJS v8 | @pixi/react v8 requires PixiJS v8 as a peer dependency. Do not mix v7 PixiJS with v8 react bindings. |
| instructor + LiteLLM | `instructor.from_litellm(litellm.completion)` is the integration pattern. Use `instructor.patch` only for direct OpenAI client. |
| ChromaDB + sentence-transformers | ChromaDB bundles its own sentence-transformers embedding function. If you install sentence-transformers separately, ensure the same version to avoid tokenizer conflicts. |
| Python 3.11+ + asyncio | `asyncio.TaskGroup` (Python 3.11+) is preferred over `asyncio.gather` for structured concurrency. Use it for per-agent step execution. |
| SQLAlchemy 2.0 + aiosqlite | SQLAlchemy 2.0 requires `async_sessionmaker` (not `sessionmaker`) for async engines. Old tutorials using `create_async_engine` + `Session` are broken. |
## Sources
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI latest release (0.135.x): https://pypi.org/project/fastapi/
- PixiJS v8 stable (8.17.1): https://pixijs.com/blog/8.13.0
- @pixi/react v8 launch (March 2025): https://pixijs.com/blog/pixi-react-v8-live
- Phaser v4 RC1 (April 2025): https://phaser.io/news/2025/04/phaser-v4-release-candidate-1
- LiteLLM PyPI (1.83.x, April 2026): https://pypi.org/project/litellm/
- LiteLLM supply-chain incident (1.82.7–1.82.8): https://docs.litellm.ai/blog/security-update-march-2026
- ChromaDB local persistence: https://johal.in/chroma-db-python-local-persistence-for-llm-memory-stores-2025-2/
- instructor (Pydantic structured output): https://python.useinstructor.com/
- Zustand for WebSocket state: https://github.com/pmndrs/zustand
- Vite + React TypeScript standard setup: https://vite.dev/guide/
- asyncio concurrency patterns for LLM calls: https://python.useinstructor.com/blog/2023/11/13/learn-async/
- pixi-tiledmap (PixiJS v8 Tiled loader): https://www.npmjs.com/package/pixi-tiledmap
- Vector database comparison 2025: https://liquidmetal.ai/casesAndBlogs/vector-comparison/
- FastAPI + SQLite persistence: https://fastapi.tiangolo.com/tutorial/sql-databases/
- Phaser vs PixiJS comparison: https://dev.to/ritza/phaser-vs-pixijs-for-making-2d-games-2j8c
- uv package manager: https://astral.sh/uv
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
