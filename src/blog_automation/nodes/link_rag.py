"""Fase 3a — internal linking via RAG su company_sources."""

from __future__ import annotations

import json
import re

from .. import config, llm, rag
from ..state import Article, InternalLink, NodeError, PipelineState


def _extract_concepts(article_md: str) -> list[str]:
    prompt = llm.CONCEPT_EXTRACTION.format(article_md=article_md[:3000])
    raw = llm.generate_text(prompt=prompt, temperature=0.2)
    # Parse JSON list
    m = re.search(r"\[.*?\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return [str(x) for x in data][:5]
    except Exception:
        return []


def _retrieve_candidates(concepts: list[str]) -> list[dict]:
    """Per ogni concetto query RAG, dedup per feature_slug, filtra per soglia."""
    by_slug: dict[str, dict] = {}
    for concept in concepts:
        results = rag.query(concept, top_k=2)
        for r in results:
            if r["similarity"] < config.RAG_SIMILARITY_THRESHOLD:
                continue
            slug = r["metadata"]["feature_slug"]
            if slug not in by_slug or r["similarity"] > by_slug[slug]["similarity"]:
                by_slug[slug] = r
    # Top 5 per similarity (poi LLM ne sceglie max 3)
    return sorted(by_slug.values(), key=lambda r: r["similarity"], reverse=True)[:5]


def _link_one(article: Article) -> Article:
    concepts = _extract_concepts(article.body_md)
    if not concepts:
        print(f"[link_rag] nessun concetto estratto per {article.slug}")
        return article

    candidates = _retrieve_candidates(concepts)
    if not candidates:
        print(f"[link_rag] nessun candidato sopra soglia per {article.slug}")
        return article

    candidates_payload = [
        {
            "feature_name": c["metadata"]["feature_name"],
            "feature_slug": c["metadata"]["feature_slug"],
            "url": c["metadata"]["url"],
            "snippet": c["document"][:200],
            "similarity": round(c["similarity"], 3),
        }
        for c in candidates
    ]

    prompt = llm.LINK_PLACEMENT.format(
        article_md=article.body_md,
        candidates_json=json.dumps(candidates_payload, ensure_ascii=False, indent=2),
        max_links=config.MAX_INTERNAL_LINKS_PER_ARTICLE,
    )
    new_md = llm.generate_text(prompt=prompt, temperature=0.3)
    new_md = re.sub(r"^```(?:markdown|md)?\n|\n```$", "", new_md.strip(), flags=re.MULTILINE).strip()

    # Estrai i link inseriti
    inserted: list[InternalLink] = []
    for c in candidates_payload:
        if c["url"] in new_md:
            # Trova anchor text dal markdown
            m = re.search(r"\[([^\]]+)\]\(" + re.escape(c["url"]) + r"\)", new_md)
            if m:
                inserted.append(InternalLink(
                    anchor=m.group(1), url=c["url"], feature_slug=c["feature_slug"]
                ))

    article.body_md = new_md
    article.internal_links = inserted
    print(f"[link_rag] {article.slug}: inseriti {len(inserted)} link")
    return article


def link_rag_node(state: PipelineState) -> PipelineState:
    # Assicura indice aggiornato
    rag.build_index(force=False)

    linked: list[Article] = []
    errors: list[NodeError] = list(state.get("errors", []))

    for article in state.get("drafts", []):
        try:
            linked.append(_link_one(article))
        except Exception as e:
            errors.append(NodeError(
                node="link_rag", article_slug=article.slug, message=str(e)
            ))
            print(f"[link_rag] error on {article.slug}: {e}")
            linked.append(article)  # passa attraverso anche se fallisce

    return {**state, "linked": linked, "errors": errors}
