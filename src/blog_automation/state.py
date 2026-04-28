"""Pydantic models e LangGraph PipelineState."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel, Field, HttpUrl


class ScrapedItem(BaseModel):
    title: str
    summary: str
    url: HttpUrl
    published_at: datetime
    source: str


class Topic(BaseModel):
    title: str
    summary: str
    url: HttpUrl
    source: str
    category: str  # "risparmio" | "investimento" | "attualita" | "altro"


class InternalLink(BaseModel):
    anchor: str
    url: str
    feature_slug: str


class SEOReport(BaseModel):
    primary_keyword: str
    keywords: list[str]
    meta_description: str
    title_len: int
    word_count: int
    gulpease: float
    issues: list[str] = Field(default_factory=list)
    passed: bool = False


class Article(BaseModel):
    title: str
    slug: str
    category: str
    body_md: str  # markdown del corpo (senza front-matter)
    keywords: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    satispay_angle: str | None = None
    internal_links: list[InternalLink] = Field(default_factory=list)
    seo: SEOReport | None = None


class NodeError(BaseModel):
    node: str
    article_slug: str | None = None
    message: str


class PipelineState(TypedDict, total=False):
    """Stato condiviso tra i nodi LangGraph. Total=False perché ogni nodo
    aggiunge progressivamente i suoi output."""

    run_date: str  # "2026-04-28"
    raw_sources: list[ScrapedItem]
    selected_topics: list[Topic]
    drafts: list[Article]
    linked: list[Article]
    seo_optimized: list[Article]
    published: list[str]
    errors: list[NodeError]
