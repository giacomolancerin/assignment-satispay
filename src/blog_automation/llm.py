"""Wrapper Gemini SDK + prompt templates centralizzati."""

from __future__ import annotations

from google import genai
from google.genai import types

from . import config

config.assert_api_key()
_client = genai.Client(api_key=config.GEMINI_API_KEY)


# ---------- Prompts ----------

ARTICLE_GENERATION_SYSTEM = """Sei un redattore esperto di finanza personale e FinTech per un magazine italiano.
Scrivi articoli divulgativi in italiano per un pubblico di 25-45 anni con conoscenze finanziarie di base.

Regole di stile:
- Tono chiaro, diretto, senza gergo eccessivo
- Esempi concreti (es. "se hai 5.000€ fermi sul conto...")
- Struttura: H1 (titolo), introduzione 2-3 paragrafi, 2-4 sezioni H2, conclusione
- Lunghezza: 500-700 parole
- NIENTE frasi tipo "in questo articolo esploreremo" — vai dritto al punto
- NIENTE pubblicità diretta a Satispay; l'angolatura è naturale ("una carta digitale", "un'app di pagamenti")

Output: SOLO markdown valido con front-matter YAML in cima. Nessun testo extra prima/dopo."""

ARTICLE_GENERATION_USER = """Topic: {title}

Sintesi della fonte: {summary}

URL fonte: {url}
Categoria: {category}

Genera un articolo da blog (500-700 parole) in markdown con front-matter:

```yaml
---
title: "<titolo SEO 50-60 char>"
slug: "<slug-url-friendly>"
date: {date}
category: {category}
keywords: ["<5 keyword>"]
source_urls:
  - {url}
satispay_angle: "<slug feature Satispay rilevante o 'none'>"
---
```

Possibili `satispay_angle`: pagamenti-tra-amici, salvadanaio, risparmio-smart,
pagamenti-in-negozio, cashback, bollette-pagamenti, ricarica-telefonica,
buoni-regalo, donazioni, bonifici-sepa, carta-satispay, pagamenti-ricorrenti, none."""

CONCEPT_EXTRACTION = """Dato l'articolo seguente, elenca i 3-5 CONCETTI CHIAVE che potrebbero
collegarsi a feature di prodotto FinTech (risparmio, pagamenti, carte, investimenti, etc).
Restituisci SOLO una lista JSON di stringhe brevi.

Esempio output: ["risparmio automatico", "pagamenti contactless", "carta di debito digitale"]

Articolo:
{article_md}"""

LINK_PLACEMENT = """Hai questo articolo markdown:

{article_md}

E questa lista di link interni candidati:
{candidates_json}

Inserisci AL MASSIMO {max_links} link nei punti più naturali del testo.
Regole:
- Il link va su una frase rilevante (no a inizio/fine paragrafo)
- Anchor text = frase corta (2-5 parole) già presente nel testo, scelta per essere semanticamente legata alla feature
- Formato markdown: [anchor](url)
- NON cambiare nient'altro del contenuto

Restituisci SOLO il markdown completo aggiornato (front-matter incluso)."""

SEO_REWRITE = """Rivedi questo articolo per fixare i seguenti problemi SEO senza perdere naturalezza.

Problemi:
{issues}

Keyword principale: {primary_keyword}
Keyword secondarie: {keywords}

Articolo originale:
{article_md}

Restituisci SOLO il markdown completo aggiornato (front-matter incluso).
Se serve, aggiungi/aggiorna `meta_description` nel front-matter (140-160 char)."""


# ---------- API helpers ----------

def generate_text(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.8,
) -> str:
    """Genera testo con Gemini Flash. Ritorna la stringa di output."""
    contents = [prompt]
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
    )
    resp = _client.models.generate_content(
        model=config.GEMINI_GEN_MODEL,
        contents=contents,
        config=cfg,
    )
    return resp.text or ""


def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Genera embeddings per una lista di testi. Ritorna lista di vettori float."""
    cfg = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=config.EMBED_DIM,
    )
    resp = _client.models.embed_content(
        model=config.GEMINI_EMBED_MODEL,
        contents=texts,
        config=cfg,
    )
    return [list(e.values) for e in resp.embeddings]


def embed_query(text: str) -> list[float]:
    """Embedding singolo per query (RAG retrieval)."""
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]
