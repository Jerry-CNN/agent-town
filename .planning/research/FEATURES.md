# Feature Research

**Domain:** LLM-powered agent simulation web app (generative agents, 2D tile-map town)
**Researched:** 2026-04-08
**Confidence:** MEDIUM — Competitor products are sparse; most evidence is from the original research paper, one major open-source fork (ai-town/a16z), and HN community feedback. No polished commercial products dominate this space.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users expect from any agent simulation web app. Missing any of these causes "this feels unfinished" reactions.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 2D tile-map rendering with agent sprites | Reference paper (Smallville) established this as the visual contract for the genre | Medium | Phaser or similar canvas-based renderer; tile collision maps |
| Agents visibly moving between locations | Core "living town" promise — static agents kill the illusion | Medium | Interpolated movement between tile positions; async backend pushes positions |
| Agents performing labeled activities | Users need to see WHAT an agent is doing at a glance, not just where they are | Low-Medium | Emoji above sprite (ai-town pattern) + text label; set from LLM action output |
| Real-time conversation display | Watching agents talk is the main entertainment hook | Medium | Speech bubbles on map OR conversation panel — both seen in demos |
| Activity feed / event log | Users want a running record, especially when there are many agents | Low | Reverse-chronological list of actions, conversations, thoughts |
| Click-to-inspect an agent | HN commenters and ai-town v2 both confirm this as expected | Low-Medium | Sidebar or modal showing: current activity, location, recent memories |
| Event injection (broadcast) | Described as a "wow" feature in the original paper and core to Agent Town's value prop | Medium | Text input → all agents perceive it next step |
| Pause / resume simulation | Standard expectation from any simulation product (flight sim, city builders) | Low | Single button; pause backend processing |
| LLM provider + API key configuration | ai-town, the reference implementation, and user requests all point to this | Low-Medium | Config UI before simulation start; support OpenAI, Anthropic, OpenRouter, Ollama |
| Agent count selection at start | Users want to experiment with population size vs. LLM cost | Low | Slider or number input at simulation setup |
| Save / load simulation state | Users invest time watching a simulation evolve; losing it on refresh is jarring | Medium | Serialize world state to JSON; restore on next visit |
| Simulation speed / tick rate control | Flight sim users universally want this; slow sims are boring, fast ones miss details | Low-Medium | Multiplier on backend step cadence |

---

### Differentiators (Competitive Advantage)

Features that set Agent Town apart from existing demos. Not expected, but create "this is so much better" reactions.

| Feature | Value Proposition | Complexity | Notes |
|---------|------------------|------------|-------|
| Whisper mode (event to one agent) | No existing demo has targeted event injection; organic information spreading through gossip is uniquely compelling | Medium | Route event to single agent's perception stream; they carry it socially |
| Visible agent thought stream | Users in the research paper watched "inner monologue" — seeing an agent reason in real-time builds attachment | High | Requires streaming LLM output into UI; privacy setting (hidden by default?) |
| Memory timeline per agent | Showing WHY an agent did something (what memory triggered it) makes the simulation legible | High | Vector store retrieval results surfaced in UI; high complexity, high payoff |
| Reflection display | When agents form insights ("Isabella has realized that Tom is ambitious"), surfacing this creates narrative moments | Medium | Reflection text stored and shown in activity feed with special formatting |
| Agent-to-agent relationship graph | Showing who knows what about whom surfaces emergent social structure | High | Computed from shared memory entries; D3 or similar graph viz |
| Named thematic locations with purpose | Competitor demos use generic "coffee shop" — a stock exchange + wedding hall makes event injection obvious and fun | Medium | Requires map design investment; major brand differentiator |
| Cost estimation / token counter | Users are anxious about LLM costs; showing estimated cost per step removes that anxiety | Low-Medium | Token count from LLM responses × current model pricing |
| Event injection history | Let users replay what events they injected; useful for "I wonder what would happen if…" experiments | Low | Persist injection log; re-inject button |
| Per-agent speech style / personality | Commenters complained existing demos felt "boringly nice" — visible personality differentiation makes agents feel real | Medium | Seed prompts drive this; surfaced in agent profile sidebar |
| Conversation transcript archive | Full conversation logs per agent pair, accessible after the fact | Medium | Stored server-side; accessible from agent inspector |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem obvious to request but cause more problems than they solve.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| User-created custom maps | Tile editor UX is a product unto itself; maintenance burden is high; one great map beats infinite mediocre ones | Ship one carefully designed map with all relevant location types; extensibility later |
| Real-time multiplayer shared simulation | Requires conflict resolution, agent ownership, turn-ordering — dramatically increases complexity; doesn't validate core concept | Design state to not block multiplayer later (no single-process assumptions), but don't build it in v1 |
| Hosted LLM (built-in API) | Adds cost, billing, rate limiting, abuse prevention — turns a playground into a SaaS with infra ops | Users bring their own keys; show cost estimates to set expectations |
| Voice/audio output | TTS adds latency, cost, and distracts from the visual simulation; text bubbles suffice | Text-only; users read at their own pace |
| Natural language map editing | "Add a hospital" via prompt is tempting but brittle; map is a creative asset, not a config | Tile editor or hardcoded map variants |
| Mobile-first design | Tile maps on mobile are cramped; managing a simulation is a deliberate desktop activity | Web-first; basic responsive layout is fine, but don't optimize for mobile UX |
| Agent direct control (player-as-agent) | ai-town v2 added player movement; it muddles the observer/director role and adds collision/sync complexity | Keep user as director (event injection) not player; "inner voice" directive is the right interaction model |
| Real-time LLM streaming for all agents | Streaming all 5-25 agents simultaneously is visually overwhelming and resource-intensive | Show completed actions; stream selectively for inspected agent |
| Automated social media sharing | Feature requests exist but engagement loop is speculative; not core to value prop | Add later if organic sharing patterns emerge |

---

## Feature Dependencies

```
LLM Provider Config ──────────────────────┐
                                           ▼
Agent Count Config ───────────────────► Simulation Start
                                           │
                                           ▼
                                    Tile Map Rendering
                                           │
                          ┌────────────────┼────────────────┐
                          ▼                ▼                ▼
                   Agent Movement    Activity Feed    Event Injection
                          │                │                │
                          ▼                ▼                ▼
              Click-to-Inspect Agent   Reflection     Whisper Mode
                          │            Display              │
                          ▼                                 ▼
                   Memory Timeline              Agent carries info
                                               through conversations

Save/Load State ──► depends on: all core simulation state (agents, memories, positions, step count)

Visible Thought Stream ──► depends on: agent inspector panel (click-to-inspect)
Memory Timeline ──────────► depends on: agent inspector panel (click-to-inspect)
Conversation Transcript ──► depends on: activity feed infrastructure

Cost Estimation ──► depends on: LLM provider config (to know pricing)
Event Injection History ──► depends on: event injection
```

---

## MVP Definition

### Launch With (v1)

The minimal set that delivers the core promise: "type an event, watch agents react."

1. **2D tile-map rendering** with agent sprites and movement
2. **Agents visibly acting** — labeled activities, emoji overlay
3. **Real-time conversation display** — speech bubbles or feed
4. **Activity feed** — running log of actions + conversations
5. **Broadcast event injection** — text input → all agents perceive
6. **Whisper event injection** — directed to one agent (core differentiator, v1 because it's central to the concept)
7. **Click-to-inspect agent** — basic sidebar: current activity, location, last few memories
8. **LLM provider configuration** — API key, model selection (OpenAI / Anthropic / OpenRouter / Ollama)
9. **Agent count selection** — choose at simulation start
10. **Pause / resume** — single button
11. **Fresh simulation by default; manual save/load** — serialize to JSON file

### Add After Validation (v1.x)

Features that enhance the core loop once it's confirmed to work and be engaging.

- **Visible thought stream** on inspected agent — high delight, post-v1
- **Simulation speed control** — multiplier on tick rate
- **Reflection display** — surface insight moments in activity feed
- **Event injection history** — log of past events + re-inject button
- **Cost estimation / token counter** — reassure cost-conscious users
- **Per-agent personality detail** in inspector panel — seed prompt visible

### Future Consideration (v2+)

Features that require validation that users want them, or significant engineering investment.

- **Memory timeline** — full vector store visualization per agent
- **Agent-to-agent relationship graph** — emergent social structure viz
- **Conversation transcript archive** — searchable full conversation history
- **Alternative map themes** — different town archetypes
- **Export simulation replay** — record + play back a session
- **Multiplayer shared simulation** — architecture must not block this

---

## Feature Prioritization Matrix

| Feature | User Value | Build Effort | v1? |
|---------|-----------|--------------|-----|
| 2D tile-map rendering | Critical | Medium | YES |
| Agent movement + activity labels | Critical | Medium | YES |
| Activity feed | High | Low | YES |
| Broadcast event injection | Critical | Medium | YES |
| Whisper event injection | High (differentiator) | Medium | YES |
| LLM provider config | Critical (required) | Low-Medium | YES |
| Agent count config | High | Low | YES |
| Pause/resume | High | Low | YES |
| Save/load state | High | Medium | YES |
| Click-to-inspect | High | Low-Medium | YES |
| Conversation display | High | Medium | YES |
| Simulation speed control | Medium | Low | v1.x |
| Reflection display | Medium | Low | v1.x |
| Visible thought stream | High (differentiator) | High | v1.x |
| Cost estimation | Medium | Low | v1.x |
| Event injection history | Medium | Low | v1.x |
| Memory timeline | Medium (niche) | High | v2+ |
| Relationship graph | Medium (niche) | High | v2+ |
| Multiplayer | Low (v1) | Very High | v2+ |
| Custom maps | Low (v1) | Very High | v2+ |

---

## Competitor Feature Analysis

| Feature | Park et al. (Smallville, 2023) | a16z ai-town | Agent Town (target) |
|---------|-------------------------------|--------------|---------------------|
| 2D tile-map (browser) | YES (Phaser) | YES (Phaser) | YES |
| Agent sprites + movement | YES | YES | YES |
| Activity labels / emoji | YES | YES (emoji) | YES |
| Real-time (not batch) | NO (batch + replay) | YES | YES |
| Activity feed | YES (replay-only) | Partial | YES |
| Agent inspector (click) | NO | YES (v2) | YES |
| Broadcast event injection | YES (via backend command) | NO | YES |
| Whisper event injection | YES ("inner voice" directive) | NO | YES |
| Object state manipulation | YES | NO | Deferred |
| User-as-agent embodiment | YES | YES (v2 walk-around) | NO (anti-feature) |
| LLM provider config | NO (hardcoded) | YES | YES |
| Agent count config | NO | NO (hardcoded chars) | YES |
| Pause/resume | Partial (batch control) | YES | YES |
| Save/load state | YES (batch checkpoints) | YES (archive) | YES |
| Simulation speed | YES (replay speed) | NO | YES (v1.x) |
| Thought stream visible | NO (research-only) | NO | YES (v1.x) |
| Memory timeline UI | NO | NO | v2+ |
| Reflection display | NO | NO | YES (v1.x) |
| Cost estimation | NO | NO | YES (v1.x) |
| Multiplayer | NO | Architecture supports | NO (v1) |
| Custom maps | NO | YES (Tiled editor) | NO (v1) |

**Competitive gap:** No existing public demo combines broadcast + whisper event injection with real-time streaming, agent inspection, and configurable LLM providers in a single product. Agent Town has clear differentiation space.

**Key insight from HN feedback on ai-town:** Users want agents to feel distinct in personality, want to understand emergent behavior (not just observe it), and want interaction to feel meaningful — not just watch bots walk around. The activity feed + event injection + inspector panel combination directly addresses this.

---

## Sources

- [Generative Agents paper (Park et al., 2023) — ACM UIST](https://dl.acm.org/doi/abs/10.1145/3586183.3606763) — HIGH confidence; primary source for interaction model (inner voice, user embodiment, object manipulation)
- [joonspk-research/generative_agents GitHub](https://github.com/joonspk-research/generative_agents) — HIGH confidence; reference implementation features (replay, demo mode, batch commands)
- [a16z-infra/ai-town GitHub](https://github.com/a16z-infra/ai-town) — HIGH confidence; most developed public fork with UX observations
- [AI Town v2 (Convex blog)](https://stack.convex.dev/ai-town-v2) — MEDIUM confidence; describes v2 player movement and world editing features
- [Show HN: AI-town (Hacker News thread)](https://news.ycombinator.com/item?id=37128293) — MEDIUM confidence; community feedback on missing features and desired behaviors
- [101dotxyz/GPTeam GitHub](https://github.com/101dotxyz/GPTeam) — MEDIUM confidence; confirms CLI-only UX is insufficient for consumer products
- [Agent UX Patterns — Hatchworks](https://hatchworks.com/blog/ai-agents/agent-ux-patterns/) — MEDIUM confidence; informs anti-patterns around chat-first UX and invisible state
- [7 UX Patterns for Ambient AI Agents](https://www.bprigent.com/article/7-ux-patterns-for-human-oversight-in-ambient-ai-agents) — MEDIUM confidence; informs "make work visible" pattern for activity feed design
- [Generative Agents Smallville paper review — Medium](https://artgor.medium.com/paper-review-generative-agents-interactive-simulacra-of-human-behavior-cc5f8294b4ac) — MEDIUM confidence; secondary source confirming inner voice / user intervention mechanics
