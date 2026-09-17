// Flush list rows with a colored status rail (border-left, driven by
// CLAIM_STATUS_TONE) instead of the old bordered-box claim cards.

import { CLAIM_STATUS_LABELS, CLAIM_STATUS_TONE } from "../../constants";
import { toPercent } from "../../lib/format";
import type { Claim } from "../../api/types";

interface ClaimListProps {
  claims: Claim[];
  selectedClaimId: string | null;
  onSelectClaim: (claimId: string) => void;
}

export function ClaimList({ claims, selectedClaimId, onSelectClaim }: ClaimListProps) {
  return (
    <ul className="claim-list">
      {claims.map((claim) => {
        const tone = CLAIM_STATUS_TONE[claim.status];
        const isSelected = claim.id === selectedClaimId;
        return (
          <li key={claim.id} className="claim-list__item">
            <button
              type="button"
              className={`claim-list__row claim-list__row--${tone}${
                isSelected ? " claim-list__row--selected" : ""
              }`}
              onClick={() => onSelectClaim(claim.id)}
              aria-current={isSelected}
            >
              <span className="claim-list__text">{claim.text}</span>
              <span className="claim-list__meta">
                <span className="claim-list__status">{CLAIM_STATUS_LABELS[claim.status]}</span>
                <span className="claim-list__confidence">{toPercent(claim.confidence)}%</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
