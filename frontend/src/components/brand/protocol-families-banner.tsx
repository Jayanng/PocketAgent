"use client";

import { cn } from "@/lib/utils";

const PROTOCOLS = ["EVM", "Solana", "Sui", "NEAR", "Tron", "Cosmos"] as const;

type ProtocolFamiliesBannerProps = {
  className?: string;
};

function ProtocolSvg({ name }: { name: string }) {
  switch (name) {
    case "EVM":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="EVM">
          <circle cx="32" cy="32" r="31" fill="#627EEA"/>
          <text x="32" y="39" textAnchor="middle" fill="#ffffff" fontSize="17" fontWeight="700" fontFamily="Inter, system-ui, sans-serif">EVM</text>
        </svg>
      );
    case "Solana":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="Solana">
          <defs>
            <linearGradient id="sol-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00FFA3"/>
              <stop offset="100%" stopColor="#DC1FFF"/>
            </linearGradient>
          </defs>
          <circle cx="32" cy="32" r="31" fill="#000000"/>
          <g transform="translate(4, 4) scale(0.875)">
            <rect x="8" y="14" width="48" height="10" rx="3" fill="url(#sol-gradient)"/>
            <rect x="8" y="27" width="48" height="10" rx="3" fill="url(#sol-gradient)" opacity="0.85"/>
            <rect x="8" y="40" width="48" height="10" rx="3" fill="url(#sol-gradient)" opacity="0.7"/>
          </g>
        </svg>
      );
    case "Sui":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="Sui">
          <circle cx="32" cy="32" r="31" fill="#4DA2FF"/>
          <path d="M32 14 C24 24 18 30 18 38 C18 44 24 50 32 50 C40 50 46 44 46 38 C46 30 40 24 32 14 Z" fill="#ffffff"/>
        </svg>
      );
    case "NEAR":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="NEAR">
          <circle cx="32" cy="32" r="31" fill="#000000"/>
          <text x="32" y="39" textAnchor="middle" fill="#ffffff" fontSize="14" fontWeight="700" fontFamily="Inter, system-ui, sans-serif">NEAR</text>
        </svg>
      );
    case "Tron":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="Tron">
          <circle cx="32" cy="32" r="31" fill="#FF060A"/>
          <g stroke="#ffffff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="none">
            <polygon points="32,52 14,20 50,20" />
            <line x1="32" y1="52" x2="32" y2="34" />
            <line x1="14" y1="20" x2="32" y2="34" />
            <line x1="50" y1="20" x2="32" y2="34" />
            <line x1="14" y1="20" x2="32" y2="25" />
            <line x1="50" y1="20" x2="32" y2="25" />
            <line x1="32" y1="34" x2="32" y2="25" />
          </g>
        </svg>
      );
    case "Cosmos":
      return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" className="h-full w-full" role="img" aria-label="Cosmos">
          <circle cx="32" cy="32" r="31" fill="#2E3148"/>
          <circle cx="32" cy="32" r="10" fill="none" stroke="#6F7390" strokeWidth="3"/>
          <ellipse cx="32" cy="32" rx="22" ry="8" fill="none" stroke="#6F7390" strokeWidth="2.5" transform="rotate(60 32 32)"/>
          <ellipse cx="32" cy="32" rx="22" ry="8" fill="none" stroke="#6F7390" strokeWidth="2.5" transform="rotate(-60 32 32)"/>
        </svg>
      );
    default:
      return null;
  }
}

function ProtocolLogo({ name }: { name: string }) {
  return (
    <div className="flex flex-col items-center gap-1.5 select-none">
      <div className="landing-protocol-tile flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-transform duration-200 group-hover:scale-105">
        <div className="h-6.5 w-6.5 flex items-center justify-center">
          <ProtocolSvg name={name} />
        </div>
      </div>
      <span className="landing-protocol-name text-[10px] font-semibold tracking-wide sm:text-[11px]">
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
        "landing-protocol-banner landing-card-image mt-6 rounded-xl border p-4 sm:p-5",
        className,
      )}
    >
      <p className="landing-protocol-label mb-3.5 text-center text-[10px] font-semibold uppercase tracking-[0.16em]">
        6 Protocol Families · 52 Chains
      </p>
      <div className="grid grid-cols-3 gap-4 sm:grid-cols-6 sm:gap-2">
        {PROTOCOLS.map((protocol) => (
          <ProtocolLogo key={protocol} name={protocol} />
        ))}
      </div>
    </div>
  );
}
