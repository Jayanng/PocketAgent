"use client";

import { Bot, Menu, Plus, RefreshCw, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { Agent, Conversation } from "@/lib/api";
import { cn } from "@/lib/utils";

type ChatSidebarProps = {
  agents: Agent[];
  conversations: Conversation[];
  selectedAgentId: string | null;
  currentConversationId: string | null;
  isOpen: boolean;
  isBootstrapping: boolean;
  onToggle: () => void;
  onNewChat: () => void;
  onSelectAgent: (id: string) => void;
  onLoadConversation: (id: string) => void;
  onCreateAgent: () => void;
  onRefresh: () => void;
};

export function ChatSidebar({
  agents,
  conversations,
  selectedAgentId,
  currentConversationId,
  isOpen,
  isBootstrapping,
  onToggle,
  onNewChat,
  onSelectAgent,
  onLoadConversation,
  onCreateAgent,
  onRefresh,
}: ChatSidebarProps) {
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);

  return (
    <>
      <div className="mb-3 flex items-center justify-between lg:hidden">
        <Button variant="secondary" size="sm" onClick={onToggle}>
          <Menu size={16} />
          Conversations
        </Button>
        <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh workspace">
          <RefreshCw size={16} />
        </Button>
      </div>
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-72 border-r border-border bg-card p-4 shadow-xl transition-transform lg:static lg:z-auto lg:block lg:h-full lg:translate-x-0 lg:shadow-none",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Agent</p>
            <p className="mt-1 truncate text-sm font-semibold">{selectedAgent?.name ?? "No agent selected"}</p>
          </div>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={onToggle} title="Close sidebar">
            <X size={16} />
          </Button>
        </div>

        <div className="mt-4 space-y-3">
          <select
            value={selectedAgentId ?? ""}
            disabled={!agents.length || isBootstrapping}
            onChange={(event) => onSelectAgent(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary/35"
          >
            {!agents.length && <option value="">No agents</option>}
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <Button onClick={onNewChat} disabled={!selectedAgentId}>
              <Plus size={16} />
              New Chat
            </Button>
            <Button variant="secondary" size="icon" onClick={onRefresh} title="Refresh workspace">
              <RefreshCw size={16} />
            </Button>
          </div>
          {!agents.length && (
            <Card className="p-3">
              <div className="flex gap-3">
                <Bot className="mt-0.5 shrink-0 text-muted-foreground" size={18} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Create an agent to start chatting.</p>
                  <Button size="sm" onClick={onCreateAgent} disabled={isBootstrapping}>
                    Create Agent
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </div>

        <Separator className="my-4" />

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Conversations</p>
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                onClick={() => onLoadConversation(conversation.id)}
                className={cn(
                  "w-full rounded-md border border-border px-3 py-2 text-left text-sm transition-colors",
                  conversation.id === currentConversationId
                    ? "bg-muted text-foreground"
                    : "bg-background text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <span className="block truncate font-medium">{conversation.title || "Untitled conversation"}</span>
                {conversation.created_at && (
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {new Date(conversation.created_at).toLocaleString()}
                  </span>
                )}
              </button>
            ))}
            {!conversations.length && (
              <p className="rounded-md border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">
                No conversations yet.
              </p>
            )}
          </div>
        </div>
      </aside>
      {isOpen && <button type="button" aria-label="Close sidebar" className="fixed inset-0 z-30 bg-black/25 lg:hidden" onClick={onToggle} />}
    </>
  );
}
