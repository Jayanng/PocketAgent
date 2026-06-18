"use client";

import "@rainbow-me/rainbowkit/styles.css";

import { RainbowKitProvider, getDefaultConfig, lightTheme } from "@rainbow-me/rainbowkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";
import { WagmiProvider } from "wagmi";
import { arbitrum, avalanche, base, bsc, mainnet as ethereum, optimism, polygon } from "wagmi/chains";
import { http } from "viem";

import { WalletSync } from "@/components/wallet/wallet-sync";
import { POCKET_RPC_ENDPOINTS } from "@/lib/constants";

const chains = [ethereum, polygon, arbitrum, optimism, bsc, avalanche, base] as const;

export const walletConfig = getDefaultConfig({
  appName: "PocketAgent",
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID ?? "pocketagent-local",
  chains,
  ssr: true,
  transports: {
    [ethereum.id]: http(POCKET_RPC_ENDPOINTS.ethereum),
    [polygon.id]: http(POCKET_RPC_ENDPOINTS.polygon),
    [arbitrum.id]: http(POCKET_RPC_ENDPOINTS.arbitrum),
    [optimism.id]: http(POCKET_RPC_ENDPOINTS.optimism),
    [bsc.id]: http(POCKET_RPC_ENDPOINTS.bsc),
    [avalanche.id]: http(POCKET_RPC_ENDPOINTS.avalanche),
    [base.id]: http(POCKET_RPC_ENDPOINTS.base),
  },
});

type WalletProviderProps = {
  children: ReactNode;
};

export function WalletProvider({ children }: WalletProviderProps) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={walletConfig}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider
          theme={lightTheme({
            accentColor: "#1e88e5",
            accentColorForeground: "#ffffff",
            borderRadius: "medium",
          })}
        >
          <WalletSync />
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
