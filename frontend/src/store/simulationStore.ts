import { create } from "zustand";
import type { AgentState, ProviderConfig, SimulationStore, WSMessage } from "../types";

const initialState = {
  agents: {} as Record<string, AgentState>,
  feed: [] as WSMessage[],
  isConnected: false,
  isPaused: false,
  selectedAgentId: null as string | null,
  providerConfig: null as ProviderConfig | null,
};

export const useSimulationStore = create<SimulationStore>()((set) => ({
  ...initialState,

  setAgents: (agents: Record<string, AgentState>) => set({ agents }),

  appendFeed: (msg: WSMessage) =>
    set((state) => ({ feed: [...state.feed, msg] })),

  setConnected: (v: boolean) => set({ isConnected: v }),

  setPaused: (v: boolean) => set({ isPaused: v }),

  setSelectedAgent: (id: string | null) => set({ selectedAgentId: id }),

  setProviderConfig: (config: ProviderConfig) => set({ providerConfig: config }),

  reset: () => set({ ...initialState }),
}));
