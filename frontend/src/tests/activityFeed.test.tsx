/**
 * Tests for upgraded ActivityFeed component with formatted entries.
 */
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { useSimulationStore } from "../store/simulationStore";
import { ActivityFeed } from "../components/ActivityFeed";

// jsdom does not implement scrollIntoView — mock it globally
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

beforeEach(() => {
  useSimulationStore.getState().reset();
  vi.restoreAllMocks();
});

describe("ActivityFeed", () => {
  it("Test 1: conversation WSMessage renders with agent name colored span, action text, and formatted HH:MM:SS timestamp", () => {
    const msg = {
      type: "conversation" as const,
      payload: {
        turns: [{ speaker: "Alice", text: "Hello, how are you?" }],
      },
      timestamp: 1712700000, // Unix seconds
    };
    useSimulationStore.getState().appendFeed(msg);

    render(<ActivityFeed />);

    // Agent name should be visible
    expect(screen.getByText("Alice")).toBeTruthy();
    // Action/text should be present
    expect(screen.getByText(/Hello, how are you\?/)).toBeTruthy();
    // Timestamp should be formatted (HH:MM:SS pattern)
    const timeEl = document.querySelector("[data-testid='entry-time']");
    expect(timeEl).not.toBeNull();
    // Should be HH:MM:SS format
    expect(timeEl?.textContent).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it("Test 2: event WSMessage renders with 'Event' prefix and the event text", () => {
    const msg = {
      type: "event" as const,
      payload: { text: "A fire broke out at the cafe!" },
      timestamp: 1712700060,
    };
    useSimulationStore.getState().appendFeed(msg);

    render(<ActivityFeed />);

    // Should show Event prefix
    expect(screen.getByText(/Event:/)).toBeTruthy();
    // Should show event text
    expect(screen.getByText(/A fire broke out at the cafe!/)).toBeTruthy();
  });

  it("Test 3: empty feed renders 'No activity yet.' placeholder text", () => {
    render(<ActivityFeed />);
    expect(screen.getByText(/No activity yet\./)).toBeTruthy();
  });

  it("Test 4: feed container has overflowY auto for scrolling", () => {
    render(<ActivityFeed />);
    // The outer scrollable container should have overflow-y: auto
    const container = document.querySelector("[data-testid='feed-container']");
    expect(container).not.toBeNull();
    // In jsdom, inline styles are accessible via element.style
    expect((container as HTMLElement).style.overflowY).toBe("auto");
  });
});
