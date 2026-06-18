"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Bot } from "lucide-react";

import { ChainIndicator } from "@/components/chat/chain-indicator";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chat-store";

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
    <section className="flex h-[calc(100vh-7rem)] min-h-[42rem] flex-col lg:h-[calc(100vh-4rem)] lg:flex-row">
      <ChatSidebar
        agents={agents}
        conversations={conversations}
        selectedAgentId={selectedAgentId}
        currentConversationId={currentConversationId}
        isOpen={sidebarOpen}
        isBootstrapping={isBootstrapping}
        onToggle={() => setSidebarOpen((value) => !value)}
        onNewChat={() => {
          createNewChat();
          setSidebarOpen(false);
        }}
        onSelectAgent={(id) => void selectAgent(id)}
        onLoadConversation={(id) => {
          void loadConversation(id);
          setSidebarOpen(false);
        }}
        onCreateAgent={() => void createDefaultAgent()}
        onRefresh={() => void initialize()}
      />

      <div className="flex min-h-0 flex-1 flex-col lg:ml-4">
        <header className="flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Natural language interface for Pocket Network RPC across chains.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ChainIndicator chains={activeChains} isLoading={isLoading} />
          </div>
        </header>

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
            <AlertCircle className="mt-0.5 shrink-0" size={16} />
            <span className="break-words">{error}</span>
          </div>
        )}

        <Card className="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden">
          <ScrollArea className="flex-1 px-4 py-5">
            <div className="mx-auto max-w-4xl space-y-5">
              {!messages.length && !isLoading && (
                <div className="flex min-h-[20rem] items-center justify-center">
                  <div className="max-w-lg text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground">
                      <Bot size={22} />
                    </div>
                    <h2 className="mt-4 text-lg font-semibold">
                      {selectedAgent ? `Ask ${selectedAgent.name} about a chain.` : "Select or create an agent."}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      Messages are sent to the backend chat API and persisted by conversation.
                    </p>
                    {selectedAgent && (
                      <div className="mt-4 flex flex-wrap justify-center gap-2">
                        {selectedAgent.chains.slice(0, 6).map((chain) => (
                          <Button
                            key={chain}
                            variant="secondary"
                            size="sm"
                            onClick={() => void sendMessage(`What's the gas price on ${chain}?`)}
                            disabled={isLoading}
                          >
                            {chain}
                          </Button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && <ChatMessage loading />}
              <div ref={bottomRef} />
            </div>
          </ScrollArea>

          <div className="border-t border-border bg-card p-3">
            <div className="mx-auto max-w-4xl space-y-2">
              <ChatInput disabled={isLoading || !selectedAgentId || isBootstrapping} onSend={(message) => void sendMessage(message)} />
              <div className="flex min-h-5 items-center justify-between gap-3 text-xs text-muted-foreground">
                <span className="truncate">
                  {selectedAgent ? `${selectedAgent.chains.length} chains enabled` : "No active agent"}
                </span>
                <ChainIndicator chains={activeChains} isLoading={isLoading} compact />
              </div>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}
