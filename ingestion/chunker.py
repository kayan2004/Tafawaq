"""Exercise-level chunking: one chunk per complete exercise, never split across exercise boundaries."""
import re

# Lebanese GS exams label exercises with Roman numerals.
# Longer alternatives must precede shorter ones so "III" isn't matched as "I" + leftover text.
_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9,
}

# Matches the start of an exercise at the beginning of a line.
# Handles both old format  "II - ( 3 points)"  and new format  "III- Complex numbers (4 points)".
# Requires only: Roman numeral + optional spaces + dash — does NOT require immediate "(".
_ROMAN_EXERCISE = re.compile(
    r"^(IX|VIII|VII|VI|V|IV|III|II|I)\s*[-–]",
    re.MULTILINE,
)

# Fallback for PDFs that spell out "Exercise 1", "Exercise 2", etc.
_WORD_EXERCISE = re.compile(r"Exercise\s+(\d+)", re.IGNORECASE)

# Answer-key section headers found across the 20 PDFs.
# Matched at the start of a line (re.MULTILINE) to avoid false positives inside problem text.
#   2004:      "GENERAL SCIENCES MATH 1st SESSION(2004)" / "Q Short answers M"
#   2006 S2:   "GENERAL SCIENCES – MATHEMATICS ; 2nd SESSION – 2006"
#   2012:      "I Solution Grade"  (first per-exercise answer header)
#   2015 S2:   "Answer Key- Math SG – Second Session - 2015"
#   2016 S1:   "QI Solution G"
#   2016 S2:   "Q-I Solutions N"
_ANSWER_KEY = re.compile(
    r"^(?:"
    r"GENERAL SCIENCES"                             # 2004, 2006 S2
    r"|Q\s+Short\s+answers"                         # 2004 S1 table header
    r"|Answer\s+Key"                                # 2015 S2
    r"|(?:Q[-\s]?)?(?:IX|VIII|VII|VI|V|IV|III|II|I)\s+Solution"  # 2012 / 2016
    r")",
    re.MULTILINE | re.IGNORECASE,
)


def chunk_pdf(pages: dict[int, str], year: int, session: int) -> list[dict]:
    """Split PDF text into exercise-level chunks.

    Detects a known answer-key section header and produces source_type='past_exam'
    chunks for questions and source_type='answer_key' chunks for corrections.
    If no answer-key boundary is found, only question chunks are returned.

    session=0 is the sentinel value for Exceptional sessions.
    """
    full_text = "\n".join(pages[p] for p in sorted(pages))

    answer_key_match = _ANSWER_KEY.search(full_text)

    if answer_key_match:
        question_text = full_text[: answer_key_match.start()]
        answer_text = full_text[answer_key_match.start():]
    else:
        question_text = full_text
        answer_text = None

    chunks: list[dict] = []
    chunks.extend(_split_exercises(question_text, year, session, "past_exam"))
    if answer_text:
        chunks.extend(_split_exercises(answer_text, year, session, "answer_key"))
    return chunks


def _split_exercises(
    text: str, year: int, session: int, source_type: str
) -> list[dict]:
    matches = list(_ROMAN_EXERCISE.finditer(text))
    if matches:
        get_id = lambda m: _ROMAN_TO_INT.get(m.group(1), 0)
    else:
        matches = list(_WORD_EXERCISE.finditer(text))
        if not matches:
            return []
        get_id = lambda m: int(m.group(1))

    chunks: list[dict] = []
    for i, match in enumerate(matches):
        exercise_id = get_id(match)
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if not content:
            continue

        marks_match = re.search(r"(\d+\.?\d*)\s*p(?:oint|t)", content, re.IGNORECASE)
        marks = float(marks_match.group(1)) if marks_match else 0.0

        chunks.append(
            {
                "source_type": source_type,
                "year": year,
                "session": session,
                "exercise_id": exercise_id,
                "marks": marks,
                "content": content,
            }
        )

    return chunks
