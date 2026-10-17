# dft-campaign

An agent skill for carrying a DFT research project from question to submitted paper: Quantum ESPRESSO (pw.x, ph.x,
projwfc.x, dos.x) and Yambo on rented vast.ai or cloud machines, with every decision cited, every step critiqued by an
independent model, and every number traceable to a raw output file.

It was distilled from three real Quantum ESPRESSO projects. The fast route to a paper was rarely the problem; the
mistakes were. They are written down here so the next project does not repeat them:
- a PBE volume error found too late;
- an unfair tilted-vs-untilted comparison that flipped a headline;
- convergence tests on the wrong pair;
- 188 MPI ranks on a 46-CPU quota;
- a disk filled by phonon scratch;
- a watcher that kept alerting for three days after its machine was gone.

## Install

Paste this into your coding agent (Claude Code, Codex, Gemini CLI, Cursor, Copilot or any other):

> Install the dft-campaign skill from https://github.com/nio808/dft-campaign. Follow INSTALL.md in that repository.

Or do it yourself:

```bash
# Claude Code (Cursor and Copilot read this folder too)
git clone --depth 1 https://github.com/nio808/dft-campaign.git ~/.claude/skills/dft-campaign
# Codex, Gemini CLI, Cursor, Copilot (the cross-agent folder)
git clone --depth 1 https://github.com/nio808/dft-campaign.git ~/.agents/skills/dft-campaign
```

Start a new session afterwards. The agent picks the skill up whenever you talk about DFT, QE inputs, convergence,
renting a box, running or monitoring jobs, results or a DFT manuscript. Details, other agents, checks and personal
settings: [INSTALL.md](INSTALL.md).

Requirements: Python 3.9 or newer on your workstation, plus numpy and spglib for the structure and force gates.
Quantum ESPRESSO only on the compute machine.

## What it does

| Phase | What the skill makes the agent do |
|---|---|
| 0 Charter | State the claim and a pre-registered decision rule before computing; read prior work; pick one Hamiltonian that serves every planned property |
| 1 Inputs | Pseudopotential gate per element (type, valence, ghosts, cutoff hints, hashes on every host); structure gate (space group from Wyckoff sites, formula, coordination with periodic images, the deposited CIF) |
| 2 Convergence | One parameter at a time; energy per atom and pressure from the stress tensor; tolerances declared before the data; tested on the pair that decides the claim |
| 3 Reference state | Compare volume, shape, bonds and rotation angles with the measured structure before building on it |
| 4 Box | Rent, benchmark exclusivity, build, and validate energies to every printed digit; read the real cgroup limits |
| 5 Launch | Generated and linted inputs, structure-gated chains, a reviewed scheduler, a STOP file until the launch critique passes |
| 6 Run | Laptop watcher plus box status script, alerts, hard stops, numerical-only fixes for stuck SCFs |
| 7 Results | Acceptance separate from JOB DONE; post-result critique; claims registry with allowed wording |
| 8 Release | Checksum-verified sync, watcher stopped, handoff written |
| 9 Manuscript | Harsh-referee review, reference checks against Crossref, numbers checked against the claims registry |

Every action is logged twice: in the work folder's `RUNBOOK.md`, `CITES.md` and `REASONING.md`, and in the project's
master logs. `scripts/logbook.py` writes both with the real clock, and `logbook.py audit` finds uncited input keys,
launches without a decision, and unknown citations.

## What is inside

```
SKILL.md                    the workflow, hard rules and agent roles (read by the agent)
references/
  critique-protocol.md      when and how to get independent critiques; prompt templates
  records.md                runbook, cite and reasoning logs, decisions, claims, gates, handoff
  vm-campaign.md            renting, validating, MPI/pools, scheduler design, monitoring, sync, release
  benchmarks.md             measured numbers from 18 machines, 17 of them rented (see below)
  verification-gates.md     how each element, structure, ladder, relaxation and property was verified
  common-mistakes.md        42 real mistakes: what happened, why, the fix, the gate that now prevents it
  manuscript-review.md      referee-style review, reference and figure checks
  case-studies.md           the three source projects
scripts/                    logbook, input lint, status and alerts, structure and force gates, convergence ladder,
                            one-box scheduler, watcher, box check, deploy with hashes, benchmark accounting
assets/                     project and work-folder templates, example configs, the benchmark data (CSV)
```

## Measured benchmarks

`references/benchmarks.md` collects what the three campaigns measured. The 961 underlying runs are in
`assets/benchmarks/qe-jobs.csv`. Highlights:

- **Box roster.** 18 machines (AMD EPYC 7K62, 7C13, 7J13, 7Y83, 7B13, 7763, 7532, 9684X, Threadripper 2970WX), with usable cores, memory, price and a verdict. Two of five rentals in one night were unusable: one shared, one overloaded.
- **Same-input speeds.** The same 5-atom SCF ran at 1.9 s per iteration on the best box and 39.5 s on the overloaded one.
- **Parallel layouts.** k-point pools for 40-atom cells were 2.2× faster at 6 ranks per pool than at 2. SMT siblings slowed a running job 5×. Yambo was fastest as pure MPI (63% efficiency on 16 ranks; hybrid layouts reached 33–37%). Energies were identical to every printed digit across layouts and hosts.
- **Workload (Projects A and M).** 89 h of busy wall-clock time (3.7 days, within a 10.6-day span; 154 machine-hours, 1.7 machines busy on average) used about 4,800 core-hours. One core busy for one hour is one core-hour, never counting more cores than a machine had. Typical durations per job type are included.

Run `scripts/qe_bench.py` over your own outputs to produce the same tables for your campaign.

## Agent roles

The skill was written for Claude Code:
- an Opus critic subagent reviews every meaningful step;
- Haiku subagents do field work (reference checks, parsing many outputs);
- Codex CLI joins as an independent second-family reviewer when installed.

On other agents the roles map by capability: the strongest available model as critic in a fresh read-only context, a model from another vendor as the independent critic, and a cheap model for field work. The gates, citations and logs are the same everywhere. See "Agent roles" in `SKILL.md`.

## Scope and limits

- **Codes.** The parsers and scheduler target Quantum ESPRESSO. The workflow itself (gates, critiques, citations, logs, VM practice) is code-agnostic. For VASP, CP2K or ABINIT, replace the parsers and keep the rest.
- **Values.** Nothing that decides a result is built into the scripts: cutoffs, k spacings, convergence tolerances, test parameters and gate thresholds come from the project's cited config or the command line. A few labelling, lint and alert heuristics have documented defaults you can override by flag: the 135° adjacent/opposite cut and 0.6 Å minimum distance in `structure_gate.py`, the lint warning levels in `qe_lint.py`, and the memory and disk alert levels in `qe_status.py` and `qsched.py`. Numbers in the documents are labelled examples from the source projects.
- **Providers.** The vast.ai notes are correct as of October 2026. Provider APIs change, so re-check them.
- **Personal settings** belong in `LOCAL.md` (git-ignored; template in `LOCAL.example.md`).

## License

MIT. See [LICENSE](LICENSE).
