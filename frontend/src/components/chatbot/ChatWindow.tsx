import type { CSSProperties } from "react";
import { motion } from "framer-motion";
import MessageList from "./MessageList";
import InputBar from "./InputBar";
import type { ChatMessage } from "../../useChat";

interface Props {
  messages: ChatMessage[];
  typing: boolean;
  connected: boolean;
  onSendText: (text: string) => void;
  onSendButton: (value: string, label?: string) => void;
  onUpload: (file: File) => void;
  onClose: () => void;
  /** Absolute placement + transform-origin, computed by the container. */
  style?: CSSProperties;
}

export default function ChatWindow({
  messages,
  typing,
  connected,
  onSendText,
  onSendButton,
  onUpload,
  onClose,
  style,
}: Props) {
  return (
    <motion.div
      role="dialog"
      aria-label="1Health Pharmacy chat"
      style={style}
      className="fixed z-[9998] flex flex-col overflow-hidden rounded-2xl bg-white shadow-chat ring-1 ring-black/5"
      initial={{ opacity: 0, scale: 0.82 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.85 }}
      transition={{ type: "spring", stiffness: 380, damping: 30, mass: 0.8 }}
    >
      {/* Modern header — subtle gradient, avatar, live status. */}
      <header className="flex items-center gap-3 bg-gradient-to-r from-brand-600 to-brand-500 px-4 py-3.5 text-white">
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/20 text-xl shadow-inner">
          💊
          <span
            className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-brand-600 ${
              connected ? "bg-green-400" : "bg-gray-300"
            }`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-semibold leading-tight tracking-tight">
            1Health Pharmacy
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs font-medium text-brand-50/90">
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                connected ? "bg-green-300" : "bg-gray-300"
              }`}
            />
            {connected ? "Online · replies instantly" : "Connecting…"}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Minimize chat"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/90 transition-colors hover:bg-white/15 active:bg-white/25"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M5 12h14" />
          </svg>
        </button>
      </header>

      <MessageList
        messages={messages}
        typing={typing}
        onQuickReply={onSendButton}
        onSelectStore={(index) => onSendButton(String(index), `Store ${index}`)}
        onPaid={() => onSendButton("PAID", "PAID")}
      />

      <InputBar connected={connected} onSendText={onSendText} onUpload={onUpload} />
    </motion.div>
  );
}
