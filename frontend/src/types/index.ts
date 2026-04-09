export type Provider = "ollama" | "openrouter";

export interface ProviderConfig {
  provider: Provider;
  apiKey?: string;
  model?: string;
}

export interface AgentState {
  id: string;
  name: string;
  position: { x: number; y: number };
  activity: string;
  personality: string[];
}

export type WSMessageType = "agent_update" | "event" | "ping" | "pong" | "error";

export interface WSMessage {
  type: WSMessageType;
  payload: Record<string, unknown>;
  timestamp: number;
}

export interface SimulationStore {
  // State
  agents: Record<string, AgentState>;
  feed: WSMessage[];
  isConnected: boolean;
  isPaused: boolean;
  selectedAgentId: string | null;
  providerConfig: ProviderConfig | null;

  // Actions
  setAgents: (agents: Record<string, AgentState>) => void;
  appendFeed: (msg: WSMessage) => void;
  setConnected: (v: boolean) => void;
  setPaused: (v: boolean) => void;
  setSelectedAgent: (id: string | null) => void;
  setProviderConfig: (config: ProviderConfig) => void;
  reset: () => void;
}
