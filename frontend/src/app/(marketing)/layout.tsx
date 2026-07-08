import { WalletProvider } from "@/components/wallet/wallet-provider";

/** Landing page only — keeps RainbowKit off /docs for faster compiles. */
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <WalletProvider>{children}</WalletProvider>;
}