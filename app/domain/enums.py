from enum import Enum


class SessionType(str, Enum):
    mock_generated = "mock_generated"
    real_past_exam = "real_past_exam"


class SessionStatus(str, Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"


class QuestionType(str, Enum):
    proof = "proof"
    calculation = "calculation"
    mcq = "mcq"
    sketch = "sketch"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
