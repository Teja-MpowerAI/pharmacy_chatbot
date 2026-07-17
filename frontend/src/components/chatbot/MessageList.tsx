import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import QuickReplies from "./QuickReplies";
import StoreCard from "./StoreCard";
import PrescriptionView from "./PrescriptionView";
import PaymentButton from "./PaymentButton";
import type { ChatMessage } from "../../useChat";

interface Props {
  messages: ChatMessage[];
  typing: boolean;
  onQuickReply: (value: string, label?: string) => void;
  onSelectStore: (index: number) => void;
  onPaid: () => void;
}

export default function MessageList({
  messages,
  typing,
  onQuickReply,
  onSelectStore,
  onPaid,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  const lastIndex = messages.length - 1;

  return (
    <div className="pharma-scroll flex-1 space-y-3 overflow-y-auto bg-brand-50/40 px-3 py-4">
      {messages.map((m, i) => {
        const isLast = i === lastIndex;
        return (
          <div key={m.id} className="space-y-2">
            <MessageBubble role={m.role} content={m.content} image={m.image} />

            {/* Store cards */}
            {m.role === "bot" && m.type === "store_list" && m.cards?.length ? (
              <div className="space-y-2">
                {m.cards.map((c: any) => (
                  <StoreCard
                    key={c.index ?? c.name}
                    store={c}
                    selectable={isLast}
                    onSelect={() => onSelectStore(c.index)}
                  />
                ))}
              </div>
            ) : null}

            {/* Prescription details */}
            {m.role === "bot" && m.prescription ? (
              <PrescriptionView data={m.prescription} />
            ) : null}

            {/* Online payment link */}
            {m.role === "bot" && m.type === "payment" && m.payment_link ? (
              <PaymentButton link={m.payment_link} onPaid={onPaid} />
            ) : null}

            {/* Quick replies — only interactive for the latest bot message */}
            {m.role === "bot" && isLast && m.quick_replies?.length ? (
              <QuickReplies replies={m.quick_replies} onClick={onQuickReply} />
            ) : null}
          </div>
        );
      })}

      {typing && (
        <div className="flex w-16 items-center gap-1 rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm">
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-blink" style={{ animationDelay: "0ms" }} />
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-blink" style={{ animationDelay: "200ms" }} />
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-blink" style={{ animationDelay: "400ms" }} />
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}
