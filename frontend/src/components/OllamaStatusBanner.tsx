import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";

interface OllamaStatusBannerProps {
  ollamaAvailable: boolean;
}

export function OllamaStatusBanner({ ollamaAvailable }: OllamaStatusBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const providerConfig = useSimulationStore((s) => s.providerConfig);

  // Only show when: provider is ollama AND ollama is unavailable AND not dismissed
  if (ollamaAvailable || dismissed || providerConfig?.provider !== "ollama") {
    return null;
  }

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 999,
        background: "#b45309",
        color: "#fff",
        padding: "8px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        fontSize: "14px",
      }}
    >
      <span>
        Ollama is not running. Start Ollama or switch to OpenRouter in Settings.
      </span>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss banner"
        style={{
          background: "transparent",
          border: "none",
          color: "#fff",
          cursor: "pointer",
          fontSize: "18px",
          lineHeight: 1,
          padding: "0 4px",
          marginLeft: "12px",
        }}
      >
        ×
      </button>
    </div>
  );
}
