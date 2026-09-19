import { describe, expect, it } from "vitest";

import { reportFileName } from "./download";

describe("reportFileName", () => {
  it("slugifies the question", () => {
    expect(reportFileName("Compare Qwen, Llama and Mistral for support")).toBe(
      "compare-qwen-llama-and-mistral-for-support.md",
    );
  });

  it("trims punctuation from both ends", () => {
    expect(reportFileName("  ¿Which model is cheapest?  ")).toBe(
      "which-model-is-cheapest.md",
    );
  });

  it("falls back when the question has no usable characters", () => {
    expect(reportFileName("???")).toBe("research-report.md");
  });

  it("keeps long questions to a sane file name length", () => {
    const fileName = reportFileName("word ".repeat(40));

    expect(fileName.length).toBeLessThanOrEqual("research-report.md".length + 60);
    expect(fileName.endsWith("-.md")).toBe(false);
  });
});
