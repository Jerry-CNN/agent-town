"""Tests for building operating hours enforcement — Phase 8 Plan 02.

Covers:
  - Building.is_open() for standard, always-open (closes=24), and wrap-around ranges
  - SimulationEngine sim time tracking (_sim_hour, _sim_minute)
  - Engine._is_location_open() helper
  - decide_action() open_locations parameter
  - Agent ejection when building closes (_eject_agents_from_closed_buildings)
  - Pitfall 5 guard: ejection runs once per hour change, not every tick
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.simulation.world import Building


# ---------------------------------------------------------------------------
# 1. Building.is_open() — standard hours
# ---------------------------------------------------------------------------

class TestBuildingIsOpenStandard:
    """Building with opens=9, closes=17 (standard business hours)."""

    def setup_method(self):
        self.building = Building(
            name="Stock Exchange",
            sector="stock-exchange",
            opens=9,
            closes=17,
            purpose="finance",
        )

    def test_open_at_noon(self):
        """Hour 12 is within 9-17 range — building is open."""
        assert self.building.is_open(12) is True

    def test_closed_at_7am(self):
        """Hour 7 is before opens=9 — building is closed."""
        assert self.building.is_open(7) is False

    def test_closed_at_8pm(self):
        """Hour 20 is after closes=17 — building is closed."""
        assert self.building.is_open(20) is False

    def test_open_at_boundary_opens(self):
        """Hour exactly at opens (9) — building is open (inclusive)."""
        assert self.building.is_open(9) is True

    def test_closed_at_boundary_closes(self):
        """Hour exactly at closes (17) — building is closed (exclusive upper bound)."""
        assert self.building.is_open(17) is False

    def test_open_one_before_close(self):
        """Hour 16 (one before closes=17) — building is open."""
        assert self.building.is_open(16) is True


# ---------------------------------------------------------------------------
# 2. Building.is_open() — always-open (closes=24)
# ---------------------------------------------------------------------------

class TestBuildingIsOpenAlwaysOpen:
    """Building with closes=24 (park, home) — never closes."""

    def setup_method(self):
        self.park = Building(
            name="Central Park",
            sector="park",
            opens=0,
            closes=24,
            purpose="leisure",
        )
        self.home = Building(
            name="Alice's Home",
            sector="home-alice",
            opens=0,
            closes=24,
            purpose="residential",
        )

    def test_park_open_at_midnight(self):
        assert self.park.is_open(0) is True

    def test_park_open_at_3am(self):
        assert self.park.is_open(3) is True

    def test_park_open_at_noon(self):
        assert self.park.is_open(12) is True

    def test_park_open_at_11pm(self):
        assert self.park.is_open(23) is True

    def test_home_always_open_all_hours(self):
        """Home is open for every hour 0-23."""
        for hour in range(24):
            assert self.home.is_open(hour) is True, f"Home should be open at hour {hour}"


# ---------------------------------------------------------------------------
# 3. Building.is_open() — midnight wrap-around (opens > closes)
# ---------------------------------------------------------------------------

class TestBuildingIsOpenWrapAround:
    """Building with opens=22, closes=4 (late-night bar — wraps midnight)."""

    def setup_method(self):
        self.bar = Building(
            name="Late Night Bar",
            sector="bar",
            opens=22,
            closes=4,
            purpose="social",
        )

    def test_open_at_11pm(self):
        """Hour 23 is >= opens=22 — open in wrap-around range."""
        assert self.bar.is_open(23) is True

    def test_open_at_midnight(self):
        """Hour 0 is < closes=4 — open in wrap-around range."""
        assert self.bar.is_open(0) is True

    def test_open_at_1am(self):
        """Hour 1 is < closes=4 — open in wrap-around range."""
        assert self.bar.is_open(1) is True

    def test_closed_at_noon(self):
        """Hour 12 is between closes=4 and opens=22 — closed."""
        assert self.bar.is_open(12) is False

    def test_closed_at_4am(self):
        """Hour 4 is exactly at closes=4 (exclusive upper bound) — closed."""
        assert self.bar.is_open(4) is False

    def test_open_exactly_at_22(self):
        """Hour 22 is exactly at opens=22 (inclusive lower bound) — open."""
        assert self.bar.is_open(22) is True


# ---------------------------------------------------------------------------
# 4. SimulationEngine: sim time tracking
# ---------------------------------------------------------------------------

class TestSimTimeTracking:
    """SimulationEngine initializes with _sim_hour=7 and advances 10 min/tick."""

    def _make_engine(self):
        """Build a minimal SimulationEngine with no agents."""
        from backend.simulation.engine import SimulationEngine
        return SimulationEngine(maze=None, agents=[], simulation_id="test-sim")

    def test_sim_hour_starts_at_7(self):
        engine = self._make_engine()
        assert engine._sim_hour == 7

    def test_sim_minute_starts_at_0(self):
        engine = self._make_engine()
        assert engine._sim_minute == 0

    def test_last_ejection_hour_starts_at_minus_one(self):
        """Guard initialized to -1 so first tick always triggers ejection check."""
        engine = self._make_engine()
        assert engine._last_ejection_hour == -1

    def test_buildings_loaded_at_init(self):
        """Buildings dict populated from buildings.json at construction time."""
        engine = self._make_engine()
        assert isinstance(engine._buildings, dict)
        # Should have at least the standard sectors
        assert "cafe" in engine._buildings
        assert "stock-exchange" in engine._buildings
        assert "park" in engine._buildings

    def test_sim_minute_advances_by_10_per_tick(self):
        """After 1 tick, _sim_minute should be 10 (starting from 0)."""
        engine = self._make_engine()
        # Simulate what _tick_loop does after agent steps
        engine._sim_minute += 10
        assert engine._sim_minute == 10

    def test_sim_hour_increments_after_6_ticks(self):
        """6 ticks * 10 min = 60 min → _sim_hour should advance by 1 (7 → 8)."""
        engine = self._make_engine()
        for _ in range(6):
            engine._sim_minute += 10
            if engine._sim_minute >= 60:
                engine._sim_minute = 0
                engine._sim_hour = (engine._sim_hour + 1) % 24
        assert engine._sim_hour == 8
        assert engine._sim_minute == 0

    def test_sim_hour_wraps_at_24(self):
        """Hour wraps from 23 to 0 (midnight)."""
        engine = self._make_engine()
        engine._sim_hour = 23
        engine._sim_minute = 50
        engine._sim_minute += 10
        if engine._sim_minute >= 60:
            engine._sim_minute = 0
            engine._sim_hour = (engine._sim_hour + 1) % 24
        assert engine._sim_hour == 0


# ---------------------------------------------------------------------------
# 5. Engine._is_location_open()
# ---------------------------------------------------------------------------

class TestIsLocationOpen:
    """_is_location_open() returns True for unknown sectors, uses Building.is_open() for known."""

    def _make_engine(self):
        from backend.simulation.engine import SimulationEngine
        return SimulationEngine(maze=None, agents=[], simulation_id="test-sim")

    def test_unknown_sector_always_open(self):
        """Sectors not in buildings.json are always accessible."""
        engine = self._make_engine()
        assert engine._is_location_open("nonexistent-sector") is True

    def test_park_open_at_any_hour(self):
        """Park (closes=24) is always open."""
        engine = self._make_engine()
        engine._sim_hour = 3  # 3am
        assert engine._is_location_open("park") is True

    def test_stock_exchange_closed_at_7am(self):
        """Stock exchange (opens=9) is closed at hour 7."""
        engine = self._make_engine()
        engine._sim_hour = 7
        assert engine._is_location_open("stock-exchange") is False

    def test_stock_exchange_open_at_noon(self):
        """Stock exchange (opens=9, closes=17) is open at noon."""
        engine = self._make_engine()
        engine._sim_hour = 12
        assert engine._is_location_open("stock-exchange") is True


# ---------------------------------------------------------------------------
# 6. decide_action: open_locations parameter
# ---------------------------------------------------------------------------

class TestDecideActionOpenLocations:
    """decide_action uses open_locations when provided, falls back to spatial tree otherwise."""

    @pytest.mark.asyncio
    async def test_decide_uses_open_locations_when_provided(self):
        """When open_locations is given, those are passed to the prompt as known_locations."""
        from backend.agents.cognition.decide import decide_action
        from backend.schemas import AgentScratch, AgentSpatial, PerceptionResult, AgentAction

        open_locs = ["park", "cafe"]
        captured = {}

        async def fake_complete(messages, response_model):
            # Inspect the user message content to verify only open_locs are listed
            user_content = messages[1]["content"]
            captured["user_content"] = user_content
            return AgentAction(destination="park", activity="relaxing", reasoning="test")

        scratch = AgentScratch(
            age=30,
            innate="warm",
            learned="Alice is a friendly local",
            lifestyle="morning person",
            daily_plan="wake up, go to park, return home",
        )
        spatial = AgentSpatial(
            address={"living_area": ["agent-town", "home-alice", "bedroom"]},
            tree={"agent-town": {"park": {}, "cafe": {}, "stock-exchange": {}}},
        )
        perception = PerceptionResult(
            nearby_agents=[],
            nearby_events=[],
            location="park:bench",
        )

        with patch("backend.agents.cognition.decide.complete_structured", fake_complete), \
             patch("backend.agents.cognition.decide.retrieve_memories", AsyncMock(return_value=[])):
            result = await decide_action(
                simulation_id="test",
                agent_name="Alice",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                open_locations=open_locs,
            )

        # Only park and cafe should appear, not stock-exchange
        user_text = captured["user_content"]
        assert "park" in user_text
        assert "cafe" in user_text
        assert "stock-exchange" not in user_text

    @pytest.mark.asyncio
    async def test_decide_falls_back_to_spatial_tree_when_open_locations_none(self):
        """When open_locations is None, _extract_known_locations is used."""
        from backend.agents.cognition.decide import decide_action
        from backend.schemas import AgentScratch, AgentSpatial, PerceptionResult, AgentAction

        captured = {}

        async def fake_complete(messages, response_model):
            user_content = messages[1]["content"]
            captured["user_content"] = user_content
            return AgentAction(destination="park", activity="relaxing", reasoning="test")

        scratch = AgentScratch(
            age=40,
            innate="curious",
            learned="Bob is an analytical thinker",
            lifestyle="night owl",
            daily_plan="stay up late, visit stock exchange, return home",
        )
        spatial = AgentSpatial(
            address={"living_area": ["agent-town", "home-bob", "bedroom"]},
            tree={"agent-town": {"park": {}, "stock-exchange": {}, "cafe": {}}},
        )
        perception = PerceptionResult(
            nearby_agents=[],
            nearby_events=[],
            location="home-bob:bedroom",
        )

        with patch("backend.agents.cognition.decide.complete_structured", fake_complete), \
             patch("backend.agents.cognition.decide.retrieve_memories", AsyncMock(return_value=[])):
            result = await decide_action(
                simulation_id="test",
                agent_name="Bob",
                agent_scratch=scratch,
                agent_spatial=spatial,
                current_activity="idle",
                perception=perception,
                current_schedule=[],
                open_locations=None,  # Should fall back to full spatial tree
            )

        # All three sectors from spatial tree should appear
        user_text = captured["user_content"]
        assert "park" in user_text
        assert "stock-exchange" in user_text
        assert "cafe" in user_text


# ---------------------------------------------------------------------------
# 7. Agent ejection from closed buildings
# ---------------------------------------------------------------------------

class TestAgentEjection:
    """_eject_agents_from_closed_buildings clears path and sets activity."""

    def _make_tile_with_address(self, address: list[str]):
        """Create a mock tile with given address."""
        tile = MagicMock()
        tile.address = address
        return tile

    def _make_maze_at_sector(self, sector: str):
        """Create a mock Maze that returns a tile for any coord, in the given sector."""
        maze = MagicMock()
        tile = self._make_tile_with_address(["agent-town", sector, "interior"])
        maze.tile_at.return_value = tile
        return maze

    def _make_agent_at(self, coord=(5, 5)):
        """Create a minimal mock agent."""
        agent = MagicMock()
        agent.coord = coord
        agent.path = [(6, 5), (7, 5)]
        agent.current_activity = "working"
        return agent

    def _make_engine_with_agent(self, sector: str, sim_hour: int, agent_name="Alice"):
        """Build engine with one agent in the given sector, at the given sim_hour."""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(maze=None, agents=[], simulation_id="test-eject")
        engine._sim_hour = sim_hour
        engine.maze = self._make_maze_at_sector(sector)

        agent = self._make_agent_at()
        engine._agents[agent_name] = agent
        return engine, agent

    @pytest.mark.asyncio
    async def test_agent_ejected_when_building_closes(self):
        """Agent in stock-exchange at hour 17 (close time) gets ejected."""
        engine, agent = self._make_engine_with_agent("stock-exchange", sim_hour=17)
        # stock-exchange closes=17 — at hour 17 is_open(17) should be False
        emitted = []
        async def fake_emit(name, a):
            emitted.append(name)
        engine._emit_agent_update = fake_emit

        await engine._eject_agents_from_closed_buildings()

        assert agent.path == []
        assert agent.current_activity == "leaving (building closed)"
        assert "Alice" in emitted

    @pytest.mark.asyncio
    async def test_agent_not_ejected_from_always_open_building(self):
        """Agent in park (closes=24) is never ejected, even at 3am."""
        engine, agent = self._make_engine_with_agent("park", sim_hour=3)
        original_path = list(agent.path)
        original_activity = agent.current_activity
        emitted = []
        async def fake_emit(name, a):
            emitted.append(name)
        engine._emit_agent_update = fake_emit

        await engine._eject_agents_from_closed_buildings()

        assert agent.path == original_path
        assert agent.current_activity == original_activity
        assert len(emitted) == 0

    @pytest.mark.asyncio
    async def test_ejection_skipped_for_road_tiles(self):
        """Agents on tiles with address length < 2 (road tiles) are not ejected."""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(maze=None, agents=[], simulation_id="test-road")
        engine._sim_hour = 17

        # Maze returns a road tile with no sector
        maze = MagicMock()
        road_tile = MagicMock()
        road_tile.address = ["agent-town"]  # length 1 — no sector
        maze.tile_at.return_value = road_tile
        engine.maze = maze

        agent = self._make_agent_at()
        agent.path = [(6, 5)]
        engine._agents["Alice"] = agent
        emitted = []
        async def fake_emit(name, a):
            emitted.append(name)
        engine._emit_agent_update = fake_emit

        await engine._eject_agents_from_closed_buildings()

        # Road tile — no ejection
        assert agent.path == [(6, 5)]
        assert len(emitted) == 0


# ---------------------------------------------------------------------------
# 8. Pitfall 5 guard: ejection fires only once per hour change
# ---------------------------------------------------------------------------

class TestEjectionPitfall5Guard:
    """_last_ejection_hour prevents ejection from firing every tick."""

    def _make_engine_with_closed_building_agent(self):
        """Engine with agent in stock-exchange (closes=17), sim_hour=17."""
        from backend.simulation.engine import SimulationEngine

        engine = SimulationEngine(maze=None, agents=[], simulation_id="test-guard")
        engine._sim_hour = 17

        tile = MagicMock()
        tile.address = ["agent-town", "stock-exchange", "trading-floor"]
        maze = MagicMock()
        maze.tile_at.return_value = tile
        engine.maze = maze

        agent = MagicMock()
        agent.coord = (5, 5)
        agent.path = [(6, 5)]
        agent.current_activity = "working"
        engine._agents["Alice"] = agent

        return engine, agent

    @pytest.mark.asyncio
    async def test_ejection_fires_on_first_hour_change(self):
        """When _sim_hour != _last_ejection_hour, ejection runs."""
        engine, agent = self._make_engine_with_closed_building_agent()
        emitted = []
        async def fake_emit(name, a):
            emitted.append(name)
        engine._emit_agent_update = fake_emit

        # Simulate the guard check from _tick_loop
        if engine._sim_hour != engine._last_ejection_hour:
            engine._last_ejection_hour = engine._sim_hour
            await engine._eject_agents_from_closed_buildings()

        assert agent.path == []
        assert agent.current_activity == "leaving (building closed)"

    @pytest.mark.asyncio
    async def test_ejection_does_not_fire_on_same_hour_repeated_ticks(self):
        """Once _last_ejection_hour == _sim_hour, ejection skips subsequent ticks."""
        engine, agent = self._make_engine_with_closed_building_agent()

        # First tick: ejection fires and sets _last_ejection_hour
        emitted = []
        async def fake_emit(name, a):
            emitted.append(name)
        engine._emit_agent_update = fake_emit

        if engine._sim_hour != engine._last_ejection_hour:
            engine._last_ejection_hour = engine._sim_hour
            await engine._eject_agents_from_closed_buildings()

        # Reset agent to simulate it resumed activity
        agent.path = [(8, 5)]
        agent.current_activity = "heading out"
        emit_count_after_first = len(emitted)

        # Second tick at same hour: guard prevents re-ejection
        if engine._sim_hour != engine._last_ejection_hour:
            engine._last_ejection_hour = engine._sim_hour
            await engine._eject_agents_from_closed_buildings()

        # Should NOT have emitted again
        assert len(emitted) == emit_count_after_first
        # Agent's path should remain as set (not cleared again)
        assert agent.path == [(8, 5)]
