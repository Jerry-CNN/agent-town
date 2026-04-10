import { useEffect, useState } from "react";
import { useSimulationStore } from "../store/simulationStore";

interface Memory {
  content: string;
  type: string;
  importance: number;
  created_at: number;
}

interface AgentInspectorProps {
  agentId: string;
  onClose: () => void;
}

function formatMemoryTime(unixSeconds: number): string {
  const d = new Date(unixSeconds * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/** Importance level (1-10) maps to a left-border color for memory cards */
function importanceColor(importance: number): string {
  if (importance >= 8) return "#e74c3c";
  if (importance >= 5) return "#f39c12";
  return "#3498db";
}

export function AgentInspector({ agentId, onClose }: AgentInspectorProps) {
  const agent = useSimulationStore((s) => s.agents[agentId]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loadingMemories, setLoadingMemories] = useState(true);

  useEffect(() => {
    setLoadingMemories(true);
    setMemories([]);
    fetch(`/api/agents/${encodeURIComponent(agentId)}/memories?limit=5`)
      .then((r) => r.json())
      .then((data: { memories: Memory[] }) => {
        setMemories(data.memories ?? []);
      })
      .catch(() => {
        setMemories([]);
      })
      .finally(() => {
        setLoadingMemories(false);
      });
  }, [agentId]);

  if (!agent) {
    return (
      <div
        style={{
          padding: "16px",
          color: "#888",
          fontStyle: "italic",
          fontSize: "13px",
        }}
      >
        Agent not found.
      </div>
    );
  }

  // Parse innate traits — comma-separated string
  const traits = agent.innate
    ? agent.innate.split(",").map((t) => t.trim()).filter(Boolean)
    : [];

  return (
    <div
      data-testid="agent-inspector"
      style={{
        height: "100%",
        overflowY: "auto",
        padding: "12px",
        fontSize: "13px",
        color: "#c0c0d0",
        fontFamily: "system-ui, sans-serif",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: "16px",
            fontWeight: "bold",
            color: "#e0e0e0",
          }}
        >
          {agent.name}
        </span>
        <button
          type="button"
          aria-label="Close inspector"
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#888",
            cursor: "pointer",
            fontSize: "16px",
            padding: "2px 6px",
            borderRadius: "4px",
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      </div>

      {/* Divider */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }} />

      {/* Profile section */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ color: "#888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Profile
        </div>
        <div>
          <span style={{ color: "#7eb8f7" }}>Occupation:</span>{" "}
          {agent.occupation ?? "Unknown"}
        </div>
        <div>
          <span style={{ color: "#7eb8f7" }}>Age:</span>{" "}
          {agent.age ?? "—"}
        </div>
        {/* Personality trait pills */}
        {traits.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
            {traits.map((trait) => (
              <span
                key={trait}
                style={{
                  padding: "2px 8px",
                  background: "rgba(255,255,255,0.08)",
                  borderRadius: "12px",
                  fontSize: "11px",
                  color: "#c0c0d0",
                }}
              >
                {trait}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Divider */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }} />

      {/* Current state section */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ color: "#888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Current State
        </div>
        <div>
          <span style={{ color: "#7eb8f7" }}>Activity:</span>{" "}
          {agent.activity}
        </div>
        <div>
          <span style={{ color: "#7eb8f7" }}>Location:</span>{" "}
          {agent.currentLocation ?? "Unknown"}
        </div>
      </div>

      {/* Divider */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }} />

      {/* Recent memories section */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ color: "#888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Recent Memories
        </div>
        {loadingMemories ? (
          <div style={{ color: "#666", fontStyle: "italic" }}>Loading memories...</div>
        ) : memories.length === 0 ? (
          <div style={{ color: "#666", fontStyle: "italic" }}>No memories yet.</div>
        ) : (
          memories.map((mem, i) => (
            <div
              // eslint-disable-next-line react/no-array-index-key
              key={i}
              style={{
                padding: "6px 8px",
                background: "rgba(255,255,255,0.04)",
                borderRadius: "4px",
                borderLeft: `3px solid ${importanceColor(mem.importance)}`,
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div style={{ lineHeight: "1.4" }}>{mem.content}</div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "11px",
                  color: "#666",
                  marginTop: "2px",
                }}
              >
                <span>{formatMemoryTime(mem.created_at)}</span>
                <span
                  style={{
                    padding: "1px 5px",
                    background: "rgba(255,255,255,0.08)",
                    borderRadius: "8px",
                  }}
                >
                  imp: {mem.importance}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
