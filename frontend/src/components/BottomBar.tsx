import { useSimulationStore } from "../store/simulationStore";
import { getSendMessage } from "../store/simulationStore";

export function BottomBar() {
  const isPaused = useSimulationStore((state) => state.isPaused);
  const providerConfig = useSimulationStore((state) => state.providerConfig);

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

  return (
    <div
      style={{
        height: "60px",
        background: "#0f3460",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: "12px",
        flexShrink: 0,
      }}
    >
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
        }}
      >
        {isPaused ? "Resume" : "Pause"}
      </button>

      {/* Event input — wired in Phase 6 */}
      <input
        type="text"
        placeholder="Type an event..."
        disabled
        style={{
          flex: 1,
          padding: "6px 12px",
          background: "rgba(255,255,255,0.1)",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: "4px",
          color: "#999",
          fontSize: "13px",
          cursor: "not-allowed",
        }}
      />

      {/* Provider status badge */}
      <div
        style={{
          padding: "4px 10px",
          background: providerConfig ? "#2d7a4f" : "#444",
          borderRadius: "4px",
          fontSize: "12px",
          color: "#e0e0e0",
          whiteSpace: "nowrap",
        }}
      >
        {providerConfig?.provider ?? "not configured"}
      </div>
    </div>
  );
}
