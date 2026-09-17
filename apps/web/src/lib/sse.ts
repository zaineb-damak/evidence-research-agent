// Pure server-sent-events text parser — no DOM/fetch dependency, so it is
// unit-testable without a browser. api/stream.ts feeds it raw decoded text
// chunks from a fetch response body; this module only knows about the
// `event: X\ndata: Y\n\n` wire framing (apps/api/events.py::format_sse).

export interface SseMessage {
  event: string;
  data: string;
}

const EVENT_FIELD_PREFIX = "event:";
const DATA_FIELD_PREFIX = "data:";
const RECORD_SEPARATOR = "\n";
const EVENT_BLOCK_SEPARATOR = "\n\n";
const DEFAULT_EVENT_NAME = "message";

function parseEventBlock(rawBlock: string): SseMessage | null {
  let eventName = DEFAULT_EVENT_NAME;
  const dataLines: string[] = [];

  for (const line of rawBlock.split(RECORD_SEPARATOR)) {
    if (line.startsWith(EVENT_FIELD_PREFIX)) {
      eventName = line.slice(EVENT_FIELD_PREFIX.length).trim();
    } else if (line.startsWith(DATA_FIELD_PREFIX)) {
      dataLines.push(line.slice(DATA_FIELD_PREFIX.length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }
  return { event: eventName, data: dataLines.join(RECORD_SEPARATOR) };
}

// Buffers incoming chunks (an SSE event can arrive split across two `read()`
// calls) and yields complete `{event, data}` records as full blank-line-
// delimited blocks become available.
export class SseParser {
  private buffer = "";

  push(chunk: string): SseMessage[] {
    this.buffer += chunk;
    const messages: SseMessage[] = [];

    let separatorIndex = this.buffer.indexOf(EVENT_BLOCK_SEPARATOR);
    while (separatorIndex !== -1) {
      const rawBlock = this.buffer.slice(0, separatorIndex);
      this.buffer = this.buffer.slice(separatorIndex + EVENT_BLOCK_SEPARATOR.length);
      const message = parseEventBlock(rawBlock);
      if (message !== null) {
        messages.push(message);
      }
      separatorIndex = this.buffer.indexOf(EVENT_BLOCK_SEPARATOR);
    }

    return messages;
  }
}
