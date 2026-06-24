"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Bot, Menu, Sparkles, Zap } from "lucide-react";

import { ChainIndicator } from "@/components/chat/chain-indicator";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chat-store";

const QUICK_PROMPTS = [
  "What's the latest block on Ethereum?",
  "Check gas price on Polygon",
  "Get SOL balance overview",
  "Compare latency across EVM chains",
];

export function ChatContainer() {
  const searchParams = useSearchParams();
  const requestedAgentId = searchParams.get("agent");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const {
    agents,
    selectedAgentId,
    conversations,
    currentConversationId,
    messages,
    isLoading,
    isBootstrapping,
    activeChains,
    error,
    initialize,
    selectAgent,
    sendMessage,
    loadConversation,
    createNewChat,
    createDefaultAgent,
  } = useChatStore();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  useEffect(() => {
    if (
      requestedAgentId &&
      selectedAgentId !== requestedAgentId &&
      agents.some((agent) => agent.id === requestedAgentId)
    ) {
      void selectAgent(requestedAgentId);
    }
  }, [agents, requestedAgentId, selectAgent, selectedAgentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);

  return (
    <section className="flex h-full w-full flex-col lg:flex-row animate-fade-in min-h-0 overflow-hidden bg-background">
      <ChatSidebar
        agents={agents}
        conversations={conversations}
        selectedAgentId={selectedAgentId}
        currentConversationId={currentConversationId}
        isOpen={sidebarOpen}
        isBootstrapping={isBootstrapping}
        onToggle={() => setSidebarOpen((v) => !v)}
        onNewChat={() => { createNewChat(); setSidebarOpen(false); }}
        onSelectAgent={(id) => void selectAgent(id)}
        onLoadConversation={(id) => { void loadConversation(id); setSidebarOpen(false); }}
        onCreateAgent={() => void createDefaultAgent()}
        onRefresh={() => void initialize()}
      />

      <div className="flex flex-col flex-1 h-full min-h-0 min-w-0 bg-background">
        {/* Chat Pane Top Header */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/30 bg-card/15 px-6 backdrop-blur-md z-10">
          <div className="flex items-center gap-3 min-w-0">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-8 w-8 shrink-0 rounded-lg text-muted-foreground hover:bg-muted/40"
              onClick={() => setSidebarOpen((v) => !v)}
              aria-label="Toggle sidebar"
            >
              <Menu size={16} />
            </Button>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-tight text-foreground truncate">
                  {selectedAgent ? `${selectedAgent.name}` : "Workspace"}
                </h1>
                {selectedAgent && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-green-500/10 px-2 py-0.5 text-[9px] font-semibold text-green-500 uppercase tracking-wider">
                    <span className="h-1 w-1 rounded-full bg-green-500 animate-pulse-soft" />
                    Online
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground/75 truncate mt-0.5">
                {selectedAgent
                  ? `${selectedAgent.chains.length} blockchain networks enabled`
                  : "Pocket Network RPC natural language interface"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ChainIndicator chains={activeChains} isLoading={isLoading} />
          </div>
        </header>

        {error && (
          <div className="mx-6 mt-3 flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-xs text-red-400 font-mono shadow-sm animate-slide-up z-10">
            <AlertCircle className="mt-0.5 shrink-0" size={14} />
            <span className="break-words">{error}</span>
          </div>
        )}

        {/* Scrollable Chat Area */}
        <div className="flex-1 min-h-0 relative overflow-hidden">
          <ScrollArea className="h-full w-full">
            <div className="mx-auto max-w-3xl px-6 py-8 space-y-6 w-full pb-36">
              
              {/* Empty state / Welcome screen */}
              {!messages.length && !isLoading && (
                <div className="flex min-h-[50dvh] flex-col items-center justify-center gap-8 py-8 animate-fade-in">
                  <div className="flex flex-col items-center gap-4 text-center">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/5 shadow-md shadow-primary/5">
                      {selectedAgent ? (
                        <Sparkles size={20} className="text-primary animate-pulse-soft" />
                      ) : (
                        <Bot size={20} className="text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      <h2 className="text-md font-bold tracking-tight text-foreground">
                        {selectedAgent
                          ? `${selectedAgent.name} is ready`
                          : "Select an agent to begin"}
                      </h2>
                      <p className="mt-1.5 text-xs text-muted-foreground/60 max-w-xs mx-auto leading-relaxed">
                        {selectedAgent
                          ? `Ask anything about ${selectedAgent.chains.length} enabled blockchain networks through Pocket RPC.`
                          : "Choose an agent from the workspace sidebar to start a conversation."}
                      </p>
                    </div>
                  </div>

                  {selectedAgent && (
                    <div className="flex flex-col items-center gap-3 w-full max-w-lg">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/40 font-bold">Quick suggestions</span>
                      <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 w-full">
                        {QUICK_PROMPTS.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            disabled={isLoading}
                            onClick={() => void sendMessage(prompt)}
                            className="group flex items-center gap-3 rounded-xl border border-border/50 bg-card/25 p-3.5 text-left text-xs text-muted-foreground transition-all duration-200 hover:border-primary/45 hover:bg-primary/5 hover:text-foreground disabled:pointer-events-none disabled:opacity-50 shadow-sm cursor-pointer"
                          >
                            <Zap size={12} className="text-primary opacity-30 group-hover:opacity-100 transition-opacity shrink-0" />
                            <span className="truncate">{prompt}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedAgent && selectedAgent.chains.length > 0 && (
                    <div className="flex flex-col items-center gap-2">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground/40 font-bold">Supported networks</span>
                      <div className="flex flex-wrap justify-center gap-1.5 max-w-sm">
                        {selectedAgent.chains.slice(0, 8).map((chain) => (
                          <span
                            key={chain}
                            className="rounded-md border border-border/40 bg-muted/20 px-2 py-0.5 font-mono text-[9px] text-muted-foreground uppercase"
                          >
                            {chain}
                          </span>
                        ))}
                        {selectedAgent.chains.length > 8 && (
                          <span className="rounded-md border border-border/40 bg-muted/20 px-2 py-0.5 font-mono text-[9px] text-muted-foreground/60">
                            +{selectedAgent.chains.length - 8} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Messages list */}
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && <ChatMessage loading />}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          {/* Floating Input Capsule */}
          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background/95 to-transparent pointer-events-none z-10 flex flex-col items-center">
            <div className="w-full max-w-3xl pointer-events-auto">
              <ChatInput
                disabled={isLoading || !selectedAgentId || isBootstrapping}
                onSend={(message) => void sendMessage(message)}
              />
              <div className="flex min-h-5 items-center justify-between gap-3 text-[10px] text-muted-foreground/45 px-2 mt-1">
                <span className="truncate font-mono uppercase tracking-wider">
                  {selectedAgent
                    ? `${selectedAgent.chains.length} chains active · ${selectedAgent.name}`
                    : "No active agent selector"}
                </span>
                {selectedAgent && (
                  <span className="flex items-center gap-1.5 font-mono">
                    <span className="h-1 w-1 rounded-full bg-primary animate-pulse-soft" />
                    pocket-rpc
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
