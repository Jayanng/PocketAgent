import * as React from "react";

import { cn } from "@/lib/utils";

export function Avatar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-muted text-xs font-bold text-muted-foreground",
        className
      )}
      {...props}
    />
  );
}
