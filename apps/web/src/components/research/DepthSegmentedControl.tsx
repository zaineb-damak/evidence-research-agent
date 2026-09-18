// Single-select depth control: Fast / Balanced / Deep.

import { DEPTH_OPTIONS } from "../../constants";
import type { ResearchDepth } from "../../api/types";

const GROUP_LABEL = "Research depth";

interface DepthSegmentedControlProps {
  depth: ResearchDepth;
  onChange: (depth: ResearchDepth) => void;
}

export function DepthSegmentedControl({ depth, onChange }: DepthSegmentedControlProps) {
  return (
    <div className="segmented" role="radiogroup" aria-label={GROUP_LABEL}>
      {DEPTH_OPTIONS.map((option) => {
        const isActive = option.value === depth;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            className={`segmented__segment${isActive ? " segmented__segment--active" : ""}`}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
