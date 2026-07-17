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
}

export default function ChatWindow({
  messages,
  typing,
  connected,
  onSendText,
  onSendButton,
  onUpload,
  onClose,
}: Props) {
  return (
    <div className="fixed bottom-24 right-6 z-[9999] flex h-[600px] w-[380px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl bg-white shadow-chat animate-slide-up">
      {/* Header */}
      <header className="flex items-center gap-3 bg-brand-600 px-4 py-3 text-white">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-lg">
          💊
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold leading-tight">
            1Health Pharmacy
          </div>
          <div className="flex items-center gap-1.5 text-xs text-brand-100">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                connected ? "bg-green-300" : "bg-gray-300"
              }`}
            />
            {connected ? "Online now" : "Connecting…"}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Minimize chat"
          className="rounded-full p-1.5 text-white/90 transition-colors hover:bg-white/15"
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

      <InputBar
        connected={connected}
        onSendText={onSendText}
        onUpload={onUpload}
      />
    </div>
  );
}
