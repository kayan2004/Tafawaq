"""Tagging prompt for textbook chunks (topic / subtopic)."""

TAG_PROMPT = """\
You are tagging a section of a Lebanese Grade 12 Mathematics textbook for a study platform.

Given the content below, return ONLY a JSON object with exactly two keys:
- "topic": the main mathematical topic (e.g. "Logic", "Functions", "Integration", "Probability")
- "subtopic": a specific subtopic (e.g. "Logical connectives", "Limits at infinity")

Content:
{content}

Return only the JSON object, no explanation."""
