"""Wrapper Gemini SDK + prompt templates centralizzati."""

from __future__ import annotations

import threading
import time
from typing import Callable, TypeVar

from google import genai
from google.genai import types

from . import config

config.assert_api_key()
_client = genai.Client(api_key=config.GEMINI_API_KEY)


# ---------- Rate limiting + retry ----------
# Modello primario: gemini-3.1-flash-lite-preview (15 RPM / 500 RPD free tier).
# 5s tra chiamate ⇒ 12 RPM, sotto soglia.
# Su 503/429: 2 retry a 30s e 60s; se esauriti, fallback al modello secondario.

_MIN_INTERVAL_S = 5.0
_RETRY_DELAYS_S = (30, 60)
_last_call_t = 0.0
_call_lock = threading.Lock()

T = TypeVar("T")


def _throttle() -> None:
    global _last_call_t
    with _call_lock:
        elapsed = time.monotonic() - _last_call_t
        if elapsed < _MIN_INTERVAL_S:
            wait = _MIN_INTERVAL_S - elapsed
            print(f"[llm] throttle: sleep {wait:.1f}s")
            time.sleep(wait)
        _last_call_t = time.monotonic()


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc)
    return any(s in msg for s in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))


def _call_with_retry(fn: Callable[[], T]) -> T:
    for attempt in range(len(_RETRY_DELAYS_S) + 1):
        _throttle()
        try:
            return fn()
        except Exception as e:
            if attempt == len(_RETRY_DELAYS_S) or not _is_retryable(e):
                raise
            delay = _RETRY_DELAYS_S[attempt]
            print(f"[llm] {type(e).__name__}: {str(e)[:120]} — retry in {delay}s ({attempt+1}/{len(_RETRY_DELAYS_S)})")
            time.sleep(delay)
    raise RuntimeError("unreachable")


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

Stile per leggibilità (indice Gulpease ≥ 60):
- Frasi brevi: massimo 20 parole per frase; spezza le frasi più lunghe.
- Voce attiva: scrivi "i tassi salgono", non "i tassi vengono aumentati".
- Una idea per frase: evita subordinate annidate (no "che... che... che...").

Output: SOLO markdown valido con front-matter YAML in cima. Nessun testo extra prima/dopo."""

ARTICLE_GENERATION_USER = """Topic: {title}

Sintesi della fonte: {summary}

URL fonte: {url}
Categoria: {category}

Genera un articolo da blog in markdown con front-matter YAML.

Vincoli OBBLIGATORI sul contenuto:
- Body (escluso front-matter): 550-700 parole. Sotto 500 = output rifiutato.
- Esattamente 1 H1 (riga `# Titolo`).
- Almeno 2 sezioni H2 (righe `## ...`).
- Title nel front-matter: 50-60 caratteri.

Vincoli OBBLIGATORI sul formato di output:
- L'output DEVE iniziare ESATTAMENTE con la riga `---` (apertura front-matter).
- NESSUN testo prima del front-matter.
- NESSUN code-fence ``` attorno all'output.
- NESSUN testo dopo l'articolo.
- YAML del front-matter deve essere parsabile: stringhe con `:` o virgolette interne vanno tra apici doppi.

Schema front-matter (riproduci esattamente questi campi):

---
title: "<titolo SEO 50-60 char>"
slug: "<slug-url-friendly>"
date: {date}
category: {category}
meta_description: "<descrizione SEO 140-160 char che include la keyword principale>"
keywords: ["<keyword 1>", "<keyword 2>", "<keyword 3>", "<keyword 4>", "<keyword 5>"]
source_urls:
  - {url}
satispay_angle: "<slug feature Satispay rilevante o 'none'>"
---

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

SEO_REWRITE = """Rivedi questo articolo correggendo SOLO i problemi SEO elencati sotto.
Non modificare nulla che non sia elencato.

Istruzioni per problema:

- "meta_description mancante" o "meta_description length … fuori range":
  → Nel front-matter scrivi/correggi il campo meta_description: testo di 140-160
    caratteri che include la keyword principale "{primary_keyword}".

- "Title length … fuori range":
  → Nel front-matter riscrivi title tra 50 e 60 caratteri mantenendo le keyword.

- "word_count … fuori range":
  → Aggiungi o rimuovi testo dal body fino a rientrare nel range 500-700 parole.

- "Gulpease … sotto soglia 60":
  → Spezza ogni frase più lunga di 20 parole in due frasi più brevi.
  → Converti le costruzioni passive in voce attiva ("viene aumentato" → "sale").
  → Non cambiare heading H1/H2 né i link interni.

- "H1 count" o "H2 count":
  → Aggiungi o rimuovi heading rispettando: esattamente 1 H1, almeno 2 H2.

Problemi da risolvere:
{issues}

Keyword principale: {primary_keyword}
Keyword secondarie: {keywords}

Articolo (front-matter + body):
{article_md}

Restituisci SOLO il markdown aggiornato (front-matter incluso, senza code-fence)."""


# ---------- API helpers ----------

def generate_text(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.8,
) -> str:
    """Genera testo con il modello primario; fallback al secondario se i retry si esauriscono."""
    contents = [prompt]
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
    )

    def _do(model: str) -> Callable[[], str]:
        def _inner() -> str:
            resp = _client.models.generate_content(
                model=model,
                contents=contents,
                config=cfg,
            )
            return resp.text or ""
        return _inner

    try:
        return _call_with_retry(_do(config.GEMINI_GEN_MODEL))
    except Exception as e:
        if not _is_retryable(e) or not config.GEMINI_GEN_MODEL_FALLBACK:
            raise
        print(f"[llm] primary {config.GEMINI_GEN_MODEL} esaurito, fallback → {config.GEMINI_GEN_MODEL_FALLBACK}")
        return _call_with_retry(_do(config.GEMINI_GEN_MODEL_FALLBACK))


def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
) -> list[list[float]]:
    """Genera embeddings per una lista di testi. Ritorna lista di vettori float."""
    cfg = types.EmbedContentConfig(
        task_type=task_type,
        output_dimensionality=config.EMBED_DIM,
    )

    def _do() -> list[list[float]]:
        resp = _client.models.embed_content(
            model=config.GEMINI_EMBED_MODEL,
            contents=texts,
            config=cfg,
        )
        return [list(e.values) for e in resp.embeddings]

    return _call_with_retry(_do)


def embed_query(text: str) -> list[float]:
    """Embedding singolo per query (RAG retrieval)."""
    return embed_texts([text], task_type="RETRIEVAL_QUERY")[0]
