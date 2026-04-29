import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { marked } from 'marked';
import { useState, useEffect } from 'react';
import Head from 'next/head';

function cleanBody(content) {
  // Strip secondary --- ... --- blocks at start (SEO rewrite artifact)
  return content.replace(/^\s*---[\s\S]*?---\s*/, '').trim();
}

function rewriteFeatureLinks(html) {
  // Rewrite satispay.com/it/SLUG/ links to local /features/SLUG
  return html.replace(
    /href="https?:\/\/www\.satispay\.com\/it(?:-it)?\/([^/"]+)\/?"/g,
    'href="/features/$1"'
  );
}

export async function getStaticProps() {
  const publishedDir = path.join(process.cwd(), '..', 'articles', 'published');

  let articles = [];
  try {
    const files = fs
      .readdirSync(publishedDir)
      .filter((f) => f.endsWith('.md') && f !== '.gitkeep');

    articles = files.map((filename) => {
      const raw = fs.readFileSync(path.join(publishedDir, filename), 'utf8');
      const { data, content } = matter(raw);
      const body = cleanBody(content);
      const bodyHtml = rewriteFeatureLinks(marked.parse(body));

      const excerpt =
        body
          .replace(/#{1,6}\s.+\n?/g, '')
          .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
          .replace(/\n+/g, ' ')
          .trim()
          .slice(0, 220) + '…';

      return {
        slug: data.slug || filename.replace('.md', ''),
        title: data.title || '',
        date: String(data.date || ''),
        category: data.category || '',
        keywords: data.keywords || [],
        internal_links: data.internal_links || [],
        bodyHtml,
        excerpt,
      };
    });

    articles.sort((a, b) => new Date(b.date) - new Date(a.date));
  } catch (e) {
    console.error('Could not read articles:', e.message);
  }

  return { props: { articles } };
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('it-IT', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function categoryLabel(cat) {
  const map = {
    investimento: 'Investimento',
    attualita: 'Attualità',
    risparmio: 'Risparmio',
  };
  return map[cat] || cat;
}

function RatingWidget() {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);

  return (
    <div className="rating">
      <p className="rating-label">Ti è stato utile questo articolo?</p>
      <div className="rating-dots">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            className={`dot ${n <= (hovered || rating) ? 'dot--active' : ''}`}
            onClick={() => setRating(n)}
            onMouseEnter={() => setHovered(n)}
            onMouseLeave={() => setHovered(0)}
            aria-label={`Voto ${n}`}
          />
        ))}
      </div>
      {rating > 0 && (
        <p className="rating-thanks">
          Grazie! Hai votato {rating} su 5.
        </p>
      )}
    </div>
  );
}

export default function Blog({ articles }) {
  const [selectedSlug, setSelectedSlug] = useState(null);

  const article = articles.find((a) => a.slug === selectedSlug) || null;

  // Lock body scroll when modal is open
  useEffect(() => {
    if (article) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [article]);

  // Close modal on Escape
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setSelectedSlug(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <Head>
        <title>Blog — Satispay</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta
          name="description"
          content="Notizie e approfondimenti FinTech per gestire meglio i tuoi soldi con Satispay."
        />
      </Head>

      <header className="header">
        <div className="header-inner">
          <a href="/" className="logo" aria-label="Satispay home">
            <img src="/01_symbol.png" alt="" className="logo-symbol" aria-hidden="true" />
            <img src="/02_wordmark.png" alt="satispay" className="logo-wordmark" />
          </a>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-inner">
            <span className="hero-eyebrow">Blog</span>
            <h1 className="hero-title">FinTech per tutti</h1>
            <p className="hero-sub">
              Notizie, analisi e consigli per gestire i tuoi soldi nel mondo digitale.
            </p>
          </div>
        </section>

        <section className="grid-section">
          <div className="articles-grid">
            {articles.length === 0 && (
              <p className="empty-state">Nessun articolo disponibile al momento.</p>
            )}
            {articles.map((art) => (
              <article
                key={art.slug}
                className="card"
                onClick={() => setSelectedSlug(art.slug)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedSlug(art.slug)}
                aria-label={`Leggi: ${art.title}`}
              >
                <div className="card-top">
                  <span className="card-category">{categoryLabel(art.category)}</span>
                  <time className="card-date">{formatDate(art.date)}</time>
                </div>
                <h2 className="card-title">{art.title}</h2>
                <p className="card-excerpt">{art.excerpt}</p>
                <div className="card-footer">
                  <div className="card-keywords">
                    {art.keywords.slice(0, 3).map((kw) => (
                      <span key={kw} className="tag">
                        {kw}
                      </span>
                    ))}
                  </div>
                  <span className="card-cta" aria-hidden="true">
                    Leggi →
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-logo">
            <img src="/01_symbol.png" alt="" className="logo-symbol logo-symbol--sm" aria-hidden="true" />
            <img src="/02_wordmark.png" alt="satispay" className="logo-wordmark logo-wordmark--sm" />
          </div>
          <p className="footer-copy">
            © {new Date().getFullYear()} Satispay S.p.A. — Contenuti generati automaticamente a
            scopo dimostrativo.
          </p>
        </div>
      </footer>

      {article && (
        <div
          className="overlay"
          onClick={(e) => e.target === e.currentTarget && setSelectedSlug(null)}
          role="dialog"
          aria-modal="true"
          aria-label={article.title}
        >
          <div className="modal">
            <button
              className="modal-close"
              onClick={() => setSelectedSlug(null)}
              aria-label="Chiudi"
            >
              ×
            </button>

            <div className="modal-scroll">
              <div className="modal-meta">
                <span className="modal-category">{categoryLabel(article.category)}</span>
                <time className="modal-date">{formatDate(article.date)}</time>
              </div>

              <h1 className="modal-title">{article.title}</h1>

              <div
                className="modal-body"
                dangerouslySetInnerHTML={{ __html: article.bodyHtml }}
              />

              <div className="modal-tags">
                {article.keywords.map((kw) => (
                  <span key={kw} className="tag">
                    {kw}
                  </span>
                ))}
              </div>

              <RatingWidget />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
