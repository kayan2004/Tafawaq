/* Onboarding.tsx — post-registration profile setup. */
import { useState } from "react";
import { Icons } from "../lib/icons";
import { saveUserDetails } from "../lib/api";
import type { Language, Branch, UserDetails } from "../lib/api";

interface Props {
  token: string;
  email: string;
  onComplete: (details: UserDetails) => void;
}

const LANGS: { id: Language; badge: string; name: string; sub: string }[] = [
  { id: "en", badge: "EN", name: "English", sub: "Curriculum & exams in English" },
  { id: "fr", badge: "FR", name: "Français", sub: "Programme et examens en français" },
];

const GRADES: { id: number; badge: string; name: string; sub: string; available: boolean }[] = [
  { id: 12, badge: "12", name: "Grade 12", sub: "Baccalaureate year", available: true },
  { id: 9, badge: "9", name: "Grade 9", sub: "Brevet year", available: false },
];

const TRACKS: { id: Branch; badge: string; name: string; sub: string }[] = [
  { id: "general_science", badge: "GS", name: "General Sciences", sub: "Heaviest math load · full analysis & probability" },
  { id: "life_science", badge: "LS", name: "Life Sciences", sub: "Applied math · lighter analysis track" },
];

const CheckIcon = () => {
  const I = Icons.check;
  return <I size={11} className="" />;
};

export function Onboarding({ token, email, onComplete }: Props) {
  const [lang, setLang] = useState<Language | null>(null);
  const [grade, setGrade] = useState<number | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const pickGrade = (g: number) => {
    setGrade(g);
    setBranch(null);
  };

  const needsTrack = grade === 12;
  const ready = lang !== null && grade !== null && (!needsTrack || branch !== null);

  const finish = async () => {
    if (!ready || !lang || !grade) return;
    setLoading(true);
    setError("");
    try {
      const details = await saveUserDetails(token, {
        language: lang,
        grade,
        branch: needsTrack ? branch : null,
      });
      onComplete(details);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  };

  return (
    <div className="login-stage grid-bg">
      <div className="card onb-card fade-up">
        <div className="onb-head">
          <img
            src="/brand/tafawwaq-glyph.png"
            alt="Tafawwaq"
            style={{ height: 52, width: "auto", margin: "0 auto 14px", display: "block" }}
          />
          <h1 style={{ font: "600 20px/1.2 var(--font-display)", letterSpacing: "-0.01em", margin: 0 }}>
            Set up your profile
          </h1>
          <p className="micro" style={{ marginTop: 8 }}>
            TELL US WHERE YOU ARE · WE'LL TAILOR THE CURRICULUM
          </p>
        </div>

        <div className="onb-steps">
          {/* Step 1 — Language */}
          <div className="onb-step">
            <div className="onb-step-label">
              <span className="onb-step-num">1</span>
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
                    <span className="onb-opt-sub">{l.sub}</span>
                  </span>
                  {lang === l.id && (
                    <span className="onb-opt-check"><CheckIcon /></span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Step 2 — Grade (revealed after language) */}
          {lang !== null && (
            <div className="onb-step onb-step-reveal">
              <div className="onb-step-label">
                <span className="onb-step-num">2</span>
                <span className="onb-step-title">Which grade are you in?</span>
              </div>
              <div className="onb-opts">
                {GRADES.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    className={`onb-opt ${grade === g.id ? "is-active" : ""} ${g.available ? "" : "is-disabled"}`}
                    disabled={!g.available}
                    aria-pressed={grade === g.id}
                    onClick={() => g.available && pickGrade(g.id)}
                  >
                    <span className="onb-opt-badge">{g.badge}</span>
                    <span className="onb-opt-body">
                      <span className="onb-opt-name">
                        {g.name}
                        {!g.available && <span className="onb-soon">Soon</span>}
                      </span>
                      <span className="onb-opt-sub">{g.sub}</span>
                    </span>
                    {grade === g.id && (
                      <span className="onb-opt-check"><CheckIcon /></span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3 — Track (revealed only for grade 12) */}
          {needsTrack && (
            <div className="onb-step onb-step-reveal">
              <div className="onb-step-label">
                <span className="onb-step-num">3</span>
                <span className="onb-step-title">Pick your track — it sets your subjects</span>
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
                      <span className="onb-opt-sub">{t.sub}</span>
                    </span>
                    {branch === t.id && (
                      <span className="onb-opt-check"><CheckIcon /></span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {error && (
          <p className="login-error" role="alert" style={{ marginBottom: 12 }}>
            {error}
          </p>
        )}

        <div className="onb-foot">
          <button
            type="button"
            className="btn btn-green"
            style={{ width: "100%" }}
            disabled={!ready || loading}
            onClick={finish}
          >
            {loading ? <span className="login-spinner" aria-hidden="true" /> : "Enter Tafawwaq"}
          </button>
          <span className="onb-back">Signed up as {email}</span>
        </div>
      </div>
    </div>
  );
}
