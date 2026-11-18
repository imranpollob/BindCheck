# S8 — Paper: A4 template and the sections whose evidence exists now

## Context (read first)

The paper targets **IEEE EuroS&P 2027**. The framing sections (title, abstract,
intro, motivating example, taxonomy, threat model) are drafted by S8a in
`paper/zk/`. Read `paper/zk/STATUS.md`, `reports/S8a/REPORT.md` and `main.tex`
first. This lane does the template switch and fills the placeholders whose
evidence is already in the repository. It does **not** invent results.

**Branch / worktree:** `sprint/S8`, `$BC/wt-S8`.
**Owns:** `paper/zk/` (sections, template, bib), `reports/S8/`.
**Must not edit:** code, other lanes' reports, `paper/generated/` (that is built
by `make paper-tables`; `\input` it, never hand-edit).

## Do now (evidence exists)

1. **Template.** Switch to the EuroS&P / IEEE S&P A4 format the venue requires.
   Keep the build working (use `tectonic` if no `latexmk`). Report the page
   count before and after.
2. **Design / methodology section.** Describe BindCheck as it now stands
   (frozen candidate hash `753c6e2a…`): the cross-layer triple (circuit,
   generated verifier, consumer), the five patterns P1–P5 with extent binding,
   fail-closed semantics, and the execution oracle (local-only E4 confirmation,
   mutation operators, state-corroborated effects and obligations). Sources:
   `docs/research-contract.md`, `reports/F1/REPORT.md`, `reports/F2/REPORT.md`,
   `reports/S2c/REPORT.md`, `oracle/README.md`. No held-out numbers.
3. **Generator survey subsection + condensed table.** S1 is done
   (`reports/S1/REPORT.md`, `reports/S1/generators.csv`). Write the prose and a
   **condensed** paper table (group by behaviour: reject / split / reduce) from
   the generated `T-generators`, not the full 26-row CSV. State clearly that the
   split templates are source-read and unconfirmed (no claim of acceptance).
4. **Related work.** Position against ZKAP (single-layer, unused public
   inputs), Circomspect, Picus, and the audit literature from R2. Use
   `RELATED-WORK.md` and `reports/R2/` if present.
5. **Background** touch-ups only where the new taxonomy needs them.

## Leave as explicit `\TODO{lane}` (evidence not ready)

- Held-out v3 numbers and the headline → `\TODO{S5}`.
- Oracle E4 counts in evaluation → cite only after XR2 clears; until then
  `\TODO{XR2/S5}`.
- Case A / Case B naming and the disclosure/ethics section → `\TODO{S7}`.
- Contract-revision-4 scope wording in the threat model → `\TODO{S0}`.
- Author label review of R1/R2 (Aztec P1 vs P5) → `\TODO{R1b}`.

Do not remove the S&P-era `\MISSING{}` markers for sections you do not touch.

## Rules

Plain, precise prose; no hype words. Every number comes from `paper/generated/`
macros or carries a `\TODO{}`. Never print a contract address. Refer to
undisclosed cases only as Case A / Case B. AI disclosure in the report.

## Output

`reports/S8/REPORT.md`: what was written, the page budget per section, the
template change, and the list of remaining `\TODO`s with their lane. Commit and
push `sprint/S8`.

## Reporting

End your session by printing, as the final line in this terminal, exactly:
`FINAL: S8 DONE` (or `FINAL: S8 BLOCKED: <reason>`). The orchestrator watches
this terminal for that line. Do not rely on `hc` to notify the orchestrator.
