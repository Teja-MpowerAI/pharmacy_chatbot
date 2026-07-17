import type { QuickReply } from "../../useChat";

interface Props {
  replies: QuickReply[];
  onClick: (value: string, label?: string) => void;
}

export default function QuickReplies({ replies, onClick }: Props) {
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {replies.map((r) => (
        <button
          key={r.value + r.label}
          onClick={() => onClick(r.value, r.label)}
          className="rounded-full border border-brand-200 bg-white px-3.5 py-1.5 text-xs font-medium text-brand-700 shadow-sm transition-colors hover:bg-brand-50 active:scale-95"
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
