/**
 * Tests for AgentInspector component.
 */
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { fireEvent } from "@testing-library/react";
import { useSimulationStore } from "../store/simulationStore";
import { AgentInspector } from "../components/AgentInspector";

// jsdom does not implement scrollIntoView
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  useSimulationStore.getState().reset();
  vi.restoreAllMocks();
});

/** Seed the store with a test agent */
function seedAgent() {
  const store = useSimulationStore.getState();
  store.setAgents({
    Alice: {
      id: "Alice",
      name: "Alice",
      position: { x: 64, y: 96 },
      activity: "Having coffee at the cafe",
      personality: ["curious", "kind"],
      occupation: "Barista",
      innate: "curious, kind, talkative",
      age: 28,
      currentLocation: "Cafe",
    },
  });
}

/** Mock fetch to return test memories */
function mockFetchMemories() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        memories: [
          {
            content: "Had a nice conversation with Bob about the weather.",
            type: "observation",
            importance: 6,
            created_at: 1712700000,
          },
          {
            content: "Decided to open the cafe early today.",
            type: "plan",
            importance: 8,
            created_at: 1712696400,
          },
        ],
      }),
    })
  );
}

describe("AgentInspector", () => {
  it("Test 1: renders agent name in the header", async () => {
    seedAgent();
    mockFetchMemories();

    await act(async () => {
      render(<AgentInspector agentId="Alice" onClose={vi.fn()} />);
    });

    // Wait for async fetch to settle
    await waitFor(() => expect(screen.queryByText(/Loading memories/)).toBeNull());

    expect(screen.getByText("Alice")).toBeTruthy();
  });

  it("Test 2: renders occupation and personality traits", async () => {
    seedAgent();
    mockFetchMemories();

    await act(async () => {
      render(<AgentInspector agentId="Alice" onClose={vi.fn()} />);
    });

    await waitFor(() => expect(screen.queryByText(/Loading memories/)).toBeNull());

    // Occupation label
    expect(screen.getByText(/Occupation:/)).toBeTruthy();
    // Occupation value
    expect(screen.getByText("Barista")).toBeTruthy();
    // Trait pills from innate string
    expect(screen.getByText("curious")).toBeTruthy();
    expect(screen.getByText("kind")).toBeTruthy();
    expect(screen.getByText("talkative")).toBeTruthy();
  });

  it("Test 3: renders current activity", async () => {
    seedAgent();
    mockFetchMemories();

    await act(async () => {
      render(<AgentInspector agentId="Alice" onClose={vi.fn()} />);
    });

    await waitFor(() => expect(screen.queryByText(/Loading memories/)).toBeNull());

    expect(screen.getByText(/Activity:/)).toBeTruthy();
    expect(screen.getByText("Having coffee at the cafe")).toBeTruthy();
  });

  it("Test 4: close button calls onClose callback", async () => {
    seedAgent();
    mockFetchMemories();

    const onClose = vi.fn();

    await act(async () => {
      render(<AgentInspector agentId="Alice" onClose={onClose} />);
    });

    await waitFor(() => expect(screen.queryByText(/Loading memories/)).toBeNull());

    const closeBtn = screen.getByRole("button", { name: /close inspector/i });
    fireEvent.click(closeBtn);

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("Test 5: memories section renders fetched memories", async () => {
    seedAgent();
    mockFetchMemories();

    await act(async () => {
      render(<AgentInspector agentId="Alice" onClose={vi.fn()} />);
    });

    // After act settles, loading should be done
    await waitFor(() => {
      expect(
        screen.getByText("Had a nice conversation with Bob about the weather.")
      ).toBeTruthy();
    });
    expect(screen.getByText("Decided to open the cafe early today.")).toBeTruthy();
  });

  it("Test 6: shows 'Agent not found' when agentId not in store", async () => {
    // Store is empty — no agents seeded
    // Mock fetch to avoid unhandled promise rejections (no agent = no fetch, but inspector returns early)
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => ({ memories: [] }) }));

    await act(async () => {
      render(<AgentInspector agentId="NonExistent" onClose={vi.fn()} />);
    });

    expect(screen.getByText(/Agent not found\./)).toBeTruthy();
  });
});
