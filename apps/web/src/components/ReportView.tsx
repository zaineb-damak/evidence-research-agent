interface ReportViewProps {
  reportMarkdown: string;
}

// Minimal, dependency-free Markdown rendering for the report's known structure
// (headings, list items, and paragraphs). Avoids pulling a Markdown library for
// the small, controlled output the synthesizer produces.
export function ReportView({ reportMarkdown }: ReportViewProps) {
  const lines = reportMarkdown.split("\n");
  return (
    <article className="report">
      {lines.map((line, index) => (
        <ReportLine key={index} line={line} />
      ))}
    </article>
  );
}

const HEADING_3_PREFIX = "### ";
const HEADING_2_PREFIX = "## ";
const HEADING_1_PREFIX = "# ";
const LIST_ITEM_PREFIX = "- ";
const NESTED_LIST_PREFIX = "  - ";

function ReportLine({ line }: { line: string }) {
  if (line.startsWith(HEADING_3_PREFIX)) {
    return <h3>{line.slice(HEADING_3_PREFIX.length)}</h3>;
  }
  if (line.startsWith(HEADING_2_PREFIX)) {
    return <h2>{line.slice(HEADING_2_PREFIX.length)}</h2>;
  }
  if (line.startsWith(HEADING_1_PREFIX)) {
    return <h1>{line.slice(HEADING_1_PREFIX.length)}</h1>;
  }
  if (line.startsWith(NESTED_LIST_PREFIX)) {
    return <p className="report-nested">{line.trim()}</p>;
  }
  if (line.startsWith(LIST_ITEM_PREFIX)) {
    return <p className="report-item">{line.slice(LIST_ITEM_PREFIX.length)}</p>;
  }
  if (line.trim() === "") {
    return <br />;
  }
  return <p>{line}</p>;
}
