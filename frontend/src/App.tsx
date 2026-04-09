import { useSimulationStore } from "./store/simulationStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { Layout } from "./components/Layout";

function App() {
  // Connect to backend WebSocket — handles reconnect gracefully when unavailable
  useWebSocket("ws://localhost:8000/ws");

  const selectedAgentId = useSimulationStore((state) => state.selectedAgentId);

  return <Layout selectedAgentId={selectedAgentId} />;
}

export default App;
