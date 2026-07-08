import { DocsPage } from "@/components/docs/docs-page";
import { DocsH2, DocsProse, DocsP, DocsTable } from "@/components/docs/docs-ui";

const HTTP_ERRORS = [
  { code: "400", meaning: "Bad Request", when: "Invalid tool arguments, chat persistence failure, malformed reissue proof" },
  { code: "403", meaning: "Forbidden", when: "Missing or invalid X-Agent-Access-Token on protected routes" },
  { code: "404", meaning: "Not Found", when: "Agent or conversation does not exist" },
  { code: "410", meaning: "Gone", when: "Agent is soft-deleted (inactive)" },
  { code: "422", meaning: "Unprocessable Entity", when: "Missing required fields (e.g. agent_id on chat)" },
  { code: "503", meaning: "Service Unavailable", when: "OpenAI upstream failure or RPC service unavailable" },
];

export default function ErrorsPage() {
  return (
    <DocsPage title="Errors" description="HTTP status codes and common API failure modes.">
      <DocsProse>
        <DocsP>
          FastAPI returns JSON <code className="font-mono text-[12px]">{"{ \"detail\": \"...\" }"}</code> on
          errors. SSE chat streams emit an <code className="font-mono text-[12px]">error</code> event before closing.
        </DocsP>

        <DocsH2 id="http">HTTP status codes</DocsH2>
        <DocsTable>
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-4 py-3 font-semibold">Code</th>
              <th className="px-4 py-3 font-semibold">Meaning</th>
              <th className="px-4 py-3 font-semibold">Typical cause</th>
            </tr>
          </thead>
          <tbody>
            {HTTP_ERRORS.map((e) => (
              <tr key={e.code} className="border-b border-white/5">
                <td className="px-4 py-2.5 font-mono text-[12px]">{e.code}</td>
                <td className="px-4 py-2.5 font-medium">{e.meaning}</td>
                <td className="px-4 py-2.5 text-[12px] opacity-75">{e.when}</td>
              </tr>
            ))}
          </tbody>
        </DocsTable>

        <DocsH2 id="tool-errors">Tool-level failures</DocsH2>
        <DocsP>
          Tools return structured JSON with <code className="font-mono text-[12px]">success: false</code> and a{" "}
          <code className="font-mono text-[12px]">message</code> field for RPC errors, cap violations, insufficient
          balance, or testnet URL rejection on write tools in production.
        </DocsP>
      </DocsProse>
    </DocsPage>
  );
}