import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsProse, DocsP, DocsTable } from "@/components/docs/docs-ui";
import { MCP_PROMPTS } from "@/lib/docs/tools";

export default function McpPromptsPage() {
  return (
    <DocsPage title="MCP Prompts" description="Built-in prompts for common multi-chain workflows.">
      <DocsProse>
        <DocsP>
          Prompts are pre-built instruction templates the MCP client can instantiate via{" "}
          <code className="font-mono text-[12px]">get_prompt</code>. Each prompt wires the right tools
          for its workflow.
        </DocsP>

        <DocsH2 id="list">Available prompts</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody>
            {MCP_PROMPTS.map((p) => (
              <tr key={p.name} className="border-b border-white/5">
                <td className="px-4 py-2.5 font-mono text-[12px]">{p.name}</td>
                <td className="px-4 py-2.5 text-[13px] opacity-75">{p.description}</td>
              </tr>
            ))}
          </tbody>
        </DocsTable>
      </DocsProse>
    </DocsPage>
  );
}