"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";

const PROTOCOL_FAMILIES = [
  { name: "EVM", src: "/protocols/evm.svg" },
  { name: "Solana", src: "/protocols/solana.svg" },
  { name: "Sui", src: "/protocols/sui.svg" },
  { name: "NEAR", src: "/protocols/near.svg" },
  { name: "Tron", src: "/protocols/tron.svg" },
  { name: "Cosmos", src: "/protocols/cosmos.svg" },
] as const;

type ProtocolFamiliesBannerProps = {
  theme?: "light" | "dark";
  className?: string;
};

function ProtocolLogo({
  name,
  src,
}: {
  name: string;
  src: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="landing-protocol-tile flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl border shadow-sm transition-transform duration-200 group-hover:scale-105 sm:h-16 sm:w-16">
        {failed ? (
          <span className="text-xs font-bold uppercase tracking-wide text-primary">{name.slice(0, 4)}</span>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt={`${name} protocol`}
            className="h-9 w-9 object-contain sm:h-10 sm:w-10"
            onError={() => setFailed(true)}
          />
        )}
      </div>
      <span className="landing-protocol-name text-[11px] font-semibold tracking-wide sm:text-xs">
        {name}
      </span>
    </div>
  );
}

export function ProtocolFamiliesBanner({
  className,
}: ProtocolFamiliesBannerProps) {
  return (
    <div
      className={cn(
        "landing-protocol-banner landing-card-image mt-6 rounded-xl border p-4 sm:p-5 md:p-6",
        className,
      )}
    >
      <p className="landing-protocol-label mb-4 text-center text-[10px] font-semibold uppercase tracking-[0.16em]">
        6 Protocol Families · 52 Chains
      </p>
      <div className="grid grid-cols-3 gap-4 sm:grid-cols-6 sm:gap-3">
        {PROTOCOL_FAMILIES.map((protocol) => (
          <ProtocolLogo
            key={protocol.name}
            name={protocol.name}
            src={protocol.src}
          />
        ))}
      </div>
    </div>
  );
}