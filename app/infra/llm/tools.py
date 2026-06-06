"""Anthropic tool schema definitions.

These are passed as the `tools` argument to stream_claude() / call_claude().
No agent-loop execution logic lives here — tool definitions only.
"""

RETRIEVE_PAST_QUESTIONS_TOOL: dict = {
    "name": "retrieve_past_questions",
    "description": (
        "Search the Lebanese official GS Math exam archive for past questions "
        "relevant to the given query. Returns ranked chunks with year, session, "
        "topic, and content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query describing the concept or problem type.",
            },
            "topic": {
                "type": "string",
                "description": "Optional topic filter (e.g. 'Functions', 'Integrals').",
            },
            "question_type": {
                "type": "string",
                "enum": ["proof", "calculation", "mcq", "sketch"],
                "description": "Optional question type filter.",
            },
            "year_from": {
                "type": "integer",
                "description": "Optional earliest year filter (inclusive).",
            },
            "year_to": {
                "type": "integer",
                "description": "Optional latest year filter (inclusive).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default 10, max 50).",
            },
        },
        "required": ["query"],
    },
}

RETRIEVE_ANSWER_KEY_TOOL: dict = {
    "name": "retrieve_answer_key",
    "description": (
        "Fetch the official answer key for a specific exercise from a Lebanese "
        "official GS Math exam by year, session number, and exercise number."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "year": {"type": "integer", "description": "Exam year (e.g. 2024)."},
            "session": {"type": "integer", "description": "Session number (1 or 2)."},
            "exercise_id": {"type": "integer", "description": "Exercise number within the exam."},
        },
        "required": ["year", "session", "exercise_id"],
    },
}

GET_TOPIC_STATS_TOOL: dict = {
    "name": "get_topic_stats",
    "description": (
        "Retrieve frequency statistics for topics that have appeared in Lebanese "
        "official GS Math exams. Returns appearance counts and last-seen year."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Optional: filter to a specific topic name.",
            },
        },
        "required": [],
    },
}

ALL_TOOLS: list[dict] = [
    RETRIEVE_PAST_QUESTIONS_TOOL,
    RETRIEVE_ANSWER_KEY_TOOL,
    GET_TOPIC_STATS_TOOL,
]
