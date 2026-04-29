import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';
import { marked } from 'marked';
import Head from 'next/head';
import Link from 'next/link';

export async function getStaticPaths() {
  const sourcesDir = path.join(process.cwd(), '..', 'company_sources');
  const files = fs
    .readdirSync(sourcesDir)
    .filter((f) => f.endsWith('.md') && f !== '.gitkeep');

  return {
    paths: files.map((f) => ({ params: { slug: f.replace('.md', '') } })),
    fallback: false,
  };
}

export async function getStaticProps({ params }) {
  const sourcesDir = path.join(process.cwd(), '..', 'company_sources');
  const raw = fs.readFileSync(path.join(sourcesDir, `${params.slug}.md`), 'utf8');
  const { data, content } = matter(raw);

  // keywords may be a JSON string in YAML or already an array
  let keywords = data.keywords || [];
  if (typeof keywords === 'string') {
    try {
      keywords = JSON.parse(keywords);
    } catch {
      keywords = [keywords];
    }
  }

  return {
    props: {
      feature: data.feature || '',
      slug: params.slug,
      url: data.url || '',
      keywords,
      bodyHtml: marked.parse(content),
    },
  };
}

export default function FeaturePage({ feature, keywords, bodyHtml }) {
  return (
    <>
      <Head>
        <title>{feature} — Satispay</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content={`Scopri ${feature} su Satispay.`} />
      </Head>

      <header className="header">
        <div className="header-inner">
          <Link href="/" className="logo" aria-label="Satispay home">
            <img src="/01_symbol.png" alt="" className="logo-symbol" aria-hidden="true" />
            <img src="/02_wordmark.png" alt="satispay" className="logo-wordmark" />
          </Link>
          <Link href="/" className="nav-link">
            ← Blog
          </Link>
        </div>
      </header>

      <main className="feature-main">
        <div className="feature-inner">
          <Link href="/" className="back-btn">
            ← Torna al blog
          </Link>

          <header className="feature-header">
            <span className="feature-eyebrow">Feature Satispay</span>
            <h1 className="feature-title">{feature}</h1>
            <div className="feature-tags">
              {keywords.map((kw) => (
                <span key={kw} className="tag">
                  {kw}
                </span>
              ))}
            </div>
          </header>

          <div
            className="feature-body"
            dangerouslySetInnerHTML={{ __html: bodyHtml }}
          />

          <div className="feature-footer">
            <Link href="/" className="feature-back-link">
              ← Torna al blog
            </Link>
          </div>
        </div>
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
    </>
  );
}
