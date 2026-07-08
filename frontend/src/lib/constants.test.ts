import { describe, expect, it } from "vitest";

import { CHAIN_CONFIGS, chainBadgeSymbol } from "@/lib/constants";

describe("chainBadgeSymbol", () => {
  it("uses chain-specific badges for ETH-native L2s", () => {
    expect(chainBadgeSymbol("arbitrum")).toBe("ARB");
    expect(chainBadgeSymbol("optimism")).toBe("OP");
    expect(chainBadgeSymbol("base")).toBe("BASE");
  });

  it("keeps native symbol when no badge override exists", () => {
    expect(chainBadgeSymbol("ethereum")).toBe("ETH");
    expect(chainBadgeSymbol("polygon")).toBe("POL");
    expect(chainBadgeSymbol("solana")).toBe("SOL");
  });

  it("does not change native gas token on config", () => {
    expect(CHAIN_CONFIGS.arbitrum.symbol).toBe("ETH");
    expect(CHAIN_CONFIGS.optimism.symbol).toBe("ETH");
  });
});