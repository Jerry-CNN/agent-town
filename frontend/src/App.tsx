import { useEffect, useRef, useState } from "react";
import { useSimulationStore } from "./store/simulationStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { Layout } from "./components/Layout";
import { ProviderSetup } from "./components/ProviderSetup";
import { OllamaStatusBanner } from "./components/OllamaStatusBanner";
import type { ProviderConfig } from "./types";

function App() {
  const providerConfig = useSimulationStore((s) => s.providerConfig);
  const selectedAgentId = useSimulationStore((s) => s.selectedAgentId);

  const [ollamaAvailable, setOllamaAvailable] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  const hasHydrated = useRef(false);
  useEffect(() => {
    if (hasHydrated.current) return;
    hasHydrated.current = true;
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
          useSimulationStore.getState().setProviderConfig(parsed as ProviderConfig);
        }
      }
    } catch {}
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/health");
        if (res.ok && !cancelled) {
          const data = await res.json();
          setOllamaAvailable(data?.provider_status?.ollama === true);
        }
      } catch {
        if (!cancelled) setOllamaAvailable(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useWebSocket("ws://localhost:8000/ws");

  return (
    <>
      {(providerConfig === null || showSettings) && (
        <ProviderSetup
          onClose={providerConfig !== null ? () => setShowSettings(false) : undefined}
          initialConfig={providerConfig}
        />
      )}
      <OllamaStatusBanner ollamaAvailable={ollamaAvailable} />
      <Layout
        selectedAgentId={selectedAgentId}
        onOpenSettings={() => setShowSettings(true)}
      />
    </>
  );
}

export default App;
