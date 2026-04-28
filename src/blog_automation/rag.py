"""ChromaDB indexer + retriever per le fonti aziendali Satispay."""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb
import frontmatter

from . import config, llm

COLLECTION_NAME = "company_sources"


def _chunk_text(text: str, size: int = config.CHUNK_SIZE, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Split testo in chunk di char con overlap."""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _sources_hash() -> str:
    """Hash di tutto il contenuto di company_sources/ — usato per detect changes."""
    h = hashlib.sha256()
    for f in sorted(config.COMPANY_SOURCES_DIR.glob("*.md")):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def _get_client() -> chromadb.PersistentClient:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def build_index(force: bool = False) -> None:
    """Costruisce l'indice ChromaDB da company_sources/. Skip se già aggiornato."""
    client = _get_client()
    current_hash = _sources_hash()

    # Check fingerprint per evitare rebuild inutili
    try:
        existing = client.get_collection(COLLECTION_NAME)
        meta = existing.metadata or {}
        if not force and meta.get("sources_hash") == current_hash:
            print(f"[RAG] Indice già aggiornato (hash={current_hash[:8]}). Skip rebuild.")
            return
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"sources_hash": current_hash, "hnsw:space": "cosine"},
    )

    docs: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for f in sorted(config.COMPANY_SOURCES_DIR.glob("*.md")):
        post = frontmatter.load(f)
        feature = post.get("feature", f.stem)
        url = post.get("url", "")
        slug = post.get("slug", f.stem)
        body = post.content

        for i, chunk in enumerate(_chunk_text(body)):
            docs.append(chunk)
            metadatas.append({"feature_slug": slug, "feature_name": feature, "url": url})
            ids.append(f"{slug}-{i}")

    print(f"[RAG] Embedding di {len(docs)} chunks...")
    vectors = llm.embed_texts(docs, task_type="RETRIEVAL_DOCUMENT")

    collection.add(documents=docs, embeddings=vectors, metadatas=metadatas, ids=ids)
    print(f"[RAG] Indice creato: {len(docs)} chunks, hash={current_hash[:8]}")


def query(text: str, top_k: int = config.RAG_TOP_K) -> list[dict]:
    """Query l'indice per testo. Ritorna lista di {document, metadata, distance}."""
    client = _get_client()
    collection = client.get_collection(COLLECTION_NAME)

    qvec = llm.embed_query(text)
    res = collection.query(query_embeddings=[qvec], n_results=top_k)

    out = []
    docs_list = res.get("documents", [[]])[0]
    metas_list = res.get("metadatas", [[]])[0]
    dists_list = res.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs_list, metas_list, dists_list):
        # ChromaDB con cosine ritorna distance = 1 - similarity
        similarity = 1.0 - dist
        out.append({"document": doc, "metadata": meta, "similarity": similarity})
    return out
