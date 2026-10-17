# Manuscript and SI review (harsh-referee pass)

Contents: 1 Ground rules · 2 Review file structure · 3 Science checks · 4 Writing and flow · 5 Figures and tables · 6 References (Haiku field workers) · 7 Similarity scan · 8 Submission package (example journal) · 9 Iterating with the author

Default goals (override per project): survive desk rejection, get at most a major revision, and make **no over- or under-claims**. Every claim must be defensible.

## 1. Ground rules

- **Read-only unless told otherwise.** Do not edit `main.tex`, `supplement.tex` or `references.bib`. Write the review into `review_<date>/MANUSCRIPT_REVIEW.md` (round 2: `_ROUND2.md`). Keep the evidence (renders, scan outputs, raw Haiku reports) under `review_<date>/evidence/`. Confirm at the end that the source files are unchanged (timestamps or hashes).
- Compile copies in the scratchpad, never in the source folder. Watch out: writing terminal output to `main.out` overwrote hyperref's file.
- **Recompute every number** you can from the printed tables and the raw outputs. For example, rebuild B, G, E, ν, the Born criteria and the eigenvalues from the printed tensor. Check numbers against `CLAIMS.md` (records.md §7).
- **Every number you suggest must come from a raw file**, with path. If you estimate, write "estimate, recompute before use". In Project M a reviewer's gap estimate was pasted instead of the computed value (0.01 eV apart).
- Model rewrites (abstract, introduction) are references for the author to rewrite in their own voice; say so. Unless the author asks otherwise, address the **writing**: phrase style problems as writing problems, and keep AI-policy or AI-detection talk out of the review.
- Use an Opus critic and, if Codex is available, a Codex reviewer for an independent pass on science and claims. Use Haiku field workers for references, scans and figure crops (critique-protocol.md §5).

## 2. Review file structure

```
# Full review: "<title>"
## 0. Verdict and the top 12 fixes (overall judgement; scorecard: science, claims, writing, figures, references,
      submission package; top 12 ordered by how much a referee would care)
## 1. Wrongly stated: factual and technical errors (E1..; quote line, why wrong with evidence, fix)
## 2. Over-claimed (O1..; claim, why too strong, defensible wording)
## 3. Under-claimed (U1..; result the data supports, evidence path, where to say it)
## 4. Admissions that are not the norm, and how to remove them (A1..; cheap rerun or reword)
## 5. Writing, flow and style (measurements, habits, representative rewrites)
## 6. Figures and tables (per figure: collisions, sizes, consistency, caption accuracy)
## 7. Similarity scan against the local reference PDFs (method, result, sentence-by-sentence fixes)
## 8. Reference verification (bib corrections; citations that do not support their sentence; per-reference status;
      literature a referee will expect, DOIs to verify)
## 9. Citation placement: corrected brackets, sentence by sentence (before → after)
## 10. Submission-package check (journal requirements table)
## 11. Prioritised action plan (A text-only; B cheap computations; C stronger, still affordable)
## 12. Flow and line-by-line wording (paragraph-by-paragraph edit table)
```

Round 2 adds a table: "Earlier issue | Fixed / Partly / Open | Note". It must also look for **new errors introduced by the revision**, including errors that came from your own round-1 suggestions.

## 3. Science checks

- **Desk-reject triggers:**
  - placeholder figures or "V1" notes;
  - missing author, data or competing-interest statements;
  - a template title ("Structural, electronic, elastic and optical properties of X") with no physics hook;
  - a null headline;
  - an abstract that leads with a consistency check (B₀ ≈ B_R);
  - prose that reads like an audit log.
- **Reference state:** volume and shape errors stated plainly, with numbers, and their effect on headline magnitudes bounded (common-mistakes §1).
- **Signs and mechanisms:** recompute from the paper's own equations. In Project M the stated mechanism of an anomalous elastic sign was backwards.
- **Stability wording:** phonons, Born criteria and "dynamically stable" must match the evidence (verification-gates §9). Report the negative interpolated modes.
- **Gaps:** PBE path gap vs mesh gap vs HSE Γ gap; "direct" when the top band is flat; never "optical gap" from KS eigenvalues.
- **Comparisons with experiment:** the deposited CIF bonds and angles, not only lattice constants. "Agree within 1–3°" must be true for every entry.
- **Literature the referee expects:** for a framework compound this meant the classic rigid-unit tilting and negative-thermal-expansion literature, and the same structure type under pressure. Ask a field worker for a sweep, then check every hit yourself.
- **Under-claims:** results the data already supports, such as trends visible in existing pressure or EOS runs, comparisons with experiment the outputs already allow, sound velocities from the elastic tensor, and clamped-ion constants from the saved stresses.
- **Overdone:** sections a short condensed-matter paper does not need. Move them to the SI or cut them (unconverged RPA, the QA log).

## 4. Writing and flow

Measure first, so the comments are concrete:
- mean sentence length, and the count of sentences over 45 words (and the longest);
- counts of hedges and negations ("not", "does not", "sampled", "rather than", "retain", "sensitivity");
- repeated caveats: count each one and keep it **once**, ideally in a single Limitations paragraph;
- undefined abbreviations (VBM, CBM, PDOS, QE, DOS before definition);
- notation drift (4×4×4 vs 4³, "Young modulus" vs "Young's modulus", three words for one structural unit);
- internal workflow words in the text ("step-93", "CONTINUE disposition", "optical-source dataset", "XML eigenvalues absent from the local archive").

Flow:
- Does each section answer one question?
- Is Methods content announced and then never used (Project M: D3 relaxations never discussed)?
- Are related results split across sections?
- Does each paragraph end on a result rather than a defensive clause?

Give a paragraph-by-paragraph edit table (line → problem → suggested wording).

## 5. Figures and tables

Render every figure **as it prints**: compile, extract the pages at 300 dpi, then crop and zoom each panel. If the user asks for a delay before a re-read (e.g. 30 min while figures regenerate), wait the full time.

Check:
- panel labels (a), (b) and in-plot notes sitting on data or axes; radial tick labels on polar curves; legends covering curves;
- text under 7 pt at final width (subscripts about 6.3 pt are acceptable);
- inconsistent colours or markers for the same compound across figures; italic vs upright symbol clashes (legend "c" vs panel "c");
- plotted settings that the SI marks as failing (a broadening that fails the mesh test);
- captions that disagree with the panels (e.g. "central panels" pointing at the wrong ones);
- orphan figure files and SI order;
- tables: no vertical rules (journal style); captions that collide with the table; over-wide tables (check the overfull box warnings in the log).

## 6. References (Haiku field workers)

1. Extract each citation key with its citing sentence(s) into batch files of about 6–8 references.
2. Dispatch parallel Haiku agents (Project M used 8) using the critique-protocol §5 prompt. Each checks the Crossref metadata (title, authors, journal, year, volume, issue, pages, DOI) and whether the source supports the sentence: abstract, or full text if a local PDF exists. Verdicts: SUPPORTS / PARTIAL / NO / CAN'T-TELL.
3. Verify the key experimental reference yourself against its local PDF: the lattice constants, bond lengths and deposit numbers all depend on it.
4. Re-check every NO, PARTIAL and metadata mismatch yourself before reporting it. Overrule an agent when the evidence says so, and say that you did.
5. Report bibliography corrections, citations that do not support their sentence, and corrected citation brackets (placement before the period, ranges [3–5], merged duplicates).

## 7. Similarity scan

- Extract text from the manuscript, the SI and every local reference PDF (in a scratchpad venv).
- Find verbatim 6-gram overlaps, then run a sentence-level fuzzy match (Jaccard plus a difflib ratio) for close paraphrase, which is what iThenticate flags.
- Ignore boilerplate (method names, standard declarations). For each real hit, give the source sentence and an easy rewrite. A textbook definition can usually just be deleted.

## 8. Submission package (example: an Elsevier condensed-matter journal)

From the journal's author guidelines as summarised on 13 Oct 2026. Re-check the live guide before submitting.

| Item | Requirement |
|---|---|
| Source files | editable .tex or .docx (a PDF is not accepted as source); elsarticle encouraged |
| Title page | full names, affiliations, one corresponding author with email |
| Abstract | ≤ 250 words, stands alone, no references |
| Keywords | 1–7 |
| Highlights | required: 3–5 bullets, ≤ 85 characters each, separate file named "highlights" |
| Cover letter | ≤ 1 page, with a Statement of Novelty: one paragraph ≤ 120 words (motivation, original results, advance) |
| CRediT, competing interests, funding | required statements |
| Data availability | required; Option C (deposit and cite, or explain) |
| Generative-AI declaration | the journal requires one before the references when AI tools were used; the wording is the author's decision |
| References | numbered [1] in order of citation; DOIs |
| Figures | separate files, vector or ≥ 300 dpi, readable for colour-blind readers |
| Tables | editable, no vertical rules |
| Typical size | about 3000–6000 words, 3–5 figures, 30–50 references |

## 9. Iterating with the author

- Authors often revise between rounds. Re-read the new source (check timestamps) before every round, and say which version you reviewed.
- Answer "did you fix X?" honestly. In a read-only review, nothing was fixed; then re-check the revised text against every earlier point.
- Remove sections the user asks to remove, and keep the item numbering stable (replace an item's content rather than renumbering).
