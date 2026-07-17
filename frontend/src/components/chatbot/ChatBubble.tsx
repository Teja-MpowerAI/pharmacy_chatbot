interface Props {
  open: boolean;
  onClick: () => void;
}

// Floating launcher. Offset to the LEFT of the site's existing WhatsApp float
// (bottom:24px right:90px) so the two don't overlap.
export default function ChatBubble({ open, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      aria-label={open ? "Close chat" : "Open chat"}
      style={{ bottom: "24px", right: "90px" }}
      className="fixed z-[9999] flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white shadow-bubble transition-transform hover:scale-105 hover:bg-brand-600 active:scale-95"
    >
      {open ? (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      ) : (
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      )}
    </button>
  );
}
