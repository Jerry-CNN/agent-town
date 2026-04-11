export type Provider = "ollama" | "openrouter";

export interface ProviderConfig {
  provider: Provider;
  apiKey?: string;
  model?: string;
}

export const TILE_SIZE = 32;

export interface SnapshotAgent {
  name: string;
  coord: [number, number];
  activity: string;
  occupation?: string;
  innate?: string;
  age?: number;
}

export interface AgentState {
  id: string;
  name: string;
  position: { x: number; y: number };
  activity: string;
  personality: string[];
  occupation?: string;
  innate?: string;
  age?: number;
  currentLocation?: string;
}

export type WSMessageType =
  | "agent_update"
  | "conversation"
  | "simulation_status"
  | "snapshot"
  | "event"
  | "ping"
  | "pong"
  | "error"
  | "pause"
  | "resume"
  | "inject_event"
  | "tick_interval_update";

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
  tickInterval: number;

  // Actions
  setAgents: (agents: Record<string, AgentState>) => void;
  updateAgentsFromSnapshot: (agents: SnapshotAgent[]) => void;
  updateAgentPosition: (name: string, coord: [number, number], activity: string) => void;
  appendFeed: (msg: WSMessage) => void;
  setConnected: (v: boolean) => void;
  setPaused: (v: boolean) => void;
  setSelectedAgent: (id: string | null) => void;
  setProviderConfig: (config: ProviderConfig) => void;
  setSendMessage: (fn: ((msg: WSMessage) => void) | null) => void;
  setTickInterval: (interval: number) => void;
  reset: () => void;
}
