/**
 * TafawwaqMascot
 *
 * Props:
 *   state       — 'idle' | 'talking' | 'thinking' | 'nailed'
 *   mouthOpen   — boolean  (driven externally by Web Audio amplitude)
 *   isDark      — boolean  (flips off-body spark from navy → mint)
 *   size        — number   (px, default 120)
 *
 * Usage:
 *   <TafawwaqMascot state="talking" mouthOpen={isLoud} isDark={isDark} />
 *
 * Wire state from outside:
 *   - 'idle'     → default, no audio, no stream
 *   - 'talking'  → while ElevenLabs audio is playing
 *   - 'thinking' → while SSE stream is open (tokens arriving)
 *   - 'nailed'   → fire for 1.8 s after a correct graded result
 *                  (component auto-returns to idle after animation)
 */

import { useEffect, useRef, useState } from "react";

const MINT  = "#10D982";
const NAVY  = "#1B2A4A";
const WHITE = "#FFFFFF";

const css = `
  @keyframes tfq-bob {
    0%,100% { transform: translateY(0px); }
    50%      { transform: translateY(-8px); }
  }
  @keyframes tfq-bob-fast {
    0%,100% { transform: translateY(0px); }
    50%      { transform: translateY(-7px); }
  }
  @keyframes tfq-bob-slow {
    0%,100% { transform: translateY(0px); }
    50%      { transform: translateY(-4px); }
  }
  @keyframes tfq-shadow {
    0%,100% { transform: scaleX(1); opacity: .08; }
    50%      { transform: scaleX(.8); opacity: .04; }
  }
  @keyframes tfq-blink {
    0%,88%,100% { transform: scaleY(1); }
    93%          { transform: scaleY(0.05); }
    97%          { transform: scaleY(1); }
  }
  @keyframes tfq-spark-spin {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  @keyframes tfq-spark-slow {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  @keyframes tfq-nailed-body {
    0%   { transform: scale(1) translateY(0); }
    15%  { transform: scale(1.18) translateY(-4px); }
    35%  { transform: scale(.94) translateY(0); }
    55%  { transform: scale(1) translateY(0); }
    100% { transform: scale(1) translateY(0); }
  }
  @keyframes tfq-arm-up-l {
    0%,100% { transform: rotate(0deg) translateY(0); }
    30%,65% { transform: rotate(-22deg) translateY(-12px); }
  }
  @keyframes tfq-arm-up-r {
    0%,100% { transform: rotate(0deg) translateY(0); }
    30%,65% { transform: rotate(22deg) translateY(-12px); }
  }
  @keyframes tfq-eye-nailed {
    0%,38%,68%,100% { transform: scaleY(1); }
    20%,52%         { transform: scaleY(0.05); }
  }
  @keyframes tfq-spark-celebrate {
    0%   { transform: rotate(0deg) scale(1); }
    50%  { transform: rotate(180deg) scale(1.7) translate(6px,-6px); }
    100% { transform: rotate(360deg) scale(1); }
  }
  @keyframes tfq-extra-1 {
    0%   { opacity: 0; transform: translate(0,0) scale(0); }
    25%  { opacity: 1; transform: translate(20px,-20px) scale(1); }
    100% { opacity: 0; transform: translate(36px,-40px) scale(.3); }
  }
  @keyframes tfq-extra-2 {
    0%   { opacity: 0; transform: translate(0,0) scale(0); }
    25%  { opacity: 1; transform: translate(-16px,-24px) scale(1); }
    100% { opacity: 0; transform: translate(-28px,-46px) scale(.3); }
  }
`;

function SparkPath({ x, y, size = 20, fill }) {
  const h = size / 2;
  return (
    <path
      d={`M${x},${y - h} Q${x + h * 0.32},${y} ${x + h},${y} Q${x + h * 0.32},${y} ${x},${y + h} Q${x - h * 0.32},${y} ${x - h},${y} Q${x - h * 0.32},${y} ${x},${y - h} Z`}
      fill={fill}
    />
  );
}

export default function TafawwaqMascot({
  state = "idle",
  mouthOpen = false,
  isDark = false,
  size = 120,
}) {
  const styleInjected = useRef(false);
  const [internalState, setInternalState] = useState(state);
  const nailedTimer = useRef(null);

  // inject keyframes once
  useEffect(() => {
    if (styleInjected.current) return;
    const tag = document.createElement("style");
    tag.textContent = css;
    document.head.appendChild(tag);
    styleInjected.current = true;
  }, []);

  // handle nailed-it auto-return
  useEffect(() => {
    clearTimeout(nailedTimer.current);
    setInternalState(state);
    if (state === "nailed") {
      nailedTimer.current = setTimeout(() => setInternalState("idle"), 1800);
    }
    return () => clearTimeout(nailedTimer.current);
  }, [state]);

  const s = internalState;
  const offBodyFill = isDark ? MINT : NAVY;

  /* ── derived animation styles ── */
  const bodyAnim =
    s === "nailed"
      ? "tfq-nailed-body 1.4s ease forwards"
      : s === "thinking"
      ? "tfq-bob-slow 3.2s ease-in-out infinite"
      : s === "talking"
      ? "tfq-bob-fast 1.8s ease-in-out infinite"
      : "tfq-bob 2.4s ease-in-out infinite";

  const shadowAnim = "tfq-shadow 2.4s ease-in-out infinite";

  const sparkSpinDuration =
    s === "thinking" ? "14s" : s === "talking" ? "5s" : "8s";
  const sparkAnim =
    s === "nailed"
      ? "tfq-spark-celebrate 1.4s ease forwards"
      : `tfq-spark-spin ${sparkSpinDuration} linear infinite`;

  const eyeScaleY =
    s === "talking" ? 0.88 : s === "thinking" ? 1 : 1;
  const eyeTranslateY = s === "thinking" ? -2 : 0;
  const eyeAnim =
    s === "nailed"
      ? "tfq-eye-nailed 1.4s ease forwards"
      : s === "idle"
      ? "tfq-blink 4.2s ease-in-out infinite"
      : "none";

  const browOpacity = s === "thinking" ? 1 : 0;
  const browTranslateY = s === "thinking" ? -3 : 0;

  const armLeftStyle =
    s === "nailed"
      ? { animation: "tfq-arm-up-l 1.4s ease forwards", transformOrigin: "37px 86px" }
      : s === "talking" || s === "thinking"
      ? { transform: s === "talking" ? "translateY(-5px)" : "translateY(0)", transformOrigin: "37px 86px", transition: "transform .2s" }
      : { transformOrigin: "37px 86px", transition: "transform .2s" };

  const armRightStyle =
    s === "nailed"
      ? { animation: "tfq-arm-up-r 1.4s ease forwards", transformOrigin: "83px 86px" }
      : s === "thinking"
      ? { transform: "rotate(-52deg)", transformOrigin: "83px 86px", transition: "transform .2s" }
      : s === "talking"
      ? { transform: "translateY(-5px)", transformOrigin: "83px 86px", transition: "transform .2s" }
      : { transformOrigin: "83px 86px", transition: "transform .2s" };

  /* mouth rect opacity */
  const mouthClosedOpacity = s === "talking" && mouthOpen ? 0 : 1;
  const mouthOpenOpacity   = s === "talking" && mouthOpen ? 1 : 0;

  /* nailed extra sparks */
  const extra1Anim = s === "nailed" ? "tfq-extra-1 1.4s ease forwards .2s" : "none";
  const extra2Anim = s === "nailed" ? "tfq-extra-2 1.4s ease forwards .3s" : "none";

  const scale = size / 120;

  return (
    <svg
      viewBox="0 0 120 160"
      width={size}
      height={size * (160 / 120)}
      xmlns="http://www.w3.org/2000/svg"
      style={{ overflow: "visible", display: "block" }}
    >
      {/* shadow */}
      <ellipse
        cx="60" cy="152" rx="34" ry="7"
        fill={NAVY}
        style={{ animation: shadowAnim, transformOrigin: "60px 152px" }}
      />

      {/* character group — bob */}
      <g style={{ animation: bodyAnim, transformOrigin: "60px 60px" }}>

        {/* off-body signature spark */}
        <g style={{ animation: sparkAnim, transformOrigin: "96px 22px" }}>
          <SparkPath x={96} y={22} size={18} fill={offBodyFill} />
        </g>

        {/* celebration sparks */}
        <g style={{ animation: extra1Anim, transformOrigin: "96px 22px", opacity: 0 }}>
          <SparkPath x={96} y={22} size={13} fill={MINT} />
        </g>
        <g style={{ animation: extra2Anim, transformOrigin: "26px 30px", opacity: 0 }}>
          <SparkPath x={26} y={30} size={11} fill={MINT} />
        </g>

        {/* arm left */}
        <g style={armLeftStyle}>
          <line x1="37" y1="86" x2="18" y2="110"
            stroke={MINT} strokeWidth="10" strokeLinecap="round"/>
          <circle cx="16" cy="113" r="6"
            fill={MINT} stroke={NAVY} strokeWidth="2.5"/>
        </g>

        {/* arm right */}
        <g style={armRightStyle}>
          <line x1="83" y1="86" x2="102" y2="110"
            stroke={MINT} strokeWidth="10" strokeLinecap="round"/>
          <circle cx="104" cy="113" r="6"
            fill={MINT} stroke={NAVY} strokeWidth="2.5"/>
        </g>

        {/* body — 4-point spark */}
        <path
          d="M60,18 Q69,48 99,60 Q69,72 60,102 Q51,72 21,60 Q51,48 60,18 Z"
          fill={MINT}
        />

        {/* brows */}
        <path
          d="M34,56 Q40,51 46,56"
          fill="none" stroke={NAVY} strokeWidth="3.5" strokeLinecap="round"
          style={{
            opacity: browOpacity,
            transform: `translateY(${browTranslateY}px)`,
            transition: "opacity .18s, transform .18s",
            transformOrigin: "40px 56px",
          }}
        />
        <path
          d="M74,56 Q80,51 86,56"
          fill="none" stroke={NAVY} strokeWidth="3.5" strokeLinecap="round"
          style={{
            opacity: browOpacity,
            transform: `translateY(${browTranslateY}px)`,
            transition: "opacity .18s, transform .18s",
            transformOrigin: "80px 56px",
          }}
        />

        {/* eye left */}
        <g style={{
          transform: `scaleY(${eyeScaleY}) translateY(${eyeTranslateY}px)`,
          transformOrigin: "44px 68px",
          animation: eyeAnim,
          transition: s === "idle" || s === "nailed" ? "none" : "transform .15s",
        }}>
          <circle cx="44" cy="68" r="9.5" fill={NAVY}/>
          <circle cx="41" cy="65" r="3"   fill={WHITE}/>
        </g>

        {/* eye right */}
        <g style={{
          transform: `scaleY(${eyeScaleY}) translateY(${eyeTranslateY}px)`,
          transformOrigin: "76px 68px",
          animation: eyeAnim,
          transition: s === "idle" || s === "nailed" ? "none" : "transform .15s",
        }}>
          <circle cx="76" cy="68" r="9.5" fill={NAVY}/>
          <circle cx="73" cy="65" r="3"   fill={WHITE}/>
        </g>

        {/* mouth — closed smile */}
        <path
          d="M46,84 Q60,98 74,84"
          fill="none" stroke={NAVY} strokeWidth="5.5" strokeLinecap="round"
          style={{ opacity: mouthClosedOpacity, transition: "opacity .07s" }}
        />

        {/* mouth — open (talking + mouthOpen) */}
        <rect
          x="49" y="82" width="22" height="16" rx="9"
          fill={NAVY}
          style={{ opacity: mouthOpenOpacity, transition: "opacity .07s" }}
        />

      </g>
    </svg>
  );
}
