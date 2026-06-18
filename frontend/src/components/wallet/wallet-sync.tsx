"use client";

import { useEffect } from "react";
import { useAccount } from "wagmi";

import { useChatStore } from "@/store/chat-store";

export function WalletSync() {
  const { address, isConnected } = useAccount();
  const setConnectedWalletAddress = useChatStore((state) => state.setConnectedWalletAddress);

  useEffect(() => {
    setConnectedWalletAddress(isConnected && address ? address : null);
  }, [address, isConnected, setConnectedWalletAddress]);

  return null;
}
