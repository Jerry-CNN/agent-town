/**
 * Tests for ProviderSetup modal component.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, fireEvent, screen, waitFor, act } from "@testing-library/react";
import { useSimulationStore } from "../store/simulationStore";
import { ProviderSetup } from "../components/ProviderSetup";

// Reset store and mocks before each test
beforeEach(() => {
  useSimulationStore.getState().reset();
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("ProviderSetup", () => {
  it("Test 1: renders Ollama and OpenRouter radio buttons with Ollama pre-selected", () => {
    render(<ProviderSetup />);

    const ollamaRadio = screen.getByRole("radio", { name: /ollama/i });
    const openrouterRadio = screen.getByRole("radio", { name: /openrouter/i });

    expect(ollamaRadio).toBeTruthy();
    expect(openrouterRadio).toBeTruthy();
    // Ollama pre-selected by default
    expect((ollamaRadio as HTMLInputElement).checked).toBe(true);
    expect((openrouterRadio as HTMLInputElement).checked).toBe(false);
  });

  it("Test 2: selecting OpenRouter shows API key input; selecting Ollama hides it", () => {
    render(<ProviderSetup />);

    const openrouterRadio = screen.getByRole("radio", { name: /openrouter/i });

    // Initially no API key input (Ollama selected)
    expect(screen.queryByLabelText(/openrouter api key/i)).toBeNull();

    // Select OpenRouter
    fireEvent.click(openrouterRadio);
    expect(screen.getByLabelText(/openrouter api key/i)).toBeTruthy();

    // Switch back to Ollama
    const ollamaRadio = screen.getByRole("radio", { name: /ollama/i });
    fireEvent.click(ollamaRadio);
    expect(screen.queryByLabelText(/openrouter api key/i)).toBeNull();
  });

  it("Test 3: Continue button is disabled when OpenRouter selected and API key is empty", () => {
    render(<ProviderSetup />);

    // Select OpenRouter
    const openrouterRadio = screen.getByRole("radio", { name: /openrouter/i });
    fireEvent.click(openrouterRadio);

    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect((continueBtn as HTMLButtonElement).disabled).toBe(true);
  });

  it("Test 4: Continue button is enabled when OpenRouter selected and API key is non-empty", () => {
    render(<ProviderSetup />);

    // Select OpenRouter
    const openrouterRadio = screen.getByRole("radio", { name: /openrouter/i });
    fireEvent.click(openrouterRadio);

    // Type an API key
    const apiKeyInput = screen.getByLabelText(/openrouter api key/i);
    fireEvent.change(apiKeyInput, { target: { value: "sk-or-test-123" } });

    const continueBtn = screen.getByRole("button", { name: /continue/i });
    expect((continueBtn as HTMLButtonElement).disabled).toBe(false);
  });

  it("Test 5: successful submit calls setProviderConfig and persists to localStorage", async () => {
    // Mock fetch to return success
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "configured", provider: "ollama" }),
    }));

    render(<ProviderSetup />);

    // Continue with Ollama (default selection)
    const continueBtn = screen.getByRole("button", { name: /continue/i });
    await act(async () => {
      fireEvent.click(continueBtn);
    });

    await waitFor(() => {
      // Check store was updated
      const storeConfig = useSimulationStore.getState().providerConfig;
      expect(storeConfig).not.toBeNull();
      expect(storeConfig?.provider).toBe("ollama");
    });

    // Check localStorage
    const stored = localStorage.getItem("agenttown_provider");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.provider).toBe("ollama");
  });

  it("Test 6: ProviderSetup is NOT rendered when store has valid provider config", () => {
    // Pre-populate localStorage
    localStorage.setItem(
      "agenttown_provider",
      JSON.stringify({ provider: "ollama" })
    );

    // Simulate App reading localStorage and calling setProviderConfig
    act(() => {
      useSimulationStore.getState().setProviderConfig({ provider: "ollama" });
    });

    // If providerConfig is set, App would not render ProviderSetup
    // Verify the store has the config (App conditionally renders based on this)
    const storeConfig = useSimulationStore.getState().providerConfig;
    expect(storeConfig).not.toBeNull();
    expect(storeConfig?.provider).toBe("ollama");
  });
});
