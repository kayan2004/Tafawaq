/* speechify.ts — convert a markdown+LaTeX message string to plain spoken English. */
import { convertLatexToSpeakableText } from "mathlive/ssr";

const _safe = (latex: string): string => {
  try {
    return convertLatexToSpeakableText(latex.trim());
  } catch {
    return "equation";
  }
};

/**
 * Convert a chat message (markdown + LaTeX) to spoken English text.
 * Display math ($$...$$) and inline math ($...$) are converted via mathlive.
 * Markdown decoration chars are stripped. Blank lines collapse to ". ".
 */
export function messageToSpeech(markdown: string): string {
  // 1. Display math $$...$$ — must run before inline $ pass
  let text = markdown.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex: string) =>
    " " + _safe(latex) + " "
  );

  // 2. Inline math $...$
  text = text.replace(/\$([^$\n]+?)\$/g, (_, latex: string) =>
    " " + _safe(latex) + " "
  );

  // 3. Strip markdown decoration characters (#*_`>)
  text = text.replace(/[#*_`>]/g, "");

  // 4. Collapse blank lines (2+ newlines) to period-space
  text = text.replace(/\n{2,}/g, ". ");

  // 5. Remaining single newlines → space
  text = text.replace(/\n/g, " ");

  // 6. Collapse repeated spaces and trim
  return text.replace(/  +/g, " ").trim();
}
