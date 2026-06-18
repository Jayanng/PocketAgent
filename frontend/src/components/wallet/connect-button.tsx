"use client";

import { ConnectButton as RainbowConnectButton } from "@rainbow-me/rainbowkit";
import { ChevronDown, PlugZap, Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ConnectButton() {
  return (
    <RainbowConnectButton.Custom>
      {({ account, chain, mounted, openAccountModal, openChainModal, openConnectModal }) => {
        const ready = mounted;
        const connected = ready && account && chain;

        if (!connected) {
          return (
            <Button
              className="w-full"
              disabled={!ready}
              onClick={openConnectModal}
            >
              <Wallet size={16} />
              Connect Wallet
            </Button>
          );
        }

        if (chain.unsupported) {
          return (
            <Button className="w-full border-red-500 bg-red-600 text-white hover:bg-red-700" onClick={openChainModal}>
              <PlugZap size={16} />
              Wrong Network
            </Button>
          );
        }

        return (
          <div className="grid gap-2">
            <Button variant="secondary" className="w-full justify-between" onClick={openChainModal}>
              <span className="flex min-w-0 items-center gap-2">
                {chain.hasIcon && chain.iconUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={chain.iconUrl} alt="" className="h-4 w-4 rounded-full" />
                ) : (
                  <PlugZap size={16} />
                )}
                <span className="truncate">{chain.name}</span>
              </span>
              <ChevronDown size={15} />
            </Button>
            <Button variant="secondary" className="w-full justify-between" onClick={openAccountModal}>
              <span className="truncate">{account.displayName}</span>
              {account.displayBalance && (
                <span className="shrink-0 text-xs text-muted-foreground">{account.displayBalance}</span>
              )}
            </Button>
          </div>
        );
      }}
    </RainbowConnectButton.Custom>
  );
}
