"""Unified Agent class — single source of truth for agent identity and runtime state.

D-01: All fields mutable (including identity fields like traits).
D-02: Memory accessed via store.py module functions — NEVER instantiate chromadb here.
D-03: No imports from backend.simulation — Maze passed via method parameters.
D-04: Cognition methods are thin wrappers delegating to existing standalone functions.
      Required wrappers per D-04: perceive(), decide(), converse().

Replaces the separate AgentConfig + AgentState dual-dict pattern in
SimulationEngine. Field names match AgentState exactly for mechanical migration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.schemas import AgentConfig, ScheduleEntry

if TYPE_CHECKING:
    from backend.simulation.world import Maze


@dataclass
class Agent:
    """Unified agent: identity (AgentConfig) + runtime state (was AgentState).

    Replaces the separate AgentConfig + AgentState dual-dict pattern in
    SimulationEngine. Field names match AgentState exactly for mechanical
    migration.
    """
    # --- Static identity (from AgentConfig JSON) ---
    name: str
    config: AgentConfig          # kept as sub-object, not flattened

    # --- Runtime state (was AgentState fields) ---
    coord: tuple[int, int]
    path: list[tuple[int, int]] = field(default_factory=list)
    current_activity: str = ""
    schedule: list[ScheduleEntry] = field(default_factory=list)

    # --- Per-sector gating state (D-08, Phase 9) ---
    last_sector: str | None = None
    had_new_perceptions: bool = True

    # --- Schedule-change gating (Codex P1-6) ---
    # Tracks the 'describe' of the last schedule entry seen by _agent_step so
    # the engine can detect block advancement without a dynamic attribute set.
    _last_schedule_block: str | None = field(default=None, repr=False)

    # --- D-04: Cognition wrappers (thin delegation) ---

    def perceive(self, maze: "Maze", all_agents: dict) -> "PerceptionResult":
        """Delegate to cognition.perceive.perceive() with self fields.

        Uses inline import to avoid module-level dependency on cognition
        (keeps import graph clean for testing).
        """
        from backend.agents.cognition.perceive import perceive as _perceive
        return _perceive(
            agent_coord=self.coord,
            agent_name=self.name,
            maze=maze,
            all_agents=all_agents,
        )

    async def decide(self, simulation_id: str, perception, **kwargs) -> "AgentAction | None":
        """Delegate to cognition.decide.decide_action() with self fields.

        Returns AgentAction or None (None = gating skip per D-08, Plan 09-02).
        Caller interprets None as "keep current action" — zero LLM cost for
        ticks where the agent's sector, perceptions, and schedule are all stable.

        Extra kwargs (last_sector, new_perceptions, schedule_changed) are forwarded
        to decide_action to support the per-sector gating logic (Codex P2-7).
        """
        from backend.agents.cognition.decide import decide_action
        return await decide_action(
            simulation_id=simulation_id,
            agent_name=self.name,
            agent_scratch=self.config.scratch,
            agent_spatial=self.config.spatial,
            current_activity=self.current_activity,
            perception=perception,
            current_schedule=self.schedule,
            **kwargs,
        )

    async def converse(
        self,
        other: "Agent",
        maze: "Maze",
        simulation_id: str,
    ) -> dict | None:
        """Attempt and run a conversation with another agent (D-04).

        Orchestrates the two-phase conversation flow from converse.py:
        1. attempt_conversation() — cooldown + LLM gate check
        2. run_conversation() — full multi-turn exchange if gate passes

        Returns the run_conversation() result dict if a conversation occurred,
        or None if the attempt gate returned False.

        The location string is derived from the tile at the agent's current
        coordinate via tile.get_address(as_list=False), matching the pattern
        used by perceive.py.
        """
        from backend.agents.cognition.converse import attempt_conversation, run_conversation

        # Derive location label from tile address — same as perceive.py:95
        # maze.tiles is list[list[Tile]] (2D grid), use tile_at() not .get()
        try:
            tile = maze.tile_at(self.coord)
            if tile.address and len(tile.address) >= 2:
                location = tile.get_address(as_list=False)
            else:
                location = "unknown location"
        except (IndexError, AttributeError):
            location = "unknown location"

        should_talk = await attempt_conversation(
            simulation_id=simulation_id,
            agent_name=self.name,
            agent_scratch=self.config.scratch,
            other_name=other.name,
            other_activity=other.current_activity,
            agent_current_activity=self.current_activity,
            location=location,
        )

        if not should_talk:
            return None

        return await run_conversation(
            simulation_id=simulation_id,
            agent_a_name=self.name,
            agent_a_scratch=self.config.scratch,
            agent_b_name=other.name,
            agent_b_scratch=other.config.scratch,
            location=location,
            remaining_schedule_a=list(self.schedule),
            remaining_schedule_b=list(other.schedule),
        )

    async def reflect(self) -> None:
        """Reflection stub — planned for Phase 11.

        Reflection (generating high-level insights from the memory stream) is
        a Phase 11 feature. This stub satisfies ARCH-02's method existence
        requirement while clearly marking the scope boundary.
        """
        raise NotImplementedError("Reflection is Phase 11 scope")
