import type { Metadata } from "next";
import { WalletProvider } from "@/components/wallet/wallet-provider";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "PocketAgent — AI Agents for the Multi-Chain World",
  description:
    "Deploy autonomous AI agents that read and compare 52 blockchains through Pocket Network's decentralized RPC, with guarded native transaction signing on EVM, Solana, and Tron.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-background text-foreground">
        <WalletProvider>
          <ToastProvider>{children}</ToastProvider>
        </WalletProvider>
      </body>
    </html>
  );
}
