# Author decisions on the final labels (2026-11-24)

The author accepted the orchestrator's recommendations on the six questions in the raters' NOTES_FOR_AUTHOR.md:

1. **Circuit-internal soundness bugs** where every consumer-read value is fixed by the proof stay `binding = N`, tagged `[circuit-soundness]` in notes. The paper reports them as an adjacent class.
2. **P2 wording** gains "starting/prior state not bound to the consumer's stored state".
3. **Practical proof-system forgeries** stay binding P4 with PSS = Y. Every result is reported with and without PSS = Y items.
4. **Unconstrained output the consumer stores** is P1 (stored value not fixed). The guide's Payy extent example is reclassified from OTHER to P1.
5. **Pass-through vs broken computation:** unauthenticated pass-through of witness data into a stored output = binding; an under-constrained computation over the right data = N + `[circuit-soundness]`.
6. **U items** (L206, L252, L263, L264, L254) are excluded from evaluation.

Also:
- **Tornado Cash** stays held-out (FORBIDDEN items are excluded from evaluation).
- **Labels** are "AI-proposed, adjudicated by two collaborating raters". No independent κ is claimed; an outside blind re-label of a subset is optional later.
- **FULL ground truth** for scoring is the Pass 2 code-verified label (restricted file in the labeling repo, read only by the evaluation harness after the tool is frozen). Pass 1 and Pass 2 differ on one FULL item.
