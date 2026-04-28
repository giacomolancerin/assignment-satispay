# Satispay Blog Automation — Case Study

Pipeline automatizzata in Python + LangGraph che genera 3 articoli FinTech al giorno,
ottimizzati SEO con link interni RAG, e li pubblica via git push.

## Quick start

```bash
# 1. Clone + setup
uv sync

# 2. Configura API key
cp .env.example .env
# edita .env e metti la tua GEMINI_API_KEY

# 3. Esegui la pipeline
uv run python -m blog_automation
```

Output:
- `sources/YYYY-MM-DD.json` — fonti raccolte
- `articles/draft/` — bozze pre-refinement
- `articles/published/` — articoli finali pubblicati
- `chroma_db/` — vector store RAG (rebuild on demand)

## Documenti

- [PROGETTO.md](PROGETTO.md) — overview funzionale e fasi
- [SPECIFICHE-TECNICHE.md](SPECIFICHE-TECNICHE.md) — architettura tecnica
- [docs/superpowers/specs/2026-04-28-satispay-blog-automation-design.md](docs/superpowers/specs/2026-04-28-satispay-blog-automation-design.md) — design doc completo

## Schedulato

GitHub Actions cron `0 4 * * *` (06:00 CET): vedi `.github/workflows/daily-pipeline.yml`.
