"""Tagging prompt for past exam chunks (topic / subtopic / question_type)."""

TAG_PROMPT = """\
You are tagging a Lebanese GS Grade 12 Math exam exercise for a study platform.

Given the exercise content below, return ONLY a JSON object with exactly these three keys:
- "topic": the main mathematical topic (e.g. "Functions", "Probability", "Complex Numbers", \
"Sequences", "Integration", "Geometry", "Limits")
- "subtopic": a specific subtopic within the topic (e.g. "Limits at infinity", \
"Binomial probability")
- "question_type": one of "proof", "calculation", "mcq", or "sketch"

Exercise:
{content}

Return only the JSON object, no explanation."""
