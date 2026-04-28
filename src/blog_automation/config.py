"""Configurazione centrale: paths, env vars, costanti, RSS feeds."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPANY_SOURCES_DIR = PROJECT_ROOT / "company_sources"
SOURCES_DIR = PROJECT_ROOT / "sources"
ARTICLES_DRAFT_DIR = PROJECT_ROOT / "articles" / "draft"
ARTICLES_PUBLISHED_DIR = PROJECT_ROOT / "articles" / "published"
CHROMA_DIR = PROJECT_ROOT / "chroma_db"

# API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_GEN_MODEL = "gemini-2.5-flash"
GEMINI_EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

# Pipeline
ARTICLES_PER_DAY = 3
RSS_FEEDS = [
    ("Il Sole 24 Ore - Finanza", "https://www.ilsole24ore.com/rss/finanza--mercati.xml"),
    ("ANSA Economia", "https://www.ansa.it/sito/notizie/economia/economia_rss.xml"),
    ("Repubblica Economia", "https://www.repubblica.it/rss/economia/rss2.0.xml"),
    ("Corriere Economia", "https://xml2.corriereobjects.it/rss/economia.xml"),
]

# Filtri topic FinTech rilevanti
FINTECH_KEYWORDS = [
    "risparmio", "investimento", "investimenti", "fintech", "pagamenti",
    "banca", "banche", "conto", "deposito", "carta", "carte",
    "inflazione", "tassi", "bce", "borsa", "mutuo", "prestito",
]

# RAG
RAG_TOP_K = 3
RAG_SIMILARITY_THRESHOLD = 0.72
MAX_INTERNAL_LINKS_PER_ARTICLE = 3
CHUNK_SIZE = 500  # chars
CHUNK_OVERLAP = 50

# SEO
TITLE_MIN_LEN = 50
TITLE_MAX_LEN = 60
META_DESC_MIN_LEN = 140
META_DESC_MAX_LEN = 160
ARTICLE_MIN_WORDS = 500
ARTICLE_MAX_WORDS = 1200
GULPEASE_MIN = 60
SEO_MAX_ITERATIONS = 3


def assert_api_key() -> None:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY non impostata. Crea un file .env oppure esporta la variabile."
        )
