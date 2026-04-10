import { useEffect, useRef } from "react";
import { useSimulationStore } from "../store/simulationStore";
import type { WSMessage } from "../types";

// Agent color palette — matches AgentSprite colorIndex logic
const AGENT_COLORS_HEX = [
  "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
  "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
];

function getAgentColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash + name.charCodeAt(i)) % AGENT_COLORS_HEX.length;
  }
  return AGENT_COLORS_HEX[hash];
}

function formatTimestamp(unixSeconds: number): string {
  const d = new Date(unixSeconds * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${hh}:${mm}:${ss}`;
}

function FeedEntry({ msg }: { msg: WSMessage }) {
  const ts = formatTimestamp(msg.timestamp);

  if (msg.type === "conversation") {
    const turns = (msg.payload.turns as Array<{ speaker: string; text: string }>) ?? [];
    return (
      <>
        {turns.map((turn, i) => (
          <div
            // eslint-disable-next-line react/no-array-index-key
            key={`${msg.timestamp}-${i}`}
            style={{
              padding: "4px 8px",
              background: "rgba(255,255,255,0.04)",
              borderRadius: "4px",
              wordBreak: "break-word",
              lineHeight: "1.4",
            }}
          >
            <span data-testid="entry-time" style={{ color: "#666", marginRight: "6px" }}>
              [{ts}]
            </span>
            <span style={{ color: getAgentColor(turn.speaker), fontWeight: "bold" }}>
              {turn.speaker}
            </span>
            {": "}
            {turn.text}
          </div>
        ))}
      </>
    );
  }

  if (msg.type === "event") {
    const text = (msg.payload.text as string) ?? JSON.stringify(msg.payload);
    return (
      <div
        style={{
          padding: "4px 8px",
          background: "rgba(255,255,255,0.04)",
          borderRadius: "4px",
          wordBreak: "break-word",
          lineHeight: "1.4",
        }}
      >
        <span data-testid="entry-time" style={{ color: "#666", marginRight: "6px" }}>
          [{ts}]
        </span>
        <span style={{ color: "#f39c12", fontWeight: "bold" }}>Event:</span>{" "}
        {text}
      </div>
    );
  }

  // Fallback for unexpected types
  return (
    <div
      style={{
        padding: "4px 8px",
        background: "rgba(255,255,255,0.04)",
        borderRadius: "4px",
        wordBreak: "break-word",
      }}
    >
      <span data-testid="entry-time" style={{ color: "#666", marginRight: "6px" }}>
        [{ts}]
      </span>
      <span style={{ color: "#7eb8f7", fontWeight: "bold" }}>{msg.type}</span>
      {": "}
      {JSON.stringify(msg.payload)}
    </div>
  );
}

export function ActivityFeed() {
  const feed = useSimulationStore((state) => state.feed);
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Track whether user has scrolled away from bottom
  const userScrolled = useRef(false);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10;
    userScrolled.current = !atBottom;
  };

  // Auto-scroll to bottom on new messages — unless user scrolled up
  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [feed]);

  return (
    <div
      data-testid="feed-container"
      ref={containerRef}
      onScroll={handleScroll}
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
          <FeedEntry key={`${msg.type}-${msg.timestamp}`} msg={msg} />
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}
