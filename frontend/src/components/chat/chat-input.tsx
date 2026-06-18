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
    <div className="flex items-end gap-2 rounded-lg border border-border bg-background p-2 shadow-sm">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        disabled={disabled}
        placeholder="Ask about any blockchain... (e.g., 'What's the gas price on Ethereum?')"
        className="max-h-[120px] min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
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
        aria-label="Send message"
        title="Send message"
      >
        <SendHorizontal size={17} />
      </Button>
    </div>
  );
}
