import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSimulationStore } from "../store/simulationStore";
import { TILE_SIZE } from "../types";

beforeEach(() => {
  useSimulationStore.getState().reset();
  // Clear the send function ref between tests
  useSimulationStore.getState().setSendMessage(null);
});

describe("simulationStore dispatch actions", () => {
  it("Test 1: updateAgentsFromSnapshot with 3 agents sets store.agents to Record with 3 entries keyed by name", () => {
    const store = useSimulationStore.getState();
    store.updateAgentsFromSnapshot([
      { name: "Alice Chen", coord: [10, 20], activity: "walking" },
      { name: "Bob Smith", coord: [5, 8], activity: "sleeping" },
      { name: "Carla Diaz", coord: [0, 0], activity: "chatting" },
    ]);
    const agents = useSimulationStore.getState().agents;
    expect(Object.keys(agents)).toHaveLength(3);
    expect(agents["Alice Chen"]).toBeDefined();
    expect(agents["Bob Smith"]).toBeDefined();
    expect(agents["Carla Diaz"]).toBeDefined();
    // Coord to pixel: coord[0] * TILE_SIZE, coord[1] * TILE_SIZE
    expect(agents["Alice Chen"].position).toEqual({ x: 10 * TILE_SIZE, y: 20 * TILE_SIZE });
    expect(agents["Alice Chen"].activity).toBe("walking");
    expect(agents["Bob Smith"].position).toEqual({ x: 5 * TILE_SIZE, y: 8 * TILE_SIZE });
    expect(agents["Carla Diaz"].position).toEqual({ x: 0 * TILE_SIZE, y: 0 * TILE_SIZE });
  });

  it("Test 2: updateAgentPosition updates a single agent's position and activity", () => {
    const store = useSimulationStore.getState();
    store.updateAgentsFromSnapshot([
      { name: "Alice Chen", coord: [10, 20], activity: "walking" },
    ]);
    store.updateAgentPosition("Alice Chen", [15, 42], "walking");
    const agent = useSimulationStore.getState().agents["Alice Chen"];
    expect(agent.position).toEqual({ x: 15 * TILE_SIZE, y: 42 * TILE_SIZE });
    expect(agent.activity).toBe("walking");
  });

  it("Test 3: updateAgentPosition for non-existent agent creates a new entry", () => {
    const store = useSimulationStore.getState();
    store.updateAgentPosition("NewAgent", [3, 7], "running");
    const agent = useSimulationStore.getState().agents["NewAgent"];
    expect(agent).toBeDefined();
    expect(agent.position).toEqual({ x: 3 * TILE_SIZE, y: 7 * TILE_SIZE });
    expect(agent.activity).toBe("running");
    expect(agent.name).toBe("NewAgent");
  });

  it("Test 4: setPaused(true) sets store.isPaused to true", () => {
    const store = useSimulationStore.getState();
    expect(useSimulationStore.getState().isPaused).toBe(false);
    store.setPaused(true);
    expect(useSimulationStore.getState().isPaused).toBe(true);
    store.setPaused(false);
    expect(useSimulationStore.getState().isPaused).toBe(false);
  });

  it("Test 5: appendFeed only accepts conversation and event types; updateAgentsFromSnapshot does not add to feed", () => {
    const store = useSimulationStore.getState();
    // updateAgentsFromSnapshot does NOT add to feed
    store.updateAgentsFromSnapshot([
      { name: "Alice Chen", coord: [10, 20], activity: "walking" },
    ]);
    expect(useSimulationStore.getState().feed).toHaveLength(0);
    // conversation and event types DO add to feed
    store.appendFeed({ type: "conversation", payload: { turns: [] }, timestamp: 1000 });
    expect(useSimulationStore.getState().feed).toHaveLength(1);
    store.appendFeed({ type: "event", payload: { text: "A wedding is happening" }, timestamp: 2000 });
    expect(useSimulationStore.getState().feed).toHaveLength(2);
  });

  it("Test 6: setSendMessage stores a function ref; getSendMessage returns it", () => {
    const store = useSimulationStore.getState();
    const mockSend = vi.fn();
    store.setSendMessage(mockSend);
    const retrieved = getSendMessage();
    expect(retrieved).toBe(mockSend);
    // Clear it
    store.setSendMessage(null);
    expect(getSendMessage()).toBeNull();
  });
});

// Import the module-level getter for the send function
import { getSendMessage } from "../store/simulationStore";
