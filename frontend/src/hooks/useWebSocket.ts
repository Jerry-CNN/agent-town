import { useEffect, useRef } from "react";
import { useSimulationStore } from "../store/simulationStore";
import type { WSMessage } from "../types";

const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY_MS = 3000;

export function useWebSocket(url: string): void {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const unmountedRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    unmountedRef.current = false;

    function connect() {
      if (unmountedRef.current) return;

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        console.warn("[useWebSocket] Failed to create WebSocket:", err);
        scheduleReconnect();
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) {
          ws.close();
          return;
        }
        reconnectAttempts.current = 0;
        const store = useSimulationStore.getState();
        store.setConnected(true);
        // Store send function so BottomBar and other components can send WS commands
        store.setSendMessage((msg: WSMessage) => ws.send(JSON.stringify(msg)));
      };

      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        let msg: WSMessage;
        try {
          msg = JSON.parse(event.data as string) as WSMessage;
        } catch (err) {
          // T-05-01: malformed messages are discarded and logged, never inserted into store
          console.warn("[useWebSocket] Discarding malformed message:", err);
          return;
        }

        const store = useSimulationStore.getState();

        switch (msg.type) {
          case "snapshot": {
            // Full state on connect: initialize all agent positions and paused state
            const payload = msg.payload as {
              agents?: Array<{ name: string; coord: [number, number]; activity: string }>;
              simulation_status?: string;
            };
            if (Array.isArray(payload.agents)) {
              store.updateAgentsFromSnapshot(payload.agents);
            }
            store.setPaused(payload.simulation_status === "paused");
            break;
          }
          case "agent_update": {
            // Delta: update a single agent's position and activity
            const payload = msg.payload as {
              name?: string;
              coord?: [number, number];
              activity?: string;
            };
            if (payload.name && Array.isArray(payload.coord) && payload.activity !== undefined) {
              store.updateAgentPosition(payload.name, payload.coord as [number, number], payload.activity);
            }
            break;
          }
          case "conversation":
            // Conversation turns belong in the activity feed
            store.appendFeed(msg);
            break;
          case "simulation_status": {
            // Running/paused state change broadcast from backend
            const payload = msg.payload as { status?: string };
            store.setPaused(payload.status === "paused");
            break;
          }
          case "event":
            // User-injected events belong in the activity feed
            store.appendFeed(msg);
            break;
          case "pong":
            console.debug("[useWebSocket] pong received");
            break;
          case "error":
            console.warn("[useWebSocket] Server error:", msg.payload);
            break;
          case "ping":
            // Server won't send pings to client; ignore if received
            break;
          default:
            console.warn("[useWebSocket] Unknown message type:", (msg as WSMessage).type);
        }
      };

      ws.onclose = () => {
        const store = useSimulationStore.getState();
        store.setConnected(false);
        store.setSendMessage(null);
        if (!unmountedRef.current) {
          scheduleReconnect();
        }
      };

      ws.onerror = (err) => {
        console.warn("[useWebSocket] WebSocket error:", err);
        useSimulationStore.getState().setConnected(false);
        // onclose will fire after onerror, which will trigger reconnect
      };
    }

    function scheduleReconnect() {
      if (unmountedRef.current) return;
      // T-02-03: cap reconnect attempts at 10 to avoid infinite tight loop
      if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
        console.warn(
          `[useWebSocket] Max reconnect attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`
        );
        return;
      }
      reconnectAttempts.current += 1;
      reconnectTimerRef.current = setTimeout(() => {
        if (!unmountedRef.current) {
          connect();
        }
      }, RECONNECT_DELAY_MS);
    }

    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current !== null) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      const store = useSimulationStore.getState();
      store.setConnected(false);
      store.setSendMessage(null);
    };
  }, [url]);

}
