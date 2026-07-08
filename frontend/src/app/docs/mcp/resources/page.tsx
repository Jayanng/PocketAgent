import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsProse, DocsP, DocsTable } from "@/components/docs/docs-ui";
import { MCP_RESOURCES } from "@/lib/docs/tools";

export default function McpResourcesPage() {
  return (
    <DocsPage title="MCP Resources" description="Read-only URIs exposed by the PocketAgent MCP server.">
      <DocsProse>
        <DocsP>
          Resources provide structured context without invoking tools. Clients fetch them via MCP{" "}
          <code className="font-mono text-[12px]">read_resource</code>.
        </DocsP>

        <DocsH2 id="uris">Resource URIs</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">URI</th>
              <th className="px-4 py-3 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody>
            {MCP_RESOURCES.map((r) => (
              <tr key={r.uri} className="border-b border-white/5">
                <td className="px-4 py-2.5 font-mono text-[12px]">{r.uri}</td>
                <td className="px-4 py-2.5 text-[13px] opacity-75">{r.description}</td>
              </tr>
            ))}
          </tbody>
        </DocsTable>
      </DocsProse>
    </DocsPage>
  );
}