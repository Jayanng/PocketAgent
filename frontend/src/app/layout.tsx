import type { Metadata } from "next";
import { AppProviders } from "@/components/providers";
import { WalletProvider } from "@/components/wallet/wallet-provider";
import { ToastProvider } from "@/components/ui/toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "PocketAgent — AI Agents for the Multi-Chain World",
  description:
    "Deploy autonomous AI agents that read and compare 52 blockchains through Pocket Network's decentralized RPC, with guarded native transaction signing on EVM, Solana, and Tron.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// Single blocking bootstrap script: wallet-extension shim + theme init.
// Kept as one tag so wallet extensions (Xverse, Phantom, etc.) are less likely to
// replace a head script and cause React hydration mismatches.
const bootstrapScript = `(function(){function e(e){if(!e)return!1;return e.indexOf("Cannot redefine property: ethereum")!==-1||e.indexOf("can't redefine non-configurable property")!==-1}function n(n){var t=n&&(n.message||n.reason&&n.reason.message);if(!e(t))return;n.preventDefault&&n.preventDefault();n.stopImmediatePropagation&&n.stopImmediatePropagation();return!0}var r=window.ethereum;try{Object.defineProperty(window,"ethereum",{configurable:!0,enumerable:!0,get:function(){return r},set:function(e){r=e}});void 0!==r&&(window.ethereum=r)}catch(e){}window.addEventListener("error",n,!0);window.addEventListener("unhandledrejection",n,!0);try{var t=localStorage.getItem("pocketagent-theme")||localStorage.getItem("pocketagent-landing-theme");if("dark"===t||"light"===t){var o=document.documentElement;o.setAttribute("data-theme",t);o.setAttribute("data-landing-theme",t);o.classList.remove("theme-light","theme-dark");o.classList.add("light"===t?"theme-light":"theme-dark")}}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head suppressHydrationWarning />
      <body className="min-h-full bg-background text-foreground" suppressHydrationWarning>
        <script
          id="pocketagent-bootstrap"
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: bootstrapScript }}
        />
        <AppProviders>
          <WalletProvider>
            <ToastProvider>{children}</ToastProvider>
          </WalletProvider>
        </AppProviders>
      </body>
    </html>
  );
}
