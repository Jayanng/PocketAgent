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
});
