// The plugin runs inside react-markdown's mdast pipeline; these tests drive
// it over hand-built trees, which is all it inspects.

import { describe, expect, it } from "vitest";

import { remarkCitationMarkers } from "./citationMarkers";

interface TestNode {
  type: string;
  value?: string;
  children?: TestNode[];
  data?: { hName?: string; hProperties?: Record<string, unknown> };
}

function paragraph(...values: string[]): TestNode {
  return {
    type: "root",
    children: [
      { type: "paragraph", children: values.map((value) => ({ type: "text", value })) },
    ],
  };
}

function transform(tree: TestNode): TestNode[] {
  remarkCitationMarkers()(tree);
  return tree.children?.[0].children ?? [];
}

describe("remarkCitationMarkers", () => {
  it("raises a trailing marker into a superscript", () => {
    const children = transform(paragraph("Mistral wins on cost [4]."));

    expect(children).toEqual([
      { type: "text", value: "Mistral wins on cost " },
      {
        type: "text",
        value: "4",
        data: { hName: "sup", hProperties: { className: "report__citation" } },
      },
      { type: "text", value: "." },
    ]);
  });

  it("merges a run of adjacent markers into one superscript", () => {
    const children = transform(paragraph("Qwen leads on multilingual intent [1] [4]"));

    expect(children[1].value).toBe("1,4");
  });

  it("leaves a Sources line's leading number alone", () => {
    const children = transform(paragraph("[1] Open model quality index — https://example.test"));

    expect(children).toHaveLength(1);
    expect(children[0].data).toBeUndefined();
  });

  it("leaves the whole Sources section alone", () => {
    const tree: TestNode = {
      type: "root",
      children: [
        { type: "heading", children: [{ type: "text", value: "Sources" }] },
        {
          type: "paragraph",
          children: [{ type: "text", value: "index, Q3 2026 — url [2] Serving cost" }],
        },
      ],
    };

    remarkCitationMarkers()(tree);

    expect(tree.children?.[1].children).toEqual([
      { type: "text", value: "index, Q3 2026 — url [2] Serving cost" },
    ]);
  });

  it("does not touch markers inside links or code", () => {
    const tree: TestNode = {
      type: "root",
      children: [
        {
          type: "paragraph",
          children: [
            { type: "link", children: [{ type: "text", value: "see [2]" }] },
            { type: "inlineCode", value: "arr[3]" },
          ],
        },
      ],
    };

    const children = transform(tree);

    expect(children[0].children).toEqual([{ type: "text", value: "see [2]" }]);
    expect(children[1]).toEqual({ type: "inlineCode", value: "arr[3]" });
  });
});
