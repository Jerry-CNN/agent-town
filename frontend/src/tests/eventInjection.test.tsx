import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useSimulationStore, getSendMessage } from "../store/simulationStore";
import { BottomBar } from "../components/BottomBar";

beforeEach(() => {
  useSimulationStore.getState().reset();
  useSimulationStore.getState().setSendMessage(null);
});

describe("BottomBar event injection UI", () => {
  it("Test 1: renders an enabled text input (not disabled)", () => {
    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...");
    expect(input).toBeDefined();
    expect((input as HTMLInputElement).disabled).toBe(false);
  });

  it("Test 2: typing into the input updates its value", () => {
    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "A meteor is heading toward the town" } });
    expect(input.value).toBe("A meteor is heading toward the town");
  });

  it("Test 3: clicking Send dispatches inject_event with correct broadcast payload", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "A festival begins" } });
    fireEvent.click(screen.getByTestId("submit-event"));

    expect(mockSend).toHaveBeenCalledTimes(1);
    const call = mockSend.mock.calls[0][0];
    expect(call.type).toBe("inject_event");
    expect(call.payload.text).toBe("A festival begins");
    expect(call.payload.mode).toBe("broadcast");
    expect(call.payload.target).toBeUndefined();
    expect(typeof call.timestamp).toBe("number");
  });

  it("Test 4: input clears after successful submission via button", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Big news" } });
    fireEvent.click(screen.getByTestId("submit-event"));

    expect(input.value).toBe("");
  });

  it("Test 5: pressing Enter dispatches inject_event and clears input", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Rain is coming" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mockSend).toHaveBeenCalledTimes(1);
    expect(mockSend.mock.calls[0][0].type).toBe("inject_event");
    expect(input.value).toBe("");
  });

  it("Test 6: empty input does not call getSendMessage dispatch", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    render(<BottomBar />);
    // Do not type anything — input is empty
    fireEvent.click(screen.getByTestId("submit-event"));

    expect(mockSend).not.toHaveBeenCalled();
  });

  it("Test 7: whitespace-only input does not dispatch", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    render(<BottomBar />);
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByTestId("submit-event"));

    expect(mockSend).not.toHaveBeenCalled();
  });

  it("Test 8: delivery mode toggle shows Broadcast and Whisper buttons", () => {
    render(<BottomBar />);
    const modeContainer = screen.getByTestId("delivery-mode");
    expect(modeContainer).toBeDefined();
    expect(modeContainer.textContent).toContain("Broadcast");
    expect(modeContainer.textContent).toContain("Whisper");
  });

  it("Test 9: whisper target dropdown appears when Whisper mode is selected", () => {
    // Seed one agent into the store
    useSimulationStore.getState().updateAgentsFromSnapshot([
      { name: "Alice Chen", coord: [5, 5], activity: "walking" },
    ]);

    render(<BottomBar />);

    // Whisper dropdown should not be visible initially (broadcast mode)
    expect(screen.queryByTestId("whisper-target")).toBeNull();

    // Click Whisper button
    fireEvent.click(screen.getByText("Whisper"));

    // Dropdown should now appear
    const dropdown = screen.getByTestId("whisper-target") as HTMLSelectElement;
    expect(dropdown).toBeDefined();
    // Should contain the agent name
    expect(dropdown.textContent).toContain("Alice Chen");
  });

  it("Test 10: whisper mode dispatch includes target agent name in payload", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);
    useSimulationStore.getState().updateAgentsFromSnapshot([
      { name: "Bob Smith", coord: [3, 3], activity: "chatting" },
    ]);

    render(<BottomBar />);

    // Switch to whisper mode
    fireEvent.click(screen.getByText("Whisper"));

    // The whisper target should auto-select first agent (Bob Smith)
    const input = screen.getByPlaceholderText("Type an event...") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "I have a secret treasure map" } });
    fireEvent.click(screen.getByTestId("submit-event"));

    expect(mockSend).toHaveBeenCalledTimes(1);
    const call = mockSend.mock.calls[0][0];
    expect(call.type).toBe("inject_event");
    expect(call.payload.mode).toBe("whisper");
    expect(call.payload.target).toBe("Bob Smith");
    expect(call.payload.text).toBe("I have a secret treasure map");
  });

  it("Test 11: no agents in whisper mode shows disabled 'No agents available' option", () => {
    render(<BottomBar />);

    // Switch to whisper with empty store
    fireEvent.click(screen.getByText("Whisper"));

    const dropdown = screen.getByTestId("whisper-target") as HTMLSelectElement;
    expect(dropdown.textContent).toContain("No agents available");
  });
});

// Store-level tests (no DOM rendering required)
describe("inject_event message construction", () => {
  it("Test 12: broadcast payload has no target field", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    // Simulate what handleSubmitEvent does
    const send = getSendMessage();
    send?.({
      type: "inject_event",
      payload: { text: "Storm approaching", mode: "broadcast" },
      timestamp: Date.now() / 1000,
    });

    expect(mockSend).toHaveBeenCalledTimes(1);
    const payload = mockSend.mock.calls[0][0].payload;
    expect(payload.mode).toBe("broadcast");
    expect(payload.target).toBeUndefined();
  });

  it("Test 13: whisper payload includes target agent name", () => {
    const mockSend = vi.fn();
    useSimulationStore.getState().setSendMessage(mockSend);

    const send = getSendMessage();
    send?.({
      type: "inject_event",
      payload: { text: "Secret message", mode: "whisper", target: "Alice Chen" },
      timestamp: Date.now() / 1000,
    });

    expect(mockSend).toHaveBeenCalledTimes(1);
    const payload = mockSend.mock.calls[0][0].payload;
    expect(payload.mode).toBe("whisper");
    expect(payload.target).toBe("Alice Chen");
  });
});
