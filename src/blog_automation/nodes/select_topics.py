"""Selezione deterministica dei top N topic FinTech-relevant."""

from __future__ import annotations

from datetime import datetime, timezone

from .. import config
from ..state import PipelineState, ScrapedItem, Topic

CATEGORY_KEYWORDS = {
    "risparmio": ["risparmio", "deposito", "salvadanaio", "conto"],
    "investimento": ["investimento", "investimenti", "borsa", "etf", "azioni", "btp", "mutuo"],
    "attualita": ["bce", "tassi", "inflazione", "manovra"],
}


def _categorize(text: str) -> str:
    text_lower = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in text_lower for k in kws):
            return cat
    return "altro"


def _is_fintech_relevant(item: ScrapedItem) -> bool:
    text = f"{item.title} {item.summary}".lower()
    return any(k in text for k in config.FINTECH_KEYWORDS)


def select_topics_node(state: PipelineState) -> PipelineState:
    """Filtra fonti per FinTech relevance + categorizza + seleziona top N."""
    items = state.get("raw_sources", [])
    relevant = [it for it in items if _is_fintech_relevant(it)]
    print(f"[select_topics] rilevanti: {len(relevant)}/{len(items)}")

    # Score: recency (decay lineare ultime 36h) + diversità categoria
    now = datetime.now(timezone.utc)

    def score(item: ScrapedItem) -> float:
        hours = (now - item.published_at).total_seconds() / 3600
        recency = max(0.0, 1.0 - hours / 36)
        return recency

    sorted_items = sorted(relevant, key=score, reverse=True)

    # Picking: prova a prendere uno per categoria, fallback a top score
    chosen: list[Topic] = []
    seen_cats: set[str] = set()

    for it in sorted_items:
        if len(chosen) >= config.ARTICLES_PER_DAY:
            break
        cat = _categorize(f"{it.title} {it.summary}")
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        chosen.append(Topic(
            title=it.title, summary=it.summary, url=it.url,
            source=it.source, category=cat,
        ))

    # Riempi slot rimanenti con top score (anche se categoria duplicata)
    if len(chosen) < config.ARTICLES_PER_DAY:
        chosen_urls = {str(t.url) for t in chosen}
        for it in sorted_items:
            if len(chosen) >= config.ARTICLES_PER_DAY:
                break
            if str(it.url) in chosen_urls:
                continue
            cat = _categorize(f"{it.title} {it.summary}")
            chosen.append(Topic(
                title=it.title, summary=it.summary, url=it.url,
                source=it.source, category=cat,
            ))

    print(f"[select_topics] selezionati: {len(chosen)}")
    for t in chosen:
        print(f"  [{t.category}] {t.title}")

    return {**state, "selected_topics": chosen}
