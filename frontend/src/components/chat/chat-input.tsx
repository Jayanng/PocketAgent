"use client";

import { useRef, useState } from "react";
import { SendHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";

type ChatInputProps = {
  disabled?: boolean;
  onSend: (message: string) => void;
};

export function ChatInput({ disabled = false, onSend }: ChatInputProps) {
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
        textareaRef.current.style.height = "auto";
      }
    });
  };

  return (
    <div className="space-y-1.5 w-full">
      <div className="flex items-end gap-2.5 rounded-2xl border border-border/50 bg-card/40 backdrop-blur-lg p-2 shadow-lg shadow-black/15 transition-all duration-200 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          placeholder="Ask about any blockchain..."
          className="max-h-[120px] min-h-[2.75rem] flex-1 resize-none bg-transparent px-2 py-2.5 text-base leading-relaxed outline-none placeholder:text-muted-foreground/50 disabled:cursor-not-allowed disabled:opacity-50 text-foreground sm:px-3 sm:text-sm"
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
      <div className="hidden items-center justify-between px-2 sm:flex">
        <span className="font-mono text-[9px] tracking-wider text-muted-foreground/35">
          Enter to send · Shift+Enter for newline
        </span>
      </div>
    </div>
  );
}
