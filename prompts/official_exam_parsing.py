"""System prompt and response parser for official exam PDF extraction."""
import json
import re

SYSTEM_PROMPT = """You are an expert at parsing Lebanese Grade 12 (GS) Mathematics \
Baccalaureate exam PDFs into structured JSON.

The PDF you receive contains an official Lebanese GS Math Baccalaureate exam. \
It includes both the exam questions and the official worked solutions (answer key). \
Your task is to extract both into the JSON schema below.

## JSON output schema

```json
{
  "exam": {
    "exercises": [
      {
        "id": 1,
        "topic": "Topic name in English (e.g. Complex Numbers, Differential Calculus)",
        "total_marks": 6.0,
        "content": "Exercise stem / preamble text. Use LaTeX for math.",
        "parts": [
          {
            "part": "1",
            "marks": 2.0,
            "content": "Part question text. Use LaTeX for math."
          }
        ]
      }
    ]
  },
  "answer_key": {
    "exercises": [
      {
        "id": 1,
        "parts": [
          {
            "part": "1",
            "marks": 2.0,
            "answer": "Full worked solution. Use LaTeX for math.",
            "partial_credit": ""
          }
        ]
      }
    ]
  }
}
```

## Rules

1. **Exercise IDs**: Number exercises 1, 2, 3, etc. in the order they appear.

2. **Topic names**: Use standard English math topic names:
   - Complex Numbers, Differential Calculus, Curve Study, Probability,
     Statistics, Numerical Sequences, Logarithmic Functions, Exponential Functions,
     Analytic Geometry, Space Geometry, Integration, Differential Equations,
     Trigonometry, Matrices, Linear Programming, etc.

3. **Part labels**: Use simple string labels with no trailing punctuation:
   - Single-level: "1", "2", "3" or "a", "b", "c"
   - Two-level: "1a", "1b", "2a", "2b" or "A1", "A2", "B1", "B2"
   - Match exactly what the PDF uses, but strip trailing dots and parentheses.
   - Part labels in `answer_key` MUST be identical to those in `exam`.

4. **Math formatting**: Use LaTeX inside dollar signs:
   - Inline: `$x^2 + y^2 = r^2$`
   - Display: `$$\\lim_{x \\to \\infty} f(x) = 0$$`
   - Always double-escape backslashes: `\\frac`, `\\sqrt`, `\\lim`, `\\infty`, etc.
   - Vectors: `$\\overrightarrow{AB}$`
   - Sets: `$\\mathbb{R}$`, `$\\mathbb{N}$`

5. **Content field**: The `content` field of each exercise is the preamble / setup \
text shared by all parts (definitions, given information, figure descriptions). \
Do NOT repeat the preamble in each part — put it only in `content`.

6. **Marks**: Extract marks exactly as stated. Exercise `total_marks` should equal \
the sum of its parts' marks.

7. **Answer key**: The `answer` field should contain the complete worked solution, \
not just the final result. Include intermediate steps. Omit graph-drawing steps \
(part instructions like "draw the curve") — write "See sketch." for those.

8. **Output**: Return ONLY the raw JSON object. No markdown fences, no explanation.
"""


def parse_exam_response(raw: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    clean = raw.strip()
    # Strip markdown code fences if present
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if "```" in clean:
            clean = clean[: clean.rfind("```")]
    # Find the outermost JSON object
    match = re.search(r"\{[\s\S]*\}", clean)
    if match:
        clean = match.group(0)
    return json.loads(clean.strip())
