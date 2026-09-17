// Adapted from the pre-router components/ResearchForm.tsx: same fields
// (question, depth, source types) and submit contract, restyled per the
// established design tokens and centered per the plan's wireframe. Owns its
// own submitting/error state so pages/HomePage.tsx only has to hand it an
// onSubmit that creates the job.

import { useState } from "react";
import type { FormEvent } from "react";

import type { CreateResearchInput } from "../../api/client";
import type { ResearchDepth, SourceType } from "../../api/types";

const DEPTH_OPTIONS: { value: ResearchDepth; label: string }[] = [
  { value: "fast", label: "Fast" },
  { value: "normal", label: "Normal" },
  { value: "deep", label: "Deep" },
];

const SOURCE_TYPE_OPTIONS: { value: SourceType; label: string }[] = [
  { value: "web", label: "Web" },
  { value: "documentation", label: "Documentation" },
  { value: "paper", label: "Papers" },
  { value: "arxiv", label: "arXiv" },
  { value: "github", label: "GitHub" },
  { value: "reddit", label: "Reddit" },
];

const DEFAULT_SOURCE_TYPES: SourceType[] = ["web", "documentation", "paper"];
const DEFAULT_DEPTH: ResearchDepth = "fast";

const QUESTION_PLACEHOLDER = "Compare Qwen, Llama and Mistral for customer support";
const SUBMITTING_LABEL = "Starting…";
const SUBMIT_LABEL = "Start research";
const GENERIC_SUBMIT_ERROR = "Couldn't start that research job. Try again in a moment.";

interface ResearchComposerProps {
  onSubmit: (input: CreateResearchInput) => Promise<void>;
  initialQuestion?: string;
}

export function ResearchComposer({ onSubmit, initialQuestion = "" }: ResearchComposerProps) {
  const [question, setQuestion] = useState(initialQuestion);
  const [depth, setDepth] = useState<ResearchDepth>(DEFAULT_DEPTH);
  const [sourceTypes, setSourceTypes] = useState<SourceType[]>(DEFAULT_SOURCE_TYPES);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleSourceType(sourceType: SourceType): void {
    setSourceTypes((current) =>
      current.includes(sourceType)
        ? current.filter((item) => item !== sourceType)
        : [...current, sourceType],
    );
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (trimmedQuestion === "" || isSubmitting) {
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ question: trimmedQuestion, depth, sourceTypes });
    } catch {
      setError(GENERIC_SUBMIT_ERROR);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="research-composer">
      <h1 className="research-composer__title">What do you want to research?</h1>
      <form className="research-composer__form" onSubmit={handleSubmit}>
        <label className="research-composer__field">
          <span className="research-composer__label">Research question</span>
          <textarea
            className="research-composer__textarea"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={QUESTION_PLACEHOLDER}
            rows={3}
          />
        </label>

        <div className="research-composer__row">
          <label className="research-composer__field">
            <span className="research-composer__label">Depth</span>
            <select
              className="research-composer__select"
              value={depth}
              onChange={(event) => setDepth(event.target.value as ResearchDepth)}
            >
              {DEPTH_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <fieldset className="research-composer__field research-composer__source-types">
            <legend className="research-composer__label">Sources</legend>
            <div className="research-composer__checkboxes">
              {SOURCE_TYPE_OPTIONS.map((option) => (
                <label key={option.value} className="research-composer__checkbox">
                  <input
                    type="checkbox"
                    checked={sourceTypes.includes(option.value)}
                    onChange={() => toggleSourceType(option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        {error !== null && (
          <p className="research-composer__error" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="research-composer__submit"
          disabled={isSubmitting || question.trim() === ""}
        >
          {isSubmitting ? SUBMITTING_LABEL : SUBMIT_LABEL}
        </button>
      </form>
    </div>
  );
}
