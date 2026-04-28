"""Fase 2 — generazione articoli con Gemini Flash."""

from __future__ import annotations

import re

import frontmatter
from slugify import slugify

from .. import config, llm
from ..state import Article, NodeError, PipelineState, Topic


def _extract_markdown(text: str) -> str:
    """Strip eventuali fence ```markdown ... ``` se Gemini li aggiunge."""
    text = text.strip()
    m = re.match(r"^```(?:markdown|md)?\n(.*?)\n```$", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _parse_article(md_text: str, topic: Topic, run_date: str) -> Article | None:
    """Parsa il markdown generato in Article. None se invalido."""
    try:
        post = frontmatter.loads(md_text)
    except Exception as e:
        print(f"[generate] front-matter parse failed: {e}")
        return None

    fm = post.metadata
    body = post.content.strip()
    word_count = len(body.split())

    if word_count < config.ARTICLE_MIN_WORDS:
        print(f"[generate] articolo troppo corto: {word_count} parole")
        return None

    title = fm.get("title", "").strip()
    if not title:
        return None

    slug = fm.get("slug") or slugify(title)
    keywords = fm.get("keywords") or []
    angle = fm.get("satispay_angle")
    if angle == "none":
        angle = None

    return Article(
        title=title,
        slug=slug,
        category=fm.get("category", topic.category),
        body_md=body,
        keywords=keywords,
        source_urls=[str(topic.url)],
        satispay_angle=angle,
    )


def _generate_one(topic: Topic, run_date: str) -> Article | None:
    user = llm.ARTICLE_GENERATION_USER.format(
        title=topic.title,
        summary=topic.summary,
        url=topic.url,
        category=topic.category,
        date=run_date,
    )
    text = llm.generate_text(prompt=user, system=llm.ARTICLE_GENERATION_SYSTEM, temperature=0.85)
    md = _extract_markdown(text)

    article = _parse_article(md, topic, run_date)
    if article is None:
        # 1 retry
        print("[generate] retry...")
        text2 = llm.generate_text(prompt=user, system=llm.ARTICLE_GENERATION_SYSTEM, temperature=0.85)
        article = _parse_article(_extract_markdown(text2), topic, run_date)

    return article


def _save_draft(article: Article, run_date: str) -> None:
    """Persisti il draft come .md per ispezione manuale."""
    config.ARTICLES_DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.ARTICLES_DRAFT_DIR / f"{run_date}-{article.slug}.md"
    post = frontmatter.Post(
        article.body_md,
        title=article.title,
        slug=article.slug,
        date=run_date,
        category=article.category,
        keywords=article.keywords,
        source_urls=article.source_urls,
        satispay_angle=article.satispay_angle or "none",
    )
    path.write_bytes(frontmatter.dumps(post).encode("utf-8"))


def generate_node(state: PipelineState) -> PipelineState:
    drafts: list[Article] = []
    errors: list[NodeError] = list(state.get("errors", []))

    for topic in state.get("selected_topics", []):
        print(f"[generate] topic: {topic.title}")
        try:
            article = _generate_one(topic, state["run_date"])
            if article is None:
                errors.append(NodeError(node="generate", message=f"failed to generate for: {topic.title}"))
                continue
            _save_draft(article, state["run_date"])
            drafts.append(article)
            print(f"[generate] OK: {article.slug}")
        except Exception as e:
            errors.append(NodeError(node="generate", message=f"{topic.title}: {e}"))
            print(f"[generate] error: {e}")

    return {**state, "drafts": drafts, "errors": errors}
