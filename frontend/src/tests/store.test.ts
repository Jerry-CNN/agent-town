import { beforeEach, describe, expect, it } from "vitest";
import { useSimulationStore } from "../store/simulationStore";

beforeEach(() => {
  useSimulationStore.getState().reset();
});

describe("simulationStore", () => {
  it("Test 1: agents initializes as empty object", () => {
    const state = useSimulationStore.getState();
    expect(state.agents).toEqual({});
  });

  it("Test 2: setSelectedAgent sets and clears selectedAgentId", () => {
    const store = useSimulationStore.getState();
    store.setSelectedAgent("agent-1");
    expect(useSimulationStore.getState().selectedAgentId).toBe("agent-1");
    store.setSelectedAgent(null);
    expect(useSimulationStore.getState().selectedAgentId).toBeNull();
  });

  it("Test 3: appendFeed adds to feed array correctly", () => {
    const store = useSimulationStore.getState();
    const msg1 = { type: "event" as const, payload: { text: "hello" }, timestamp: 1000 };
    const msg2 = { type: "agent_update" as const, payload: { id: "a1" }, timestamp: 2000 };
    store.appendFeed(msg1);
    expect(useSimulationStore.getState().feed).toHaveLength(1);
    store.appendFeed(msg2);
    expect(useSimulationStore.getState().feed).toHaveLength(2);
    expect(useSimulationStore.getState().feed[0]).toEqual(msg1);
    expect(useSimulationStore.getState().feed[1]).toEqual(msg2);
  });

  it("Test 4: reset returns all state to initial values", () => {
    const store = useSimulationStore.getState();
    store.setSelectedAgent("agent-1");
    store.appendFeed({ type: "ping", payload: {}, timestamp: 999 });
    store.setConnected(true);
    store.reset();
    const state = useSimulationStore.getState();
    expect(state.agents).toEqual({});
    expect(state.feed).toEqual([]);
    expect(state.selectedAgentId).toBeNull();
    expect(state.isConnected).toBe(false);
    expect(state.isPaused).toBe(false);
  });

  it("Test 5: providerConfig initializes as null and setProviderConfig stores it", () => {
    expect(useSimulationStore.getState().providerConfig).toBeNull();
    useSimulationStore.getState().setProviderConfig({ provider: "ollama" });
    expect(useSimulationStore.getState().providerConfig).toEqual({ provider: "ollama" });
  });
});
