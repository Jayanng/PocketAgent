import { Suspense } from "react";

import { ChatContainer } from "@/components/chat/chat-container";

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatContainer />
    </Suspense>
  );
}
