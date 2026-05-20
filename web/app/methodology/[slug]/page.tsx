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
    <div className="mx-auto max-w-6xl px-6 py-12">
      <nav className="mb-8 text-sm">
        <Link
          href="/methodology"
          className="text-ink-400 hover:text-accent-700"
        >
          ← All methodology
        </Link>
      </nav>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[1fr_280px]">
        <article>
          <header className="mb-8">
            <div className="text-xs uppercase tracking-wider text-accent-700">
              {entry.filename}
            </div>
            <h1 className="mt-1 font-serif text-3xl text-ink-900 sm:text-4xl">
              {entry.title}
            </h1>
            {entry.summary ? (
              <p className="mt-4 text-lg text-ink-600">{entry.summary}</p>
            ) : null}
          </header>

          <div className="prose prose-ink max-w-none prose-headings:font-serif prose-headings:text-ink-900 prose-a:text-accent-700 prose-a:no-underline hover:prose-a:underline prose-code:bg-ink-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-[0.9em] prose-pre:bg-ink-900 prose-pre:text-ink-50 prose-table:text-sm">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => {
                  // Rewrite cross-references to other methodology files to use
                  // the slug-based URLs.
                  if (href && /^\d{2}-[a-z0-9-]+\.md$/i.test(href)) {
                    const slug = href.replace(/\.md$/, "");
                    return <Link href={`/methodology/${slug}`}>{children}</Link>;
                  }
                  // External links get target="_blank"
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

          <nav className="mt-12 flex justify-between gap-4 border-t border-ink-200 pt-6 text-sm">
            <div>
              {prev ? (
                <Link
                  href={`/methodology/${prev.slug}`}
                  className="block text-ink-600 hover:text-accent-700"
                >
                  <div className="text-xs uppercase tracking-wider text-ink-400">
                    Previous
                  </div>
                  <div className="mt-0.5 font-medium">{prev.title}</div>
                </Link>
              ) : null}
            </div>
            <div className="text-right">
              {next ? (
                <Link
                  href={`/methodology/${next.slug}`}
                  className="block text-ink-600 hover:text-accent-700"
                >
                  <div className="text-xs uppercase tracking-wider text-ink-400">
                    Next
                  </div>
                  <div className="mt-0.5 font-medium">{next.title}</div>
                </Link>
              ) : null}
            </div>
          </nav>
        </article>

        <aside className="space-y-6 lg:sticky lg:top-8 lg:self-start">
          {entry.audience ? (
            <Card label="Read this if">
              <p className="text-sm text-ink-600">{entry.audience}</p>
            </Card>
          ) : null}

          {entry.framework ? (
            <Card label="Framework">
              <p className="text-sm text-ink-600">{entry.framework}</p>
            </Card>
          ) : null}

          {entry.framing ? (
            <Card label="Framing">
              <p className="text-sm text-ink-600">{entry.framing}</p>
            </Card>
          ) : null}

          {entry.primary_sources.length > 0 ? (
            <Card label={`Primary sources (${entry.primary_sources.length})`}>
              <ul className="space-y-2 text-xs text-ink-600">
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
              <ul className="space-y-2 text-xs text-ink-600">
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
    <div className="rounded-lg border border-ink-200 bg-white p-4">
      <div className="mb-2 text-xs font-medium uppercase tracking-wider text-ink-400">
        {label}
      </div>
      {children}
    </div>
  );
}
