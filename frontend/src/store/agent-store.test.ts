import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock the api module so store tests don't make real network calls.
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      agents: {
        list: vi.fn().mockResolvedValue([]),
        create: vi.fn(),
        get: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
        fund: vi.fn(),
        balances: vi.fn(),
        reissue: vi.fn(),
        reissueChallenge: vi.fn(),
      },
      chat: {
        sendMessage: vi.fn(),
        getConversations: vi.fn().mockResolvedValue([]),
        getMessages: vi.fn(),
        deleteConversation: vi.fn(),
      },
      analytics: {
        relayStats: vi.fn(),
        chainHealth: vi.fn(),
        costTracker: vi.fn(),
        portfolio: vi.fn(),
      },
    },
  };
});

import { useAgentStore } from "./agent-store";
import { api, rememberAgentAccessToken } from "@/lib/api";
import { tokenStore } from "@/lib/token-store";

const originalFetch = globalThis.fetch;

function resetStore() {
  useAgentStore.setState({
    agents: [],
    selectedAgentId: null,
    selectedAgent: null,
    conversations: [],
    balances: {},
    isLoadingBalances: false,
    isLoading: false,
    isCreating: false,
    isUpdating: false,
    isRotating: false,
    error: null,
    createdWalletAddress: null,
    createdWalletAddresses: {},
    createdAccessToken: null,
  });
}

describe("useAgentStore.rotateAgentAccessToken", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
    resetStore();
    vi.clearAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("throws and sets error when no current token exists", async () => {
    const { rotateAgentAccessToken } = useAgentStore.getState();
    await expect(rotateAgentAccessToken("a1")).rejects.toThrow(
      "No current token in this browser.",
    );
    expect(useAgentStore.getState().error).toMatch(/no current token/i);
  });

  it("calls api.agents.reissue with current_token proof and stores the new token", async () => {
    rememberAgentAccessToken("a1", "old-tok");
    (api.agents.reissue as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      access_token: "new-tok",
    });

    const { rotateAgentAccessToken } = useAgentStore.getState();
    const result = await rotateAgentAccessToken("a1");

    expect(result).toBe("new-tok");
    expect(api.agents.reissue).toHaveBeenCalledWith("a1", {
      proof: { type: "current_token", token: "old-tok" },
    });
    // The store should update tokenStore via rememberAgentAccessToken
    expect(tokenStore.get("a1")).toBe("new-tok");
    expect(useAgentStore.getState().isRotating).toBe(false);
  });

  it("sets isRotating during the call and clears it on success", async () => {
    rememberAgentAccessToken("a1", "old-tok");
    let resolveReissue: (v: { access_token: string }) => void = () => {};
    (api.agents.reissue as ReturnType<typeof vi.fn>).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveReissue = resolve;
      }),
    );

    const promise = useAgentStore.getState().rotateAgentAccessToken("a1");
    expect(useAgentStore.getState().isRotating).toBe(true);

    resolveReissue({ access_token: "new-tok" });
    await promise;

    expect(useAgentStore.getState().isRotating).toBe(false);
  });

  it("captures server error message and resets isRotating", async () => {
    rememberAgentAccessToken("a1", "old-tok");
    (api.agents.reissue as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Invalid proof"),
    );

    const { rotateAgentAccessToken } = useAgentStore.getState();
    await expect(rotateAgentAccessToken("a1")).rejects.toThrow("Invalid proof");
    expect(useAgentStore.getState().error).toBe("Invalid proof");
    expect(useAgentStore.getState().isRotating).toBe(false);
  });
});

describe("useAgentStore.exportAllAgentTokens", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
    tokenStore.forget("a2");
    resetStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("triggers a download with the tokenStore bundle as JSON", () => {
    tokenStore.set("a1", "tok-1");
    tokenStore.set("a2", "tok-2");

    // Mock URL.createObjectURL and click on the anchor element
    const createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    const revokeObjectURL = vi.fn();
    globalThis.URL.createObjectURL = createObjectURL;
    globalThis.URL.revokeObjectURL = revokeObjectURL;

    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    useAgentStore.getState().exportAllAgentTokens();

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("application/json");

    // Verify the anchor got the right download filename and clicked
    const anchor = clickSpy.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.href).toBe("blob:mock-url");
    expect(anchor.download).toMatch(/^pocketagent-tokens-\d{4}-\d{2}-\d{2}\.json$/);
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });
});

describe("useAgentStore.importAgentAccessToken", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
    resetStore();
    vi.clearAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns false and sets error on empty token", async () => {
    const { importAgentAccessToken } = useAgentStore.getState();
    const ok = await importAgentAccessToken("a1", "   ");
    expect(ok).toBe(false);
    expect(useAgentStore.getState().error).toMatch(/required/i);
  });

  it("validates, stores, and selects agent on success", async () => {
    (api.agents.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      id: "a1",
      name: "Test Agent",
    });
    (api.chat.getConversations as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { id: "c1", title: "First" },
    ]);

    const ok = await useAgentStore.getState().importAgentAccessToken("a1", "valid-tok");
    expect(ok).toBe(true);
    expect(tokenStore.get("a1")).toBe("valid-tok");
    const state = useAgentStore.getState();
    expect(state.selectedAgentId).toBe("a1");
    expect(state.selectedAgent?.id).toBe("a1");
    expect(state.conversations).toHaveLength(1);
  });

  it("returns false and captures error on verification failure", async () => {
    (api.agents.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("Invalid token"),
    );
    const ok = await useAgentStore.getState().importAgentAccessToken("a1", "bad-tok");
    expect(ok).toBe(false);
    expect(useAgentStore.getState().error).toMatch(/invalid token/i);
    expect(tokenStore.get("a1")).toBeNull();
  });
});
