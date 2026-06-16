/* SessionPicker.tsx — header trigger + floating panel for managing chat sessions. */
import { useState, useRef, useEffect } from "react";
import { Icons } from "../lib/icons";
import type { ChatSession } from "../lib/api";

const SUBJECTS = [
  { id: "math_gs12", label: "Math GS12" },
] as const;

type Subject = typeof SUBJECTS[number];

function sessionDisplayName(s: ChatSession): string {
  if (s.title) return s.title;
  const d = new Date(s.created_at);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function subjectLabel(subjectId: string): string {
  return SUBJECTS.find((s) => s.id === subjectId)?.label ?? subjectId;
}

interface Props {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  onSelect: (session: ChatSession) => void;
  onCreate: (subject: string, title?: string) => Promise<void>;
  onRename: (sessionId: string, title: string) => Promise<void>;
  disabled?: boolean;
}

export function SessionPicker({
  sessions,
  activeSession,
  onSelect,
  onCreate,
  onRename,
  disabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newSubject, setNewSubject] = useState<Subject>(SUBJECTS[0]);
  const [newTitle, setNewTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const panelRef = useRef<HTMLDivElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        closePanel();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    if (creating) setTimeout(() => titleInputRef.current?.focus(), 0);
  }, [creating]);

  useEffect(() => {
    if (renamingId) setTimeout(() => renameInputRef.current?.focus(), 0);
  }, [renamingId]);

  const closePanel = () => {
    setOpen(false);
    setCreating(false);
    setNewTitle("");
    setRenamingId(null);
    setRenameValue("");
  };

  const handleCreate = async () => {
    setSaving(true);
    try {
      await onCreate(newSubject.id, newTitle.trim() || undefined);
      setNewTitle("");
      setCreating(false);
    } finally {
      setSaving(false);
    }
  };

  const handleRename = async (sessionId: string) => {
    if (!renameValue.trim()) { setRenamingId(null); return; }
    setSaving(true);
    try {
      await onRename(sessionId, renameValue.trim());
      setRenamingId(null);
      setRenameValue("");
    } finally {
      setSaving(false);
    }
  };

  const startRename = (s: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingId(s.id);
    setRenameValue(s.title ?? "");
  };

  const ChevIcon = Icons.chevron;
  const PencilIcon = Icons.pencil;
  const PlusIcon = Icons.plus;
  const ScaleIcon = Icons.scale;
  const CheckIcon = Icons.check;

  const triggerLabel = activeSession
    ? `${subjectLabel(activeSession.subject)} · ${sessionDisplayName(activeSession)}`
    : "Select session";

  return (
    <div className="sess-wrap" ref={panelRef}>
      <button
        type="button"
        className={`sess-trigger${open ? " is-open" : ""}`}
        onClick={() => { if (!disabled) setOpen((o) => !o); }}
        aria-haspopup="dialog"
        aria-expanded={open}
        disabled={disabled}
      >
        <span className="sess-trigger-ico"><ScaleIcon size={14} className="" /></span>
        <span className="sess-trigger-label">{triggerLabel}</span>
        <span className="sess-trigger-chev"><ChevIcon size={13} className="" /></span>
      </button>

      {open && (
        <div className="sess-panel" role="dialog" aria-label="Chat sessions">
          <div className="sess-panel-head">Sessions</div>

          <div className="sess-list">
            {sessions.length === 0 && (
              <div className="sess-empty">No sessions yet</div>
            )}
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`sess-item${s.id === activeSession?.id ? " is-active" : ""}`}
                onClick={() => { if (renamingId !== s.id) { onSelect(s); closePanel(); } }}
              >
                {renamingId === s.id ? (
                  <input
                    ref={renameInputRef}
                    className="sess-rename-input"
                    value={renameValue}
                    placeholder={sessionDisplayName(s)}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRename(s.id);
                      if (e.key === "Escape") { setRenamingId(null); setRenameValue(""); }
                    }}
                    onClick={(e) => e.stopPropagation()}
                    disabled={saving}
                  />
                ) : (
                  <>
                    <div className="sess-item-body">
                      <span className="sess-item-name">{sessionDisplayName(s)}</span>
                      <span className="sess-item-subj">{subjectLabel(s.subject)}</span>
                    </div>
                    <div className="sess-item-actions">
                      {s.id === activeSession?.id && <CheckIcon size={13} className="sess-active-check" />}
                      <button
                        type="button"
                        className="sess-rename-btn"
                        aria-label="Rename session"
                        onClick={(e) => startRename(s, e)}
                        title="Rename"
                      >
                        <PencilIcon size={12} className="" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>

          <div className="sess-panel-foot">
            {creating ? (
              <div className="sess-create-form">
                {SUBJECTS.length > 1 && (
                  <div className="sess-create-subj">
                    {SUBJECTS.map((sub) => (
                      <button
                        key={sub.id}
                        type="button"
                        className={`sess-subj-opt${newSubject.id === sub.id ? " is-active" : ""}`}
                        onClick={() => setNewSubject(sub)}
                      >
                        {sub.label}
                      </button>
                    ))}
                  </div>
                )}
                <div className="sess-create-subj-static">
                  <span className="sess-subj-badge">{newSubject.label}</span>
                </div>
                <input
                  ref={titleInputRef}
                  className="sess-create-input"
                  placeholder="Session name (optional)"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreate();
                    if (e.key === "Escape") { setCreating(false); setNewTitle(""); }
                  }}
                  disabled={saving}
                />
                <div className="sess-create-actions">
                  <button
                    type="button"
                    className="sess-create-cancel"
                    onClick={() => { setCreating(false); setNewTitle(""); }}
                    disabled={saving}
                  >Cancel</button>
                  <button
                    type="button"
                    className="sess-create-confirm"
                    onClick={handleCreate}
                    disabled={saving}
                  >{saving ? "Creating…" : "Create"}</button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="sess-new-btn"
                onClick={() => setCreating(true)}
              >
                <PlusIcon size={13} className="" />
                New session
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
