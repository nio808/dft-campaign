# Common mistakes: what went wrong, why, and the gate that prevents it

Read all of this before planning a campaign. Each entry follows the same pattern:
- **What happened**: the real case and the project it came from
- **Why**: the mechanism
- **Fix**: what repaired it, or would have
- **Gate**: the check that prevents it now

Sources (anonymised: the projects were unpublished when this was written, so compositions are omitted and results appear only as rounded magnitudes where a lesson needs them):
- **A** = Project A: anion ordering against octahedral tilting in a three-composition mixed-anion series, 20- and 40-atom cells, five rented boxes.
- **M** = Project M: two isostructural framework compounds (M1, M2); structure, elastic tensors, phonons, EOS, pressure and optics.
- **Y** = Project Y: hydrogen ordering in an intermetallic hydride.

Method numbers (cutoffs, tolerances, timings, ranks) are kept as measured.

Contents: Science 1–12 · Numerics and parsing 13–20 · Operations 21–34 · Records and writing 35–42

---

## Science

### 1. The volume we never got right (M). The most expensive lesson.
- **What happened.**
  - PBE relaxed M1 about 5% and M2 about 10% too large in volume, and **reversed the experimental c/a ordering** between the two compounds.
  - Both a and c came out too long, a much more so for the compound with the larger cation.
  - **The functional comparison put the error in the polyhedral rotation, not in the bonds.**
    - PBE, PBEsol and D3 gave nearly the same bond lengths (within ~0.01 Å of each other).
    - Their volumes differed through the soft cation–anion–cation bridge angle, which moved by about 15° across the three functionals.
  - **The experimental bridge angle was never measured in this workflow.**
    - The starting anion site was built as regular polyhedra at the reported bond lengths, so the "experimental" bridge angles were constructed, not measured.
    - The deposited CIFs were not read until the manuscript stage.
    - So the decisive angle could not be compared with experiment when it mattered, and a reviewer flagged the "unverified experimental geometry".
  - Each fix repaired one quantity and broke another:
    - PBEsol fixed one compound's volume, but c/a stayed reversed.
    - PBE-D3(BJ) brought both volumes within ~1.5%, but made c/a worse.
    - Hydrostatic pressure to the experimental volume matched V within 0.1%, but the shape stayed wrong (a too short, c too long, by ~1–2%).
  - The elastic tensor at the experimental volume was started last and then deferred when the budget shrank.
  - Result: every headline mechanical number rested on the state with ~10% too much volume. A key anisotropy ratio fell by about 10% at the experimental volume. Both manuscript reviews named this the most likely referee request.
- **Why.**
  - GGA underbinding of an ionic framework is amplified by a rigid-unit rotation mode that costs almost no energy. A tiny energy error becomes a large volume and shape error.
  - The rotation also sets c/a, so no functional fixed both at once.
  - The problem was characterised early (the first vc-relax flagged the bridge opening within minutes), but treated as a side table rather than a design decision.
  - Without the measured anion coordinates, nobody could say which functional got the rotation right.
- **Fix.**
  - Read the deposited CIF (bond lengths **and** bridge angles) at Phase 1.
  - At the reference-structure step, tabulate V, a, c, c/a, the bond lengths (`structure_gate.py --shell`) and the bridge angles (`--bridge`) for PBE, PBEsol and D3 against the measured structure. Decide whether the error sits in the bonds or in the rotation.
  - If no functional gets both volume and shape, carry the headline property at **two reference states** from the start. The decisive check is one tensor at a better-volume state, about 25 strained relaxations per compound.
  - That check outranks optional extras (RPA ladders, extra phonon post-processing) in the budget.
- **Gate.** verification-gates.md §5. The reference-state decision is a critic-reviewed decision (D-id) **before** any expensive property step.

### 2. Comparing structures that were not given the same freedom (A, Y)
- **What happened.**
  - Project A's first headline ("one composition switches to the other ordering") compared a **tilted** cell of one ordering against an **untilted** cell of the other. With tilts allowed on both sides, the original ordering came out lowest by tens of meV per formula unit at matched settings. The hypothesis had not failed; the comparison was unfair.
  - In Y, 19 of 22 census relaxations ran under symmetry constraints and only three unconstrained: a symmetry-biased census.
- **Why.** Each candidate's energy reflects the relaxation freedom it was allowed. Tilts or symmetry breaking can be worth tens of meV per formula unit.
- **Fix.** Give every competitor the same supercell and the same tilt and symmetry freedom. Report "within the sampled models" otherwise.
- **Gate.** verification-gates.md §6 checklist. The launch review asks "is the comparison fair?" explicitly.

### 3. Convergence tests on the wrong pair (A)
- **What happened.** The cutoff, k and smearing tests for one composition were run on a proxy pair separated by ~60 meV/f.u. The headline pair was separated by only a few meV/f.u. The tests were not error bars for the headline.
- **Fix.** Run one-parameter tests on the decisive pair at fixed geometry and report pair shifts (both sides). After the fix, the decisive pair's shifts were below 1 meV/f.u. against a margin of tens.
- **Gate.** The post-result review Q3 asks "which pair do the tests bound?"

### 4. The closest competitor was not stationary at the final settings (A)
- **What happened.** The coarse relaxation converged. The static at the denser k mesh then showed a maximum force component about 13× the threshold and about 1 kbar of stress. A few-meV claim rested on an unrelaxed endpoint; the fine-grid relaxation moved it by about 0.1 meV/f.u.
- **Fix and gate.** Accept an endpoint only if the forces in the **final static** pass (verification-gates.md §4). Chain coarse → fine → static.

### 5. Wrong-stoichiometry lineage (A)
- **What happened.** One structural lineage had the two anion counts swapped (one anion too many of one kind, one too few of the other) and ran alongside the right one. Its elastic, phonon and Debye numbers had to be withdrawn and quarantined.
- **Gate.** A formula-per-f.u. check in every FORMULA-CHECK and in every scheduler follow-up (`scripts/structure_gate.py --formula`).

### 6. Pseudopotential family chosen before the property list (M)
- **What happened.** A PAW plus ultrasoft pass ran through the force check. Then `epsilon.x` and Yambo were found to need norm-conserving potentials. The pass was discarded.
- **Fix and gate.** Phase 0 lists every property code and checks its pseudopotential support before Phase 1. Check ghost states before any empty-band work: a two-electron alkaline-earth NC potential had a ghost about 80 eV above the Fermi level, so the semicore (s+p) variant was used.

### 7. Prior art missed (A)
- **What happened.** A 2018 paper had already reported the same ordering preference for one of the three compositions. The manuscript did not cite it, and a referee would have caught it at once.
- **Gate.** A Phase 0 literature sweep (field workers plus your check). The critic asks "what is already published?"

### 8. Interpolated negative phonon modes and ASR choices under-reported (M)
- **What happened.**
  - The "simple" ASR moved a grid mode by about 5 cm⁻¹, and the raw Γ acoustic modes sat near 24 cm⁻¹.
  - The interpolated grid of one compound dipped to about −60 cm⁻¹, but the main text listed only the passing modes.
- **Fix.** Compare ASR variants. Word the claim as "positive on the sampled grid and at Γ after ASR". Report negative interpolated modes plainly. Keep the HOLD until resolved.

### 9. Frozen-phonon supercell on the wrong axes (Y)
- **What happened.** A supercell meant to freeze the (0, ½, ½) soft mode doubled a and b instead of b and c. A "stable" claim based on it was retracted.
- **Gate.** Before running, check that the supercell basis is commensurate with q, and run ± displacements.

### 10. A per-cell number compared with a per-f.u. number (Y)
- **What happened.** A constraint cost per cell (three formula units) was compared with RT per formula unit. The conclusion flipped.
- **Gate.** Units and normalisation in every table header. The critic checks normalisation.

### 11. The functional-dependent claim stated as physics (A, M)
- **What happened.**
  - One composition's energy ordering differed in sign from a cited HSE06 result, and the U value was a proxy taken from a different compound.
  - "Missing dispersion is the likely cause" was attributed to D3 without evidence.
- **Fix.** Keep claims at "static PBE within the sampled models". Run a matched functional check only for claims that cross functionals.

### 12. Claiming mechanisms the data do not show, and missing ones they do (M)
- **What happened.**
  - The mechanism for an anomalous elastic sign was stated backwards: the term cited as driving it actually weakens it.
  - Meanwhile the saved pre-relaxation stresses already showed the real mechanism: comparing the clamped-ion constants with the relaxed-ion ones pinned it on internal relaxation.
- **Fix.** Before writing a mechanism, look at what the existing outputs contain. Recompute every sign from the paper's own equations.

## Numerics and parsing

### 13. Spin-polarised, symmetry-free, creeping relaxations (A)
- **What happened.**
  - A 40-atom relaxation took about 20 h and still had not converged.
  - Causes:
    - nspin=2 on a non-magnetic cell: 2× cost, a wandering moment, and a first SCF of 119 iterations;
    - "No symmetry found" from a rattled ML seed: 36 k-points and all 120 coordinates free, although the cell had monoclinic symmetry within 0.01 Å;
    - a BFGS trust radius stuck at 0.01–0.02 bohr along soft tilt modes.
- **Fix.** Relax NM when matched controls show |NM − SP| ≲ 0.1 meV/f.u., then run an SP static. Symmetrise the seed. Pre-relax on a coarse mesh. Restart from the last geometry. Set a hard time cap for the job.

### 14. Pool layout that crippled a big cell (A)
- **What happened.** 18 pools × 2 ranks ran at 259–336 s per SCF iteration against about 45 s for an earlier 36-rank, 6-pool layout of the same cell on another box. Relaunching at 6 ranks per pool gave 2.2× at equal work.
- **Gate.** Measure s/iteration within the first 30 minutes against a reference layout, and fix the layout from that measurement. For these 40-atom cells, ≥ 6 ranks per pool was the measured answer (benchmarks.md §4.1).

### 15. SCF sloshing in magnetic cells (A)
- **What happened.** One composition's tilted cell sloshed (accuracy 0.08–4.8 Ry at iterations 30–70) under default mixing, and again under local-TF from a rattled start.
- **Fix.**
  - Numerical-only changes first, after review.
  - Then a symmetric start, with its limitation stated: the tilted structure of a sister composition, with the cation swapped and the cell scaled to the right volume.
  - Gentler mixing (β 0.2, ndim 16) finally converged it.
- **Never** change the functional, pseudopotentials, cutoffs, smearing or spin to get convergence.

### 16. "JOB DONE" taken as success (A, M, Y)
- **What happened.**
  - pw.x prints JOB DONE after stopping at `electron_maxstep`.
  - An EXIT-file stop prints "Program stopped by user request" and then JOB DONE.
  - IEEE_INVALID_FLAG notices follow normal finishes in some builds; they are harmless, but check for non-finite values.
- **Gate.** Strict outcome classification (vm-campaign.md §6). Rename or label EXIT-stopped outputs.

### 17. Parser read the wrong field (M)
- **What happened.** The optics validator read Yambo's bare `[X]` gap instead of the scissor-corrected `[X+QP]` gap, so a correct run "failed".
- **Gate.** Test parsers on real outputs, with a self-check on known good and bad cases. A parser change gets a critic review before deployment.

### 18. Gates that pass on missing data (M)
- **What happened.** A NaN-skipping `max()` in the elastic and EOS gates, and a force check that accepted a file with a deleted atom line.
- **Gate.** Require every atom exactly once and finite values; reject NaN explicitly. Self-test with corrupted inputs (the `scripts/fcheck.py --check` pattern).

### 19. Unit conversions (Y, M)
- **What happened.**
  - ASE converts Ry→eV with CODATA-2006, so subtracting raw Ry energies from ASE energies left a 0.19 kJ/mol error.
  - PseudoDojo cutoff hints are in hartree.
  - Pressure printed at 0.01 kbar resolution created a false "tie" in a convergence ladder.
- **Gate.** Raw `!` lines for all energy differences. Pressure from the stress tensor. Units in every `.dat` header.

### 20. k-path and projwfc traps (M)
- **What happened.**
  - A crystal_b weight of 0 generates no points in QE 7.x (caught before launch).
  - projwfc.x died in `d_matrix` under rhombohedral symmetry.
  - A DOS written on a coarse grid integrated to well short of the valence electron count.
- **Gate.** verification-gates.md §7.

## Operations

### 21. Shared or overloaded rented boxes (A)
- Box A was a slice of a shared host (about 8 core-equivalents).
- Box B was about 7× slower than box 1 on the same 8-rank 5-atom input (39.5 against 5.5 s per iteration; 1-core dgemm 5.6 GFLOPS).
- Both were caught only by benchmarking. Gate: vm-campaign.md §2 before any production job; numbers in benchmarks.md §3.

### 22. Paying for hyperthreads and GPUs (A)
"50% CPU" alarmed the user. It was 64 of 128 logical CPUs, i.e. full use. Measured SMT made things worse (80 → 445 s per iteration). The GPUs were useless for CPU QE. Rent by physical cores.

### 23. Pattern kills over ssh (A, Y)
`pkill -f qsched.py` matched the agent's own ssh shell and killed the scheduler. `pgrep -f` wait loops never ended and left a GPU idle for 80 min. Gate: hard rule 1.

### 24. Orphaned loops and duplicate runners (A)
- Six concurrent watchers ran, because the monitor tool's expiry on Windows did not kill bash loops. They multiplied the ssh polling and created extra follow-up jobs.
- A stopped launcher's orphan started a second runner on occupied cores (16 ranks on 8 CPUs).
- Gate: pid files plus a `ps` check after stopping anything.

### 25. Truncated "read-only" dry run executed a launch (A)
A `head -n -1` copy of a state-changing script, whose truncation grep did not match, ran the whole script on a live host without clearance. Gate: hard rule 2. Write probe-only scripts.

### 26. A watcher outliving its box (A)
After box D moved to another project, Project A's watcher logged 160+ ssh failures over three days into the runbook. Gate: touch WATCH-STOP at release (vm-campaign.md §11).

### 27. Disk exhaustion (M, Y)
- ph.x electric-field scratch (dwf, ebar, mixd, recovery, about 1 GB each) was never estimated. The overlay filled up, and one compound's run crashed with davcio error 22.
- `/dev/shm` filled with leftover wavefunctions, and later jobs died in write_rhog.
- Gate: measure peak scratch first, clean scratch per job, hard stop below 5 GB free.

### 28. OOM under cgroup caps (Y)
`-nk` = ranks for large cells used 9–11 GB per rank, and every job was killed (13 OOM kills under a 277 GB cap). Gate: estimate per-rank memory from the first job's VmRSS against `memory.max`, and watch `memory.events`. Here nk ≤ ranks/4 fixed it.

### 29. mpirun hangs silently on vast (Y)
Even `mpirun -np 1 hostname` hung. The cause was hwloc's gl plugin, not sshd. Fix: `HWLOC_COMPONENTS=-gl,-opencl,-cuda,-nvml`.

### 30. Default MPI binding overlapping jobs (M)
Open MPI 5 ignored the MCA env var and pinned six jobs to cores 0–15. They were killed and relaunched. Fix: taskset plus `--bind-to none`.

### 31. Sync clobbering local edits (Y, M)
A periodic `rsync -a` into the working folder reverted a citation block. A pull overwrote an uncommitted test fix during a takeover. Gate: mirror folders, hash verification both ways, and pausing sync before editing mirrored files.

### 32. A scheduler change that crashed or misfired (A)
- Dict mutation during iteration would have crashed at the first follow-up (caught by the Codex review).
- A name rule matched `_n8_` and set npool 1.
- An inline edit with a syntax slip stopped the scheduler.
- Gate: offline tests, syntax checks, uploaded restart scripts, and `nat` stored in the job record.

### 33. Stale cached results (M)
One review returned STOP: upstream data in the cache was stale, and a failed rerun could inherit a sidecar stamp. Fix: hash the input, DEPS and UPFs, and remove the stamp before rerunning.

### 34. Open-ended runs against a fixed budget (A)
The user stopped the 1–2-day probes, because a lot had already been spent. Fix: offer bounded arguments and hard caps up front, and pre-register what each probe would change.

## Records and writing

### 35. Timestamps written by hand (A, Y)
Rows were stamped 5–14 min ahead of the clock in A, and up to an hour ahead in Y. Fix: `logbook.py` stamps the real clock.

### 36. Claims from memory (A)
An author list and a "one monitor running" statement were both wrong and had to be corrected. Fix: verify before writing. Corrections are appended, never edited.

### 37. Handoff and STATUS treated as truth (A)
Old host statuses were read as live. Two "nearly finished" 40-atom attempts lacked even one converged SCF energy. Fix: the session-start protocol (records.md §10).

### 38. Audit-log prose in the manuscript (M)
- Counts: 48 "not", 25 "does/did not", 20 "sampled", plus internal workflow terms ("optical-source dataset", "CONTINUE disposition", "step-93").
- The same caveat appeared up to 7 times.
- Fix: one Limitations paragraph; elsewhere, say what was done and what it shows.

### 39. Reviewer suggestions pasted as facts (M)
- The reviewer's interpolated gap estimates went into the paper instead of the computed values (0.01 eV apart, but not computed).
- The reviewer's wording ("every coefficient is smaller for M2") was wrong for one coefficient.
- The drafted abstract and introduction were pasted almost verbatim.
- Fix: compute every number a reviewer gives from a raw file, and cite it. Label estimates as estimates. Model text is an example to rewrite, not text to paste.

### 40. Front matter left unfinished (M)
A placeholder structure figure, a "V1 for author revision" note, and missing author or data statements are desk-reject triggers. Fix: the submission checklist in manuscript-review.md.

### 41. Figures not at print quality (M)
- Panel labels sat on the data, and text was 4.8 pt at column width.
- A broadening width that the SI marked as failing was plotted.
- Fix: render at final size and inspect each panel (manuscript-review.md §5).

### 42. Text overlap with source papers (M)
Several introduction sentences were patchwritten from a cited paper. Fix: a 6-gram plus fuzzy-sentence scan against the local PDFs, then rewrite each hit.
