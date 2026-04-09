# Pitfalls Research

**Domain:** LLM-powered agent simulation web app
**Researched:** 2026-04-08
**Confidence:** HIGH (cross-verified across multiple official and community sources)

---

## Critical Pitfalls

### Pitfall 1: LLM Cost Explosion From Uncapped Per-Agent Call Rates

**What goes wrong:** With 25 agents each making 5-20 LLM calls per simulation step and steps firing every few seconds, costs can reach $2,000-10,000/day at scale. Multi-agent systems generate up to 15x more tokens than single-agent setups because of coordination overhead and repeated context. An unconstrained agentic loop can cost $5-8 per task in API fees — multiply that across agents running continuously and the numbers become untenable fast.

**Why it happens:** Each agent cycle includes planning, tool/action selection, dialogue generation, reflection trigger checks, and memory retrieval scoring — all separate LLM calls. Developers scope costs based on per-call pricing and miss the multiplicative effect of real-time continuous operation.

**How to avoid:**
- Route by call type: use cheap models (GPT-4o-mini, Haiku, small Ollama models) for routine calls (schedule generation, short-term action selection, importance scoring) and reserve expensive models only for reflection and complex social reasoning.
- Implement a per-simulation token budget with hard throttling — if budget exceeded, slow step frequency rather than cutting calls silently.
- Use prompt caching aggressively: system prompts, agent persona, and world descriptions are identical across most calls for a given agent. OpenAI and Anthropic both support prompt caching, which is critical here.
- Apply observation masking (sliding window): older observations are replaced with summary placeholders, cutting per-instance cost by 40-60% with negligible quality loss vs. full context.
- Batch non-urgent calls: reflection, memory consolidation, and daily schedule planning do not need real-time turnaround — use async batch APIs for 50% cost reduction on these.

**Warning signs:**
- API spend growing faster than user count
- Reflection triggers firing on every step instead of on poignancy threshold
- Daily schedule being re-generated every few steps instead of once per day

**Phase to address:** Foundation/Architecture phase (Phase 1). Cost controls must be baked into the agent loop design, not bolted on after the fact. Retrofitting rate limiting into a running simulation is extremely painful.

---

### Pitfall 2: Sequential Agent Processing Bottleneck

**What goes wrong:** Processing agents one-at-a-time (the reference implementation's approach) means with 25 agents and 1-second average LLM call latency, one full simulation tick takes 25+ seconds. The simulation feels frozen, not real-time. Users perceive the town as dead.

**Why it happens:** The reference Python implementation uses sequential iteration over agents. LlamaIndex memory queries are synchronous. Developers port this logic directly to FastAPI without async conversion.

**How to avoid:**
- Run all agents concurrently using `asyncio.gather()` with per-agent async LLM clients. Each agent's step should be a coroutine, not a blocking call.
- Never use `requests` (synchronous) inside `async def` FastAPI routes — this blocks the entire event loop and serializes all concurrent agent processing.
- Use `httpx.AsyncClient` or the async variants of OpenAI/Anthropic SDKs.
- Apply a semaphore to cap concurrent outgoing LLM requests (prevents API rate limit errors): `asyncio.Semaphore(N)` where N is your rate limit headroom.
- Decouple the simulation tick from per-agent completion: start all agents' steps simultaneously, emit partial updates to the frontend as each agent finishes, rather than waiting for all 25 to complete before sending any update.

**Warning signs:**
- Step duration scales linearly with agent count
- Frontend receives bursts of updates after long silences
- Python event loop `asyncio.get_event_loop()` warnings in logs

**Phase to address:** Core Agent Loop phase (Phase 2). Architecture decision must be made before any agent processing code is written.

---

### Pitfall 3: Fragile JSON Parsing of LLM Responses

**What goes wrong:** LLMs return structured data wrapped in markdown code fences (` ```json ... ``` `), with trailing commas, strings instead of numbers, null fields in unexpected locations, or extra explanatory prose. A single parse failure crashes the agent's step and either freezes that agent or throws an unhandled exception that disrupts the simulation.

**Why it happens:** Prompt-based format enforcement is probabilistically unreliable. Even with explicit instructions, models deviate — especially smaller/cheaper models used for cost optimization. The reference implementation's string-matching approach to parse LLM decisions is fragile by design.

**How to avoid:**
- Use OpenAI structured outputs (JSON mode with schema) or Anthropic's tool_use for all decisions requiring structured data. These enforce format at the API level, not the prompt level.
- For providers without native structured output (Ollama, custom models), implement a two-layer parser: (1) strip markdown wrappers and normalize formatting, (2) validate against a Pydantic model, (3) on failure, retry the call once with the error embedded in the prompt as a correction signal.
- Never hard-crash the simulation on a parse failure. Implement per-agent fallback states (agent idles, continues previous action, or selects a default action) when an LLM response cannot be parsed.
- Log every failed parse with the raw response — these are the most valuable debugging artifacts.
- Define strict Pydantic schemas for every LLM call type: `ActionDecision`, `DialogueTurn`, `DailySchedule`, `ReflectionInsight`, `ImportanceScore`.

**Warning signs:**
- Agents occasionally freezing mid-simulation with no visible error
- `JSONDecodeError` or `ValidationError` appearing in logs at low frequency (easy to miss)
- Agent behavior becoming erratic after a model upgrade or prompt change

**Phase to address:** Core Agent Loop phase (Phase 2). Every LLM call interface must have a schema contract before implementation.

---

### Pitfall 4: WebSocket State Divergence on Reconnection

**What goes wrong:** When a browser tab reconnects after a disconnection (tab sleep, network hiccup, mobile switching networks), the frontend has stale state: agents are in wrong positions, activities are outdated, and the event feed has gaps. Naive reconnection just re-establishes the connection without replaying missed events, leaving the user watching a broken town.

**Why it happens:** Most WebSocket implementations handle connection lifecycle but not state reconciliation. The simulation state on the backend has moved forward; the frontend has no mechanism to catch up.

**How to avoid:**
- Assign monotonically increasing sequence numbers to every simulation event emitted over WebSocket.
- On reconnect, the client sends its last-received sequence number; the backend replays all events since that sequence from a short ring buffer (last N seconds of events).
- Alternatively, on reconnect, send a full snapshot of current simulation state (all agent positions, activities, current conversations) as a single "state dump" message, then resume streaming from current.
- Implement exponential backoff with jitter for reconnection (start 500ms, double, cap at 30s).
- Handle backpressure: if the client's message queue grows (slow browser tab), drop non-critical updates (intermediate movement frames) and keep critical events (conversations, state changes). Never let backpressure crash the server.

**Warning signs:**
- Agents teleporting to wrong positions after a tab sleep
- Feed showing gaps or duplicate events
- Memory usage growing on server side for "ghost" disconnected sessions

**Phase to address:** Real-Time Transport phase (Phase 2 or 3). Design the event sequence numbering scheme before any frontend-backend messaging is built.

---

### Pitfall 5: Context Window Accumulation and Poisoning

**What goes wrong:** Agent memory context grows unbounded as the simulation runs. After a few hours, each LLM call carries hundreds of memories in context. Performance degrades: the model focuses on early/late context and ignores the middle ("lost in the middle" effect). Worse, if a hallucinated memory or bad reflection gets stored, it contaminates all future calls for that agent — context poisoning — causing the agent to pursue impossible goals or behave incoherently.

**Why it happens:** Naively appending every perception and reflection to the agent's context without pruning or scoring creates unbounded growth. Retrieval by recency alone without relevance weighting surfaces stale or irrelevant memories.

**How to avoid:**
- Implement the triple-weighted retrieval from the paper (recency × 0.5, relevance × 3, importance × 2) and cap retrieved memories at K items per call (typically 10-15). Never pass all memories in context.
- Impose a hard context token budget per LLM call. Before building the prompt, measure token count; if over budget, drop least-scored memories first.
- Add a "distraction ceiling": monitor output quality and if agents begin repeating old actions or ignoring the current situation, reduce the memory retrieval window.
- Sanitize reflection outputs before storing: if a reflection contains factual impossibilities (agent remembers an event that hasn't happened yet, references a person who hasn't been met), discard or flag it.
- Implement memory decay: memories below a recency+importance threshold are archived rather than retrieved, preventing the memory pool from growing unbounded.

**Warning signs:**
- LLM call token counts growing steadily over simulation runtime
- Agents repeating the same activity for hours without variation
- Agents referencing events or people incorrectly (hallucinated associations)

**Phase to address:** Memory System phase (Phase 2). Memory architecture must be designed with retrieval budget limits from day one.

---

### Pitfall 6: FastAPI Blocking the Event Loop With Synchronous LLM Calls

**What goes wrong:** Developers declare routes with `async def` but call synchronous LLM client libraries (`openai` synchronous client, `requests`, synchronous LlamaIndex calls) inside them. FastAPI runs these on the event loop directly, blocking it. With 25 concurrent agents all waiting on LLM responses, the single event loop serializes all I/O, defeating the purpose of async.

**Why it happens:** The Python `async/await` syntax looks correct but the underlying library calls are synchronous. This is the #1 FastAPI mistake in AI service development. The reference implementation uses synchronous Python throughout — porting without async conversion reproduces this problem at scale.

**How to avoid:**
- Use the async variants of all LLM clients: `openai.AsyncOpenAI`, `anthropic.AsyncAnthropic`, `httpx.AsyncClient`.
- For LlamaIndex memory operations that don't have async variants: offload with `asyncio.run_in_executor(executor, sync_fn)` to a thread pool.
- Compute-heavy operations (embedding generation for many memories) should run in a `ProcessPoolExecutor` to bypass the GIL.
- Audit every `await`-less call inside `async def` routes before shipping.

**Warning signs:**
- Server CPU stays high even when all agents are "waiting" on LLM responses
- `/health` endpoint responds slowly during active simulation
- Event loop lag metrics show consistent delays

**Phase to address:** Core Agent Loop phase (Phase 2). Enforcing async patterns from the start is far easier than refactoring later.

---

## Technical Debt Patterns

### Hardcoded Prompt Templates That Become Load-Bearing

**What goes wrong:** Prompt templates are written once and scattered across agent logic files. Over time, subtle wording changes by developers cause wildly different agent behavior. Since prompts are not versioned or tested, regressions are invisible until a user reports strange agent behavior.

**Prevention:**
- Store all prompt templates in a single `prompts/` directory, one file per call type.
- Version prompts with the agent architecture version in config.
- Write behavioral tests that run a short simulation and assert agent output patterns (agent reaches location, initiates conversation, generates reflection) against known-good outputs.
- Never embed prompt text inline in agent logic code.

### Memory Vector Store Grows Without Bounds

**What goes wrong:** Each agent's vector store accumulates every perception, conversation turn, and reflection. After 24 simulated hours, stores become very large. Retrieval time increases, embedding costs grow, and save/load times become slow enough that users give up on persistence.

**Prevention:**
- Set hard limits on per-agent memory count (e.g., 500 entries max).
- Implement memory consolidation: when the limit is reached, merge low-importance memories into summary nodes rather than deleting them.
- Use a lightweight embedded vector store (ChromaDB, LanceDB) rather than LlamaIndex's default setup, which has high memory overhead per index.

### Save/Load State Is Brittle to Schema Changes

**What goes wrong:** Simulation save files serialize agent memory stores, vector embeddings, schedules, and positions. After any code change that modifies these schemas (new memory field, changed schedule format), old save files fail to load and are silently corrupted.

**Prevention:**
- Version all save file schemas with a `schema_version` field.
- Write migration functions for schema upgrades.
- Test save/load as part of the CI pipeline.
- Separate vector store serialization (ChromaDB supports native persistence) from JSON state serialization to reduce coupling.

### No Error Recovery When One Agent's LLM Call Fails

**What goes wrong:** If one agent's LLM call returns a 429 (rate limit), 500 (server error), or timeout, and there is no fallback logic, the agent stops acting. In a simulation running for hours, transient failures are guaranteed. Without recovery, agents gradually "die" over long runs.

**Prevention:**
- Implement per-agent try/except with retry + backoff for all LLM calls.
- On repeated failure, put the agent into an "idle" state with a plausible activity ("resting at home") rather than removing them.
- Emit the idle state to the frontend so users see the agent paused, not disappeared.
- Track per-agent error rates; alert if any agent has >5% failure rate in a session.

---

## Integration Gotchas

### LlamaIndex Memory Has High RAM Overhead

The reference implementation uses LlamaIndex for memory. LlamaIndex's in-memory vector index uses significantly more RAM than raw embedding arrays. With 25 agents each having a separate LlamaIndex instance, memory pressure is substantial. On a standard laptop, this can cause OOM kills during long simulations.

**Alternative:** Use ChromaDB with a local persistent collection per agent. It has lower overhead, native persistence, and an async-compatible interface. Or use `numpy` arrays with `faiss` for pure in-process similarity search — no external dependencies.

### OpenRouter / Multi-Provider Routing Has Inconsistent Structured Output Support

If users bring OpenRouter keys, the structured output mode (JSON schema enforcement) may not be supported for all proxied models. Falling back to prompt-only format enforcement reintroduces JSON fragility.

**Prevention:** At simulation start, detect whether the user's configured provider supports native structured output. If not, enable the more aggressive prompt-retry-parse pipeline for all structured calls.

### Embedding Models Must Be Consistent Across Save/Load

If a user saves a simulation using one embedding model (e.g., `text-embedding-3-small`) and later loads it while the backend has switched to a different embedding model, all vector similarity retrieval returns garbage. Memories become semantically mismatched.

**Prevention:** Store the embedding model ID in the save file header. On load, verify it matches the current model. If not, either reject the load with a clear error or re-embed all stored memories with the new model before resuming.

### Ollama Local Model Latency Is Unpredictable

Users running Ollama on a laptop will experience wildly variable LLM call latency depending on model size and hardware. A 7B model on CPU can take 30+ seconds per call, making real-time simulation impossible.

**Prevention:** At simulation start, run a latency benchmark call and recommend step interval accordingly. Surface the estimated "simulation speed" to the user (e.g., "At current latency, simulation runs at 0.1x real-time speed").

---

## Performance Traps

### 2D Tile Map Rendering With 25 Animated Sprites

**What goes wrong:** Naively rendering 25 sprites with per-frame position updates and animations causes frame rate drops on lower-end hardware, especially when React re-renders are involved on every simulation tick.

**Prevention:**
- Use PixiJS or Phaser for tile map rendering — these use WebGL batch rendering and maintain 60 FPS with hundreds of sprites.
- Never trigger React state re-renders for every simulation update. Keep the canvas renderer separate from React's reconciliation cycle.
- Use a dedicated animation loop (requestAnimationFrame) for smooth movement interpolation between agent positions, decoupled from the WebSocket message rate.
- Pre-load all sprite sheets and tile assets before simulation starts. Asset loading during active simulation causes hitches.

### Movement Interpolation Gap

**What goes wrong:** Agents move in discrete tile-by-tile steps. When a WebSocket message says "agent moved from tile (3,4) to tile (3,5)," rendering this as an instant teleport looks janky. Users perceive agents as teleporting rather than walking.

**Prevention:**
- Implement client-side movement interpolation: when an agent receives a new target position, animate movement over the expected step duration (e.g., 500ms).
- Maintain a client-side position buffer separate from the authoritative server position.
- If a new position arrives before the interpolation completes, snap to current interpolated position and start interpolating to the new target.

### WebSocket Message Rate vs. Browser Rendering Rate

**What goes wrong:** The backend emits messages at the simulation tick rate (e.g., every 2 seconds). The frontend renders at 60 FPS. If large simulation state dumps are sent at 2-second intervals, the browser must process a large message payload mid-frame, causing jank.

**Prevention:**
- Send small, incremental state diffs rather than full state dumps.
- Only send agent position updates for agents that moved; skip agents that are stationary.
- Throttle the feed (thought/action/conversation log) to a reasonable display rate — no user reads faster than 1-2 entries per second.

---

## Security Mistakes

### API Keys in Browser LocalStorage or Logs

**What goes wrong:** Users configure their LLM API keys in the frontend, and the keys get stored in LocalStorage or sent to the backend where they appear in server logs. Keys in LocalStorage are accessible to any JavaScript on the page (XSS vulnerability). Keys in logs get leaked through log aggregation systems.

**Prevention:**
- Never log API keys. Sanitize all request/response logging at the HTTP client layer.
- Store the key in memory on the backend only for the duration of the simulation session — do not persist it to disk or a database.
- On the frontend, treat the key as a session credential: send it to the backend once at simulation start (over HTTPS), never store it in LocalStorage or cookies. Use a session token for subsequent WebSocket authentication.
- Consider a backend-for-frontend pattern: the user's key is held server-side for the session, never re-transmitted to the browser after initial setup.

### Uncapped LLM Proxy Costs From Malicious Event Injection

**What goes wrong:** The event injection interface allows users to type arbitrary text. A malicious or curious user injects events designed to force maximum LLM processing: extremely long event texts, events that trigger simultaneous reflections in all 25 agents, or rapid-fire injections.

**Prevention:**
- Enforce a maximum event text length (e.g., 500 characters) at the API layer.
- Rate-limit event injection: no more than N events per minute per simulation session.
- Cap the token budget per simulation step regardless of how many events are pending.
- Since this is single-user per instance (user brings their own key), the primary risk is self-inflicted cost — clearly surface token consumption to the user so they can self-govern.

### Simulation State Leaking Between Sessions

**What goes wrong:** If simulation state (agent memories, conversation histories, user-injected events) is stored globally on the server and not scoped to a session, restarting the application might serve one user's simulation data to another user.

**Prevention:**
- Scope all simulation state to a session ID generated at simulation start.
- Clean up session state when simulation is stopped or the WebSocket disconnects.
- Never use module-level global variables to hold simulation state in the Python backend.

---

## UX Pitfalls

### Agents Feel Dead During LLM Thinking Time

**What goes wrong:** LLM calls take 0.5-5 seconds. During this time, agents stand still. Users see 25 statues rather than a living town. The perceived responsiveness collapses — users interpret the frozen agents as a bug.

**Prevention:**
- Decouple visual animation from simulation state. Agents should always be animating (idle animation, breathing, subtle movement) even when waiting for their next LLM decision.
- Implement "thinking" indicators: a subtle visual cue (thought bubble, pulsing color) for agents currently processing an LLM call.
- Show intermediate action text in the feed even before the action is fully resolved: "John is thinking about where to go..." before the decision arrives.
- Use the streaming API to emit partial responses for long outputs (reflection text, conversation dialogue) so the feed feels live rather than delayed.

### Real-Time Feed Information Overload

**What goes wrong:** With 25 agents each emitting thoughts, movements, and conversations, the real-time feed becomes a firehose. Users cannot follow any single agent. The feed becomes background noise rather than an engaging window into agent behavior.

**Prevention:**
- Implement feed filtering: users can follow a specific agent, or filter by event type (conversations only, actions only, whispered events only).
- Rate-limit feed entries: emit at most N entries per second to the frontend, prioritizing conversations and user-triggered event reactions over routine movements.
- Group concurrent conversation turns into a single feed card rather than individual messages.
- Highlight agents reacting to user-injected events — this is the core magic moment and must be visually distinct.

### Save/Load UX Mismatches Expectations

**What goes wrong:** Users expect "save" to be instant and "load" to fully restore the visual simulation state including agent positions, ongoing conversations, and the activity feed history. In practice, saving a vector store takes seconds and loading it reconstructs the world but may not restore in-progress conversations or the feed history.

**Prevention:**
- Surface save/load duration expectations to the user ("saving may take 10-30 seconds").
- Clearly define what is and is not restored: "agent memories and positions are saved; in-progress conversations are not."
- Implement auto-save checkpoints periodically (every 5 simulated minutes) so users don't lose long sessions.

### No Feedback When Event Is Ignored

**What goes wrong:** A user injects an event. Nothing visibly changes. The user doesn't know if the event was received, if agents perceived it, or if it had any effect. They inject it again. Now agents are processing it twice.

**Prevention:**
- Immediately acknowledge event injection in the feed: "Event injected: [text]" with a timestamp.
- Show which agents perceived the event within one step.
- If an agent's reaction to the event is delayed (LLM still processing), show "Agent X is considering the news..." in the feed.
- Prevent duplicate injections: brief debounce on the injection button.

---

## "Looks Done But Isn't" Checklist

These are features that appear complete during development but have hidden failure modes only visible in long-running simulations or edge cases.

- [ ] **Reflection system triggers correctly** — Reflection that never triggers means agents never form higher-level insights; reflection that always triggers means constant expensive calls. Verify poignancy threshold accumulates correctly and resets after reflection.

- [ ] **Memory retrieval returns varied results** — After many steps, check that retrieved memories are not always the same top-K. If retrieval is stuck returning the same 10 memories, the recency decay is broken.

- [ ] **Conversation initiation terminates** — Multi-turn agent conversations must have a defined end condition. Without it, two agents can lock into an infinite conversation loop, consuming LLM budget while blocking other agents.

- [ ] **Daily schedule respects location constraints** — Agents should not schedule activities at locations they cannot pathfind to. Verify the schedule generator is aware of the map topology.

- [ ] **Whispered events spread organically** — A whispered event should spread through agent-to-agent conversation, not broadcast immediately. Verify that only the target agent receives the initial event, and others learn it only through dialogue.

- [ ] **Agent count limits are enforced** — Verify that selecting maximum agents (25) doesn't degrade simulation performance beyond acceptable thresholds. Test at max agent count explicitly.

- [ ] **Pathfinding handles blocked tiles correctly** — Agents should not freeze when their path is blocked by another agent or a closed location. Verify BFS pathfinding handles dynamic obstacles gracefully.

- [ ] **LLM call failures don't orphan agents** — Kill the LLM backend mid-simulation. Verify agents enter idle state gracefully rather than disappearing or throwing uncaught exceptions.

- [ ] **Save/load round-trip integrity** — Save a simulation, reload it, run for 10 more minutes, save again. Verify no state corruption (agents in impossible positions, memory retrieval returning errors).

- [ ] **WebSocket reconnection works** — Close the browser tab, wait 30 seconds, reopen. Verify agents are in correct positions and the feed resumes correctly.

---

## Recovery Strategies

### When an Agent Gets Stuck in a Behavioral Loop

Detect: Agent has taken the same action for N consecutive steps. Response: Force a context reset for that agent — clear the most recent K memories from the active retrieval window (do not delete, just exclude) and trigger a fresh planning call with a reduced context. This breaks the loop without losing history.

### When LLM API Is Rate Limited

Detect: HTTP 429 responses from LLM provider. Response: Implement graduated backoff per agent. Slow the simulation step rate (double the tick interval) to reduce call volume. Surface a status indicator to the user: "Simulation slowing down — API rate limit reached." Resume normal rate once 429s stop.

### When Vector Store Retrieval Degrades

Detect: LLM call quality drops, agents reference irrelevant memories, retrieval latency increases. Response: Trigger a memory consolidation pass for affected agents — score all memories, archive bottom quartile, and re-index the active pool. This is expensive but recovers retrieval quality.

### When the Simulation Step Desynchronizes (Agents Running at Different Rates)

Detect: Some agents have completed many more steps than others (stale agent problem). Response: At each simulation tick, enforce a maximum step differential — agents more than N steps ahead of the slowest agent pause until the group reconverges. This prevents simulation state from fragmenting.

### When User-Injected Events Create Impossible Scenarios

Detect: Agent receives an event that contradicts their current location, known world state, or another agent's simultaneous state. Response: Don't block the injection. Instead, surface the contradiction to the receiving agent in the LLM call context: "You hear that X is happening, but this seems at odds with what you know." Let the agent reason about it — emergent contradiction handling is part of the generative agent value proposition.

---

## Pitfall-to-Phase Mapping

| Pitfall | Phase to Address | Priority |
|---------|-----------------|----------|
| LLM cost explosion from uncapped per-agent calls | Phase 1: Architecture | Critical |
| Sequential agent processing bottleneck | Phase 1-2: Architecture + Agent Loop | Critical |
| FastAPI blocking event loop with sync LLM calls | Phase 2: Agent Loop | Critical |
| Fragile JSON parsing of LLM responses | Phase 2: Agent Loop | Critical |
| Context window accumulation and poisoning | Phase 2: Memory System | High |
| Memory vector store grows without bounds | Phase 2: Memory System | High |
| WebSocket state divergence on reconnection | Phase 2-3: Real-Time Transport | High |
| Agents appearing dead during LLM thinking time | Phase 3: Frontend | High |
| 2D rendering performance with 25 agents | Phase 3: Frontend | High |
| Movement interpolation gap (teleporting agents) | Phase 3: Frontend | Medium |
| Real-time feed information overload | Phase 3: Frontend | Medium |
| Hardcoded prompt templates become load-bearing | Phase 2: Agent Loop | Medium |
| LlamaIndex high RAM overhead | Phase 1-2: Architecture | Medium |
| API keys in browser LocalStorage or logs | Phase 2-3: Security | Medium |
| Embedding model inconsistency across save/load | Phase 4: Persistence | Medium |
| Save/load state brittle to schema changes | Phase 4: Persistence | Medium |
| Conversation initiation without end condition | Phase 2: Agent Loop | Medium |
| No feedback when event is ignored | Phase 3: Frontend | Low |
| Ollama local model latency expectations | Phase 3-4: UX | Low |
| Simulation determinism for debugging | Cross-cutting | Low |

---

## Sources

- [The JSON Parsing Problem That's Killing Your AI Agent Reliability (DEV Community)](https://dev.to/the_bookmaster/the-json-parsing-problem-thats-killing-your-ai-agent-reliability-4gjg) — HIGH confidence (community, multiple upvotes, specific failure modes)
- [The Concurrency Mistake Hiding in Every FastAPI AI Service (JAMwithAI)](https://jamwithai.substack.com/p/the-concurrency-mistake-hiding-in) — HIGH confidence (specific FastAPI async issue, matches official FastAPI docs)
- [How to Build Concurrent Agentic AI Systems Without Losing Control (DEV Community)](https://dev.to/yeahiasarker/how-to-build-concurrent-agentic-ai-systems-without-losing-control-5ag0) — HIGH confidence (multi-source verified)
- [The Hidden Costs of Agentic AI: Why 40% of Projects Fail Before Production (Galileo AI)](https://galileo.ai/blog/hidden-cost-of-agentic-ai) — MEDIUM confidence (vendor blog, but data points verified against other sources)
- [How Long Contexts Fail (dbreunig.com)](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) — HIGH confidence (well-cited technical analysis, matches academic findings on lost-in-middle effect)
- [Why Your Agent's Memory Architecture Is Probably Wrong (DEV Community)](https://dev.to/agentteams/why-your-agents-memory-architecture-is-probably-wrong-55fc) — HIGH confidence (specific anti-patterns, cross-verified with Park et al. memory architecture)
- [AI Agent Cost Optimization Strategies (CallSphere)](https://callsphere.tech/blog/ai-agent-cost-optimization-strategies-production) — MEDIUM confidence (vendor blog, cost numbers corroborated by multiple sources)
- [Backpressure in WebSocket Streams (Skyline Codes)](https://skylinecodes.substack.com/p/backpressure-in-websocket-streams) — HIGH confidence (technical implementation details, matches WebSocket spec behavior)
- [WebSocket Reconnection: State Sync and Recovery Guide (WebSocket.org)](https://websocket.org/guides/reconnection/) — HIGH confidence (official WebSocket.org)
- [FastAPI Mistakes That Kill Your Performance (DEV Community)](https://dev.to/igorbenav/fastapi-mistakes-that-kill-your-performance-2b8k) — HIGH confidence (specific, actionable, cross-verified with FastAPI docs)
- [Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers (arXiv 2603.07670)](https://arxiv.org/html/2603.07670v1) — HIGH confidence (peer-reviewed survey)
- [API Key Exposure in Frontend Applications (Red Secure Tech)](https://www.redsecuretech.co.uk/blog/post/api-key-exposure-in-frontend-applications/614) — HIGH confidence (well-established security principle)
- [LLM Structured Output in 2026 (DEV Community)](https://dev.to/pockit_tools/llm-structured-output-in-2026-stop-parsing-json-with-regex-and-do-it-right-34pk) — MEDIUM confidence (2026 article, matches OpenAI/Anthropic official structured output docs)
- [Park et al. 2023, Generative Agents (referenced paper)](https://arxiv.org/abs/2304.03442) — HIGH confidence (original paper, referenced across all findings)
- [Understanding Backpressure in Real-Time Streaming with WebSockets (Apurav Chauhan / Medium)](https://apuravchauhan.medium.com/understanding-backpressure-in-real-time-streaming-with-websockets-20f504c2d248) — MEDIUM confidence (specific implementation details)
