import { create } from "zustand";
import type { AgentState, ProviderConfig, SimulationStore, SnapshotAgent, WSMessage } from "../types";
import { TILE_SIZE } from "../types";

// Module-level non-reactive ref for the send function.
// Stored outside Zustand state to avoid triggering re-renders on every WS message.
let _sendMessage: ((msg: WSMessage) => void) | null = null;

export function getSendMessage(): ((msg: WSMessage) => void) | null {
  return _sendMessage;
}

const initialState = {
  agents: {} as Record<string, AgentState>,
  feed: [] as WSMessage[],
  isConnected: false,
  isPaused: false,
  selectedAgentId: null as string | null,
  providerConfig: null as ProviderConfig | null,
  tickInterval: 10,
};

export const useSimulationStore = create<SimulationStore>()((set) => ({
  ...initialState,

  setAgents: (agents: Record<string, AgentState>) => set({ agents }),

  updateAgentsFromSnapshot: (agents: SnapshotAgent[]) => {
    const record: Record<string, AgentState> = {};
    for (const a of agents) {
      record[a.name] = {
        id: a.name,
        name: a.name,
        position: { x: a.coord[0] * TILE_SIZE, y: a.coord[1] * TILE_SIZE },
        activity: a.activity,
        personality: [],
        occupation: a.occupation,
        innate: a.innate,
        age: a.age,
      };
    }
    set({ agents: record });
  },

  updateAgentPosition: (name: string, coord: [number, number], activity: string) =>
    set((state) => {
      const existing = state.agents[name];
      const updated: AgentState = existing
        ? { ...existing, position: { x: coord[0] * TILE_SIZE, y: coord[1] * TILE_SIZE }, activity }
        : {
            id: name,
            name,
            position: { x: coord[0] * TILE_SIZE, y: coord[1] * TILE_SIZE },
            activity,
            personality: [],
          };
      return { agents: { ...state.agents, [name]: updated } };
    }),

  appendFeed: (msg: WSMessage) =>
    set((state) => ({ feed: [...state.feed, msg] })),

  setConnected: (v: boolean) => set({ isConnected: v }),

  setPaused: (v: boolean) => set({ isPaused: v }),

  setSelectedAgent: (id: string | null) => set({ selectedAgentId: id }),

  setProviderConfig: (config: ProviderConfig) => set({ providerConfig: config }),

  setTickInterval: (interval: number) => set({ tickInterval: interval }),

  setSendMessage: (fn: ((msg: WSMessage) => void) | null) => {
    _sendMessage = fn;
  },

  reset: () => {
    _sendMessage = null;
    set({ ...initialState });
  },
}));
