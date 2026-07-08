import { DocsPage } from "@/components/docs/docs-page";
import { CodeBlock, DocsProse, DocsP } from "@/components/docs/docs-ui";
import { EnvVarsTable } from "@/components/docs/env-vars-table";
import { BACKEND_ENV_VARS, FRONTEND_ENV_VARS, MCP_ENV_VARS } from "@/lib/docs/env-vars";

export default function ConfigurationPage() {
  return (
    <DocsPage
      title="Configuration"
      description="Environment variables for the backend, frontend, and MCP server."
    >
      <DocsProse>
        <DocsP>
          Copy <code className="font-mono text-[12px]">backend/.env.example</code> and{" "}
          <code className="font-mono text-[12px]">frontend/.env.example</code> when running locally.
          Never commit real secrets.
        </DocsP>

        <CodeBlock>{`# Generate secrets (example)
python -c "import secrets; print(secrets.token_hex(32))"  # ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"  # JWT_SECRET`}</CodeBlock>

        <EnvVarsTable vars={BACKEND_ENV_VARS} title="Backend variables" />
        <EnvVarsTable vars={FRONTEND_ENV_VARS} title="Frontend variables" />
        <EnvVarsTable vars={MCP_ENV_VARS} title="MCP server variables" />
      </DocsProse>
    </DocsPage>
  );
}