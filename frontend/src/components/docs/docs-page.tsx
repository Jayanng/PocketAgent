"use client";

import { usePathname } from "next/navigation";
import { getAdjacentDocsLinks } from "@/lib/docs/nav";
import { DocsPageHeader, DocsPager } from "@/components/docs/docs-ui";

export function DocsPage({
  title,
  description,
  version,
  children,
}: {
  title: string;
  description?: string;
  version?: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { prev, next } = getAdjacentDocsLinks(pathname);

  return (
    <article>
      <DocsPageHeader title={title} description={description} version={version} />
      {children}
      <DocsPager prev={prev} next={next} />
    </article>
  );
}