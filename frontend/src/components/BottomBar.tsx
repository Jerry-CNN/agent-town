import { useState, useMemo } from "react";
import { useSimulationStore, getSendMessage } from "../store/simulationStore";
import type { WSMessageType } from "../types";

export function BottomBar() {
  const isPaused = useSimulationStore((state) => state.isPaused);
  const providerConfig = useSimulationStore((state) => state.providerConfig);
  const agents = useSimulationStore((state) => state.agents);
  const agentKeys = useMemo(() => Object.keys(agents), [agents]);

  const [eventText, setEventText] = useState("");
  const [deliveryMode, setDeliveryMode] = useState<"broadcast" | "whisper">("broadcast");
  const [whisperTarget, setWhisperTarget] = useState("");

  function handlePauseResume() {
    const send = getSendMessage();
    if (send) {
      send({
        type: isPaused ? "resume" : "pause",
        payload: {},
        timestamp: Date.now() / 1000,
      });
    }
    // Do NOT call setPaused locally — backend will broadcast simulation_status,
    // which the WS dispatch handler sets isPaused. Single source of truth.
  }

  function handleSubmitEvent() {
    if (!eventText.trim()) return;
    const send = getSendMessage();
    if (!send) return;
    send({
      type: "inject_event" as WSMessageType,
      payload: {
        text: eventText.trim(),
        mode: deliveryMode,
        ...(deliveryMode === "whisper" ? { target: whisperTarget } : {}),
      },
      timestamp: Date.now() / 1000,
    });
    setEventText("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      handleSubmitEvent();
    }
  }

  function handleDeliveryModeChange(mode: "broadcast" | "whisper") {
    setDeliveryMode(mode);
    // Auto-select first agent when switching to whisper
    if (mode === "whisper" && !whisperTarget && agentKeys.length > 0) {
      setWhisperTarget(agentKeys[0]);
    }
  }

  return (
    <div
      style={{
        height: "60px",
        background: "#0f3460",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: "10px",
        flexShrink: 0,
      }}
    >
      {/* Pause / Resume */}
      <button
        type="button"
        onClick={handlePauseResume}
        style={{
          padding: "6px 16px",
          background: isPaused ? "#e07b39" : "#3a86ff",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "13px",
          fontWeight: "bold",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        {isPaused ? "Resume" : "Pause"}
      </button>

      {/* Delivery mode toggle */}
      <div
        data-testid="delivery-mode"
        style={{ display: "flex", gap: "4px", flexShrink: 0 }}
      >
        <button
          type="button"
          onClick={() => handleDeliveryModeChange("broadcast")}
          style={{
            padding: "4px 10px",
            background: deliveryMode === "broadcast" ? "#3a86ff" : "rgba(255,255,255,0.12)",
            color: "#fff",
            border: "none",
            borderRadius: "4px 0 0 4px",
            cursor: "pointer",
            fontSize: "12px",
            fontWeight: deliveryMode === "broadcast" ? "bold" : "normal",
          }}
        >
          Broadcast
        </button>
        <button
          type="button"
          onClick={() => handleDeliveryModeChange("whisper")}
          style={{
            padding: "4px 10px",
            background: deliveryMode === "whisper" ? "#9b59b6" : "rgba(255,255,255,0.12)",
            color: "#fff",
            border: "none",
            borderRadius: "0 4px 4px 0",
            cursor: "pointer",
            fontSize: "12px",
            fontWeight: deliveryMode === "whisper" ? "bold" : "normal",
          }}
        >
          Whisper
        </button>
      </div>

      {/* Whisper target dropdown — only visible in whisper mode */}
      {deliveryMode === "whisper" && (
        <select
          data-testid="whisper-target"
          value={whisperTarget}
          onChange={(e) => setWhisperTarget(e.target.value)}
          style={{
            padding: "5px 8px",
            background: "#1a2a4a",
            border: "1px solid rgba(255,255,255,0.2)",
            borderRadius: "4px",
            color: "#e0e0e0",
            fontSize: "12px",
            maxWidth: "140px",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          {agentKeys.length === 0 ? (
            <option value="" disabled>
              No agents available
            </option>
          ) : (
            agentKeys.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))
          )}
        </select>
      )}

      {/* Event text input */}
      <input
        type="text"
        placeholder="Type an event..."
        value={eventText}
        onChange={(e) => setEventText(e.target.value)}
        onKeyDown={handleKeyDown}
        style={{
          flex: 1,
          padding: "6px 12px",
          background: "rgba(255,255,255,0.1)",
          border: "1px solid rgba(255,255,255,0.25)",
          borderRadius: "4px",
          color: "#fff",
          fontSize: "13px",
          outline: "none",
          minWidth: 0,
        }}
      />

      {/* Submit button */}
      <button
        type="button"
        data-testid="submit-event"
        onClick={handleSubmitEvent}
        style={{
          padding: "6px 14px",
          background: deliveryMode === "whisper" ? "#9b59b6" : "#3a86ff",
          color: "#fff",
          border: "none",
          borderRadius: "4px",
          cursor: "pointer",
          fontSize: "13px",
          fontWeight: "bold",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Send
      </button>

      {/* Provider status badge */}
      <div
        style={{
          padding: "4px 10px",
          background: providerConfig ? "#2d7a4f" : "#444",
          borderRadius: "4px",
          fontSize: "12px",
          color: "#e0e0e0",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        {providerConfig?.provider ?? "not configured"}
      </div>
    </div>
  );
}
