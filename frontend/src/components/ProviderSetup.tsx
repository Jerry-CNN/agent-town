import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import type { ProviderConfig } from "../types";

type Provider = "ollama" | "openrouter";

interface ProviderSetupProps {
  onClose?: () => void;
  initialConfig?: ProviderConfig | null;
}

export function ProviderSetup(props: ProviderSetupProps) {
  const setProviderConfig = useSimulationStore((s) => s.setProviderConfig);

  const [provider, setProvider] = useState<Provider>(
    props.initialConfig?.provider ?? "openrouter"
  );
  const [apiKey, setApiKey] = useState(props.initialConfig?.apiKey ?? "");
  const [model, setModel] = useState(
    props.initialConfig?.model ?? "openrouter/openai/gpt-4o-mini"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Continue is disabled when openrouter is selected and apiKey is empty
  const isDisabled = provider === "openrouter" && apiKey.trim() === "";

  async function handleContinue() {
    if (isDisabled) return;

    setLoading(true);
    setError(null);

    try {
      const body: Record<string, unknown> = { provider };
      if (provider === "openrouter") {
        body.api_key = apiKey.trim();
        body.model = model.trim();
      }

      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        setError(`Configuration failed: ${res.status} ${text}`);
        setLoading(false);
        return;
      }

      // Build the config object for the store (T-03-01: API key stored in localStorage as known tradeoff)
      const config: ProviderConfig = {
        provider,
        ...(provider === "openrouter" ? { apiKey: apiKey.trim(), model: model.trim() } : {}),
      };

      // Update Zustand store
      setProviderConfig(config);

      // Persist to localStorage (INF-01: only provider choice, not simulation state)
      localStorage.setItem("agenttown_provider", JSON.stringify(config));

      // Close the modal if this was opened via settings
      if (props.onClose) {
        props.onClose();
      }
    } catch (err) {
      setError("Could not connect to backend. Is it running?");
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "#1a1a2e",
          padding: "32px",
          borderRadius: "8px",
          maxWidth: "480px",
          width: "100%",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
      >
        <h2
          style={{
            margin: "0 0 8px 0",
            fontSize: "22px",
            color: "#e0e0e0",
            fontWeight: "bold",
          }}
        >
          Configure LLM Provider
        </h2>
        <p
          style={{
            margin: "0 0 24px 0",
            fontSize: "14px",
            color: "#9ca3af",
          }}
        >
          Agent Town uses your own LLM provider. Choose below.
        </p>

        {/* Provider radio group — OpenRouter first (D-01) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer",
              color: "#e0e0e0",
              fontSize: "15px",
            }}
          >
            <input
              type="radio"
              name="provider"
              value="openrouter"
              checked={provider === "openrouter"}
              onChange={() => setProvider("openrouter")}
              aria-label="OpenRouter (cloud, requires API key)"
              style={{ accentColor: "#3a86ff", cursor: "pointer" }}
            />
            OpenRouter (cloud, requires API key)
          </label>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer",
              color: "#e0e0e0",
              fontSize: "15px",
            }}
          >
            <input
              type="radio"
              name="provider"
              value="ollama"
              checked={provider === "ollama"}
              onChange={() => setProvider("ollama")}
              aria-label="Ollama (Local -- advanced)"
              style={{ accentColor: "#3a86ff", cursor: "pointer" }}
            />
            Ollama (Local -- advanced)
          </label>
        </div>

        {/* Conditional API key and model section — only when OpenRouter selected */}
        {provider === "openrouter" && (
          <>
            <div style={{ marginBottom: "16px" }}>
              <label
                htmlFor="openrouter-api-key"
                style={{
                  display: "block",
                  fontSize: "13px",
                  color: "#9ca3af",
                  marginBottom: "6px",
                  fontWeight: "500",
                }}
              >
                OpenRouter API Key
              </label>
              <input
                id="openrouter-api-key"
                type="password"
                placeholder="sk-or-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                aria-label="OpenRouter API Key"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "#111827",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "4px",
                  color: "#e0e0e0",
                  fontSize: "14px",
                  boxSizing: "border-box",
                }}
              />
              <p
                style={{
                  margin: "6px 0 0 0",
                  fontSize: "12px",
                  color: "#6b7280",
                }}
              >
                Get your key at{" "}
                <a
                  href="https://openrouter.ai/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#3a86ff" }}
                >
                  openrouter.ai/keys
                </a>
              </p>
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label
                htmlFor="openrouter-model"
                style={{
                  display: "block",
                  fontSize: "13px",
                  color: "#9ca3af",
                  marginBottom: "6px",
                  fontWeight: "500",
                }}
              >
                Model
              </label>
              <input
                id="openrouter-model"
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                aria-label="OpenRouter model"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  background: "#111827",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "4px",
                  color: "#e0e0e0",
                  fontSize: "14px",
                  boxSizing: "border-box",
                }}
              />
            </div>
          </>
        )}

        {/* Error message */}
        {error && (
          <p
            style={{
              margin: "0 0 16px 0",
              padding: "8px 12px",
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "4px",
              color: "#f87171",
              fontSize: "13px",
            }}
          >
            {error}
          </p>
        )}

        {/* Continue button + optional Cancel link */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            type="button"
            onClick={handleContinue}
            disabled={isDisabled || loading}
            style={{
              flex: 1,
              padding: "10px 20px",
              background: isDisabled || loading ? "#374151" : "#3a86ff",
              color: isDisabled || loading ? "#6b7280" : "#fff",
              border: "none",
              borderRadius: "4px",
              fontSize: "15px",
              fontWeight: "bold",
              cursor: isDisabled || loading ? "not-allowed" : "pointer",
              transition: "background 0.15s",
            }}
          >
            {loading ? "Connecting..." : "Continue"}
          </button>

          {props.onClose && (
            <button
              type="button"
              onClick={props.onClose}
              style={{
                background: "none",
                border: "none",
                color: "#6b7280",
                fontSize: "14px",
                cursor: "pointer",
                padding: "4px",
                textDecoration: "underline",
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
