"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/**
 * Friendly alias for Automations UI.
 * Chat "Schedule this" navigates here; we forward query params to /scheduled-tasks.
 */
function AutomationsRedirectInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const q = searchParams.toString();
    router.replace(q ? `/scheduled-tasks?${q}` : "/scheduled-tasks");
  }, [router, searchParams]);

  return (
    <div className="p-6 text-sm text-muted-foreground">Opening Automations…</div>
  );
}

export default function AutomationsAliasPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Opening Automations…</div>}>
      <AutomationsRedirectInner />
    </Suspense>
  );
}
