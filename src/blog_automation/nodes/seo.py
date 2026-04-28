"""Fase 3b — SEO optimization (heuristic checks + LLM rewrite)."""

from __future__ import annotations

import re

import frontmatter
import textstat
import yake

from .. import config, llm
from ..state import Article, NodeError, PipelineState, SEOReport


def _extract_keywords(text: str, top: int = 5) -> list[str]:
    extractor = yake.KeywordExtractor(lan="it", n=2, top=top)
    keywords = extractor.extract_keywords(text)
    return [kw for kw, _ in keywords]


def _gulpease(text: str) -> float:
    return float(textstat.gulpease_index(text))


def _check_headings(md: str) -> list[str]:
    issues: list[str] = []
    h1_count = len(re.findall(r"^#\s+", md, re.MULTILINE))
    h2_count = len(re.findall(r"^##\s+", md, re.MULTILINE))
    if h1_count != 1:
        issues.append(f"H1 count = {h1_count} (atteso 1)")
    if h2_count < 2:
        issues.append(f"H2 count = {h2_count} (atteso almeno 2)")
    return issues


def _build_report(article: Article, post_meta: dict) -> SEOReport:
    text = article.body_md
    word_count = len(text.split())
    keywords = _extract_keywords(text, top=5)
    primary = keywords[0] if keywords else (article.keywords[0] if article.keywords else "finanza")
    meta_desc = post_meta.get("meta_description") or post_meta.get("seo", {}).get("meta_description") or ""
    title_len = len(article.title)
    gulp = _gulpease(text)

    issues: list[str] = []
    if not (config.TITLE_MIN_LEN <= title_len <= config.TITLE_MAX_LEN):
        issues.append(f"Title length {title_len} fuori range {config.TITLE_MIN_LEN}-{config.TITLE_MAX_LEN}")
    if not meta_desc:
        issues.append("meta_description mancante (140-160 char)")
    elif not (config.META_DESC_MIN_LEN <= len(meta_desc) <= config.META_DESC_MAX_LEN):
        issues.append(f"meta_description length {len(meta_desc)} fuori range")
    if not (config.ARTICLE_MIN_WORDS <= word_count <= config.ARTICLE_MAX_WORDS):
        issues.append(f"word_count {word_count} fuori range {config.ARTICLE_MIN_WORDS}-{config.ARTICLE_MAX_WORDS}")
    if gulp < config.GULPEASE_MIN:
        issues.append(f"Gulpease {gulp:.1f} sotto soglia {config.GULPEASE_MIN}")
    issues.extend(_check_headings(text))

    return SEOReport(
        primary_keyword=primary,
        keywords=keywords,
        meta_description=meta_desc,
        title_len=title_len,
        word_count=word_count,
        gulpease=gulp,
        issues=issues,
        passed=len(issues) == 0,
    )


def _rewrite(article: Article, report: SEOReport) -> str:
    prompt = llm.SEO_REWRITE.format(
        issues="\n".join(f"- {i}" for i in report.issues),
        primary_keyword=report.primary_keyword,
        keywords=", ".join(report.keywords),
        article_md=article.body_md,
    )
    out = llm.generate_text(prompt=prompt, temperature=0.5)
    out = re.sub(r"^```(?:markdown|md)?\n|\n```$", "", out.strip(), flags=re.MULTILINE).strip()
    return out


def _optimize_one(article: Article) -> Article:
    for iteration in range(config.SEO_MAX_ITERATIONS):
        # Parse front-matter dal corpo (potrebbe contenerlo dopo rewrite LLM)
        try:
            post = frontmatter.loads(article.body_md)
            body = post.content.strip() if post.content else article.body_md
            meta = dict(post.metadata)
        except Exception:
            body = article.body_md
            meta = {}

        # Per il check usiamo il body completo (con/senza front-matter è simile)
        report = _build_report(article, meta)
        if report.passed:
            article.seo = report
            print(f"[seo] {article.slug}: passed iter={iteration}")
            return article

        print(f"[seo] {article.slug}: iter {iteration} issues={len(report.issues)}")
        new_md = _rewrite(article, report)
        # Estrai potenziale nuovo title/meta dal nuovo markdown
        try:
            post2 = frontmatter.loads(new_md)
            article.body_md = post2.content.strip() if post2.content else new_md
            if post2.metadata.get("title"):
                article.title = post2.metadata["title"]
        except Exception:
            article.body_md = new_md

    # Cap raggiunto: salva l'ultimo report
    article.seo = _build_report(article, {})
    return article


def seo_node(state: PipelineState) -> PipelineState:
    optimized: list[Article] = []
    errors: list[NodeError] = list(state.get("errors", []))

    for article in state.get("linked", []):
        try:
            optimized.append(_optimize_one(article))
        except Exception as e:
            errors.append(NodeError(
                node="seo", article_slug=article.slug, message=str(e)
            ))
            optimized.append(article)

    return {**state, "seo_optimized": optimized, "errors": errors}
