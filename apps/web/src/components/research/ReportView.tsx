// Replaces the old hand-rolled line-prefix Markdown parser (which silently
// dropped anything beyond #/flat lists/paragraphs) with react-markdown +
// remark-gfm, so tables/nested lists/emphasis in the synthesized report all
// render correctly — a correctness requirement for a citation-backed report.

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ReportViewProps {
  reportMarkdown: string;
}

export function ReportView({ reportMarkdown }: ReportViewProps) {
  return (
    <article className="report">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportMarkdown}</ReactMarkdown>
    </article>
  );
}
