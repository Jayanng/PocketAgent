import { AppShell } from "@/components/layout/app-shell";
import { WalletProvider } from "@/components/wallet/wallet-provider";

export default function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <WalletProvider>
      <AppShell>{children}</AppShell>
    </WalletProvider>
  );
}