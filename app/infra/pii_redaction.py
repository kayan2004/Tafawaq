"""PII redaction for guardrail audit-log previews ONLY — never applied to live
chat content. Presidio's NER false-positives on math notation (e.g. flags
"f(x" as ORGANIZATION and corrupts it on anonymize, verified during design),
so it must stay scoped to the short, already-flagged text_preview field that
only exists because something tripped a guardrail.
"""
from __future__ import annotations

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None


def _get_analyzer() -> AnalyzerEngine:
    global _analyzer
    if _analyzer is None:
        # Explicit en_core_web_sm config — the no-args default tries to
        # auto-download en_core_web_lg via a `pip` subprocess that doesn't
        # exist in this uv-managed environment (verified during design).
        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        )
        _analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    return _analyzer


def _get_anonymizer() -> AnonymizerEngine:
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def redact(text: str) -> str:
    """Replace detected PII entities (names, emails, phone numbers, etc.) with placeholders."""
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()
    results = analyzer.analyze(text=text, language="en", score_threshold=0.4)
    return anonymizer.anonymize(text=text, analyzer_results=results).text
