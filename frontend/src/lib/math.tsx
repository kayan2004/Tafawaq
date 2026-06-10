/* math.tsx — KaTeX rendering + markdown parser for assistant messages. */
import { useEffect, useMemo, useRef } from "react";
import type { CSSProperties, ReactNode } from "react";

interface KatexLike {
  render: (
    tex: string,
    el: HTMLElement,
    opts?: { throwOnError?: boolean; displayMode?: boolean }
  ) => void;
}
declare global { interface Window { katex?: KatexLike; } }

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

// ─── Inline parser: $$..$$, $..$, **bold**, *italic*, `code` ─────────────────

const INLINE_RE = /\$\$([^$]+?)\$\$|\$([^$\n]+?)\$|\*\*([^*]+?)\*\*|\*([^*\n]+?)\*|`([^`\n]+?)`/g;

function parseInline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0, k = 0;
  let m: RegExpExecArray | null;
  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text)) !== null) {
    if (m.index > last) out.push(<span key={k++}>{text.slice(last, m.index)}</span>);
    if      (m[1] != null) out.push(<Tex key={k++} tex={m[1]} block />);
    else if (m[2] != null) out.push(<Tex key={k++} tex={m[2]} />);
    else if (m[3] != null) out.push(<strong key={k++}>{m[3]}</strong>);
    else if (m[4] != null) out.push(<em key={k++}>{m[4]}</em>);
    else if (m[5] != null) out.push(<code key={k++} className="chat-inline-code">{m[5]}</code>);
    last = INLINE_RE.lastIndex;
  }
  if (last < text.length) out.push(<span key={k++}>{text.slice(last)}</span>);
  return out;
}

// ─── Block parser ─────────────────────────────────────────────────────────────

const TABLE_ROW_RE = /^\s*\|.+\|\s*$/;
const TABLE_SEP_RE = /^\s*\|[\s\-:|]+\|\s*$/;

function splitTableRow(line: string): string[] {
  return line.split("|").slice(1, -1).map((c) => c.trim());
}

function buildNodes(raw: string): ReactNode[] {
  const lines = raw.split("\n");
  const nodes: ReactNode[] = [];
  let k = 0;
  let paraBuf: string[] = [];
  let listBuf: { ordered: boolean; text: string }[] = [];
  let tableBuf: string[] = [];
  let mathBuf: string[] | null = null;

  const flushPara = () => {
    const s = paraBuf.join("\n").trim();
    if (s) nodes.push(<p key={k++} className="chat-md-p">{parseInline(s)}</p>);
    paraBuf = [];
  };

  const flushList = () => {
    if (!listBuf.length) return;
    const ordered = listBuf[0].ordered;
    const Tag = ordered ? "ol" : "ul";
    nodes.push(
      <Tag key={k++} className="chat-md-list">
        {listBuf.map((it, j) => <li key={j}>{parseInline(it.text)}</li>)}
      </Tag>
    );
    listBuf = [];
  };

  const flushTable = () => {
    if (!tableBuf.length) return;
    // Require: header row + separator row + at least zero body rows
    const hasSep = tableBuf.length >= 2 && TABLE_SEP_RE.test(tableBuf[1]);
    if (!hasSep) {
      // Not a real table — treat as regular paragraphs
      tableBuf.forEach((l) => paraBuf.push(l));
      flushPara();
      tableBuf = [];
      return;
    }
    const headers = splitTableRow(tableBuf[0]);
    const bodyRows = tableBuf.slice(2).map(splitTableRow);
    nodes.push(
      <div key={k++} className="chat-md-table-wrap">
        <table className="chat-md-table">
          <thead>
            <tr>{headers.map((h, i) => <th key={i}>{parseInline(h)}</th>)}</tr>
          </thead>
          {bodyRows.length > 0 && (
            <tbody>
              {bodyRows.map((row, i) => (
                <tr key={i}>{row.map((cell, j) => <td key={j}>{parseInline(cell)}</td>)}</tr>
              ))}
            </tbody>
          )}
        </table>
      </div>
    );
    tableBuf = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();

    // Multi-line block math: opening or closing $$
    if (trimmed === "$$") {
      if (mathBuf !== null) {
        nodes.push(<Tex key={k++} tex={mathBuf.join("\n")} block />);
        mathBuf = null;
      } else {
        flushTable(); flushList(); flushPara();
        mathBuf = [];
      }
      continue;
    }
    if (mathBuf !== null) { mathBuf.push(line); continue; }

    // Horizontal rule
    if (/^---+$/.test(trimmed)) {
      flushTable(); flushList(); flushPara();
      nodes.push(<hr key={k++} className="chat-md-hr" />);
      continue;
    }

    // Headings: # / ## / ###
    const hm = trimmed.match(/^(#{1,3})\s+(.*)/);
    if (hm) {
      flushTable(); flushList(); flushPara();
      const level = hm[1].length;
      const Tag = `h${level}` as "h1" | "h2" | "h3";
      nodes.push(<Tag key={k++} className={`chat-md-h${level}`}>{parseInline(hm[2])}</Tag>);
      continue;
    }

    // Markdown table row: | cell | cell |
    if (TABLE_ROW_RE.test(line)) {
      flushList(); flushPara();
      tableBuf.push(trimmed);
      continue;
    }

    // Non-table line while building a table → flush it
    if (tableBuf.length) flushTable();

    // Ordered list: "1. item"
    const olm = trimmed.match(/^\d+\.\s+(.*)/);
    if (olm) { flushPara(); listBuf.push({ ordered: true, text: olm[1] }); continue; }

    // Unordered list: "- item" or "* item" (space required to avoid *italic*)
    const ulm = trimmed.match(/^[-*]\s+(.*)/);
    if (ulm) { flushPara(); listBuf.push({ ordered: false, text: ulm[1] }); continue; }

    // Blank line — flush pending blocks
    if (!trimmed) { flushList(); flushPara(); continue; }

    // Regular text
    flushList();
    paraBuf.push(line);
  }

  flushTable();
  flushList();
  flushPara();
  return nodes;
}

/**
 * Render assistant message text: markdown headings, lists, tables, bold,
 * italic, inline code, and $...$ / $$...$$ math via KaTeX.
 * Pass `streaming` to show the blinking cursor inside the container.
 */
export function RichMath({ children, streaming, style }: { children: string; streaming?: boolean; style?: CSSProperties }) {
  const nodes = useMemo(() => buildNodes(children ?? ""), [children]);
  return (
    <div className="chat-md" style={style}>
      {nodes}
      {streaming && <span className="chat-cursor" />}
    </div>
  );
}
