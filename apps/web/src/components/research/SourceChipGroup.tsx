// Independent on/off chips for the source connectors a run may use.

import { SOURCE_TYPE_OPTIONS } from "../../constants";
import type { SourceType } from "../../api/types";

const GROUP_LABEL = "Sources";

interface SourceChipGroupProps {
  selected: SourceType[];
  onToggle: (sourceType: SourceType) => void;
}

export function SourceChipGroup({ selected, onToggle }: SourceChipGroupProps) {
  return (
    <div className="source-chips" role="group" aria-label={GROUP_LABEL}>
      {SOURCE_TYPE_OPTIONS.map((option) => {
        const isOn = selected.includes(option.value);
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={isOn}
            className={`source-chip${isOn ? " source-chip--on" : ""}`}
            onClick={() => onToggle(option.value)}
          >
            <span className="source-chip__dot" aria-hidden="true" />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
