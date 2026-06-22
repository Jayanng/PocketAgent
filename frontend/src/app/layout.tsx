import { Inter, JetBrains_Mono } from "next/font/google";
import type { Metadata } from "next";
import { WalletProvider } from "@/components/wallet/wallet-provider";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "PocketAgent — AI Agents for the Multi-Chain World",
  description:
    "Deploy autonomous AI agents that read, compare, and transact across 60+ blockchains through Pocket Network's decentralized RPC. One interface. Zero centralized gatekeepers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <WalletProvider>
          <ToastProvider>{children}</ToastProvider>
        </WalletProvider>
      </body>
    </html>
  );
}
