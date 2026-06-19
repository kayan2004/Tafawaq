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


class GuardrailCategory(str, Enum):
    off_topic = "off_topic"
    prompt_injection = "prompt_injection"
    harmful_content = "harmful_content"


class GuardrailLevel(str, Enum):
    warned = "warned"
    blocked = "blocked"


class GuardrailSource(str, Enum):
    chat = "chat"
    exam_generation = "exam_generation"


class GuardrailDirection(str, Enum):
    input = "input"
    output = "output"
