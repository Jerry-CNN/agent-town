import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import { ActivityFeed } from "./ActivityFeed";
import { AgentInspector } from "./AgentInspector";
import { BottomBar } from "./BottomBar";
import { MapCanvas } from "./MapCanvas";

interface LayoutProps {
  selectedAgentId: string | null;
}

export function Layout({ selectedAgentId }: LayoutProps) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "#1a1a2e",
        color: "#e0e0e0",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          height: "48px",
          background: "#0d1b2a",
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: "12px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: "bold", fontSize: "16px", letterSpacing: "0.05em" }}>
          Agent Town
        </span>
        <div style={{ flex: 1 }} />
        <button
          type="button"
          onClick={() => setIsSidebarCollapsed((v) => !v)}
          style={{
            padding: "4px 10px",
            background: "rgba(255,255,255,0.1)",
            border: "1px solid rgba(255,255,255,0.2)",
            borderRadius: "4px",
            color: "#e0e0e0",
            cursor: "pointer",
            fontSize: "12px",
          }}
        >
          {isSidebarCollapsed ? "Show Panel" : "Hide Panel"}
        </button>
      </div>

      {/* Main area: canvas + sidebar */}
      <div
        style={{
          flex: 1,
          display: "flex",
          overflow: "hidden",
        }}
      >
        {/* Canvas area */}
        <div
          style={{
            flex: 1,
            position: "relative",
            background: "#16213e",
            overflow: "hidden",
          }}
        >
          <MapCanvas />
        </div>

        {/* Sidebar: activity feed or agent inspector */}
        <div
          style={{
            width: isSidebarCollapsed ? 0 : "300px",
            minWidth: 0,
            transition: "width 0.2s ease",
            overflow: "hidden",
            background: "#111827",
            borderLeft: isSidebarCollapsed ? "none" : "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {selectedAgentId !== null ? (
            <AgentInspector
              agentId={selectedAgentId}
              onClose={() => useSimulationStore.getState().setSelectedAgent(null)}
            />
          ) : (
            <ActivityFeed />
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <BottomBar />
    </div>
  );
}
