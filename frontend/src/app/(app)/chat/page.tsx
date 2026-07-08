import { Suspense } from "react";

import { ChatContainer } from "@/components/chat/chat-container";

export default function ChatPage() {
  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
      <Suspense fallback={null}>
        <ChatContainer />
      </Suspense>
    </div>
  );
}
