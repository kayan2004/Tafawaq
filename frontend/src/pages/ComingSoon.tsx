/* ComingSoon.tsx — placeholder for pages not yet ported from the design.
   Replaced one-by-one as each page (Exam, Results, Topics, Chat, History) is built. */
import { Icons } from "../lib/icons";
import type { IconName } from "../lib/icons";

export function ComingSoon({ title, icon, blurb }: { title: string; icon: IconName; blurb: string }) {
  const I = Icons[icon];
  return (
    <div className="page fade-up">
      <div className="coming-soon">
        <div className="coming-soon-mark"><I size={32} /></div>
        <h1 className="coming-soon-title">{title}</h1>
        <p className="coming-soon-sub">{blurb}</p>
      </div>
    </div>
  );
}
