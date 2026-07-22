import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

interface Props {
  open: boolean;
  /** Number of unread bot messages while the widget is closed. */
  unread?: number;
  onClick: () => void;
}

function ChatIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

// Professional floating action button (FAB). Purely presentational — drag,
// positioning and persistence live in the FloatingWidget container / hook.
export default function ChatBubble({ open, unread = 0, onClick }: Props) {
  const reduce = useReducedMotion();
  const showPulse = !open && unread > 0 && !reduce;

  return (
    <div className="relative h-14 w-14 select-none">
      {/* Radiating pulse rings — only while there is an unread message. */}
      <AnimatePresence>
        {showPulse &&
          [0, 0.6].map((delay) => (
            <motion.span
              key={delay}
              className="pointer-events-none absolute inset-0 rounded-full bg-brand-500"
              initial={{ scale: 1, opacity: 0.5 }}
              animate={{ scale: 1.9, opacity: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 1.8, ease: "easeOut", repeat: Infinity, delay }}
            />
          ))}
      </AnimatePresence>

      <motion.button
        type="button"
        onClick={onClick}
        aria-label={open ? "Close chat" : "Open chat"}
        className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-brand-500 text-white shadow-bubble outline-none ring-brand-200 focus-visible:ring-4"
        whileHover={{ scale: 1.08, backgroundColor: "#008A45" }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 500, damping: 28 }}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={open ? "close" : "chat"}
            className="flex items-center justify-center"
            initial={{ rotate: -75, opacity: 0, scale: 0.5 }}
            animate={{ rotate: 0, opacity: 1, scale: 1 }}
            exit={{ rotate: 75, opacity: 0, scale: 0.5 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            {open ? <CloseIcon /> : <ChatIcon />}
          </motion.span>
        </AnimatePresence>
      </motion.button>

      {/* Unread count badge. */}
      <AnimatePresence>
        {!open && unread > 0 && (
          <motion.span
            key="badge"
            className="absolute -right-1 -top-1 z-20 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full border-2 border-white bg-red-500 px-1 text-[11px] font-bold leading-none text-white"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 600, damping: 20 }}
          >
            {unread > 9 ? "9+" : unread}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}
