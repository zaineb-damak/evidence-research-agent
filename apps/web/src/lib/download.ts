// Client-side file download for the header's Export action. The report is
// already in the browser (GET /api/research/{id}/report), so saving it is a
// Blob and an anchor click — no extra endpoint.

const MARKDOWN_MIME_TYPE = "text/markdown;charset=utf-8";
const MARKDOWN_EXTENSION = ".md";
const FILE_NAME_FALLBACK = "research-report";
const FILE_NAME_MAX_LENGTH = 60;

const NON_FILE_NAME_CHARACTERS = /[^a-z0-9]+/g;
const LEADING_OR_TRAILING_DASHES = /^-+|-+$/g;
const FILE_NAME_SEPARATOR = "-";
const EMPTY = "";

// "Compare Qwen, Llama and Mistral" -> "compare-qwen-llama-and-mistral.md"
export function reportFileName(question: string): string {
  const slug = question
    .toLowerCase()
    .replace(NON_FILE_NAME_CHARACTERS, FILE_NAME_SEPARATOR)
    .replace(LEADING_OR_TRAILING_DASHES, EMPTY)
    .slice(0, FILE_NAME_MAX_LENGTH)
    .replace(LEADING_OR_TRAILING_DASHES, EMPTY);
  return (slug === EMPTY ? FILE_NAME_FALLBACK : slug) + MARKDOWN_EXTENSION;
}

export function downloadMarkdown(fileName: string, markdown: string): void {
  const blob = new Blob([markdown], { type: MARKDOWN_MIME_TYPE });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Releasing the object URL immediately after the click is safe: the
  // browser has already taken its own reference to the blob.
  URL.revokeObjectURL(objectUrl);
}
