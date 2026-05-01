"""Fase 4 — sposta articoli in published/ e prepara summary per il workflow."""

from __future__ import annotations

import frontmatter

from .. import config
from ..state import Article, NodeError, PipelineState


def _serialize(article: Article, run_date: str) -> str:
    """Serializza un Article in markdown con front-matter completo."""
    seo_dict = article.seo.model_dump() if article.seo else {}
    metadata = {
        "title": article.title,
        "slug": article.slug,
        "date": run_date,
        "category": article.category,
        "meta_description": article.meta_description,
        "keywords": article.keywords,
        "source_urls": article.source_urls,
        "satispay_angle": article.satispay_angle or "none",
        "internal_links": [l.model_dump() for l in article.internal_links],
        "seo": seo_dict,
    }
    post = frontmatter.Post(article.body_md, **metadata)
    return frontmatter.dumps(post)


def deploy_node(state: PipelineState) -> PipelineState:
    config.ARTICLES_PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    published: list[str] = []
    errors: list[NodeError] = list(state.get("errors", []))

    for article in state.get("seo_optimized", []):
        try:
            path = config.ARTICLES_PUBLISHED_DIR / f"{state['run_date']}-{article.slug}.md"
            path.write_text(_serialize(article, state["run_date"]), encoding="utf-8")
            published.append(str(path.relative_to(config.PROJECT_ROOT)))
            print(f"[deploy] published: {path.name}")
        except Exception as e:
            errors.append(NodeError(
                node="deploy", article_slug=article.slug, message=str(e)
            ))

    # Summary per il workflow GH Actions (commit message)
    summary_path = config.PROJECT_ROOT / "published_summary.txt"
    titles = [a.title for a in state.get("seo_optimized", [])]
    summary_lines = [f"Daily run: {state['run_date']}", ""] + [f"- {t}" for t in titles]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return {**state, "published": published, "errors": errors}
