// A remark plugin turning the synthesizer's inline citation markers into
// superscripts, so the brief reads as prose with raised reference numbers
// rather than bracketed digits.
//
// The backend writes markers as "[1] [2]" after a claim
// (src/evidence/report_format.py::format_markers) and opens each line of the
// Sources section with "[1] Title — url"
// (src/evidence/citations.py::render_sources). Only markers that follow other
// text are converted, which leaves those Sources lines alone.

const CITATION_RUN_PATTERN = /\[\d+\](?:\s*\[\d+\])*/g;
const CITATION_NUMBER_PATTERN = /\d+/g;
const CITATION_SEPARATOR = ",";
const SUPERSCRIPT_TAG = "sup";
const CITATION_CLASS_NAME = "report__citation";
const TEXT_NODE_TYPE = "text";
const HEADING_NODE_TYPE = "heading";
const START_INDEX = 0;

// The report's Sources section lists "[1] Title — url" entries: those
// brackets are the list's own numbering, not citations.
const SOURCES_HEADING = "sources";

// Nodes whose text is literal, not prose — a marker inside them is content.
const OPAQUE_NODE_TYPES: ReadonlySet<string> = new Set(["link", "linkReference", "code", "inlineCode"]);

interface MarkdownNode {
  type: string;
  value?: string;
  children?: MarkdownNode[];
  data?: { hName?: string; hProperties?: Record<string, unknown> };
}

function citationNode(markerRun: string): MarkdownNode {
  const numbers = markerRun.match(CITATION_NUMBER_PATTERN) ?? [];
  return {
    type: TEXT_NODE_TYPE,
    value: numbers.join(CITATION_SEPARATOR),
    data: {
      hName: SUPERSCRIPT_TAG,
      hProperties: { className: CITATION_CLASS_NAME },
    },
  };
}

// Splits one text node into text/superscript parts. Returns null when the
// node holds no convertible marker, so callers can leave it untouched.
function splitTextNode(node: MarkdownNode): MarkdownNode[] | null {
  const value = node.value ?? "";
  const parts: MarkdownNode[] = [];
  let cursor = START_INDEX;

  CITATION_RUN_PATTERN.lastIndex = START_INDEX;
  let match = CITATION_RUN_PATTERN.exec(value);
  while (match !== null) {
    // A marker opening the node is a Sources-section line number, not a
    // citation attached to a sentence.
    if (match.index > START_INDEX) {
      parts.push({ type: TEXT_NODE_TYPE, value: value.slice(cursor, match.index) });
      parts.push(citationNode(match[0]));
      cursor = match.index + match[0].length;
    }
    match = CITATION_RUN_PATTERN.exec(value);
  }

  if (parts.length === 0) {
    return null;
  }
  if (cursor < value.length) {
    parts.push({ type: TEXT_NODE_TYPE, value: value.slice(cursor) });
  }
  return parts;
}

function transformChildren(node: MarkdownNode): void {
  if (node.children === undefined || OPAQUE_NODE_TYPES.has(node.type)) {
    return;
  }
  const nextChildren: MarkdownNode[] = [];
  for (const child of node.children) {
    if (child.type === TEXT_NODE_TYPE) {
      const split = splitTextNode(child);
      nextChildren.push(...(split ?? [child]));
      continue;
    }
    transformChildren(child);
    nextChildren.push(child);
  }
  node.children = nextChildren;
}

function nodeText(node: MarkdownNode): string {
  if (node.value !== undefined) {
    return node.value;
  }
  return (node.children ?? []).map(nodeText).join("");
}

export function remarkCitationMarkers() {
  return (tree: MarkdownNode): void => {
    for (const node of tree.children ?? []) {
      if (
        node.type === HEADING_NODE_TYPE &&
        nodeText(node).trim().toLowerCase() === SOURCES_HEADING
      ) {
        return;
      }
      transformChildren(node);
    }
  };
}
