// The brief itself: the synthesized report markdown, rendered with
// react-markdown + remark-gfm (so tables/nested lists/emphasis all survive)
// and the citation-marker plugin that raises "[1] [2]" into superscripts.

import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import type { PluggableList } from "unified";

import { remarkCitationMarkers } from "../../lib/citationMarkers";

// remark-breaks keeps the synthesizer's single-newline lists (the Sources
// section, src/evidence/citations.py::render_sources) on separate lines.
const REMARK_PLUGINS = [remarkGfm, remarkBreaks, remarkCitationMarkers] as PluggableList;

interface ReportViewProps {
  reportMarkdown: string;
}

export function ReportView({ reportMarkdown }: ReportViewProps) {
  return (
    <article className="report">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{reportMarkdown}</ReactMarkdown>
    </article>
  );
}
