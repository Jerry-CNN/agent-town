import { useEffect, useRef } from "react";
import { useSimulationStore } from "../store/simulationStore";

export function ActivityFeed() {
  const feed = useSimulationStore((state) => state.feed);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed]);

  return (
    <div
      style={{
        height: "100%",
        overflowY: "auto",
        padding: "12px",
        fontSize: "12px",
        color: "#c0c0d0",
        display: "flex",
        flexDirection: "column",
        gap: "4px",
      }}
    >
      {feed.length === 0 ? (
        <p style={{ color: "#666", fontStyle: "italic" }}>No activity yet.</p>
      ) : (
        feed.map((msg) => (
          <div
            key={msg.timestamp}
            style={{
              padding: "4px 8px",
              background: "rgba(255,255,255,0.04)",
              borderRadius: "4px",
              wordBreak: "break-all",
            }}
          >
            <span style={{ color: "#7eb8f7", fontWeight: "bold" }}>
              {msg.type}
            </span>
            {": "}
            {JSON.stringify(msg.payload)}
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}
