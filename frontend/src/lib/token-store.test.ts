import { describe, it, expect, beforeEach, vi } from "vitest";
import { createTokenStore } from "./token-store";

describe("TokenStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null for unknown agent", () => {
    const store = createTokenStore();
    expect(store.get("missing")).toBeNull();
  });

  it("stores and retrieves a token", () => {
    const store = createTokenStore();
    store.set("agent-1", "token-abc");
    expect(store.get("agent-1")).toBe("token-abc");
  });

  it("forgets a token", () => {
    const store = createTokenStore();
    store.set("agent-1", "token-abc");
    store.forget("agent-1");
    expect(store.get("agent-1")).toBeNull();
  });

  it("persists to localStorage", () => {
    const store1 = createTokenStore();
    store1.set("agent-1", "token-abc");
    const store2 = createTokenStore();
    expect(store2.get("agent-1")).toBe("token-abc");
  });

  it("exports all tokens as a bundle", () => {
    const store = createTokenStore();
    store.set("agent-1", "token-1");
    store.set("agent-2", "token-2");
    const bundle = store.exportAll();
    expect(bundle.version).toBe(1);
    expect(bundle.tokens).toHaveLength(2);
  });

  it("imports a bundle", () => {
    const store = createTokenStore();
    store.importMany({
      version: 1,
      exportedAt: new Date().toISOString(),
      tokens: [
        { agentId: "a", token: "t-a" },
        { agentId: "b", token: "t-b" },
      ],
    });
    expect(store.get("a")).toBe("t-a");
    expect(store.get("b")).toBe("t-b");
  });

  it("notifies listeners on set", () => {
    const store = createTokenStore();
    const listener = vi.fn();
    store.onChange(listener);
    store.set("agent-1", "token-abc");
    expect(listener).toHaveBeenCalledWith({ type: "set", agentId: "agent-1", token: "token-abc" });
  });

  it("falls back to in-memory when localStorage quota is exceeded", () => {
    const store = createTokenStore();
    const setItemSpy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new DOMException("QuotaExceededError", "QuotaExceededError");
      });
    expect(() => store.set("agent-1", "token-abc")).not.toThrow();
    expect(store.get("agent-1")).toBe("token-abc");
    setItemSpy.mockRestore();
  });

  // ─── Regression: trim whitespace on set ─────────────────────────────────
  it("trims whitespace around the token on set", () => {
    const store = createTokenStore();
    // Simulate a user pasting a token with surrounding whitespace from a
    // copy/paste action or accidental trailing newline.
    store.set("agent-1", "  tok-abc\n");
    expect(store.get("agent-1")).toBe("tok-abc");
  });

  it("emits listener event with the trimmed token", () => {
    const store = createTokenStore();
    const listener = vi.fn();
    store.onChange(listener);
    store.set("agent-1", "  tok-abc\n");
    expect(listener).toHaveBeenCalledWith({
      type: "set",
      agentId: "agent-1",
      token: "tok-abc",
    });
  });

  // ─── Regression: importMany should send ONE postMessage, not N ─────────
  it("importMany sends exactly one BroadcastChannel message for N tokens", () => {
    const store = createTokenStore();
    const postSpy = vi.fn();
    // Replace the BroadcastChannel instance the store uses after creation.
    // We spy on the prototype method so any postMessage call is captured.
    const proto = BroadcastChannel.prototype;
    const realPost = proto.postMessage;
    proto.postMessage = postSpy;
    try {
      store.importMany({
        version: 1,
        exportedAt: new Date().toISOString(),
        tokens: [
          { agentId: "a", token: "t-a" },
          { agentId: "b", token: "t-b" },
          { agentId: "c", token: "t-c" },
          { agentId: "d", token: "t-d" },
          { agentId: "e", token: "t-e" },
        ],
      });
      // Either one composite "import" message, or N individual set messages.
      // The bug was N individual set messages; the fix should be 1.
      expect(postSpy).toHaveBeenCalledTimes(1);
    } finally {
      proto.postMessage = realPost;
    }
  });
});
