"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import { useAccount } from "wagmi";
import { AlertCircle, Bot, Menu, Settings2, Wallet, Zap } from "lucide-react";

import { ChainIndicator } from "@/components/chat/chain-indicator";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { Button } from "@/components/ui/button";
import { useChatStore, teardownConversationStream } from "@/store/chat-store";
import { useAgentStore } from "@/store/agent-store";

const QUICK_PROMPTS = [
  "What's the latest block on Ethereum?",
  "Check gas price on Polygon",
  "Get SOL balance overview",
  "Compare latency across EVM chains",
];

export function ChatContainer() {
  const searchParams = useSearchParams();
  const requestedAgentId = searchParams.get("agent");
  const { address, isConnected } = useAccount();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesRef = useRef<HTMLDivElement | null>(null);

  const {
    agents,
    selectedAgentId,
    selectedAgent,
    conversations,
    selectAgent,
  } = useAgentStore();

  const {
    currentConversationId,
    messages,
    isLoading,
    isBootstrapping,
    activeChains,
    streamingHint,
    error,
    initialize,
    sendMessage,
    loadConversation,
    createNewChat,
    deleteConversation,
    refreshWorkspace,
  } = useChatStore();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  // Tear down the conversation SSE stream when the chat page unmounts so we
  // don't leak an open EventSource if the user navigates away mid-confirmation.
  useEffect(() => () => teardownConversationStream(), []);

  useEffect(() => {
    if (
      requestedAgentId &&
      selectedAgentId !== requestedAgentId &&
      agents.some((agent) => agent.id === requestedAgentId)
    ) {
      void selectAgent(requestedAgentId);
    }
  }, [agents, requestedAgentId, selectAgent, selectedAgentId]);

  // Scroll only the message pane — instant scroll avoids composer jank in Chrome.
  useEffect(() => {
    const pane = messagesRef.current;
    if (!pane) return;
    pane.scrollTop = pane.scrollHeight;
  }, [messages, isLoading]);

  const agent = selectedAgent ?? agents.find((item) => item.id === selectedAgentId);

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
        onDeleteConversation={(id) => void deleteConversation(id)}
        onRefresh={() => void refreshWorkspace()}
      />

      <div className="grid h-full min-h-0 min-w-0 flex-1 grid-rows-[auto_1fr_auto] bg-background">
        <header className="z-10 flex h-14 shrink-0 items-center justify-between gap-2 border-b border-border/30 bg-card/15 px-3 backdrop-blur-md sm:h-16 sm:px-6">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
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
                  {agent ? agent.name : "Workspace"}
                </h1>
                {agent && (
                  <span className="hidden items-center gap-1.5 rounded-full bg-green-500/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-green-500 sm:inline-flex">
                    <span className="h-1 w-1 animate-pulse-soft rounded-full bg-green-500" />
                    Online
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground/75 truncate mt-0.5">
                {agent
                  ? `${agent.chains.length} blockchain networks enabled`
                  : "Pocket Network RPC natural language interface"}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {isConnected && address && (
              <span
                className="hidden items-center gap-1 rounded-md border border-border/50 bg-muted/20 px-2 py-1 font-mono text-[10px] text-muted-foreground sm:inline-flex"
                title="Connected wallet passed to agent tools"
              >
                <Wallet size={11} className="text-primary/70" />
                {address.slice(0, 6)}…{address.slice(-4)}
              </span>
            )}
            {agent && (
              <Link
                href="/agents"
                className="hidden items-center gap-1 rounded-md border border-border/50 px-2 py-1 text-[10px] font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
              >
                <Settings2 size={12} />
                Manage
              </Link>
            )}
            <div className="hidden max-w-[42%] shrink-0 sm:block sm:max-w-none">
              <ChainIndicator chains={activeChains} isLoading={isLoading} compact />
            </div>
          </div>
        </header>

        <div
          ref={messagesRef}
          className="min-h-0 overflow-y-auto overscroll-contain"
        >
          <div
            className={
              !messages.length && !isLoading
                ? "mx-auto flex min-h-full w-full max-w-3xl flex-col px-3 py-6 sm:px-6 sm:py-8"
                : "mx-auto w-full max-w-3xl space-y-6 px-3 py-6 sm:px-6 sm:py-8"
            }
          >
            {error && (
              <div className="sticky top-0 z-10 flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-3 text-xs font-mono text-red-400 shadow-sm backdrop-blur-md animate-slide-up sm:px-4">
                <AlertCircle className="mt-0.5 shrink-0" size={14} />
                <span className="break-words">{error}</span>
              </div>
            )}

            {!messages.length && !isLoading && (
              <div className="flex min-h-full flex-col items-center justify-center gap-8 py-16 animate-fade-in">
                  <div className="flex flex-col items-center gap-4 text-center">
                    <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-primary/20 bg-primary/5 shadow-md shadow-primary/5">
                      {agent ? (
                        <Image
                          src="/logo.png"
                          alt="PocketAgent"
                          width={32}
                          height={32}
                          className="rounded-full object-cover"
                        />
                      ) : (
                        <Bot size={20} className="text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      <h2 className="text-md font-bold tracking-tight text-foreground">
                        {agent ? `${agent.name} is ready` : "Select an agent to begin"}
                      </h2>
                      <p className="mt-1.5 text-xs text-muted-foreground/60 max-w-xs mx-auto leading-relaxed">
                        {agent
                          ? `Ask anything about ${agent.chains.length} enabled blockchain networks through Pocket RPC.`
                          : "Create an agent on the Agents page to start a conversation."}
                      </p>
                    </div>
                  </div>

                  {agent && (
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

                  {!agent && (
                    <Link href="/agents" className="pa-button text-sm">
                      Go to Agents
                    </Link>
                  )}
                </div>
              )}

            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                streamingHint={
                  isLoading && message.role === "assistant" && !message.content
                    ? streamingHint ?? "thinking"
                    : null
                }
              />
            ))}
          </div>
        </div>

        <footer className="safe-bottom z-20 shrink-0 border-t border-border/30 bg-background/95 backdrop-blur-md px-3 py-3 sm:px-6 sm:py-4">
            <div className="mx-auto w-full max-w-3xl">
              <ChatInput
                disabled={isLoading || !selectedAgentId || isBootstrapping}
                agentId={selectedAgentId}
                onSend={(message) => void sendMessage(message)}
              />
              <div className="mt-1 flex min-h-5 items-center justify-between gap-3 px-2 text-[10px] text-muted-foreground/45">
                <span className="truncate font-mono uppercase tracking-wider">
                  {agent
                    ? `${agent.chains.length} chains active · ${agent.name}`
                    : "No active agent"}
                </span>
                {agent && (
                  <span className="flex items-center gap-1.5 font-mono">
                    <span className="h-1 w-1 rounded-full bg-primary animate-pulse-soft" />
                    pocket-rpc
                  </span>
                )}
              </div>
            </div>
        </footer>
      </div>
    </section>
  );
}