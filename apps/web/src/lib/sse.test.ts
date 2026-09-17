import { describe, expect, it } from "vitest";

import { SseParser } from "./sse";

describe("SseParser", () => {
  it("parses a single event delivered in one chunk", () => {
    const parser = new SseParser();
    const messages = parser.push('event: snapshot\ndata: {"a":1}\n\n');
    expect(messages).toEqual([{ event: "snapshot", data: '{"a":1}' }]);
  });

  it("parses multiple events delivered in one chunk", () => {
    const parser = new SseParser();
    const messages = parser.push(
      'event: stage_started\ndata: {"a":1}\n\n' + 'event: substep\ndata: {"b":2}\n\n',
    );
    expect(messages).toEqual([
      { event: "stage_started", data: '{"a":1}' },
      { event: "substep", data: '{"b":2}' },
    ]);
  });

  it("parses an event split across two chunks", () => {
    const parser = new SseParser();
    const firstChunkMessages = parser.push('event: done\ndata: {"fin');
    expect(firstChunkMessages).toEqual([]);

    const secondChunkMessages = parser.push('ished":true}\n\n');
    expect(secondChunkMessages).toEqual([{ event: "done", data: '{"finished":true}' }]);
  });

  it("joins multiple data: lines within one block with newlines", () => {
    const parser = new SseParser();
    const messages = parser.push("event: message\ndata: line one\ndata: line two\n\n");
    expect(messages).toEqual([{ event: "message", data: "line one\nline two" }]);
  });

  it("defaults the event name to 'message' when no event: line is present", () => {
    const parser = new SseParser();
    const messages = parser.push('data: {"x":1}\n\n');
    expect(messages).toEqual([{ event: "message", data: '{"x":1}' }]);
  });

  it("ignores a block with no data: line", () => {
    const parser = new SseParser();
    const messages = parser.push(": this is a comment\n\n");
    expect(messages).toEqual([]);
  });
});
