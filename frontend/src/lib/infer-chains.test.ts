import { describe, expect, it } from "vitest";

import { inferChains } from "@/lib/infer-chains";

describe("inferChains", () => {
  it("reads chain from args.chain", () => {
    expect(inferChains([{ tool: "evm_get_balance", args: { chain: "arbitrum" } }])).toEqual([
      "arbitrum",
    ]);
  });

  it("reads multiple chains from args.chains", () => {
    expect(
      inferChains([{ tool: "compare_gas_fees", args: { chains: ["ethereum", "polygon"] } }]),
    ).toEqual(["ethereum", "polygon"]);
  });

  it("returns an empty list when no chain hints exist", () => {
    expect(inferChains([])).toEqual([]);
  });
});