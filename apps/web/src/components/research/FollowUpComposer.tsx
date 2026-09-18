// The bar pinned to the bottom of a run: ask a follow-up or narrow the
// scope. There is no follow-up endpoint on a run yet, so the page starts a
// new run from the follow-up text (see pages/ResearchPage.tsx).

import { ArrowUp } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import { ICON_STROKE_WIDTH } from "../../constants";

const PLACEHOLDER = "Ask a follow-up or narrow the scope";
const SUBMIT_LABEL = "Send follow-up";
const SUBMIT_ICON_SIZE = 14;

interface FollowUpComposerProps {
  onSubmit: (question: string) => Promise<void>;
}

export function FollowUpComposer({ onSubmit }: FollowUpComposerProps) {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (trimmedQuestion === "" || isSubmitting) {
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit(trimmedQuestion);
      setQuestion("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="follow-up">
      <form className="follow-up__bar" onSubmit={handleSubmit}>
        <input
          className="follow-up__input"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={PLACEHOLDER}
          aria-label={PLACEHOLDER}
        />
        <button
          type="submit"
          className="submit-circle submit-circle--small"
          aria-label={SUBMIT_LABEL}
          disabled={isSubmitting || question.trim() === ""}
        >
          <ArrowUp size={SUBMIT_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} />
        </button>
      </form>
    </div>
  );
}
