import type { ChainCall } from "@/lib/api";

/** Extract chain slugs from tool-call args for the active-chain indicator. */
export function inferChains(calls: ChainCall[]): string[] {
  const values = new Set<string>();
  for (const call of calls) {
    const args = call.args ?? {};
    const chain =
      call.chain ?? (typeof args.chain === "string" ? args.chain : undefined);
    const chains =
      call.chains ?? (Array.isArray(args.chains) ? args.chains : undefined);
    if (chain) values.add(chain);
    if (chains) {
      for (const value of chains) {
        if (typeof value === "string") values.add(value);
      }
    }
  }
  return Array.from(values);
}