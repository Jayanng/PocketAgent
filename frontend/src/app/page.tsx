import Link from "next/link";
import { ConnectButton } from "@/components/wallet/connect-button";
import { CHAIN_CONFIGS } from "@/lib/constants";

export default function Home() {
  const chainPreview = Object.values(CHAIN_CONFIGS).slice(0, 4);

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10 md:px-10 md:py-14">
      <div className="grid gap-6 lg:grid-cols-12">
        <section className="space-y-5 rounded-xl border border-border bg-card p-6 lg:col-span-8 lg:p-8">
          <span className="inline-flex rounded-md border border-border bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
            Built on Pocket
          </span>
          <h1 className="max-w-xl text-4xl font-semibold tracking-tight md:text-5xl">
            PocketAgent
          </h1>
          <p className="max-w-2xl text-base text-muted-foreground md:text-lg">
            AI agents for 60+ chains through Pocket Network decentralized RPC.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/chat"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Open Chat
            </Link>
            <Link
              href="/dashboard"
              className="rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-card-foreground"
            >
              View Dashboard
            </Link>
          </div>
          <div className="max-w-xs">
            <ConnectButton />
          </div>
        </section>
        <aside className="rounded-xl border border-border bg-card p-5 lg:col-span-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Chain Preview
          </p>
          <ul className="mt-3 space-y-2">
            {chainPreview.map((chain) => (
              <li
                key={chain.key}
                className="flex items-center justify-between rounded-md border border-border bg-muted px-3 py-2 text-sm"
              >
                <span>{chain.name}</span>
                <span className="text-muted-foreground">{chain.symbol}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </main>
  );
}
