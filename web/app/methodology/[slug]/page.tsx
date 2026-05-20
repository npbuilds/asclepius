import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  METHODOLOGY_ENTRIES,
  getEntryBySlug,
} from "@/lib/methodology-content";

interface PageProps {
  params: { slug: string };
}

export function generateStaticParams() {
  return METHODOLOGY_ENTRIES.map((e) => ({ slug: e.slug }));
}

export function generateMetadata({ params }: PageProps) {
  const entry = getEntryBySlug(params.slug);
  if (!entry) return { title: "Not found" };
  return {
    title: `${entry.title} — Asclepius methodology`,
    description: entry.summary,
  };
}

export default function MethodologyEntryPage({ params }: PageProps) {
  const entry = getEntryBySlug(params.slug);
  if (!entry) notFound();

  // Strip the first H1 from the body since we render the title separately above.
  const body = entry.body.replace(/^# .+\n+/, "");

  const indexInOrder = METHODOLOGY_ENTRIES.findIndex((e) => e.slug === entry.slug);
  const prev = indexInOrder > 0 ? METHODOLOGY_ENTRIES[indexInOrder - 1] : null;
  const next =
    indexInOrder < METHODOLOGY_ENTRIES.length - 1
      ? METHODOLOGY_ENTRIES[indexInOrder + 1]
      : null;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <nav className="mb-6 font-display text-xs uppercase tracking-wider">
        <Link
          href="/methodology"
          className="text-text-dim hover:text-cyan-bright"
        >
          ← All methodology
        </Link>
      </nav>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_260px]">
        <article>
          <header className="mb-6">
            <div className="font-mono text-[11px] uppercase tracking-wider text-amber-bright">
              {entry.filename}
            </div>
            <h1 className="mt-2 font-display text-2xl font-bold uppercase leading-[1.15] tracking-[0.04em] text-text-bright sm:text-3xl">
              {entry.title}
            </h1>
            {entry.summary ? (
              <p className="mt-3 font-prose text-base text-text-primary">
                {entry.summary}
              </p>
            ) : null}
          </header>

          <div className="prose max-w-none font-prose prose-headings:font-display prose-headings:font-bold prose-headings:uppercase prose-headings:tracking-wider prose-headings:text-text-bright prose-p:text-text-primary prose-strong:text-text-bright prose-li:text-text-primary prose-a:text-cyan-bright prose-a:no-underline hover:prose-a:underline prose-code:rounded prose-code:bg-bg-panel-hover prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-[0.9em] prose-code:text-cyan-bright prose-code:before:content-none prose-code:after:content-none prose-pre:rounded prose-pre:bg-bg-panel-hover prose-pre:text-text-primary prose-blockquote:border-l-cyan-bright prose-blockquote:text-text-primary prose-table:text-sm prose-th:text-text-bright prose-td:text-text-primary prose-hr:border-border-dim">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => {
                  if (href && /^\d{2}-[a-z0-9-]+\.md$/i.test(href)) {
                    const slug = href.replace(/\.md$/, "");
                    return <Link href={`/methodology/${slug}`}>{children}</Link>;
                  }
                  if (href && /^https?:\/\//.test(href)) {
                    return (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    );
                  }
                  return <a href={href}>{children}</a>;
                },
              }}
            >
              {body}
            </ReactMarkdown>
          </div>

          <nav className="mt-10 flex justify-between gap-4 border-t border-border-dim pt-5 text-sm">
            <div>
              {prev ? (
                <Link
                  href={`/methodology/${prev.slug}`}
                  className="block text-text-primary hover:text-cyan-bright"
                >
                  <div className="font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
                    Previous
                  </div>
                  <div className="mt-0.5 font-display text-sm font-semibold uppercase tracking-wider">
                    {prev.title}
                  </div>
                </Link>
              ) : null}
            </div>
            <div className="text-right">
              {next ? (
                <Link
                  href={`/methodology/${next.slug}`}
                  className="block text-text-primary hover:text-cyan-bright"
                >
                  <div className="font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
                    Next
                  </div>
                  <div className="mt-0.5 font-display text-sm font-semibold uppercase tracking-wider">
                    {next.title}
                  </div>
                </Link>
              ) : null}
            </div>
          </nav>
        </article>

        <aside className="space-y-4 lg:sticky lg:top-8 lg:self-start">
          {entry.audience ? (
            <Card label="Read this if">
              <p className="text-sm text-text-primary">{entry.audience}</p>
            </Card>
          ) : null}

          {entry.framework ? (
            <Card label="Framework">
              <p className="text-sm text-text-primary">{entry.framework}</p>
            </Card>
          ) : null}

          {entry.framing ? (
            <Card label="Framing">
              <p className="text-sm text-text-primary">{entry.framing}</p>
            </Card>
          ) : null}

          {entry.primary_sources.length > 0 ? (
            <Card label={`Primary sources (${entry.primary_sources.length})`}>
              <ul className="space-y-2 text-xs text-text-primary">
                {entry.primary_sources.map((src, i) => (
                  <li key={i} className="leading-snug">
                    {src}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {entry.related_implementations.length > 0 ? (
            <Card label="Related implementations">
              <ul className="space-y-2 text-xs text-text-primary">
                {entry.related_implementations.map((src, i) => (
                  <li key={i} className="leading-snug">
                    {src}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </aside>
      </div>
    </div>
  );
}

function Card({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded border border-border-dim bg-bg-panel p-3">
      <div className="mb-1.5 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-dim">
        {label}
      </div>
      {children}
    </div>
  );
}
