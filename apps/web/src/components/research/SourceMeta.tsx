// Replaces the old dot-joined "{type} · quality {score}%" meta string with a
// type badge and a separately labeled quality figure.

import { toPercent } from "../../lib/format";
import type { SourceType } from "../../api/types";

interface SourceMetaProps {
  sourceType: SourceType;
  qualityScore: number;
}

export function SourceMeta({ sourceType, qualityScore }: SourceMetaProps) {
  return (
    <span className="source-meta">
      <span className="source-meta__badge">{sourceType}</span>
      <span className="source-meta__quality">Quality {toPercent(qualityScore)}%</span>
    </span>
  );
}
