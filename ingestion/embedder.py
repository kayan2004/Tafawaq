"""voyage-large-2 batch embedding of chunks into 1536-d vectors."""
import voyageai


def embed_batch(chunks: list[dict], api_key: str) -> list[dict]:
    """Embed chunk content in batches of 16 using voyage-large-2.

    Populates each chunk's 'embedding' key with a list of 1536 floats.
    """
    client = voyageai.Client(api_key=api_key)
    batch_size = 16
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        result = client.embed(
            [c["content"] for c in batch],
            model="voyage-large-2",
            input_type="document",
        )
        for j, chunk in enumerate(batch):
            chunk["embedding"] = result.embeddings[j]
    return chunks
