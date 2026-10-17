# Case studies: the projects this skill came from

Three real Quantum ESPRESSO projects. They were unpublished when this skill was released, so they are described here without compositions, and results appear only as rounded magnitudes where a lesson needs them. What is kept is how each was run, what records it kept, and how it ended. Measured machine and layout numbers from all three are in `benchmarks.md`; their mistakes are in `common-mistakes.md` (tags A, M, Y).

## Project A: anion ordering against octahedral tilting (three compositions)

- **Question:** which of two anion orderings is lowest across a three-member series, and how octahedral tilting competes with the ordering.
- **Hamiltonian:** QE 7.3.1 built from source, PBE, SSSP 1.3.0 efficiency pseudopotentials (GBRV ultrasoft and PSLibrary PAW/US), 60/480 Ry set by the hardest element, Gaussian smearing 0.01 Ry, spin-polarised starts. k from spacing rules: 0.3 Å⁻¹ coarse, 0.2 fine and static, 0.15 test, after a published high-throughput protocol.
- **Arc:**
  1. **Census.** Cite files C001–C066 cover a large census on several rented hosts, with an ML pre-screen used only to seed candidates. A wrong-stoichiometry lineage was quarantined. The first headline said one composition switches ordering.
  2. **Audit.** An internal audit found three problems: the closest competitor was not relaxed at the final settings, the convergence tests were on the wrong pair, and the 40-atom attempts had no converged energy.
  3. **Tilt-resolved campaign (C067).** Two days on boxes 1, 2, A, B and D. Tilts were allowed on both sides at matched fine-grid settings, and the pre-registered decision rule set the wording.
  4. **Bounded close.** The user cut all 1–2-day probes and replaced them with bounded arguments.
- **Records that worked well (the models for this skill's templates):**
  - `RULES-HARD.md` (R1–R13);
  - a single `RUNLOG.md`;
  - `02-citations/` with START/DONE cite files and a per-parameter cite table;
  - `12-critique/` with 383 review files, each with its prompt;
  - a scheduler, status script and watcher per box;
  - a scripted input generator;
  - a handoff file per campaign;
  - a publication audit script.
- **Ending state:** the manuscript needs rewriting around the tilt-resolved result. Box D moved to Project M, and Project A's watcher kept logging ssh failures (common-mistakes §26).

## Project M: two isostructural framework compounds (structure, elastic, phonons, optics)

- **Question:** structure, elastic, electronic and optical properties of two isostructural trigonal framework compounds (8-atom primitive cell).
- **Hamiltonian:** QE 7.5 (conda-forge), PseudoDojo NC SR v0.4.1 PBE standard (semicore variants where needed), 90/360 Ry, 4×4×4 Γ-centred mesh. On top of that:
  - Yambo 5.3 for independent-particle optics;
  - HSE06 Γ gaps;
  - DFPT phonons on a 4³ q grid;
  - PBEsol and PBE-D3(BJ) structure tables;
  - a third-order Birch–Murnaghan EOS and a pressure series;
  - cells at the experimental volume.
- **Hosts:** a local WSL machine (first compound, early steps), a GCP 8-core box (second compound), vast box D (64 cores, most steps) and box E (elastic).
- **Arc:**
  1. **Per-compound trees.** Per-step convergence and gating records, with reviews R1–R31.
  2. **Box D master plan.** A decision log with reviews RD1–RD28, including a six-area independent audit.
  3. **Codex close-out.** A second agent took over orchestration for a 6–7 h journal close-out. The experimental-volume elastic tensor was deferred.
  4. **Manuscript.** Two harsh manuscript reviews, then a prepared submission package.
- **Records that worked well:**
  - shared helpers with cache stamps;
  - a force/stress gate with a self-test (generalised as `scripts/fcheck.py`);
  - a queue runner that reserves QUEUED as well as RUNNING cores;
  - an acknowledged sync;
  - a build-identity gate;
  - deploy manifests with hashes;
  - a disk-incident report;
  - a journal-requirements summary.
- **Ending state:** submission files prepared. The recorded referee risks are the PBE volume and shape error with no tensor at a better-volume state, a phonon acoustic-sum-rule HOLD, and DOS mesh failures at the finest broadening.

## Pseudopotential verification, as practised (worked pattern for verification-gates §1)

Each project kept one row per element in its `pseudo/README.md`, every column read from the file itself:
- the file name and its library and version (separate from the generator version);
- type (NC, US or PAW), functional, z_valence and NLCC;
- the valence configuration;
- the cutoff hint with its unit (PseudoDojo hints are in hartree);
- the ghost-state check;
- an md5/SHA-256 hash, verified on every host.

Two routes were used:
- **Route A (SSSP efficiency):** the cutoff pair is the maximum over elements of the SSSP recommendation (one light anion set 60/480 Ry), then confirmed by the project's own ladder.
- **Route M (PseudoDojo NC):** standard accuracy, semicore variants where a two-electron potential has a ghost state, and the hardest element's high hint as the ladder's upper end; the ladder kept 90 Ry.

Never copy hashes from a document; read them from the recorded files.

## Project Y: hydrogen ordering in an intermetallic hydride

- **Lessons folded into this skill:**
  - the ASE CODATA-2006 conversion;
  - pools against memory under cgroup caps;
  - `/dev/shm` cleanup;
  - pgrep self-match;
  - rsync clobbering edits;
  - the hwloc hang;
  - frequent sanity sweeps;
  - no compute on the workstation;
  - ETAs in hours;
  - making the logical call and logging it.
- **Sanity sweep.** A 10-minute lint plus job-health sweep that flagged:
  - duplicate namelist keys;
  - nspin without starting_magnetization;
  - a cutoff pair outside the documented set;
  - a missing pseudopotential or K_POINTS card;
  - SCF not converging, or sloshing;
  - more than 20 min per SCF step;
  - a crash without JOB DONE;
  - memory over 90%.

  `scripts/qe_lint.py` and `scripts/qe_status.py` generalise it.
- **Run-shape certification** on each new box (benchmarks.md §4.4) became this skill's validation gate.
