import { useEffect, useRef, useState } from "react";
import FloatingWidget from "./components/chatbot/FloatingWidget";
import DemoSite from "./DemoSite";
import { useChat } from "./useChat";

export default function App() {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const chat = useChat();

  // Count bot messages that arrive while the widget is closed (drives the
  // pulse + badge on the FAB). Clears as soon as the widget is opened.
  const seenCount = useRef(0);
  useEffect(() => {
    if (open) {
      seenCount.current = chat.messages.length;
      setUnread(0);
      return;
    }
    const fresh = chat.messages.slice(seenCount.current);
    const botCount = fresh.filter((m) => m.role === "bot").length;
    if (botCount > 0) setUnread((n) => n + botCount);
    seenCount.current = chat.messages.length;
  }, [chat.messages, open]);

  return (
    <div className="pharma-widget">
      {/* Mock storefront backdrop — in production the widget embeds on the
          real 1healthpharmacy.in site instead of this. */}
      <DemoSite />

      <FloatingWidget
        open={open}
        unread={unread}
        onToggle={() => setOpen((v) => !v)}
        onClose={() => setOpen(false)}
        messages={chat.messages}
        typing={chat.typing}
        connected={chat.connected}
        onSendText={chat.sendText}
        onSendButton={chat.sendButton}
        onUpload={chat.uploadImage}
      />
    </div>
  );
}
