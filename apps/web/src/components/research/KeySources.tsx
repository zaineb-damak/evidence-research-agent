// "Key sources": the highest-quality sources the run read, as a grid of
// cards linking out to the original. The favicon is a placeholder square —
// fetching real favicons would call out to third-party hosts from the
// reader's browser.

import { sourceHost, sourceTitle, topSourcesByQuality } from "../../lib/sourceCards";
import type { Source } from "../../api/types";

const SECTION_LABEL = "Key sources";

interface KeySourcesProps {
  sources: Source[];
}

export function KeySources({ sources }: KeySourcesProps) {
  const cards = topSourcesByQuality(sources);
  if (cards.length === 0) {
    return null;
  }

  return (
    <section className="key-sources">
      <h2 className="eyebrow key-sources__label">{SECTION_LABEL}</h2>
      <div className="key-sources__grid">
        {cards.map((source) => (
          <a
            key={source.id}
            className="source-card"
            href={source.url}
            target="_blank"
            rel="noreferrer"
          >
            <span className="source-card__host">
              <span className="source-card__favicon" aria-hidden="true" />
              {sourceHost(source)}
            </span>
            <span className="source-card__title">{sourceTitle(source)}</span>
          </a>
        ))}
      </div>
    </section>
  );
}
