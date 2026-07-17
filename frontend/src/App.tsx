import { useState } from "react";
import ChatBubble from "./components/chatbot/ChatBubble";
import ChatWindow from "./components/chatbot/ChatWindow";
import DemoSite from "./DemoSite";
import { useChat } from "./useChat";

export default function App() {
  const [open, setOpen] = useState(false);
  const chat = useChat();

  return (
    <div className="pharma-widget">
      {/* Mock storefront backdrop — in production the widget embeds on the
          real 1healthpharmacy.in site instead of this. */}
      <DemoSite />

      {open && (
        <ChatWindow
          messages={chat.messages}
          typing={chat.typing}
          connected={chat.connected}
          onSendText={chat.sendText}
          onSendButton={chat.sendButton}
          onUpload={chat.uploadImage}
          onClose={() => setOpen(false)}
        />
      )}
      <ChatBubble open={open} onClick={() => setOpen((v) => !v)} />
    </div>
  );
}
