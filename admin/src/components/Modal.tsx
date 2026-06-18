import type { ReactNode } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel: string;
  tone?: "warning" | "danger";
  onConfirm: () => void;
  onClose: () => void;
  confirmDisabled?: boolean;
}

export default function Modal({ open, title, body, confirmLabel, tone = "warning", onConfirm, onClose, confirmDisabled }: ModalProps) {
  if (!open) return null;
  const confirmStyle = tone === "danger"
    ? { background: "var(--danger)", color: "#fff" }
    : { background: "#262d39", color: "#fff" };

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center"
      style={{ background: "var(--overlay)" }}
      onClick={onClose}
    >
      <div
        className="w-[420px] max-w-[92vw] rounded-lg p-5"
        style={{ background: "var(--surface)", boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-[16px] font-bold">{title}</div>
        <div className="mt-2 text-[13px]" style={{ color: "var(--text-2)" }}>{body}</div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="h-[34px] px-3.5 rounded-md text-[13px] font-bold border"
            style={{ borderColor: "var(--line-strong)" }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={confirmDisabled}
            className="h-[34px] px-3.5 rounded-md text-[13px] font-bold disabled:opacity-45"
            style={confirmStyle}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
