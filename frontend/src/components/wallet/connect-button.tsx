"use client";

import { ConnectButton as RainbowConnectButton } from "@rainbow-me/rainbowkit";
import { ChevronDown, PlugZap, Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";

type ConnectButtonProps = {
  layout?: "horizontal" | "vertical";
};

export function ConnectButton({ layout = "horizontal" }: ConnectButtonProps) {
  return (
    <RainbowConnectButton.Custom>
      {({ account, chain, mounted, openAccountModal, openChainModal, openConnectModal }) => {
        const ready = mounted;
        const connected = ready && account && chain;

        if (!connected) {
          return (
            <Button
              className={layout === "horizontal" ? "h-9 px-3 text-xs gap-1.5" : "w-full"}
              disabled={!ready}
              onClick={openConnectModal}
            >
              <Wallet size={14} />
              Connect Wallet
            </Button>
          );
        }

        if (chain.unsupported) {
          return (
            <Button
              className={layout === "horizontal" ? "h-9 px-3 text-xs gap-1.5 border-red-500 bg-red-600 text-white hover:bg-red-700" : "w-full border-red-500 bg-red-600 text-white hover:bg-red-700"}
              onClick={openChainModal}
            >
              <PlugZap size={14} />
              Wrong Network
            </Button>
          );
        }

        return (
          <div className={layout === "horizontal" ? "flex items-center gap-2" : "grid gap-2"}>
            <Button
              variant="secondary"
              className={layout === "horizontal" ? "h-9 px-3 gap-1.5 rounded-lg text-xs" : "w-full justify-between"}
              onClick={openChainModal}
            >
              <span className="flex items-center gap-1.5 min-w-0">
                {chain.hasIcon && chain.iconUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={chain.iconUrl} alt="" className="h-4 w-4 rounded-full shrink-0" />
                ) : (
                  <PlugZap size={14} className="shrink-0" />
                )}
                <span className="truncate max-w-[80px] font-medium">{chain.name}</span>
              </span>
              <ChevronDown size={12} className="opacity-60 shrink-0" />
            </Button>
            
            <Button
              variant="secondary"
              className={layout === "horizontal" ? "h-9 px-3 gap-1.5 rounded-lg text-xs" : "w-full justify-between"}
              onClick={openAccountModal}
            >
              <span className="truncate font-mono font-medium">{account.displayName}</span>
              {account.displayBalance && (
                <span className="shrink-0 text-[10px] opacity-70 font-mono">
                  ({account.displayBalance})
                </span>
              )}
            </Button>
          </div>
        );
      }}
    </RainbowConnectButton.Custom>
  );
}
