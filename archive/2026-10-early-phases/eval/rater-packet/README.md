# START HERE: blind labeling of ZK smart-contract warnings ({RATER})

Thank you for helping. This packet is for an academic security study (a paper
in preparation for IEEE S&P) about **zero-knowledge (ZK) applications on
Ethereum**: Circom circuits, snarkjs-generated Solidity verifiers, and the
contracts that act on proofs. Automated analysis produced warnings on public
open-source projects. Your job is to judge, for each warning, whether the
problem it describes is really present in the code.

You are **{RATER}**. Another researcher labels the same cards independently.

## What you need
- A text editor or web browser to read Markdown/Solidity, and a spreadsheet app (Excel, Numbers, LibreOffice, Google Sheets).
- Optional internet access for GitHub links. Local copies of the analysed Solidity files are included.
- Working knowledge of Solidity. ZK background helps, but `GUIDE.md` explains everything needed.
- Nothing to install. No blockchain access. Never interact with deployed contracts.

## Time
**{TOTAL} cards.** Most take 2–5 minutes; stop at 10 minutes and label `unclear`.
Plan on about 30 minutes to read the guide plus several hours of labeling, which you can split across sessions.

## Steps
1. Read **`GUIDE.md`** fully. It explains the background, the six warning
   kinds (K1–K6), exactly what TP / FP / unclear mean, and the tags.
2. Label **set H** (`set-H/`, {N_H} cards) using `set-H/{SHEET_H}`.
3. Label **set D** (`set-D/`, {N_D} cards) using `set-D/{SHEET_D}`.
4. In each sheet, fill **only** the `label` column (`TP`, `FP` or `unclear`) and
   the `rater_reason` column (one line, cite `file:line`, optional tags such as `[TEST-CODE]`).
   Don't edit `warning_id`. If your spreadsheet app reformats other columns
   (for example commit hashes), that is fine, because only `warning_id`,
   `label` and `rater_reason` are read.
5. Save both sheets as **CSV (UTF-8)** and email them back to the sender.

## Folder layout
```
README.md          this file
GUIDE.md           background, warning kinds, labeling rules, reference, glossary
set-H/cards/       one Markdown card per warning (W0007.md, ...)
set-H/{SHEET_H}
set-D/cards/       W01.md ... W16.md
set-D/{SHEET_D}
sources/           full copies of the analysed source files, by project and commit
```
Each card links its local copies with paths starting `../../sources/`, and
GitHub permalinks pinned to the exact analysed commit.

## Ground rules
- **Work independently.** Don't discuss cards or labels with anyone, including
  the other rater, until you've sent your sheets.
- **Don't use AI assistants** to decide labels. The study measures human judgement.
- **Confidential.** Some warnings may be real, undisclosed vulnerabilities in
  public projects. Don't share this packet, don't open issues or contact
  projects, and don't post about specific findings. Disclosure is handled by
  the research team.
- The cards don't say which tool produced a warning. Expect a mix of correct
  and incorrect warnings; there is no target ratio.

## Questions
Reply to the email this packet came with. If something on a card is
ambiguous, decide as best you can, label `unclear` if needed, and explain in
`rater_reason`. Please don't wait on an answer.
