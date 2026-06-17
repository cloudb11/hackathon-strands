import chromadb
import hashlib
import re
import os

# Use persistent storage so data survives restarts
CHROMA_DIR = os.path.join(os.path.dirname(__file__), ".chroma_db")
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection("knowledge_base")


def chunk_text(text: str, max_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text using recursive, boundary-aware chunking.

    Strategy (in priority order):
      1. Split on paragraph boundaries (double newline)
      2. Split on sentence boundaries (. ! ?)
      3. Split on word boundaries (space)
      4. Hard character split (last resort)

    This preserves semantic coherence within each chunk.
    """
    # If text fits in a single chunk, return as-is
    if len(text) <= max_size:
        return [text.strip()] if text.strip() else []

    separators = [
        r'\n\n+',         # paragraph breaks
        r'(?<=[.!?])\s+', # sentence endings
        r'\s+',           # word boundaries
    ]

    chunks = _recursive_split(text, separators, max_size)

    # Apply overlap: prepend trailing context from previous chunk
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(prev_tail + chunks[i])
        chunks = overlapped

    return [c.strip() for c in chunks if c.strip()]


def _recursive_split(text: str, separators: list[str], max_size: int) -> list[str]:
    """Recursively split text trying each separator level."""
    if len(text) <= max_size:
        return [text]

    if not separators:
        # Last resort: hard split at max_size
        return [text[i:i + max_size] for i in range(0, len(text), max_size)]

    current_sep = separators[0]
    remaining_seps = separators[1:]

    # Split on current separator
    parts = re.split(current_sep, text)

    chunks = []
    current_chunk = ""

    for part in parts:
        # If adding this part exceeds max_size, finalize current chunk
        if current_chunk and len(current_chunk) + len(part) > max_size:
            chunks.append(current_chunk)
            current_chunk = part
        else:
            current_chunk = (current_chunk + " " + part).strip() if current_chunk else part

    if current_chunk:
        chunks.append(current_chunk)

    # Recursively split any chunk that's still too large using the next separator
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_size:
            final_chunks.extend(_recursive_split(chunk, remaining_seps, max_size))
        else:
            final_chunks.append(chunk)

    return final_chunks


def ingest_text(text: str, metadata: dict = {}) -> int:
    chunks = chunk_text(text)
    # Use source + chunk index for stable, collision-resistant IDs
    source = metadata.get("source", "unknown")
    ids = [hashlib.sha256(f"{source}::{i}::{c[:50]}".encode()).hexdigest() for i, c in enumerate(chunks)]
    metadatas = [{**metadata, "chunk_index": i} for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    return len(chunks)


def retrieve_context(query: str, n: int = 5, max_distance: float = 1.5) -> list[str]:
    """Retrieve relevant chunks, filtering by similarity distance threshold."""
    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["documents", "distances"]
    )
    if not results["documents"] or not results["documents"][0]:
        return []

    # Filter out low-relevance results using distance threshold
    docs = results["documents"][0]
    distances = results["distances"][0] if results.get("distances") else [0] * len(docs)

    return [doc for doc, dist in zip(docs, distances) if dist <= max_distance]

