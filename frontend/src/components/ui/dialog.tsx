"use client";

import * as React from "react";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
};

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  if (!open) return null;

  return (
    <div className="safe-top safe-bottom fixed inset-0 z-50 flex items-end justify-center bg-black/35 p-3 sm:items-center sm:p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        aria-label="Close dialog"
        className="absolute inset-0 cursor-default"
        onClick={() => onOpenChange(false)}
      />
      {children}
    </div>
  );
}

export function DialogContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("relative max-h-[85dvh] w-full overflow-y-auto rounded-t-2xl border border-border bg-card shadow-xl sm:max-h-[90vh] sm:rounded-lg", className)}
      {...props}
    />
  );
}

export function DialogHeader({
  title,
  description,
  onClose,
}: {
  title: string;
  description?: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border px-4 py-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <Button variant="ghost" size="icon" onClick={onClose} title="Close">
        <X size={16} />
      </Button>
    </div>
  );
}
