/* mock.ts — realistic placeholder content (Functions & Probability mock).
   Ported from the Claude Design prototype's data.jsx. Static stand-in until
   the pages are wired to the real backend. */

export interface Student {
  name: string;
  initials: string;
  grade: string;
  streak: number;
}

export interface ExercisePart {
  id: string;
  label: string;
  text: string;
  marks: number;
}

export interface Exercise {
  n: string;
  topic: string;
  marks: number;
  stem: string;
  parts: ExercisePart[];
}

export interface Exam {
  title: string;
  session: string;
  duration: string;
  total: number;
  exercises: Exercise[];
}

export interface EvaluatorQ {
  ex: string;
  got: number;
  max: number;
  note: string;
}

export interface Evaluator {
  name: string;
  total: number;
  style: string;
  perQ: EvaluatorQ[];
  missing: string[];
}

export interface Results {
  strict: Evaluator;
  lenient: Evaluator;
}

export interface Topic {
  name: string;
  count: number;
  last: number;
  blurb: string;
  qs: string[];
}

export interface HistoryItem {
  id: string;
  date: string;
  title: string;
  min: number;
  max: number;
  topics: string[];
  current?: boolean;
}

export const STUDENT: Student = { name: "Layla Haddad", initials: "LH", grade: "Grade 12 — GS", streak: 6 };

export const EXAM: Exam = {
  title: "Mock Exam — Functions & Probability",
  session: "2026 GS Session • Mock #4",
  duration: "3 hours",
  total: 20,
  exercises: [
    {
      n: "I", topic: "Probability", marks: 4,
      stem: "An urn contains 5 red balls and 3 green balls. Two balls are drawn successively without replacement.",
      parts: [
        { id: "1a", label: "1)", text: "Calculate the probability of drawing two red balls.", marks: 1.5 },
        { id: "1b", label: "2)", text: "Let $X$ be the number of green balls drawn. Determine the probability distribution of $X$.", marks: 1.5 },
        { id: "1c", label: "3)", text: "Calculate the expected value $E(X)$.", marks: 1 },
      ],
    },
    {
      n: "II", topic: "Functions", marks: 6,
      stem: "Consider the function $f$ defined on $\\mathbb{R}$ by $$f(x) = \\frac{2x - 1}{x + 2}$$ and let $(C)$ be its representative curve.",
      parts: [
        { id: "2a", label: "1)", text: "Determine the domain of definition of $f$ and compute $\\lim_{x \\to +\\infty} f(x)$.", marks: 1.5 },
        { id: "2b", label: "2)", text: "Show that $f'(x) = \\dfrac{5}{(x+2)^2}$ and set up the table of variations.", marks: 2 },
        { id: "2c", label: "3)", text: "Prove that the point $I(-2, 2)$ is a center of symmetry of $(C)$.", marks: 1.5 },
        { id: "2d", label: "4)", text: "Write the equation of the tangent to $(C)$ at the point of abscissa $x = 0$.", marks: 1 },
      ],
    },
    {
      n: "III", topic: "Probability", marks: 5,
      stem: "A factory produces electronic chips. 4% of chips are defective. A test detects a defective chip with probability 0.98, and wrongly flags a good chip with probability 0.03.",
      parts: [
        { id: "3a", label: "1)", text: "A chip is chosen at random. Calculate the probability that the test is positive.", marks: 2 },
        { id: "3b", label: "2)", text: "Given that the test is positive, find the probability that the chip is actually defective.", marks: 2 },
        { id: "3c", label: "3)", text: "Interpret this result in the context of quality control.", marks: 1 },
      ],
    },
    {
      n: "IV", topic: "Functions", marks: 5,
      stem: "Let $g$ be the function defined on $]0, +\\infty[$ by $g(x) = x - \\ln x$.",
      parts: [
        { id: "4a", label: "1)", text: "Study the variations of $g$ and deduce its minimum.", marks: 2 },
        { id: "4b", label: "2)", text: "Show that the equation $g(x) = 2$ admits exactly two solutions.", marks: 2 },
        { id: "4c", label: "3)", text: "Deduce the sign of $g(x) - 2$ on $]0, +\\infty[$.", marks: 1 },
      ],
    },
  ],
};

export const ANSWERS: Record<string, string> = {
  "1a": "P(two red) = (5/8) × (4/7) = 20/56 = 5/14 ≈ 0.357.",
  "1b": "X can be 0, 1 or 2. P(X=0)=5/14, P(X=1)=15/28, P(X=2)=3/28.",
  "1c": "E(X) = 0×(5/14) + 1×(15/28) + 2×(3/28) = 21/28 = 3/4 = 0.75.",
  "2a": "Domain is R minus {-2}. As x→+∞, f(x)→2 since degrees are equal and ratio of leading coefficients is 2.",
  "2b": "f'(x) = [2(x+2) - (2x-1)] / (x+2)^2 = (2x+4-2x+1)/(x+2)^2 = 5/(x+2)^2 > 0, so f is increasing on each interval.",
  "2c": "I checked f(-2+h)+f(-2-h) but didn't finish showing it equals 4.",
  "2d": "f(0) = -1/2, f'(0) = 5/4. Tangent: y = (5/4)x - 1/2.",
  "3a": "P(T+) = 0.04×0.98 + 0.96×0.03 = 0.0392 + 0.0288 = 0.068.",
  "3b": "P(D | T+) = 0.0392 / 0.068 ≈ 0.576.",
  "3c": "",
  "4a": "g'(x) = 1 - 1/x. g'(x)=0 at x=1. Minimum is g(1)=1.",
  "4b": "Since min is 1 < 2 and g→+∞ on both sides, by IVT there are two solutions.",
  "4c": "",
};

export const RESULTS: Results = {
  strict: {
    name: "Strict Examiner", total: 13.5, style: "Official marking scheme — penalises missing justification",
    perQ: [
      { ex: "I", got: 3.5, max: 4, note: "Distribution correct; minor notation slip on E(X) working." },
      { ex: "II", got: 4, max: 6, note: "Symmetry proof incomplete — no formal demonstration that f(-2+h)+f(-2-h)=4." },
      { ex: "III", got: 4, max: 5, note: "Part 3 interpretation missing entirely." },
      { ex: "IV", got: 2, max: 5, note: "IVT cited but monotonicity on each branch not justified; sign study absent." },
    ],
    missing: ["formal symmetry proof", "monotonic intervals", "Bayes interpretation", "sign table"],
  },
  lenient: {
    name: "Lenient Examiner", total: 16, style: "Rewards correct method even with gaps in rigour",
    perQ: [
      { ex: "I", got: 4, max: 4, note: "All values correct, method clear." },
      { ex: "II", got: 5, max: 6, note: "Strong work; symmetry idea present even if not fully closed." },
      { ex: "III", got: 4.5, max: 5, note: "Bayes computation correct; interpretation only lightly touched." },
      { ex: "IV", got: 2.5, max: 5, note: "Good setup, conclusion reached; deductions left open." },
    ],
    missing: ["sign table", "fuller interpretation"],
  },
};

export const TOPICS: Topic[] = [
  { name: "Complex Numbers", count: 10, last: 2025, blurb: "Geometric interpretation, nth roots, loci.",
    qs: ["2025 — Solve z² − 2z + 4 = 0 and interpret roots geometrically.", "2023 — Find the set of points M such that |z − 2i| = |z + 1|."] },
  { name: "Probability", count: 9, last: 2025, blurb: "Conditional probability, trees, Bayes, distributions.",
    qs: ["2025 — Defective-chip test, compute P(D | T+).", "2024 — Urn without replacement, distribution of X.", "2022 — Independent trials, binomial-style count."] },
  { name: "Functions & Derivatives", count: 9, last: 2025, blurb: "Variations, tangents, asymptotes, symmetry.",
    qs: ["2025 — Study f(x) = (2x−1)/(x+2), center of symmetry.", "2024 — Tangent line and table of variations."] },
  { name: "Integrals", count: 8, last: 2025, blurb: "Areas, integration by parts, definite integrals.",
    qs: ["2025 — Compute ∫ x·ln x dx by parts.", "2023 — Area between curve and x-axis."] },
  { name: "Logarithmic Functions", count: 7, last: 2024, blurb: "Equations, growth, ln-based studies.",
    qs: ["2024 — Study g(x) = x − ln x, count solutions of g(x)=2."] },
  { name: "Exponential Functions", count: 6, last: 2025, blurb: "Differential equations, modelling, limits.",
    qs: ["2025 — Solve y' = 2y with initial condition.", "2021 — Limit of x·e^(−x) at +∞."] },
  { name: "Sequences", count: 5, last: 2024, blurb: "Recurrence, convergence, arithmetic/geometric.",
    qs: ["2024 — Adjacent sequences converging to common limit."] },
  { name: "Space Geometry", count: 4, last: 2023, blurb: "Lines & planes, vectors, intersections.",
    qs: ["2023 — Plane through three points, distance to a line."] },
  { name: "Conics", count: 3, last: 2022, blurb: "Parabola, ellipse, focus-directrix.",
    qs: ["2022 — Ellipse: foci, eccentricity and tangent."] },
  { name: "Differential Equations", count: 2, last: 2024, blurb: "First/second order, applied modelling.",
    qs: ["2024 — Cooling model y' + ky = 0."] },
];

export const HISTORY: HistoryItem[] = [
  { id: "h4", date: "Jun 6, 2026", title: "Functions & Probability", min: 13.5, max: 16, topics: ["Functions", "Probability"], current: true },
  { id: "h3", date: "May 28, 2026", title: "Integrals & Complex Numbers", min: 11, max: 14, topics: ["Integrals", "Complex Numbers"] },
  { id: "h2", date: "May 14, 2026", title: "Full Mock — Session A", min: 12.5, max: 15.5, topics: ["Probability", "Logarithms", "Sequences"] },
  { id: "h1", date: "Apr 30, 2026", title: "Exponentials & Sequences", min: 9, max: 12, topics: ["Exponentials", "Sequences"] },
];
