import { useCallback, useEffect, useRef, useState } from "react";

// API base — override with VITE_API_BASE at build time for production.
const API_BASE =
  (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export interface QuickReply {
  label: string;
  value: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "bot";
  type: string; // message | store_list | prescription_details | payment
  content: string;
  image?: string; // preview URL for an uploaded image (user messages)
  quick_replies?: QuickReply[];
  cards?: any[];
  prescription?: any;
  payment_link?: string;
}

function getSessionId(): string {
  const KEY = "pharma_session_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id =
      "web-" +
      Date.now().toString(36) +
      "-" +
      Math.random().toString(36).slice(2, 8);
    localStorage.setItem(KEY, id);
  }
  return id;
}

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [typing, setTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionId = useRef<string>(getSessionId());
  const greeted = useRef(false);

  const pushBot = useCallback((payload: any) => {
    setMessages((prev) => [
      ...prev,
      {
        id: uid(),
        role: "bot",
        type: payload.type || "message",
        content: payload.content || "",
        quick_replies: payload.quick_replies || [],
        cards: payload.cards || [],
        prescription: payload.prescription,
        payment_link: payload.payment_link,
      },
    ]);
  }, []);

  const pushUser = useCallback((content: string, image?: string) => {
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", type: "message", content, image },
    ]);
  }, []);

  // Open the socket once on mount.
  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/api/chat/ws/${sessionId.current}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      if (!greeted.current) {
        greeted.current = true;
        ws.send(JSON.stringify({ type: "text", content: "hi" }));
      }
    };
    ws.onclose = () => setConnected(false);
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.type === "typing") {
        setTyping(Boolean(data.content));
        return;
      }
      pushBot(data);
    };

    return () => ws.close();
  }, [pushBot]);

  const send = useCallback((payload: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
  }, []);

  const sendText = useCallback(
    (text: string) => {
      if (!text.trim()) return;
      pushUser(text);
      send({ type: "text", content: text });
    },
    [pushUser, send]
  );

  const sendButton = useCallback(
    (value: string, label?: string) => {
      pushUser(label || value);
      send({ type: "button_click", content: value });
    },
    [pushUser, send]
  );

  const uploadImage = useCallback(
    async (file: File) => {
      // Show the picked image immediately (optimistic preview) while OCR runs.
      const preview = URL.createObjectURL(file);
      pushUser("", preview);
      setTyping(true);
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(
          `${API_BASE}/api/chat/upload-image?session_id=${sessionId.current}`,
          { method: "POST", body: form }
        );
        const data = await res.json();
        send({ type: "prescription", content: data.image_url });
      } catch (e) {
        setTyping(false);
        pushBot({
          type: "message",
          content:
            "Sorry, I couldn't upload that image. Please try again with a clear photo.",
        });
      }
    },
    [pushUser, pushBot, send]
  );

  return {
    messages,
    typing,
    connected,
    sendText,
    sendButton,
    uploadImage,
  };
}
