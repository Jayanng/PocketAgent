"use client";

import { ConnectButton as RainbowConnectButton } from "@rainbow-me/rainbowkit";
import { ChevronDown, PlugZap, Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";

type ConnectButtonProps = {
  layout?: "horizontal" | "vertical";
  tone?: "default" | "landing";
};

export function ConnectButton({ layout = "horizontal", tone = "default" }: ConnectButtonProps) {
  return (
    <RainbowConnectButton.Custom>
      {({ account, chain, mounted, openAccountModal, openChainModal, openConnectModal }) => {
        const ready = mounted;
        const connected = ready && account && chain;

        if (!connected) {
          if (tone === "landing") {
            return (
              <button
                type="button"
                disabled={!ready}
                onClick={openConnectModal}
                className={
                  layout === "horizontal"
                    ? "landing-btn h-10 min-h-11 px-3 text-[11px] sm:h-9 sm:min-h-0 sm:px-4 sm:text-xs"
                    : "landing-btn w-full min-h-11 justify-center text-sm"
                }
              >
                <Wallet size={14} />
                <span className="hidden sm:inline">Connect Wallet</span>
                <span className="sm:hidden">Connect</span>
              </button>
            );
          }

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
          <div className={layout === "horizontal" ? "flex max-w-[9.5rem] items-center gap-1.5 sm:max-w-none sm:gap-2" : "grid gap-2"}>
            <Button
              variant="secondary"
              className={layout === "horizontal" ? "h-9 min-w-0 flex-1 gap-1 rounded-lg px-2 text-[10px] sm:flex-none sm:px-3 sm:text-xs" : "w-full justify-between"}
              onClick={openChainModal}
            >
              <span className="flex min-w-0 items-center gap-1.5">
                {chain.hasIcon && chain.iconUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={chain.iconUrl} alt="" className="h-4 w-4 shrink-0 rounded-full" />
                ) : (
                  <PlugZap size={14} className="shrink-0" />
                )}
                <span className="truncate font-medium sm:max-w-[80px]">{chain.name}</span>
              </span>
              <ChevronDown size={12} className="shrink-0 opacity-60" />
            </Button>
            
            <Button
              variant="secondary"
              className={layout === "horizontal" ? "h-9 min-w-0 flex-1 gap-1 rounded-lg px-2 text-[10px] sm:flex-none sm:px-3 sm:text-xs" : "w-full justify-between"}
              onClick={openAccountModal}
            >
              <span className="truncate font-mono font-medium">{account.displayName}</span>
              {account.displayBalance && layout !== "horizontal" && (
                <span className="shrink-0 font-mono text-[10px] opacity-70">
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
