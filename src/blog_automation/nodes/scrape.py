"""Fase 1 — scraping di feed RSS FinTech italiani."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import feedparser
import trafilatura

from .. import config
from ..state import PipelineState, ScrapedItem


def _is_recent(entry, hours: int = 36) -> bool:
    """Filtra entries pubblicate ultime N ore."""
    pub = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if pub is None:
        return True  # se non c'è data, includi
    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
    return pub_dt > datetime.now(timezone.utc) - timedelta(hours=hours)


def _entry_to_item(entry, source: str) -> ScrapedItem | None:
    title = getattr(entry, "title", "").strip()
    url = getattr(entry, "link", "").strip()
    if not title or not url:
        return None

    summary = getattr(entry, "summary", "").strip()
    # Strip HTML semplice
    if "<" in summary:
        extracted = trafilatura.extract(summary) or summary
        summary = extracted.strip()

    if len(summary) < 80:
        # Fallback: scarica e estrai testo dalla pagina
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                full = trafilatura.extract(downloaded) or ""
                if full:
                    summary = full[:500]
        except Exception as e:
            print(f"[scrape] fetch failed for {url}: {e}")

    pub = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)

    try:
        return ScrapedItem(
            title=title,
            summary=summary or title,
            url=url,
            published_at=pub_dt,
            source=source,
        )
    except Exception as e:
        print(f"[scrape] invalid entry {url}: {e}")
        return None


def _dedupe(items: list[ScrapedItem]) -> list[ScrapedItem]:
    """Deduplica per URL e per similarità titolo (> 0.85)."""
    seen_urls: set[str] = set()
    out: list[ScrapedItem] = []
    for it in items:
        url = str(it.url)
        if url in seen_urls:
            continue
        is_dup = any(SequenceMatcher(None, it.title, o.title).ratio() > 0.85 for o in out)
        if is_dup:
            continue
        seen_urls.add(url)
        out.append(it)
    return out


def scrape_node(state: PipelineState) -> PipelineState:
    """Nodo LangGraph: scrape RSS feeds → ScrapedItem list."""
    print(f"[scrape] avvio per data {state['run_date']}")
    all_items: list[ScrapedItem] = []
    feeds_failed = 0

    for source_name, url in config.RSS_FEEDS:
        try:
            print(f"[scrape] feed: {source_name}")
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                if not _is_recent(entry):
                    continue
                item = _entry_to_item(entry, source_name)
                if item is not None:
                    all_items.append(item)
        except Exception as e:
            print(f"[scrape] feed FAILED {source_name}: {e}")
            feeds_failed += 1

    if feeds_failed == len(config.RSS_FEEDS):
        raise RuntimeError("Tutti i feed RSS sono falliti.")

    deduped = _dedupe(all_items)
    print(f"[scrape] totale: {len(all_items)} → dedup: {len(deduped)}")

    # Salva snapshot JSON
    config.SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    out_file = config.SOURCES_DIR / f"{state['run_date']}.json"
    out_file.write_text(
        json.dumps([it.model_dump(mode="json") for it in deduped], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[scrape] salvato: {out_file}")

    return {**state, "raw_sources": deduped}
