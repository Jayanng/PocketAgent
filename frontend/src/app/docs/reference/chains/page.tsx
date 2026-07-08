import { DocsPage } from "@/components/docs/docs-page";
import { ChainsReference } from "@/components/docs/chains-reference";

export default function ChainsReferencePage() {
  return (
    <DocsPage
      title="Supported Chains"
      description="Searchable reference for all 52 Pocket Network–backed chains."
    >
      <ChainsReference />
    </DocsPage>
  );
}