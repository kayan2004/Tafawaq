from enum import Enum


class Language(str, Enum):
    en = "en"
    fr = "fr"


class Branch(str, Enum):
    general_science = "general_science"
    life_science = "life_science"


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
