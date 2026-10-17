---
name: dft-campaign
description: Plan, run, verify, critique and record DFT research projects end to end — Quantum ESPRESSO pw.x/ph.x/projwfc.x/Yambo on rented vast.ai or cloud VMs — from pseudopotential and structure checks through convergence, relaxations and property runs (bands, DOS, elastic, phonons, EOS, HSE, optics) to a defensible journal paper. Every decision is cited and logged in every work folder; an independent critic model reviews each meaningful step and cheap subagents do field work. Includes measured benchmarks of rented boxes and parallel layouts. Use it whenever the user mentions DFT, QE, pw.x, Quantum ESPRESSO files, renting or preparing a compute box, MPI ranks or k-point pools, launching or monitoring remote jobs, convergence tests, a relaxation that will not converge, ranking structures by energy, critique of runs, a RUNLOG or citation chain, starting or resuming a computational materials project, moving a campaign to another machine, or a DFT-based manuscript, even without the words skill or workflow.
---

# DFT research projects on rented VMs

This skill carries one computational-materials project from question to submitted paper. It is distilled from two Quantum ESPRESSO projects carried to or near submission:

- **Project A**: anion ordering against octahedral tilting in a three-composition mixed-anion series. 20- and 40-atom cells on five vast.ai boxes.
- **Project M**: two isostructural framework compounds. Structure, elastic tensors, phonons, EOS, pressure, HSE and Yambo optics, on box D, box E and a GCP box.

Both were unpublished when this skill was released, so they are described without compositions, and results appear only as rounded magnitudes where a lesson needs them.

It also folds in the VM lessons of an earlier hydride project (Project Y). Summaries are in `references/case-studies.md`; measured machine, workload and parallel-layout numbers from all three are in `references/benchmarks.md`.

**Paths.** Every path in this skill is relative to the folder that holds this `SKILL.md`, wherever it is installed (`~/.claude/skills/dft-campaign`, `~/.agents/skills/dft-campaign`, ...). Below, `<skill-dir>` means that folder.

**Personal settings.** If `<skill-dir>/LOCAL.md` exists, read it first. It holds this user's own working agreement (time zone, where keys live, machine rules, standing orders) and overrides the defaults below. It is never published.

## Universal by design

Nothing in this skill is tied to one material, code build, box or journal:
- **Every physics value is the project's own.** Cutoffs, k spacings, smearing, U, thresholds, test parameters, strains, decision bands and reference energies are cited per project, in the folder `CITES.md` and in `qsched.json`.
- **The scripts hard-code nothing that decides a result.** Every physics value comes as an argument or from the project config; the few labelling, lint and alert heuristics have documented, overridable defaults. The scheduler refuses to start without a `qsched.json`, and the gate and ladder scripts require their tolerances on the command line.
- **Machine values are placeholders.** pw.x path, core count, host and key in `watch.sh`/`qsched.json` are set per validated box.
- **Numbers in these documents are worked examples** labelled with their project (A, M, Y). Examples: "1 meV/atom and 1 kbar", "≥ 6 ranks per pool for 40-atom cells", "about 3% volume error". They show what was decided and why. A new project re-derives and cites its own values; an old value is a starting point at best.
- **Code scope.** The parsers and the scheduler target Quantum ESPRESSO (pw.x outputs; ph.x/projwfc/Yambo get JOB DONE and convergence checks). The workflow itself (gates, critiques, citations, logs, VM practice) is code-agnostic; for another code, replace the parsers and keep everything else.
- **User preferences** (time zone, ETA style, where compute may run) are settings: defaults below, personal values in `LOCAL.md`, the log time zone per project (`logbook.py init --tz`).
- **Agent-neutral.** Written for Claude Code (subagents with `model: "opus"` / `"haiku"`, Codex CLI as the second family). On another agent, map the roles in "Agent roles" to what it has; the gates, citations and logs do not change.

## Six principles (each exists because something went wrong without it)

1. **Every number traces to a raw file; every parameter and every decision traces to a citation.** Any reviewer question ("why 60 Ry?", "why did you stop that probe?", "where does that energy difference come from?") is answered by lookup.
2. **Everything is logged where it happened and in one master place.** Each work folder carries its own `RUNBOOK.md`, `CITES.md` and `REASONING.md`, mirrored into the project's `MASTER-RUNBOOK.md`, `CITE-LOG.md` and `REASONING-LOG.md`. `scripts/logbook.py` writes both with the real clock.
3. **Gates are declared before their data exists.** This covers acceptance rules, convergence tolerances and the headline's pre-registered decision rule. A gate changed after seeing data is labelled post hoc.
4. **Every meaningful step gets an independent critique before the next one builds on it.** An Opus critic always reviews; Codex joins when installed. The verdict is saved before acting. These reviews caught a scheduler crash bug, a stale cache, a misread gap, a wrong frozen-phonon supercell and a k-path that would have skipped points.
5. **Verify, don't trust.** STATUS files, handoffs, summaries, earlier audits, subagent reports and your own memory are claims until re-derived from the raw `.out`. `DONE` means execution finished, not that the result is accepted.
6. **Journal parity (the target journal in `PROJECT.md`): nothing half-baked, nothing overdone.** Match what comparable papers report, close the gaps a referee will hit, and cut what nobody asked for.

## Working agreement (defaults)

These defaults came from direct corrections in past projects. Follow them unless `LOCAL.md` or the user says otherwise.

- **Agent roles.** A critic reviews every meaningful step, cheap subagents do the field work and the mechanical work, and a second-family reviewer is added when one is installed. Subagents cost usage: ask once per project before spawning them, unless `LOCAL.md` pre-authorises them. See "Agent roles" below and `references/critique-protocol.md`.
- **Every decision must be citable, with proper logs.** No input value, run, kill, move, gate or wording without a cite (VERBATIM / SoT / METHOD / USER / QEDEF) and a log entry. Run `scripts/logbook.py audit` before every review, push and manuscript pass.
- **No production compute on the workstation.** No pw.x, no ML relaxations, no multi-minute Python on the laptop. Write and statically check scripts and inputs locally; runs go on a rented or cluster machine. Parsing text outputs and syntax-checking scripts is fine.
- **ETAs in hours from now, with a spread** ("about 4–6 h"). Give clock times only if asked, in the user's time zone. Log stamps come from the real clock in the project's zone; `logbook.py` does this.
- **Make the logical technical call yourself** inside an approved plan, log it as a decision, and report what you chose and why. **Confirm first** before spending money (renting, extending, destroying boxes), before destructive actions on results, and before anything outward-facing (submission, public deposit, pushing to someone else's remote).
- **Use the box fully.** One MPI rank per physical core, no idle cores for more than about 15 minutes without a logged reason, and benchmark before moving jobs.
- **Read-only means read-only.** For a review, change nothing in the repo or on the box. Write findings into an organised `.md` file, with fixes as before → after text.
- **Short hourly checks.** Autonomous checks must be brief to save usage. Message the user only when a decision needs them.
- **The user owns figures, tables and prose** where the project says so (for example in its `AGENTS.md`). Supply verified numbers and suggestions.
- **Budget realism.** Users have cut 1–2-day runs mid-campaign (common-mistakes §34). Prefer bounded arguments and hard time caps over open-ended runs.
- **Secrets.** Never write an API key or private key into any file, log, memory or remote box, and never ask the user to paste one. Keys live in an env file outside every repository (its location goes in `LOCAL.md`): read the key into an environment variable for the one process that needs it, without printing or copying it. If a key was pasted into chat, tell the user to regenerate it.

## Agent roles

| Role | Agent | Use it for | Rule |
|---|---|---|---|
| Orchestrator | this session | Plans, decides, runs commands on boxes, edits files, writes every log entry | Never self-approves a launch or an acceptance |
| **Critic** | Opus subagent (`Agent`, `model: "opus"`, general-purpose), read-only | After **every meaningful step** (table below): physics, inputs, gates, code, fairness, wording | Prompt saved first, verdict saved verbatim in `12-critique/` before acting |
| **Independent critic** | Codex CLI at its strongest model (or `CODEX_MODEL` from `LOCAL.md`), `-s read-only`, if `command -v codex` succeeds | Launches, pivots and kills, convergence and reference-state decisions, headline results, area audits, manuscripts | Run in the background; if the model ID is rejected, use the config default, and always record which model ran |
| **Field workers** | Haiku subagents (`model: "haiku"`) | Reference and DOI checks (in parallel batches), verbatim quote harvesting for cite files, literature sweeps, output inventories and hash manifests, parsing many outputs into tables, warning sweeps, cite-coverage checks, figure-overlap inspection, n-gram similarity scans | Narrow task, explicit output format, evidence for every line. The orchestrator verifies before anything enters a log or the paper |

Meaningful steps, each followed by an Opus critique (and Codex where marked ★):
- Phase 0 charter and decision rule ★
- Phase 1 pseudopotential and structure gates
- Phase 2 convergence decision ★
- Phase 3 reference-state decision ★
- Phase 4 box validated
- Phase 5 every launch ★, with a STOP file until the verdict
- Phase 6 every relaunch, mixing change or replacement of a stuck job; every kill, pivot, migration or scope cut ★; every code or gate change on a live box ★
- Phase 7 every result before acceptance (★ for headline numbers)
- Phase 9 manuscript ★

At unmarked steps Opus alone is required; at ★ steps Codex is added whenever `codex` is installed. Without Codex, run two Opus critics with different briefs (physics and claims; operations and code) and record that the independent family was unavailable.

A critic must change nothing. After each one returns, check `git status --short` or file mtimes. Templates, commands and the Haiku prompt skeleton are in `references/critique-protocol.md`.

**On other agents** the roles map by capability, not by name:
- Critic: the strongest reasoning model available, in a fresh read-only context. That can be a subagent, or a separate headless run such as `codex exec -s read-only`, `claude -p` or `gemini -p` with the saved prompt.
- Independent critic: a model from a different vendor than the orchestrator.
- Field workers: the cheapest fast model, or the orchestrator itself in narrow, checked batches.

If no second model is available at all, run two critic passes with different briefs and record that independence was not available. The saved prompt, the saved verdict and the decision entry are mandatory on every agent.

## Starting, resuming and closing a session

- **New project:** `python3 <skill-dir>/scripts/logbook.py init <project> [--tz Area/City]`. This creates the charter, rules, status, handoff, the master logs, the claims and gates registries, `BOXES.md`, `pseudo/README.md` and the folders. Fill in `PROJECT.md` and get it critiqued, then create each work folder with `logbook.py step <folder> --purpose "..."`. Suggested numbering is in `references/records.md` §6.
- **Existing project with its own conventions** (e.g. a single `RUNLOG.md` plus numbered run folders, or per-box trees with a `PLAN.md`): keep them, and add `logbook.py step` logs to the folders that are worked on. The audit covers every folder that has a `RUNBOOK.md` and lists inputs no work folder covers.
- **Session start and end:** checklists in `references/records.md` §10. Start: read the handoff, status and runbook tail as claims, check the boxes live, re-arm the monitors, log a `CHECK` at project level. End: rewrite status and handoff, and say which monitors die with the session.

## Records in one paragraph

Every action produces a line, written to the folder `RUNBOOK.md` and to `MASTER-RUNBOOK.md` (project-level actions go to the master only):

```
- <date time> <zone label> | TAG | folder | what, with numbers | cites Cnnn | D-id
```

Every input key, pseudopotential, k mesh and decision-relevant number gets a row in the folder `CITES.md`, mirrored to `CITE-LOG.md`. Every decision gets a `D-YYYYMMDD-NN` entry (Question, Options, Evidence, Reviews, Choice, Why, Cites, Reversal condition) in the folder `REASONING.md`, mirrored to `REASONING-LOG.md`. Campaign-level justifications live in `02-citations/Cnnn-<slug>-START.md` and `-DONE.md`, which hold verbatim sources. Every number meant for the paper gets a row in `CLAIMS.md` with its evidence and allowed wording. Corrections are appended, never edited. Commands and formats: `references/records.md`.

```
LB=<skill-dir>/scripts/logbook.py
python3 $LB log    <project>  CHECK "session start: boxes checked live"           # project-level line
python3 $LB decide runs/31-x --question ... --options ... --evidence ... --reviews "<ID>-opus ..." --choice ... --why ... --cites ...
python3 $LB log    runs/31-x LAUNCH "36 ranks npool 6 cpus 0-35" --cite C067 --decision D-YYYYMMDD-NN
python3 $LB cite   runs/31-x --param "degauss = 0.01" --type VERBATIM --source "\"...\" (C051:4-20)" --id C051
python3 $LB user   <project> --quote "<the user's exact words>"                  # -> USER-YYYYMMDD-HHMM
python3 $LB gate   runs/31-x --gate "max force, final static" --threshold "< 1e-4 Ry/bohr"   # declared before data
python3 $LB claim  <project> --claim ... --evidence ... --status ACCEPTED --wording ... --critic ...
python3 $LB audit  <project>   # uncited keys/cards, unknown cite/USER/review IDs, LAUNCH/KILL/... without a decision
```

## The project lifecycle

Work through the phases in order. Each one ends at a gate, then a critique, then a logged decision. A failed gate stops the phase: investigate it; do not loosen it or blindly retry.

### Phase 0: scope the claim before computing

- Write the charter. It names the question, the properties needed, and the **pre-registered decision rule** for the headline. Project A used: "E(I) − E(II) < −10 meV/f.u. → I lowest; |ΔE| ≤ 10 → near-degenerate, matched tests decide the wording; > +10 → II stays lowest."
- Literature first. Haiku sweeps list prior work and comparable papers with DOIs, convergence levels and reported properties; you verify them. Project A missed a 2018 paper that had already reported the same ordering for one of its compositions.
- **Choose one Hamiltonian that serves every planned property.** Project M discarded a finished PAW/US pass because QE `epsilon.x` and Yambo need norm-conserving potentials.
- Estimate cost from a timing pilot, and set a hard cap per job.
- → Opus ★ critique of the charter, then a decision entry.

### Phase 1: inputs (pseudopotentials and structure)

- **Pseudopotential gate, per element.** Check the table and version (separate from the generator version), the UPF header (NC/US/PAW, functional, z_valence, NLCC), the valence configuration and resulting electron/band count, ghost states when empty bands matter, cutoff hints with units (PseudoDojo hints are hartree; 1 Ha = 2 Ry), and identical hashes on every tree and host. Details: `references/verification-gates.md` §1.
- **Structure gate.** Check the transcription against the experimental paper. Take the space group from the Wyckoff sites (a dropped overbar in the printed symbol was a trap), then confirm the QE operation count. Check the formula per f.u. and the coordination **including periodic images**. Read the deposited CIF when one exists. Project A ran a whole wrong-stoichiometry lineage (two anion counts swapped), now quarantined. Run `scripts/structure_gate.py` and write `FORMULA-CHECK.md`.
- **Cite every parameter** in the folder `CITES.md`, using the inherited parent inputs, literature quotes (Haiku harvests them, you spot-check) or labelled METHOD reasons.
- → Opus critique, then a decision entry.

### Phase 2: convergence

- Change one parameter at a time at fixed geometry. Judge energy per atom **and pressure**, read from the stress tensor (stress drives vc-relax, EOS and elastic constants). Declare the tolerances with `logbook.py gate` before the ladder runs, then apply them with `scripts/conv_ladder.py`. Example (M): within 1 meV/atom and 1 kbar of the tightest point, with every tighter point also passing. That kept 90 Ry; 80 Ry passed on energy but failed on pressure by 1.6 kbar.
- **Test the pair that decides the claim, not a proxy.** Project A's tests were run on a proxy pair ~60 meV/f.u. apart while the headline pair was a few meV/f.u. apart. Report **pair shifts**.
- k meshes come from a spacing rule recomputed for each actual cell: n_i = max(1, ceil(|b_i| / spacing)), with the 2π included.
- → Opus ★ critique of the kept values, then a decision entry.

### Phase 3: the reference structure, and the volume trap

- Accept a relaxation only after a final SCF with fresh G-vectors. The largest force component must be below threshold **at the final k mesh and cutoffs**, the stress below `press_conv_thr`, and the symmetry retained. Project A's closest competitor carried a residual force 13× the threshold after the grid changed.
- For soft frameworks, run a two-start check: both starts must reach the same minimum.
- **Compare against experiment before building on the structure.** Tabulate V, a, c, c/a, bond lengths (`structure_gate.py --shell`) and bridge or tilt angles (`--bridge`) for PBE, PBEsol and PBE-D3(BJ), against the **measured** structure from the deposited CIF. Decide whether the error sits in the bonds or in the rotation. Declare a threshold (the M hindsight value is about 3% in V, plus the right shape ordering). If it is exceeded, **decide now** which reference state carries the headline properties, and budget a second state from the start.
- This is the mistake Project M never recovered from:
  - PBE overestimated V by about 5% and 10% for the two compounds, and reversed their c/a ordering.
  - The three functionals agreed on the bonds and differed in a soft cation–anion–cation rotation (about 15° apart), so the error sat in the rotation. The measured anion positions had not been read, so nobody could say which rotation was right.
  - PBEsol and D3 each fixed one quantity and broke another, and were only side tables.
  - The experimental-volume tensor was started last and then deferred, so every headline mechanical number rested on the state with ~10% too much volume.
  - Full story: `references/common-mistakes.md` §1.
- → Opus ★ critique of the reference-state decision, then a decision entry.

### Phase 4: rent and prepare the box

Full procedure: `references/vm-campaign.md`.

- Rent whole machines with the most physical cores. vast's `cpu_cores_effective` counts threads, and the GPUs are useless for QE. The user confirms the money. Record the box in `BOXES.md`.
- **Benchmark exclusivity** before trusting a box: the same small input solo and four at once, plus a one-core dgemm. Two of five Project A rentals were shared or overloaded. Compare against the measured boxes in `references/benchmarks.md`.
- Usable cores are the cgroup `cpu.max` quota, not `nproc`. Project A's first night ran 188 ranks on a 46-CPU quota.
- Build QE with the earlier runs' flags, or use package-identical conda builds. Verify the pseudopotential hashes on the box.
- **Validation gate:** earlier production inputs, with only `pseudo_dir`/`outdir` changed, must reproduce the energy to every printed digit. Run `scripts/box_check.sh` for the limits, the dgemm check and `--validate`. Deploy scripts with `scripts/deploy.sh`, which checks SHA-256 on both sides.
- Container MPI environment: `OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HWLOC_COMPONENTS=-gl,-opencl,-cuda,-nvml`, plus `taskset` on disjoint core lists with `mpirun --bind-to none`.
- Read the real limits: `/sys/fs/cgroup/cpu.max`, `memory.max`, `df -h / /dev/shm`. The disk is not persistent.
- → Short Opus critique of the box and job layout, then log it.

### Phase 5: launch

- Generate inputs with a script, never by hand. Run `scripts/qe_lint.py` on every input; `--compare <parent.in>` must show only the intended differences. Run `scripts/structure_gate.py` on every geometry.
- **Launch review** ★ on the inputs, scheduler and plan, with a `STOP` file in place. Codex returned "LAUNCH=NO" on Project A's C067 launch because the scheduler would have crashed at the first follow-up. Fix, re-test offline, then lift the STOP.
- Use one scheduler per box (`scripts/qsched.py run`; offline-test it first with `qsched.py offline-test`). It reads every physics and machine value from the project's cited `qsched.json` (example in `assets/examples/`). It chains coarse relax → fine relax → static → matched tests, with a structure gate on every child.
- Arm the monitors (Phase 6). Log the START cite file, the LAUNCH lines and the decision entry.

### Phase 6: run and watch

- **Box side:** the scheduler logs START/END/FOLLOWUP, hard-stops at free disk < 5 GB or MemAvailable < 12 GB, and never retries a failure.
- **Laptop side:** one `scripts/watch.sh` per box, kept awake (`caffeinate` on macOS). It mirror-rsyncs every 10 min, runs `qe_status.py` on the box, and appends alerts to `ALERTS.txt` and `MASTER-RUNBOOK.md`. Stop it with `WATCH-STOP` when the box is released: Project A's watcher logged 160+ failures for three days after Box D left the project.
- **Agent side:** an hourly check (template in `references/vm-campaign.md` §7) and an alert watch on `tail -n 0 -F ALERTS.txt` (Claude Code: session cron plus `Monitor`). Both die with the session unless a system scheduler runs them.
- Diagnosing a stuck job: read the raw `pw.out`/`pw.err`.
  - Sloshing gets **numerical-only** changes first (`mixing_mode='local-TF'`, `mixing_beta` 0.1–0.2, `mixing_ndim` 16–20), then a symmetric start with its limitation stated.
  - Never change functional, pseudopotentials, cutoffs, smearing or spin.
  - Critique before relaunching, keep the aborted output, and log a decision.
- Slow jobs: measure s/SCF-iteration against a known layout; that measurement, not a fixed rule, sets the layout. Examples (all in `references/benchmarks.md` §4): (A) 40-atom cells were 2.2× faster at 6 ranks per k-pool than at 2; (A) a job on SMT siblings slowed its neighbour 5×; (Y) large cells needed `nk ≤ ranks/4` to stay under the cgroup memory cap.
- At the end of a campaign, run `scripts/qe_bench.py` over the mirrors. It reports busy wall-clock hours, machine-hours, rank-hours and core-hours used side by side and flags oversubscription. Keep its table with the handoff.

### Phase 7: results

- **Acceptance is separate from DONE.** Apply the declared gates (`references/verification-gates.md`), recompute the number from raw output with a script, and get the post-result critique (★ for headline numbers).
- Apply the pre-registered rule exactly as written.
- Log an ACCEPT or HOLD line, write a DONE cite with the verbatim result lines, and add a `CLAIMS.md` row with its allowed wording.
- Keep failed and superseded runs identifiable. A genuine failed gate is evidence: report it.

### Phase 8: release, handoff, version control

- Before destroying a box:
  1. Do a final rsync and a **checksum dry-run with zero differences**.
  2. Stop its watcher, and record unfinished jobs with their last evaluated geometries (`structure_gate.py --evaluated --write-cards`).
  3. Get a critique if work is unfinished, and the user's go-ahead.
- Refresh `HANDOFF.md`. Run `logbook.py audit`, scan for secrets and files over 100 MB, then commit and push when asked.

### Phase 9: the manuscript

Run `references/manuscript-review.md`: a harsh-referee pass with Opus plus Codex, Haiku reference verification against Crossref, and a similarity scan. Check every number against `CLAIMS.md`. Any number you suggest must come from a raw file.

## Hard rules (each one cost real time once)

1. No `pkill -f`, `pgrep -f` or pattern kills over ssh: they match your own shell. Kill explicit PIDs after checking comm, cwd and start time. Restart schedulers through uploaded scripts.
2. Never execute a truncated or "read-only prefix" copy of a state-changing script against a live host.
3. Never `rsync -a` a server into the working folder. Mirror it; verify hashes both ways after editing scripts that live on a box.
4. Never compare structures that were not given the same freedom: same tilts, supercell, symmetry constraints and spin treatment, matched k density, per f.u. Project A's first headline compared a tilted cell of one ordering with an untilted cell of the other; with tilts on both sides, the conclusion reversed.
5. Never treat "JOB DONE" as converged. Check for `convergence NOT achieved`, the BFGS convergence plus final-coordinates block, and EXIT-file stops.
6. Never mix unit conventions silently: ASE uses CODATA-2006 Ry→eV; keep Ha/Ry, kbar/GPa, bohr/Å and per cell/per f.u. explicit.
7. Never let a gate pass on missing data (NaN-skipping `max()`, a missing atom line, a regex that grabs the wrong field). Every gate gets a self-test.
8. Never write a credential anywhere persistent.
9. Never delete failed attempts, quarantined lineages or raw outputs. Archive them with hashes, and only with permission.
10. Never call an unconverged or unmatched energy a result. Label it a probe, an upper bound, or not an endpoint.
11. Never act on a meaningful step without its saved critique, and never let a Haiku result enter a log or the paper unchecked.
12. Never type a timestamp, or record a decision without its cite and reasoning entry.

## The mistakes that cost the most

Full entries (what happened, why, fix, gate) are in `references/common-mistakes.md`:
1. PBE volume and shape error found too late (M).
2. Unfair comparison: tilted vs untilted, constrained vs unconstrained symmetry (A, Y).
3. Tests on a proxy pair (A).
4. Endpoint not stationary at the final settings (A).
5. Wrong-stoichiometry lineage (A).
6. 20-hour relaxations: spin-polarised on a non-magnetic cell, rattled seed with no symmetry, bad pool layout (A).
7. Pseudopotential family incompatible with a later property code (M).
8. Disk exhaustion from ph.x scratch or `/dev/shm` (M, Y).
9. Orphaned watchers and launchers; a watcher outliving its box (A).
10. Parser and gate bugs (M, Y).
11. Negative phonon modes and ASR sensitivity under-reported (M).
12. Manuscript audit-log prose, and reviewer estimates pasted as facts (M).

## Reference files

| File | Read it when |
|---|---|
| `references/critique-protocol.md` | spawning an Opus critic, a Codex reviewer or Haiku field workers; writing a launch, stuck-job, post-result, migration or area-audit prompt; recording verdicts |
| `references/records.md` | setting up or auditing logs, cite files, decisions, claims and gates registries, hashes, git, the handoff and session start/end |
| `references/vm-campaign.md` | renting, benchmarking, building and validating QE, MPI and pools, memory and disk, scheduler design, monitoring, sync, process safety, migration, release, the hourly-check template |
| `references/benchmarks.md` | choosing or rejecting a box, sizing ranks/pools/slots, estimating job durations and budget, or accounting for a finished campaign: 18 measured machines, same-input speeds, layout experiments, typical durations |
| `references/verification-gates.md` | checking a pseudopotential, structure, convergence ladder, relaxation, comparison, or any property (bands, DOS/PDOS, HSE, elastic, phonons, EOS, pressure, optics, formation) |
| `references/common-mistakes.md` | before planning (skim all of it) and whenever a result looks surprising |
| `references/manuscript-review.md` | reviewing or preparing a manuscript, SI, figures, references or the submission package |
| `references/case-studies.md` | the source projects: what they computed, where their files are, how they ended |

## Scripts and templates

All scripts are Python 3 or bash. `structure_gate.py`, `fcheck.py` and `qsched.py` need numpy; spglib is required whenever symmetry is checked. They read text inputs and outputs only; `qsched.py run` and `box_check.sh --validate` launch jobs on the box. Each one prints usage with `--help` or with no arguments.

Tests on the source projects' outputs:
- the status, gate and ladder numbers reproduce the records;
- qsched's builder regenerated the scheduler-written static and all three one-parameter tests with zero difference;
- the critic's mocked scheduler loop ran the full chain.

| Script | Purpose |
|---|---|
| `scripts/logbook.py` | `init` project, `step` folder, `log` (folder or project), `cite`, `newcite`, `user`, `decide`, `gate`, `claim`, `audit`. Writes folder and master logs together, with the real clock. |
| `scripts/conv_ladder.py` | Applies a declared convergence rule (energy per atom + pressure from the stress tensor) to an ordered ladder of outputs and prints the kept value. |
| `scripts/qe_status.py` | One line per job: state, SCF count, energy, ΔE/f.u. against a reference, force, pressure, \|M\|, iteration, accuracy, age. Alerts for stale, failed, FAIL result, scheduler-log errors, not converged, EXIT-stopped, sloshing, band-run eigenvalue warnings, memory and disk. |
| `scripts/qe_lint.py` | pw.x input lint. `--compare parent.in` diffs every namelist key and physics card (pseudopotentials, HUBBARD, OCCUPATIONS, CONSTRAINTS, K_POINTS); `--expect key=value` asserts settings. |
| `scripts/structure_gate.py` | Formula per f.u., exact space group and operation count, distances, coordination shells with periodic images and adjacent/opposite (cis/trans) labels, bridge angles, k mesh from a spacing. Reads inputs, final coordinates or the last evaluated geometry; `--write-cards` writes a restart geometry; `--check` runs a self-test. |
| `scripts/fcheck.py` | Force and stress gate on the last blocks, with cross-output differences. It rejects missing atoms and NaN, and handles verbosity='high'; `--check` runs the self-test. |
| `scripts/qsched.py` | One-box core-packing scheduler (Linux), driven by `qsched.json`: QE-process liveness by realpath, adoption, disjoint taskset slots, pool choice, gated chains and tests, collision-safe names, opt-in scratch deletion, hard stops, STOP file. Ship it with `structure_gate.py`. |
| `scripts/watch.sh` | Laptop watcher template: mirror rsync, de-duplicated alerts into ALERTS.txt and MASTER-RUNBOOK, rate-limited SSH alerts, hourly block, pid file, WATCH-STOP. |
| `scripts/box_check.sh` | Run on a new box: cores, siblings, cgroup quota and memory, disk, GPUs; optional 1-core dgemm and a pw.x validation against an expected energy. |
| `scripts/deploy.sh` | Copy reviewed files to a box, verify SHA-256 both sides, and write a manifest. |
| `scripts/qe_bench.py` | Benchmark and accounting table from finished pw.x/ph.x outputs. Per run: layout, size, s/iteration, core-s per k-point per iteration. Per box: busy hours, rank-hours, capped core-hours, peak ranks and an oversubscription flag. Drops duplicate copies, and compares matched-shape runs across boxes. |
| `assets/templates/` | Project files (PROJECT, RULES, STATUS, HANDOFF, MASTER-RUNBOOK, CITE-LOG, REASONING-LOG, CLAIMS, GATES, BOXES, pseudo README, cite START/DONE) and per-folder README/RUNBOOK/CITES/REASONING. |
| `assets/examples/` | `qsched.json` and `jobs.json` with Project A C067 values (anonymised), and `bench-hosts.json`, all labelled as examples to replace. |
| `assets/benchmarks/qe-jobs.csv` | The 961 measured runs behind `references/benchmarks.md` (layout, size, timing; no paths or energies). |
