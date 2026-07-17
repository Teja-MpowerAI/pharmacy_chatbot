import { useRef, useState } from "react";

interface Props {
  connected: boolean;
  onSendText: (text: string) => void;
  onUpload: (file: File) => void;
}

export default function InputBar({ connected, onSendText, onUpload }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    if (!text.trim()) return;
    onSendText(text);
    setText("");
  };

  return (
    <div className="flex items-center gap-2 border-t border-gray-100 bg-white px-3 py-2.5">
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload(f);
          e.target.value = "";
        }}
      />
      <button
        onClick={() => fileRef.current?.click()}
        aria-label="Upload prescription"
        title="Upload prescription"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-brand-600 transition-colors hover:bg-brand-50"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21.44 11.05l-9.19 9.19a5 5 0 0 1-7.07-7.07l9.19-9.19a3.5 3.5 0 0 1 4.95 4.95L10.12 18.1a1.5 1.5 0 0 1-2.12-2.12l8.49-8.49" />
        </svg>
      </button>

      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder="Type a medicine or message…"
        className="flex-1 rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-800 outline-none transition-colors focus:border-brand-400 focus:bg-white"
      />

      <button
        onClick={submit}
        disabled={!connected || !text.trim()}
        aria-label="Send"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white transition-colors hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
        </svg>
      </button>
    </div>
  );
}
