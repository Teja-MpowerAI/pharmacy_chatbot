import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ChatBubble from "./ChatBubble";
import ChatWindow from "./ChatWindow";
import { useWidgetPosition, FAB_SIZE, type Side } from "../../useWidgetPosition";
import type { ChatMessage } from "../../useChat";

interface Props {
  open: boolean;
  unread: number;
  onToggle: () => void;
  onClose: () => void;
  messages: ChatMessage[];
  typing: boolean;
  connected: boolean;
  onSendText: (text: string) => void;
  onSendButton: (value: string, label?: string) => void;
  onUpload: (file: File) => void;
}

const GAP = 14; // space between the FAB and the chat window
const TOP_SAFE = 88; // keep the window clear of the navbar (matches the hook)
const MARGIN = 16;
const DESKTOP_W = 380;
const DESKTOP_H = 600;

type Placement = { style: CSSProperties };

// Compute where the chat window should sit relative to the FAB's current
// position, clamped so it always stays fully inside the viewport.
function computePlacement(fabLeft: number, fabTop: number, side: Side): Placement {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Mobile: near-fullscreen sheet below the navbar.
  if (vw < 480) {
    return {
      style: {
        left: MARGIN / 2,
        top: TOP_SAFE,
        width: vw - MARGIN,
        height: vh - TOP_SAFE - MARGIN / 2,
        transformOrigin: `${side === "right" ? "right" : "left"} bottom`,
      },
    };
  }

  const width = Math.min(DESKTOP_W, vw - 2 * MARGIN);

  // Decide vertical direction by whichever side of the FAB has more room.
  const spaceAbove = fabTop - TOP_SAFE - GAP;
  const spaceBelow = vh - (fabTop + FAB_SIZE) - MARGIN - GAP;
  const openUp = spaceAbove >= spaceBelow;

  const available = Math.max(openUp ? spaceAbove : spaceBelow, 240);
  const height = Math.min(DESKTOP_H, available);

  let top: number;
  if (openUp) {
    top = Math.max(TOP_SAFE, fabTop - GAP - height);
  } else {
    top = fabTop + FAB_SIZE + GAP;
  }

  // Align the window's edge with the FAB's edge on its snapped side.
  let left = side === "right" ? fabLeft + FAB_SIZE - width : fabLeft;
  left = Math.min(vw - MARGIN - width, Math.max(MARGIN, left));

  return {
    style: {
      left,
      top,
      width,
      height,
      transformOrigin: `${side === "right" ? "right" : "left"} ${openUp ? "bottom" : "top"}`,
    },
  };
}

export default function FloatingWidget({
  open,
  unread,
  onToggle,
  onClose,
  messages,
  typing,
  connected,
  onSendText,
  onSendButton,
  onUpload,
}: Props) {
  const { x, y, side, constraints, onDragEnd, draggedRef } = useWidgetPosition();
  const [placement, setPlacement] = useState<Placement | null>(null);

  // Recompute placement whenever the window opens or the viewport resizes.
  const refresh = useCallback(() => {
    setPlacement(computePlacement(x.get(), y.get(), side));
  }, [x, y, side]);

  useEffect(() => {
    if (!open) return;
    refresh();
    window.addEventListener("resize", refresh);
    return () => window.removeEventListener("resize", refresh);
  }, [open, refresh]);

  // Swallow the click that framer-motion fires at the end of a drag gesture.
  const handleToggle = useCallback(() => {
    if (draggedRef.current) {
      draggedRef.current = false;
      return;
    }
    onToggle();
  }, [draggedRef, onToggle]);

  return (
    <>
      <AnimatePresence>
        {open && placement && (
          <ChatWindow
            key="chat-window"
            style={placement.style}
            messages={messages}
            typing={typing}
            connected={connected}
            onSendText={onSendText}
            onSendButton={onSendButton}
            onUpload={onUpload}
            onClose={onClose}
          />
        )}
      </AnimatePresence>

      <motion.div
        className="fixed left-0 top-0 z-[9999]"
        style={{ x, y, touchAction: "none" }}
        drag={!open}
        dragConstraints={constraints}
        dragElastic={0}
        dragMomentum={false}
        onDragEnd={onDragEnd}
        whileDrag={{ cursor: "grabbing" }}
      >
        <ChatBubble open={open} unread={unread} onClick={handleToggle} />
      </motion.div>
    </>
  );
}
