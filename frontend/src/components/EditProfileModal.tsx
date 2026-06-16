/* EditProfileModal.tsx — edit name + curriculum details (language/grade/branch).
   Reuses the onboarding's onb-opt pill pattern and login-input styling for
   visual consistency with Onboarding.tsx and Login.tsx. */
import { useEffect, useRef, useState } from "react";
import { Icons } from "../lib/icons";
import { changePassword, getUserDetails, saveUserDetails, updateMe } from "../lib/api";
import type { Branch, Language, Me } from "../lib/api";

interface Props {
  token: string;
  me: Me;
  onClose: () => void;
  onSaved: (me: Me) => void;
}

const LANGS: { id: Language; badge: string; name: string }[] = [
  { id: "en", badge: "EN", name: "English" },
  { id: "fr", badge: "FR", name: "Français" },
];

const GRADES: { id: number; badge: string; name: string }[] = [
  { id: 12, badge: "12", name: "Grade 12" },
  { id: 9, badge: "9", name: "Grade 9" },
];

const TRACKS: { id: Branch; badge: string; name: string }[] = [
  { id: "general_science", badge: "GS", name: "General Sciences" },
  { id: "life_science", badge: "LS", name: "Life Sciences" },
];

export function EditProfileModal({ token, me, onClose, onSaved }: Props) {
  const [name, setName] = useState(me.name ?? "");
  const [lang, setLang] = useState<Language | null>(null);
  const [grade, setGrade] = useState<number | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const backdropRef = useRef<HTMLDivElement>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState("");
  const [pwSuccess, setPwSuccess] = useState(false);

  useEffect(() => {
    getUserDetails(token)
      .then((d) => {
        if (d) {
          setLang(d.language);
          setGrade(d.grade);
          setBranch(d.branch);
        }
      })
      .finally(() => setLoadingDetails(false));
  }, [token]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const needsTrack = grade === 12;
  const ready = lang !== null && grade !== null && (!needsTrack || branch !== null);

  const pickGrade = (g: number) => {
    setGrade(g);
    if (g !== 12) setBranch(null);
  };

  const save = async () => {
    if (!ready || !lang || !grade) return;
    setSaving(true);
    setError("");
    try {
      const updatedMe = await updateMe(token, { name: name.trim() || null });
      await saveUserDetails(token, { language: lang, grade, branch: needsTrack ? branch : null });
      onSaved(updatedMe);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSaving(false);
    }
  };

  const changePw = async () => {
    setPwError("");
    setPwSuccess(false);
    if (!currentPassword || !newPassword) {
      setPwError("Fill in both password fields");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError("Passwords don't match");
      return;
    }
    setPwSaving(true);
    try {
      await changePassword(token, currentPassword, newPassword);
      setPwSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPwError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPwSaving(false);
    }
  };

  const CheckIcon = Icons.check;

  return (
    <div
      className="profile-modal-backdrop"
      ref={backdropRef}
      onMouseDown={(e) => { if (e.target === backdropRef.current) onClose(); }}
    >
      <div className="card profile-modal fade-up">
        <div className="profile-modal-head">
          <h2 className="profile-modal-title">Edit profile</h2>
          <button type="button" className="profile-modal-close" aria-label="Close" onClick={onClose}>×</button>
        </div>

        <label className="login-label profile-modal-name">
          Full name
          <input
            type="text"
            className="login-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
            autoFocus
          />
        </label>

        {!loadingDetails && (
          <div className="onb-steps profile-modal-steps">
            <div className="onb-step">
              <div className="onb-step-label">
                <span className="onb-step-title">Which language do you study math in?</span>
              </div>
              <div className="onb-opts">
                {LANGS.map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    className={`onb-opt ${lang === l.id ? "is-active" : ""}`}
                    aria-pressed={lang === l.id}
                    onClick={() => setLang(l.id)}
                  >
                    <span className="onb-opt-badge">{l.badge}</span>
                    <span className="onb-opt-body">
                      <span className="onb-opt-name">{l.name}</span>
                    </span>
                    {lang === l.id && <span className="onb-opt-check"><CheckIcon size={11} className="" /></span>}
                  </button>
                ))}
              </div>
            </div>

            <div className="onb-step">
              <div className="onb-step-label">
                <span className="onb-step-title">Which grade are you in?</span>
              </div>
              <div className="onb-opts">
                {GRADES.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    className={`onb-opt ${grade === g.id ? "is-active" : ""}`}
                    aria-pressed={grade === g.id}
                    onClick={() => pickGrade(g.id)}
                  >
                    <span className="onb-opt-badge">{g.badge}</span>
                    <span className="onb-opt-body">
                      <span className="onb-opt-name">{g.name}</span>
                    </span>
                    {grade === g.id && <span className="onb-opt-check"><CheckIcon size={11} className="" /></span>}
                  </button>
                ))}
              </div>
            </div>

            {needsTrack && (
              <div className="onb-step onb-step-reveal">
                <div className="onb-step-label">
                  <span className="onb-step-title">Track</span>
                </div>
                <div className="onb-opts">
                  {TRACKS.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`onb-opt ${branch === t.id ? "is-active" : ""}`}
                      aria-pressed={branch === t.id}
                      onClick={() => setBranch(t.id)}
                    >
                      <span className="onb-opt-badge">{t.badge}</span>
                      <span className="onb-opt-body">
                        <span className="onb-opt-name">{t.name}</span>
                      </span>
                      {branch === t.id && <span className="onb-opt-check"><CheckIcon size={11} className="" /></span>}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {error && <p className="login-error" role="alert">{error}</p>}

        <div className="profile-modal-foot">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="button" className="btn btn-green" onClick={save} disabled={!ready || saving}>
            {saving ? <span className="login-spinner" aria-hidden="true" /> : "Save changes"}
          </button>
        </div>

        <div className="profile-modal-divider" />

        <div className="profile-modal-pw">
          <h3 className="profile-modal-subtitle">Change password</h3>
          <label className="login-label">
            Current password
            <input
              type="password"
              className="login-input"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          <label className="login-label">
            New password
            <input
              type="password"
              className="login-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          </label>
          <label className="login-label">
            Confirm new password
            <input
              type="password"
              className="login-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
            />
          </label>

          {pwError && <p className="login-error" role="alert">{pwError}</p>}
          {pwSuccess && <p className="profile-modal-success">Password updated.</p>}

          <button
            type="button"
            className="btn btn-blue"
            style={{ width: "100%" }}
            onClick={changePw}
            disabled={pwSaving}
          >
            {pwSaving ? <span className="login-spinner" aria-hidden="true" /> : "Update password"}
          </button>
        </div>
      </div>
    </div>
  );
}
