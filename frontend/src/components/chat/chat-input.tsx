"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, SendHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";

type ChatInputProps = {
  disabled?: boolean;
  /** Optional agent for pre-selecting in the Automations create dialog. */
  agentId?: string | null;
  onSend: (message: string) => void;
};

export function ChatInput({ disabled = false, agentId = null, onSend }: ChatInputProps) {
  const router = useRouter();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const resize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  };

  const submit = () => {
    const message = value.trim();
    if (!message || disabled) return;
    onSend(message);
    setValue("");
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "";
      }
    });
  };

  const scheduleThis = () => {
    const message = value.trim();
    if (!message || disabled) return;
    const params = new URLSearchParams({ prefill: message.slice(0, 2000) });
    if (agentId) params.set("agent_id", agentId);
    // /automations aliases to the Automations page (scheduled-tasks).
    router.push(`/automations?${params.toString()}`);
  };

  return (
    <div className="w-full">
      <div className="flex items-end gap-2.5 rounded-2xl border border-border/50 bg-card/40 backdrop-blur-lg p-2 shadow-lg shadow-black/15 transition-colors duration-200 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          placeholder="Ask about any blockchain..."
          className="h-11 max-h-[120px] min-h-[2.75rem] flex-1 resize-none bg-transparent px-2 py-2.5 text-base leading-relaxed outline-none placeholder:text-muted-foreground/50 disabled:cursor-not-allowed disabled:opacity-50 text-foreground sm:px-3 sm:h-9 sm:text-sm"
          onChange={(event) => {
            setValue(event.target.value);
            requestAnimationFrame(resize);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={disabled || !value.trim()}
          onClick={scheduleThis}
          className="mb-0.5 h-9 shrink-0 gap-1 rounded-xl px-2 text-[11px] font-medium text-muted-foreground hover:text-foreground sm:h-8"
          aria-label="Schedule this as an automation"
          title="Open Automations with this prompt pre-filled"
        >
          <CalendarClock size={13} />
          <span className="hidden sm:inline">Schedule this</span>
        </Button>
        <Button
          type="button"
          size="icon"
          disabled={disabled || !value.trim()}
          onClick={submit}
          className="h-11 w-11 shrink-0 rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/10 transition-all hover:scale-105 hover:bg-primary/95 active:scale-95 disabled:pointer-events-none disabled:scale-100 disabled:opacity-40 sm:h-9 sm:w-9"
          aria-label="Send message"
          title="Send message"
        >
          <SendHorizontal size={14} />
        </Button>
      </div>
    </div>
  );
}
