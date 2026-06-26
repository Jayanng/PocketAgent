"use client";

import { Bot, Menu, MessageSquare, Plus, RefreshCw, X } from "lucide-react";

import { Button } from "@/components/ui/button";
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
      {/* Mobile overlay */}
      {isOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={onToggle}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-[min(100vw,20rem)] border-r border-border/30 bg-card/35 shadow-2xl backdrop-blur-xl transition-transform duration-350 ease-out safe-top safe-bottom",
          "flex flex-col h-full",
          "lg:static lg:z-auto lg:translate-x-0 lg:shadow-none",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between gap-2 border-b border-border/30 px-5 py-4">
          <div className="flex items-center gap-2">
            <Bot size={15} className="text-primary shrink-0 animate-pulse-soft" />
            <span className="text-[13px] font-semibold tracking-tight text-foreground">Agent Workspace</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              variant="ghost"
              size="icon"
              onClick={onRefresh}
              title="Refresh workspace"
              className="h-7 w-7 rounded-lg text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              <RefreshCw size={13} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-7 w-7 rounded-lg"
              onClick={onToggle}
              title="Close sidebar"
            >
              <X size={13} />
            </Button>
          </div>
        </div>

        {/* Agent Selection & Configuration */}
        <div className="px-5 py-4 space-y-4 border-b border-border/30 bg-card/10">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/60 mb-1.5">Active Agent</p>
            {agents.length > 0 ? (
              <div className="relative">
                <select
                  value={selectedAgentId ?? ""}
                  disabled={!agents.length || isBootstrapping}
                  onChange={(e) => onSelectAgent(e.target.value)}
                  className="h-9 w-full rounded-lg border border-border/60 bg-background/50 px-3 text-xs font-semibold outline-none transition-all focus:border-primary/50 disabled:cursor-not-allowed disabled:opacity-50 text-foreground appearance-none cursor-pointer"
                >
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground/60">
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border/50 bg-muted/10 p-3 space-y-2">
                <p className="text-xs text-muted-foreground/80">No agents configured yet.</p>
                <Button
                  size="sm"
                  onClick={onCreateAgent}
                  disabled={isBootstrapping}
                  className="w-full h-8 text-xs font-semibold"
                >
                  <Bot size={13} />
                  Create First Agent
                </Button>
              </div>
            )}
          </div>

          {/* Active agent chains list */}
          {selectedAgent && (
            <div className="rounded-lg bg-muted/10 border border-border/20 px-3.5 py-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50">Chains</span>
                <span className="text-[10px] font-mono text-primary font-semibold">{selectedAgent.chains.length} active</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {selectedAgent.chains.slice(0, 5).map((chain) => (
                  <span key={chain} className="rounded border border-border/40 bg-background/30 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground uppercase">
                    {chain.slice(0, 4)}
                  </span>
                ))}
                {selectedAgent.chains.length > 5 && (
                  <span className="rounded border border-border/40 bg-background/30 px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground/55">
                    +{selectedAgent.chains.length - 5}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* New chat button */}
          <Button
            onClick={onNewChat}
            disabled={!selectedAgentId || isBootstrapping}
            className="w-full h-9 text-xs font-bold bg-primary hover:bg-primary/95 text-white rounded-lg shadow-sm hover:scale-[1.01] active:scale-[0.99] transition-all"
          >
            <Plus size={14} />
            New Conversation
          </Button>
        </div>

        {/* Conversation History List */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1.5">
          <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/50 px-2 mb-2">
            History · {conversations.length}
          </p>

          {conversations.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/30 px-3 py-6 text-center">
              <MessageSquare size={16} className="mx-auto text-muted-foreground/30 mb-2" />
              <p className="text-xs text-muted-foreground/50">No conversations yet.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conversation) => {
                const isActive = conversation.id === currentConversationId;
                return (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={() => onLoadConversation(conversation.id)}
                    className={cn(
                      "w-full rounded-lg px-3 py-2 text-left transition-all duration-200 border cursor-pointer",
                      isActive
                        ? "border-primary/20 bg-primary/5 text-foreground shadow-sm"
                        : "border-transparent bg-transparent text-muted-foreground hover:bg-muted/20 hover:text-foreground"
                    )}
                  >
                    <div className="flex items-start gap-2.5">
                      <MessageSquare
                        size={12}
                        className={cn("mt-0.5 shrink-0", isActive ? "text-primary" : "text-muted-foreground/45")}
                      />
                      <div className="min-w-0 flex-1">
                        <span className={cn("block truncate text-xs font-medium leading-normal", isActive ? "text-foreground font-semibold" : "text-muted-foreground")}>
                          {conversation.title || "Untitled conversation"}
                        </span>
                        {conversation.created_at && (
                          <span className="mt-0.5 block font-mono text-[9px] text-muted-foreground/40">
                            {new Date(conversation.created_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </aside>

      {/* Mobile toggle button (when closed) */}
      <div className="mb-3 flex items-center justify-between lg:hidden px-4 py-2 border-b border-border/20 bg-card/20">
        <Button variant="secondary" size="sm" onClick={onToggle} className="text-xs h-8">
          <Menu size={14} />
          Conversations
        </Button>
        <Button variant="ghost" size="icon" onClick={onRefresh} title="Refresh" className="h-8 w-8">
          <RefreshCw size={14} />
        </Button>
      </div>
    </>
  );
}
