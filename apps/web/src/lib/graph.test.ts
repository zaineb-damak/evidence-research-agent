import { describe, expect, it } from "vitest";

import {
  claimIdsContradicting,
  relatedClaimIds,
  sourceIdsSupportingClaim,
} from "./graph";
import type { EvidenceGraph } from "../api/types";

const graph: EvidenceGraph = {
  nodes: [],
  edges: [
    { src: "claim_a", rel: "SUPPORTS", dst: "source_1" },
    { src: "claim_a", rel: "ABOUT", dst: "entity_x" },
    { src: "claim_b", rel: "ABOUT", dst: "entity_x" },
    { src: "claim_a", rel: "CONTRADICTS", dst: "claim_b" },
  ],
};

describe("evidence graph helpers", () => {
  it("finds sources that support a claim", () => {
    expect(sourceIdsSupportingClaim(graph, "claim_a")).toEqual(["source_1"]);
  });

  it("finds contradicting claims from either direction", () => {
    expect(claimIdsContradicting(graph, "claim_a")).toEqual(["claim_b"]);
    expect(claimIdsContradicting(graph, "claim_b")).toEqual(["claim_a"]);
  });

  it("finds claims about the same entity as related", () => {
    expect(relatedClaimIds(graph, "claim_a")).toEqual(["claim_b"]);
  });
});
