# Satispay Blog Automation — Case Study

> Pipeline automatizzata che genera 3 articoli FinTech al giorno, ottimizzati SEO con link interni via RAG, e li pubblica tramite GitHub Actions — scalabile a 700 articoli/mese.

---

## Come funziona

```
RSS feeds → scrape → select_topics → generate → link_rag → seo → deploy → git push
             det.       det.          agentic    agentic   agentic  det.
```

Ogni mattina alle 06:00 CET GitHub Actions esegue l'intera pipeline:

1. **Scrape** — parsing di 10 feed RSS (Il Sole 24 Ore, ANSA, Repubblica, Corriere) → `sources/YYYY-MM-DD.json`
2. **Select topics** — filtraggio per keyword FinTech, selezione di 3 topic rilevanti per Satispay
3. **Generate** — Gemini Flash genera articoli 550-700 parole con angolatura brand-aligned e `meta_description` SEO
4. **Link RAG** — ChromaDB indicizza 12 feature Satispay; agente LLM inserisce max 3 link interni rilevanti (cosine > 0.72)
5. **SEO** — check euristico (title, meta desc, Gulpease ≥ 60, word count, headings) + rewrite LLM per-issue, max 3 iterazioni
6. **Deploy** — articoli spostati in `articles/published/`, commit + push automatico

---

## Quick start

```bash
# 1. Clone + dipendenze
uv sync

# 2. Configura le API keys
cp .env.example .env
# → inserisci GEMINI_API_KEY in .env

# 3. Esegui la pipeline
uv run python -m blog_automation               # data odierna
uv run python -m blog_automation 2026-05-01    # data specifica
```

---

## Stack

| Componente | Tecnologia |
|---|---|
| Orchestrazione | `langgraph` |
| LLM (primario) | `gemini-3.1-flash-lite-preview` (fallback: `gemini-3-flash-preview`) |
| Embeddings | `gemini-embedding-001`, dim 768 |
| Vector store | `chromadb` locale, cosine distance |
| RSS parsing | `feedparser` + `trafilatura` |
| SEO | `yake` (keyword extraction), `textstat` (Gulpease) |
| Schema / validazione | `pydantic` v2 |
| Package manager | `uv` |
| CI/CD | GitHub Actions |
| Landing page | Next.js + Vercel |

---

## Struttura del progetto

```
src/blog_automation/
├── main.py              # entrypoint
├── graph.py             # definizione grafo LangGraph
├── state.py             # BlogState (TypedDict + Pydantic models)
├── config.py            # RSS_FEEDS, soglie SEO/RAG, paths
├── llm.py               # prompt centralizzati + chiamate Gemini
├── rag.py               # ChromaDB build / query
└── nodes/
    ├── scrape.py        # fetch + parsing RSS
    ├── select_topics.py # filtro FinTech, topic selection
    ├── generate.py      # article generation LLM
    ├── link_rag.py      # internal linking via RAG
    ├── seo.py           # SEO heuristics + LLM rewrite
    └── deploy.py        # git commit + push
```

Output generato a runtime:

```
sources/            YYYY-MM-DD.json        fonti RSS raccolte
articles/draft/     YYYY-MM-DD-slug.md     bozze pre-refinement
articles/published/ YYYY-MM-DD-slug.md     articoli finali
chroma_db/                                 vector store (rebuild automatico se company_sources/ cambia)
```

---

## Scheduling

GitHub Actions cron `0 4 * * *` (06:00 CET) — vedi [`.github/workflows/daily-pipeline.yml`](.github/workflows/daily-pipeline.yml).

Trigger manuale disponibile via `workflow_dispatch`.

---

## Fasi future (non implementate)

**Fase 5 — Validation & Feedback**
- LLM-as-judge: factual accuracy, brand safety, anti-ripetizione via embedding similarity su articoli storici
- Widget feedback utente (thumbs/stars) → score persistito su DB

**Fase 6 — Optimization Loop ML**
- Feature engineering su articoli + score utenti
- LightGBM regressor predice expected score → orienta selezione topic
- A/B testing 80/20 per evitare bias da feedback loop

-..