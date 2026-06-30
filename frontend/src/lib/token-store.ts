/**
 * TokenStore: persists per-agent access tokens in localStorage with
 * in-memory caching and BroadcastChannel cross-tab sync.
 *
 * Storage key: pocketagent:agent-token:<agentId>
 * Channel name: pocketagent:tokens
 * Bundle version: 1
 */
const STORAGE_PREFIX = "pocketagent:agent-token:";
const CHANNEL_NAME = "pocketagent:tokens";
const BUNDLE_VERSION = 1;

export interface TokenBundle {
  version: number;
  exportedAt: string;
  tokens: Array<{ agentId: string; token: string }>;
}

export type TokenChangeEvent =
  | { type: "set"; agentId: string; token: string }
  | { type: "forget"; agentId: string };

export interface TokenStore {
  get(agentId: string): string | null;
  set(agentId: string, token: string): void;
  forget(agentId: string): void;
  has(agentId: string): boolean;
  exportAll(): TokenBundle;
  importOne(agentId: string, token: string): void;
  importMany(bundle: TokenBundle): { ok: number; failed: string[] };
  onChange(listener: (event: TokenChangeEvent) => void): () => void;
}

export function createTokenStore(): TokenStore {
  const memory = new Map<string, string>();
  const listeners = new Set<(event: TokenChangeEvent) => void>();
  let hydrated = false;
  let quotaWarned = false;
  let channel: BroadcastChannel | null = null;

  function hydrate(): void {
    if (hydrated || typeof window === "undefined") return;
    hydrated = true;
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith(STORAGE_PREFIX)) {
          const agentId = key.slice(STORAGE_PREFIX.length);
          const token = localStorage.getItem(key);
          if (agentId && token) memory.set(agentId, token);
        }
      }
    } catch {
      // localStorage unavailable
    }
  }

  function storageKey(agentId: string): string {
    return STORAGE_PREFIX + agentId;
  }

  function notify(event: TokenChangeEvent, broadcast = true): void {
    for (const listener of listeners) {
      try {
        listener(event);
      } catch (e) {
        console.error("TokenStore listener threw", e);
      }
    }
    if (broadcast) {
      try {
        channel?.postMessage(event);
      } catch {
        // BroadcastChannel unavailable
      }
    }
  }

  if (typeof window !== "undefined") {
    try {
      if (typeof BroadcastChannel !== "undefined") {
        channel = new BroadcastChannel(CHANNEL_NAME);
        channel.onmessage = (e) => {
          const event = e.data as TokenChangeEvent;
          if (event.type === "set") {
            memory.set(event.agentId, event.token);
          } else if (event.type === "forget") {
            memory.delete(event.agentId);
          }
          // Notify local listeners but don't re-broadcast
          notify(event, false);
        };
      }
    } catch {
      // ignore
    }
  }

  return {
    get(agentId) {
      hydrate();
      return memory.get(agentId) ?? null;
    },
    set(agentId, token) {
      hydrate();
      memory.set(agentId, token);
      try {
        localStorage.setItem(storageKey(agentId), token);
      } catch (e) {
        if (
          !quotaWarned &&
          e instanceof DOMException &&
          e.name === "QuotaExceededError"
        ) {
          quotaWarned = true;
          console.warn(
            "localStorage quota exceeded; tokens will not persist across sessions.",
          );
        }
      }
      notify({ type: "set", agentId, token });
    },
    forget(agentId) {
      hydrate();
      memory.delete(agentId);
      try {
        localStorage.removeItem(storageKey(agentId));
      } catch {
        // ignore
      }
      notify({ type: "forget", agentId });
    },
    has(agentId) {
      return this.get(agentId) !== null;
    },
    exportAll() {
      hydrate();
      return {
        version: BUNDLE_VERSION,
        exportedAt: new Date().toISOString(),
        tokens: Array.from(memory.entries()).map(([agentId, token]) => ({
          agentId,
          token,
        })),
      };
    },
    importOne(agentId, token) {
      this.set(agentId, token);
    },
    importMany(bundle) {
      if (bundle.version !== BUNDLE_VERSION) {
        return { ok: 0, failed: bundle.tokens.map((t) => t.agentId) };
      }
      let ok = 0;
      const failed: string[] = [];
      for (const { agentId, token } of bundle.tokens) {
        if (!agentId || !token) {
          failed.push(agentId);
          continue;
        }
        this.set(agentId, token);
        ok++;
      }
      return { ok, failed };
    },
    onChange(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export const tokenStore = createTokenStore();
