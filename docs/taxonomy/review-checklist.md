# D1P-C03 human empirical sign-off sheet

Protocol version: `0.2.0`
Status: **blank template — no human act or signature is asserted**

Design choices are reviewed in typed AI-planner records, not on this sheet.
This sheet is limited to the three empirical controls that must be performed
by humans. Complete it only after the named activity actually occurs. Do not
record reserved-family names, selection paths, nonce, seed, or manifest bytes.

## 1. Staffing

- Human annotator 1 controlled ID: ____________________
- Human annotator 2 controlled ID: ____________________
- Human adjudicator controlled ID: ____________________
- Conflict/exposure review reference: ____________________
- Staff are three distinct humans: ☐ confirmed ☐ not confirmed
- Staffing custodian controlled ID: ____________________
- Recorded UTC date: ____________________
- Custodian attestation: ____________________

Required staffing is exactly two independent annotators and one distinct
adjudicator. A controlled ID may map to a legal name outside the repository.
No AI system may fill a human role or sign this section.

## 2. Reservation draw

- Frozen grouped-list SHA-256: ____________________
- Frozen rounding and strata reference: ____________________
- Draw-tool SHA-256: ____________________
- `SHA256(nonce || canonical_selection_manifest)`: ____________________
- Draw completed before development screening: ☐ yes ☐ no
- Output kept outside every worktree: ☐ yes ☐ no
- Repository contains no membership/opening data: ☐ confirmed ☐ not confirmed
- Human custodian controlled ID: ____________________
- Recorded UTC date: ____________________
- Custodian attestation that the frozen rule and tool were followed:
  ____________________

This commitment supports comparison with a later opening. It does not prove
randomness or timing. Operational non-exposure of every reserved family is the
essential protection.

## 3. Annotation rounds

### Four-packet unscored calibration

- Packet-set hash/reference: ____________________
- Exactly four development packets: ☐ yes ☐ no
- Joint discussion marked unscored: ☐ yes ☐ no
- Completed by both annotators, UTC date: ____________________
- Human round custodian attestation: ____________________

### Sixteen-packet independent round

- Fresh packet-set hash/reference: ____________________
- Exactly sixteen packets across several non-reserved families: ☐ yes ☐ no
- Includes borderline/unresolved and excluded candidates: ☐ yes ☐ no
- Ratings sealed before comparison: ☐ yes ☐ no
- No BindCheck/tool/E4 results supplied: ☐ confirmed ☐ not confirmed
- No AI-suggested labels supplied: ☐ confirmed ☐ not confirmed
- Both independent human ratings complete, UTC date: ____________________
- Agreement report reference: ____________________
- Per-label and include/exclude/unresolved agreement reported: ☐ yes ☐ no
- Nulls and uninformative intervals reported explicitly: ☐ yes ☐ no
- Human round custodian attestation: ____________________

### Adjudication

- Sealed disagreement set reference: ____________________
- Distinct human adjudicator completed review, UTC date: ____________________
- Original ratings preserved: ☐ yes ☐ no
- Adjudication record reference: ____________________
- Codebook changed: ☐ no ☐ yes, new version: __________
- If changed, next reliability round uses fresh packets: ☐ confirmed ☐ N/A
- Human adjudicator attestation: ____________________

Unchecked boxes and blank fields mean pending, not failed. Never complete a
field retrospectively without recording the date basis and limitation.
