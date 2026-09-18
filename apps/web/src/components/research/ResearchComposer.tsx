// The empty / new-run state: heading, composer card (question, depth,
// sources, submit) and the prefill-and-run suggestion chips. Depth is owned
// by the page so the header pill can read it; question and source selection
// are local.

import { ArrowUp } from "lucide-react";
import { useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import type { CreateResearchInput } from "../../api/client";
import type { ResearchDepth, SourceType } from "../../api/types";
import {
  DEFAULT_SOURCE_TYPES,
  ICON_STROKE_WIDTH,
  SUGGESTED_QUESTIONS,
} from "../../constants";
import { DepthSegmentedControl } from "./DepthSegmentedControl";
import { SourceChipGroup } from "./SourceChipGroup";

const TITLE = "What do you want to research?";
const SUBTITLE =
  "Ask a question and the agent plans its own searches, reads the sources, and writes back a cited brief.";
const QUESTION_PLACEHOLDER = "Compare Qwen, Llama and Mistral for customer support";
const QUESTION_LABEL = "Research question";
const SUBMIT_LABEL = "Start research";
const GENERIC_SUBMIT_ERROR = "Couldn't start that research job. Try again in a moment.";
const QUESTION_ROWS = 3;
const SUBMIT_ICON_SIZE = 15;
const SUBMIT_KEY = "Enter";

interface ResearchComposerProps {
  depth: ResearchDepth;
  onDepthChange: (depth: ResearchDepth) => void;
  onSubmit: (input: CreateResearchInput) => Promise<void>;
  initialQuestion?: string;
}

export function ResearchComposer({
  depth,
  onDepthChange,
  onSubmit,
  initialQuestion = "",
}: ResearchComposerProps) {
  const [question, setQuestion] = useState(initialQuestion);
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

  async function startRun(rawQuestion: string): Promise<void> {
    const trimmedQuestion = rawQuestion.trim();
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

  function handleSubmit(event: FormEvent): void {
    event.preventDefault();
    void startRun(question);
  }

  // Enter submits; Shift+Enter keeps the newline, as in the design's
  // single-question composer.
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === SUBMIT_KEY && !event.shiftKey) {
      event.preventDefault();
      void startRun(question);
    }
  }

  function handleSuggestion(suggestion: string): void {
    setQuestion(suggestion);
    void startRun(suggestion);
  }

  return (
    <div className="composer-view">
      <div className="composer-view__inner">
        <h1 className="composer-view__title">{TITLE}</h1>
        <p className="composer-view__subtitle">{SUBTITLE}</p>

        <form className="composer-card" onSubmit={handleSubmit}>
          <label className="visually-hidden" htmlFor="research-question">
            {QUESTION_LABEL}
          </label>
          <textarea
            id="research-question"
            className="composer-card__question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={QUESTION_PLACEHOLDER}
            rows={QUESTION_ROWS}
          />
          <div className="composer-card__controls">
            <DepthSegmentedControl depth={depth} onChange={onDepthChange} />
            <SourceChipGroup selected={sourceTypes} onToggle={toggleSourceType} />
            <button
              type="submit"
              className="submit-circle"
              aria-label={SUBMIT_LABEL}
              title={SUBMIT_LABEL}
              disabled={isSubmitting || question.trim() === ""}
            >
              <ArrowUp size={SUBMIT_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} />
            </button>
          </div>
        </form>

        {error !== null && (
          <p className="composer-view__error" role="alert">
            {error}
          </p>
        )}

        <div className="suggestion-chips">
          {SUGGESTED_QUESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              className="suggestion-chip"
              onClick={() => handleSuggestion(suggestion)}
              disabled={isSubmitting}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
