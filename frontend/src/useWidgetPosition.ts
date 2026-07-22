import { useCallback, useEffect, useRef, useState } from "react";
import { animate, useMotionValue, type PanInfo } from "framer-motion";

// ---------------------------------------------------------------------------
// Draggable-widget geometry. The launcher lives inside a `position: fixed`
// container anchored at the top-left (0,0); we translate it with x/y motion
// values (GPU transforms → 60fps) instead of animating left/top.
// ---------------------------------------------------------------------------
export const FAB_SIZE = 56;
const MARGIN = 16; // gap from viewport edges
const TOP_SAFE = 88; // clears a typical top navbar so the FAB never overlaps it
const BOTTOM_SAFE = 16;
const STORE_KEY = "pharma_widget_pos";
const DRAG_THRESHOLD = 5; // px moved before a press counts as a drag (not a click)

export type Side = "left" | "right";

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function getBounds(): Bounds {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  return {
    minX: MARGIN,
    maxX: Math.max(MARGIN, vw - FAB_SIZE - MARGIN),
    minY: TOP_SAFE,
    maxY: Math.max(TOP_SAFE, vh - FAB_SIZE - BOTTOM_SAFE),
  };
}

interface Saved {
  side: Side;
  yRatio: number; // vertical position as a 0..1 ratio so it survives viewport resizes
}

function loadSaved(): Saved {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if ((p.side === "left" || p.side === "right") && typeof p.yRatio === "number") {
        return { side: p.side, yRatio: Math.min(1, Math.max(0, p.yRatio)) };
      }
    }
  } catch {
    /* ignore malformed / unavailable storage */
  }
  return { side: "right", yRatio: 1 }; // default: bottom-right corner
}

function save(side: Side, yRatio: number) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({ side, yRatio }));
  } catch {
    /* storage may be unavailable (private mode) — non-fatal */
  }
}

export interface WidgetPosition {
  x: ReturnType<typeof useMotionValue<number>>;
  y: ReturnType<typeof useMotionValue<number>>;
  side: Side;
  constraints: { left: number; right: number; top: number; bottom: number };
  onDragEnd: (e: PointerEvent | MouseEvent | TouchEvent, info: PanInfo) => void;
  /** True right after a drag so the launcher can swallow the trailing click. */
  draggedRef: React.MutableRefObject<boolean>;
}

/**
 * Manages the launcher's on-screen position: constrained dragging within the
 * viewport, snap-to-nearest-edge on release, and localStorage persistence that
 * is restored on refresh and re-clamped on window resize.
 */
export function useWidgetPosition(): WidgetPosition {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const [side, setSide] = useState<Side>("right");
  const draggedRef = useRef(false);
  const [constraints, setConstraints] = useState(() => {
    const b = getBounds();
    return { left: b.minX, right: b.maxX, top: b.minY, bottom: b.maxY };
  });

  // Place the launcher on a given side at a vertical ratio, optionally animating
  // (snap) rather than jumping (init / resize).
  const place = useCallback(
    (s: Side, yRatio: number, withAnimation: boolean) => {
      const b = getBounds();
      const targetX = s === "left" ? b.minX : b.maxX;
      const targetY = b.minY + yRatio * (b.maxY - b.minY);
      setConstraints({ left: b.minX, right: b.maxX, top: b.minY, bottom: b.maxY });
      setSide(s);
      if (withAnimation) {
        animate(x, targetX, { type: "spring", stiffness: 550, damping: 40 });
        animate(y, targetY, { type: "spring", stiffness: 550, damping: 40 });
      } else {
        x.set(targetX);
        y.set(targetY);
      }
    },
    [x, y]
  );

  // Restore saved position on mount.
  useEffect(() => {
    const saved = loadSaved();
    place(saved.side, saved.yRatio, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the launcher in-bounds and edge-pinned when the viewport changes.
  useEffect(() => {
    const onResize = () => {
      const b = getBounds();
      const ratio = (y.get() - b.minY) / Math.max(1, b.maxY - b.minY);
      place(side, Math.min(1, Math.max(0, ratio)), false);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [place, side, y]);

  const onDragEnd = useCallback(
    (_e: PointerEvent | MouseEvent | TouchEvent, info: PanInfo) => {
      draggedRef.current =
        Math.abs(info.offset.x) > DRAG_THRESHOLD ||
        Math.abs(info.offset.y) > DRAG_THRESHOLD;

      const b = getBounds();
      // Snap to whichever edge the FAB's centre is closest to.
      const centreX = x.get() + FAB_SIZE / 2;
      const snapSide: Side = centreX < window.innerWidth / 2 ? "left" : "right";
      const clampedY = Math.min(b.maxY, Math.max(b.minY, y.get()));
      const ratio = (clampedY - b.minY) / Math.max(1, b.maxY - b.minY);

      place(snapSide, ratio, true);
      save(snapSide, ratio);
    },
    [place, x, y]
  );

  return { x, y, side, constraints, onDragEnd, draggedRef };
}
