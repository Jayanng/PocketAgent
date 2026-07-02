import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  api,
  getAgentAccessToken,
  rememberAgentAccessToken,
  forgetAgentAccessToken,
  API_BASE_URL,
} from "./api";
import { tokenStore } from "./token-store";

const originalFetch = globalThis.fetch;

describe("api.agents reissue methods", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("reissueChallenge fetches the challenge endpoint", async () => {
    const mockResponse = { message: "pocketagent:reissue:a1:1700000000", timestamp: 1700000000 };
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await api.agents.reissueChallenge("a1");

    expect(result).toEqual(mockResponse);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/agents/a1/reissue-challenge`);
    expect(init.headers["X-Agent-Access-Token"]).toBeUndefined();
    expect(init.method).toBeUndefined();
  });

  it("reissueChallenge includes access token when available", async () => {
    rememberAgentAccessToken("a1", "secret-tok");
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ message: "x", timestamp: 1 }),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await api.agents.reissueChallenge("a1");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["X-Agent-Access-Token"]).toBe("secret-tok");
  });

  it("reissue sends POST with current_token proof body", async () => {
    rememberAgentAccessToken("a1", "old-tok");
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "new-tok", access_token_created_at: "2026-06-30T00:00:00Z" }),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await api.agents.reissue("a1", {
      proof: { type: "current_token", token: "old-tok" },
    });

    expect(result.access_token).toBe("new-tok");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/agents/a1/reissue-token`);
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.headers["X-Agent-Access-Token"]).toBe("old-tok");
    expect(JSON.parse(init.body)).toEqual({
      proof: { type: "current_token", token: "old-tok" },
    });
  });

  it("reissue sends POST with wallet_signature proof body", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ access_token: "new-tok" }),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await api.agents.reissue("a1", {
      proof: {
        type: "wallet_signature",
        chain: "ethereum",
        message: "pocketagent:reissue:a1:1700000000",
        signature: "0xabc",
        public_key: "0xpub",
      },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      proof: {
        type: "wallet_signature",
        chain: "ethereum",
        message: "pocketagent:reissue:a1:1700000000",
        signature: "0xabc",
        public_key: "0xpub",
      },
    });
  });

  it("reissue throws on server error", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Invalid proof" }),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      api.agents.reissue("a1", { proof: { type: "current_token", token: "bad" } }),
    ).rejects.toThrow("Invalid proof");
  });
});

describe("token helper delegation to tokenStore", () => {
  beforeEach(() => {
    localStorage.clear();
    tokenStore.forget("a1");
  });

  it("getAgentAccessToken returns null for unknown agent", () => {
    expect(getAgentAccessToken("a1")).toBeNull();
  });

  it("rememberAgentAccessToken then getAgentAccessToken returns the token", () => {
    rememberAgentAccessToken("a1", "tok-1");
    expect(getAgentAccessToken("a1")).toBe("tok-1");
  });

  it("rememberAgentAccessToken trims whitespace", () => {
    rememberAgentAccessToken("a1", "  tok-1  ");
    expect(getAgentAccessToken("a1")).toBe("tok-1");
  });

  it("rememberAgentAccessToken ignores empty strings", () => {
    rememberAgentAccessToken("a1", "");
    expect(getAgentAccessToken("a1")).toBeNull();
  });

  it("forgetAgentAccessToken removes the token", () => {
    rememberAgentAccessToken("a1", "tok-1");
    forgetAgentAccessToken("a1");
    expect(getAgentAccessToken("a1")).toBeNull();
  });

  it("tokens persist across new api module reference (same store)", () => {
    rememberAgentAccessToken("a1", "tok-1");
    // Re-import would return same token via the underlying tokenStore singleton
    expect(tokenStore.get("a1")).toBe("tok-1");
  });
});
