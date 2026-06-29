import { getAgentAccessToken } from "@/lib/api";

/** Mirrors backend DISABLE_AGENT_AUTH for local dev when agent tokens are not enforced. */
export function isAgentAuthDisabled(): boolean {
  const flag = process.env.NEXT_PUBLIC_DISABLE_AGENT_AUTH?.trim().toLowerCase();
  return flag === "true" || flag === "1" || flag === "yes";
}

export function canUseProtectedAgentRoutes(agentId: string | null | undefined): boolean {
  if (!agentId) return false;
  if (isAgentAuthDisabled()) return true;
  return Boolean(getAgentAccessToken(agentId));
}