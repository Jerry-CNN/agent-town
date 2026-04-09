import { useEffect, useRef } from "react";
import { useSimulationStore } from "../store/simulationStore";
import type { WSMessage } from "../types";

const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY_MS = 3000;

export function useWebSocket(url: string): { isConnected: boolean } {
  const isConnected = useSimulationStore((state) => state.isConnected);
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
        useSimulationStore.getState().setConnected(true);
      };

      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        try {
          const msg = JSON.parse(event.data as string) as WSMessage;
          useSimulationStore.getState().appendFeed(msg);
        } catch (err) {
          console.warn("[useWebSocket] Discarding malformed message:", err);
          // T-02-02: malformed messages are discarded, not appended to feed
        }
      };

      ws.onclose = () => {
        useSimulationStore.getState().setConnected(false);
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
      useSimulationStore.getState().setConnected(false);
    };
  }, [url]);

  return { isConnected };
}
