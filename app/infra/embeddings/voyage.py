"""Voyage AI embedding adapter.

embed_text  — query-mode embedding for retrieval (single string → 1536-d vector)
embed_batch — document-mode embedding for ingestion (list of strings)

Wraps voyageai.APIError in domain EmbeddingServiceUnavailable so higher
layers stay decoupled from the vendor SDK.
"""
from __future__ import annotations

import voyageai

from app.domain.exceptions import EmbeddingServiceUnavailable

_MODEL = "voyage-large-2"


def embed_text(text: str, api_key: str) -> list[float]:
    try:
        client = voyageai.Client(api_key=api_key)
        result = client.embed([text], model=_MODEL, input_type="query")
        return result.embeddings[0]
    except voyageai.error.APIError as exc:
        raise EmbeddingServiceUnavailable(str(exc)) from exc


def embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    try:
        client = voyageai.Client(api_key=api_key)
        result = client.embed(texts, model=_MODEL, input_type="document")
        return result.embeddings
    except voyageai.error.APIError as exc:
        raise EmbeddingServiceUnavailable(str(exc)) from exc
