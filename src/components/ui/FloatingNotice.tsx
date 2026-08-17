import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";

export const FLOATING_NOTICE_AUTO_DISMISS_MS = 7000;
export const FLOATING_NOTICE_EXIT_MS = 300;

export type FloatingNoticeTone = "success" | "info";

const TONE_STYLES: Record<
  FloatingNoticeTone,
  { container: string; button: string }
> = {
  success: {
    container:
      "text-emerald-800 bg-emerald-50 border-emerald-200",
    button: "text-emerald-700 hover:bg-emerald-100 hover:text-emerald-900",
  },
  info: {
    container: "text-brand-red-dark bg-brand-red/10 border-brand-red/30",
    button: "text-brand-red hover:bg-brand-red/15 hover:text-brand-red-dark",
  },
};

export function useFloatingNotice() {
  const [message, setMessage] = useState<string | null>(null);
  const [exiting, setExiting] = useState(false);
  const autoTimerRef = useRef<number | null>(null);
  const exitTimerRef = useRef<number | null>(null);
  const exitingRef = useRef(false);
  const messageRef = useRef<string | null>(null);

  const clearTimers = useCallback(() => {
    if (autoTimerRef.current != null) {
      window.clearTimeout(autoTimerRef.current);
      autoTimerRef.current = null;
    }
    if (exitTimerRef.current != null) {
      window.clearTimeout(exitTimerRef.current);
      exitTimerRef.current = null;
    }
  }, []);

  const dismiss = useCallback(() => {
    if (!messageRef.current || exitingRef.current) return;
    exitingRef.current = true;
    setExiting(true);
    if (autoTimerRef.current != null) {
      window.clearTimeout(autoTimerRef.current);
      autoTimerRef.current = null;
    }
    exitTimerRef.current = window.setTimeout(() => {
      exitingRef.current = false;
      messageRef.current = null;
      setMessage(null);
      setExiting(false);
    }, FLOATING_NOTICE_EXIT_MS);
  }, []);

  const show = useCallback(
    (text: string) => {
      clearTimers();
      exitingRef.current = false;
      setExiting(false);
      messageRef.current = text;
      setMessage(text);
      autoTimerRef.current = window.setTimeout(() => {
        dismiss();
      }, FLOATING_NOTICE_AUTO_DISMISS_MS);
    },
    [clearTimers, dismiss],
  );

  useEffect(() => {
    return () => {
      clearTimers();
    };
  }, [clearTimers]);

  return { message, exiting, show, dismiss };
}

interface FloatingNoticeProps {
  message: string;
  exiting: boolean;
  onDismiss: () => void;
  tone?: FloatingNoticeTone;
  className?: string;
}

export function FloatingNotice({
  message,
  exiting,
  onDismiss,
  tone = "success",
  className = "",
}: FloatingNoticeProps) {
  const styles = TONE_STYLES[tone];

  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-lg border px-3 py-2.5 text-xs font-medium shadow-md transition-all duration-300 ease-in ${styles.container} ${
        exiting ? "-translate-y-6 opacity-0 pointer-events-none" : "translate-y-0 opacity-100"
      } ${className}`}
      role="status"
    >
      <span className="min-w-0 flex-1 leading-snug">{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        className={`shrink-0 rounded p-0.5 ${styles.button}`}
        aria-label="Dismiss notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
