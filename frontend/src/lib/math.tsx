/* math.tsx — KaTeX rendering helpers, ported from the prototype's lib.jsx.
   KaTeX is loaded via CDN in index.html and exposed as window.katex. */
import { useEffect, useMemo, useRef } from "react";
import type { CSSProperties, ReactNode } from "react";

interface KatexLike {
  render: (
    tex: string,
    el: HTMLElement,
    opts?: { throwOnError?: boolean; displayMode?: boolean }
  ) => void;
}

declare global {
  interface Window {
    katex?: KatexLike;
  }
}

/** Render a single LaTeX expression (inline by default, block when `block`). */
export function Tex({ tex, block }: { tex: string; block?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current && window.katex) {
      try {
        window.katex.render(tex, ref.current, { throwOnError: false, displayMode: !!block });
      } catch {
        ref.current.textContent = tex;
      }
    } else if (ref.current) {
      ref.current.textContent = tex;
    }
  }, [tex, block]);
  if (block) return <span className="math-block"><span ref={ref} /></span>;
  return <span ref={ref} style={{ whiteSpace: "nowrap" }} />;
}

type Part =
  | { t: "text"; v: string }
  | { t: "bold"; v: string }
  | { t: "inline"; v: string }
  | { t: "block"; v: string };

/** Render a string with $...$ (inline), $$...$$ (block) math and **bold** interleaved. */
export function RichMath({ children, style }: { children: string; style?: CSSProperties }) {
  const parts = useMemo<Part[]>(() => {
    const out: Part[] = [];
    const re = /\$\$([^$]+)\$\$|\$([^$]+)\$|\*\*([^*]+)\*\*/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(children)) !== null) {
      if (m.index > last) out.push({ t: "text", v: children.slice(last, m.index) });
      if (m[1] != null) out.push({ t: "block", v: m[1] });
      else if (m[2] != null) out.push({ t: "inline", v: m[2] });
      else out.push({ t: "bold", v: m[3] });
      last = re.lastIndex;
    }
    if (last < children.length) out.push({ t: "text", v: children.slice(last) });
    return out;
  }, [children]);

  return (
    <span style={style}>
      {parts.map((p, i): ReactNode =>
        p.t === "text" ? <span key={i}>{p.v}</span>
          : p.t === "bold" ? <strong key={i}>{p.v}</strong>
          : <Tex key={i} tex={p.v} block={p.t === "block"} />
      )}
    </span>
  );
}
