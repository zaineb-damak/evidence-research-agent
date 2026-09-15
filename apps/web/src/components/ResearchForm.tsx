import { useState } from "react";

import type { ResearchDepth, SourceType } from "../api/types";

const DEPTH_OPTIONS: ResearchDepth[] = ["fast", "normal", "deep"];
const SOURCE_TYPE_OPTIONS: SourceType[] = [
  "web",
  "documentation",
  "paper",
  "arxiv",
  "github",
  "reddit",
];
const DEFAULT_SOURCE_TYPES: SourceType[] = ["web", "documentation", "paper"];

export interface ResearchFormSubmit {
  question: string;
  depth: ResearchDepth;
  sourceTypes: SourceType[];
}

interface ResearchFormProps {
  onSubmit: (input: ResearchFormSubmit) => void;
  isSubmitting: boolean;
}

export function ResearchForm({ onSubmit, isSubmitting }: ResearchFormProps) {
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("fast");
  const [sourceTypes, setSourceTypes] = useState<SourceType[]>(
    DEFAULT_SOURCE_TYPES,
  );

  function toggleSourceType(sourceType: SourceType): void {
    setSourceTypes((current) =>
      current.includes(sourceType)
        ? current.filter((item) => item !== sourceType)
        : [...current, sourceType],
    );
  }

  function handleSubmit(event: React.FormEvent): void {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }
    onSubmit({ question: question.trim(), depth, sourceTypes });
  }

  return (
    <form className="research-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Research question</span>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Compare Qwen, Llama and Mistral for customer support"
          rows={3}
        />
      </label>

      <label className="field">
        <span>Depth</span>
        <select
          value={depth}
          onChange={(event) => setDepth(event.target.value as ResearchDepth)}
        >
          {DEPTH_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="field">
        <legend>Sources</legend>
        {SOURCE_TYPE_OPTIONS.map((sourceType) => (
          <label key={sourceType} className="checkbox">
            <input
              type="checkbox"
              checked={sourceTypes.includes(sourceType)}
              onChange={() => toggleSourceType(sourceType)}
            />
            {sourceType}
          </label>
        ))}
      </fieldset>

      <button type="submit" disabled={isSubmitting || !question.trim()}>
        {isSubmitting ? "Starting…" : "Start research"}
      </button>
    </form>
  );
}
