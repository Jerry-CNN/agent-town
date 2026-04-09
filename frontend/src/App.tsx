import { useEffect, useState } from "react";
import { useSimulationStore } from "./store/simulationStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { Layout } from "./components/Layout";
import { ProviderSetup } from "./components/ProviderSetup";
import { OllamaStatusBanner } from "./components/OllamaStatusBanner";
import type { ProviderConfig } from "./types";

function App() {
  const providerConfig = useSimulationStore((s) => s.providerConfig);
  const setProviderConfig = useSimulationStore((s) => s.setProviderConfig);
  const selectedAgentId = useSimulationStore((s) => s.selectedAgentId);

  const [ollamaAvailable, setOllamaAvailable] = useState(true);

  // On mount: re-hydrate provider config from localStorage (INF-01)
  // T-03-03: wrap in try/catch; validate schema before trusting
  useEffect(() => {
    try {
      const raw = localStorage.getItem("agenttown_provider");
      if (raw) {
        const parsed: unknown = JSON.parse(raw);
        if (
          parsed !== null &&
          typeof parsed === "object" &&
          "provider" in parsed &&
          (
            (parsed as ProviderConfig).provider === "ollama" ||
            (parsed as ProviderConfig).provider === "openrouter"
          )
        ) {
          setProviderConfig(parsed as ProviderConfig);
        }
      }
    } catch {
      // Invalid JSON or schema — treat as unconfigured, show modal
    }
  }, [setProviderConfig]);

  // On mount: check Ollama availability via /api/health
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          const data = await res.json();
          const ollamaStatus: boolean =
            data?.provider_status?.ollama === true;
          setOllamaAvailable(ollamaStatus);
        }
      } catch {
        // Backend not reachable — assume Ollama unavailable
        setOllamaAvailable(false);
      }
    })();
  }, []);

  // Connect to backend WebSocket — handles reconnect gracefully when unavailable
  useWebSocket("ws://localhost:8000/ws");

  return (
    <>
      {/* First-visit setup modal — blocks UI until provider is configured */}
      {providerConfig === null && <ProviderSetup />}

      {/* Non-blocking Ollama availability banner */}
      <OllamaStatusBanner ollamaAvailable={ollamaAvailable} />

      {/* Main layout */}
      <Layout selectedAgentId={selectedAgentId} />
    </>
  );
}

export default App;
