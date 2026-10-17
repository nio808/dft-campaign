# Records: logs, citations, reasoning, provenance and handoff

Contents: 1 The rule · 2 Project layout · 3 The three logs (master + per folder) · 4 Citation types and cite files · 5 Decisions and the reasoning log · 6 Step folders · 7 Claims ledger and gates registry · 8 Hashes, manifests, backups · 9 Git and secrets · 10 Handoff and session start/end · 11 Using `scripts/logbook.py`

## 1. The rule

The rule, repeated across projects: *no input parameter, no value, no decision without a proper cite*. *Every decision must be citable, with proper logs: a master runbook log, a cite log in every folder of the work, and a log of the reasoning.*

The purpose is that any reviewer question can be answered by lookup:
- "Why 60 Ry?" → the folder's `CITES.md` row → `C008` → the verbatim line.
- "Why did you stop that probe?" → the RUNBOOK line → `D-20261007-07` → its reasoning, evidence and both critic verdicts.
- "Where does that energy difference come from?" → `CLAIMS.md` → the DONE cite → `runs/31-x/p0_<job>_scF/pw.out:<line>`.

Nothing is "our own interpretation" unless it is labelled METHOD, with its reason, and has passed a critic.

## 2. Project layout

`scripts/logbook.py init <project>` creates this skeleton from `assets/templates/`:

```
<project>/
  PROJECT.md          charter: question, claim, journal, scope in/out, budget, pre-registered decision rules, ownership
  RULES.md            hard rules for this project (skill rules + project-specific ones)
  STATUS.md           current state, rewritten (not appended) at every check; boxes, running jobs, budget used
  HANDOFF.md          pick-up file for another machine or session (§10)
  MASTER-RUNBOOK.md   append-only: one line per action anywhere in the project
  CITE-LOG.md         append-only: every cite ID and every parameter citation, project-wide
  REASONING-LOG.md    append-only: every decision with its reasoning, project-wide
  CLAIMS.md           claim ledger: paper claim → evidence → status → allowed wording
  GATES.md            gates registry: each step's acceptance gates, with the time they were declared
  BOXES.md            each rented machine: ID, host, cores, quota, RAM, disk, $/h, start/end, validation result
  02-citations/       Cnnn-<slug>-START.md / -DONE.md files (verbatim sources); _sources/ local copies of papers
  12-critique/        reviews: <ID>-<critic>-prompt.md, -review.md, -codex-full-stdout.txt; field/ for Haiku outputs
  pseudo/             UPF files + README.md (per-element table, verification-gates.md §1)
  runs/NN-<step>/     work folders (§6), numbered in order of creation
  scripts/            generators, analysis, gates (copied or adapted from the skill)
  quarantine/         wrong-identity data, never deleted, never in tables
```

An existing project with its own conventions keeps them. Project A used `RUNLOG.md`, `02-citations/`, `12-critique/`; Project M used per-tree `runlog.md`, `reviews/` and step READMEs. Add the missing pieces (per-folder logs, the reasoning log, the claims ledger) rather than renaming everything.

## 3. The three logs (master + per folder)

Every work folder has `RUNBOOK.md`, `CITES.md` and `REASONING.md`. Each entry is written to the folder file **and** mirrored to the master file at the project root. `scripts/logbook.py` does both in one call and stamps the real clock in the project's time zone (`init --tz Europe/Berlin`, else the machine's local zone). Never type a time by hand: Project A once wrote rows 5–60 minutes ahead of the clock and had to correct them.

**RUNBOOK line** (folder and MASTER-RUNBOOK):
```
- 2026-10-07 01:46 Berlin | LAUNCH | runs/31-tilt-I | qsched pid 12508; 36 ranks npool 6 cpus 0-35 | cites C067 | D-20261007-03
```
Tags: `START` (step created), `INPUT`, `GATE` (declared, or pass/fail with numbers), `REVIEW` (critic verdict), `DECISION` (written by `decide`), `LAUNCH`, `CHECK` (hourly), `ALERT`, `FIX`, `DONE`, `FAILED`, `KILL`, `STOP`, `ACCEPT`, `HOLD`, `MOVE`, `SYNC`, `RELEASE`, `INCIDENT`, `CORRECTION`, `NOTE`.
- `LAUNCH`, `KILL`, `MOVE`, `ACCEPT`, `STOP` and `RELEASE` lines must carry the decision ID that authorised them; the audit flags any that don't.
- Project-level actions (session checks, box rental, scope cuts) are logged at the project root: `logbook.py log <project> CHECK ...` writes the master runbook only.

- Corrections never edit an old line. Append a `CORRECTION` line that quotes what was wrong.
- Incidents get a short `INCIDENT` block: what happened, scientific impact, disposition, **lesson**.

**CITES row** (folder `CITES.md`; mirrored to CITE-LOG as `| when | PARAM | id | folder | parameter = value | type | source |`):
```
| ecutwfc = 60.0, ecutrho = 480.0 | VERBATIM | "Max over all six elements: ecutwfc=60.0 ecutrho=480.0" (02-citations/C008-phase0-sssp.md:19) | C008 |
| K_POINTS 5 5 5 0 0 0 | METHOD | spacing 0.2 Å⁻¹, n_i = max(1, ceil(|b_i|/0.2)); rule from C051 (Liu & Wolverton KSPACING) | C051 |
| mixing_beta = 0.2 | SoT | rescue that converged a sister cell earlier: queueB/p1_<job>_vr/pw.out:812 "convergence has been achieved" | C058 |
```
Every key in every `*.in` of the folder has a row: namelist keys, pseudopotential files, k-points, masses, magnetic order. Purely mechanical keys such as `prefix`, `outdir` and `pseudo_dir` are exempt. `logbook.py audit` lists uncited keys.

**REASONING entry** (folder `REASONING.md` and REASONING-LOG): see §5.

## 4. Citation types and cite files

| Type | What it is | Must contain |
|---|---|---|
| `VERBATIM` | literature | The exact quoted paragraph or sentence, DOI or URL, page or line; local copy in `02-citations/_sources/` when possible |
| `SoT` | an earlier output or record of this project | The verbatim line(s) with path:line |
| `METHOD` | our design choice | The label METHOD (never presented as an external fact), the reason, and the critic that accepted it |
| `USER` | an instruction or authorisation from the user | The verbatim words with date (typos kept). Project A's C067 START quotes the authorisation |
| `QEDEF` | code default or behaviour | The INPUT_PW doc line, or the source/help text with version |

Cite files, `02-citations/Cnnn-<slug>-START.md` and `-DONE.md`:
- **START** (before inputs exist): scientific reason (with SoT lines); settings inherited verbatim from the cited parent inputs; numerical-only deviations and their reasons; build and validation plan; jobs, gates and scheduler; the **pre-registered claim rule**; second checks planned.
- **DONE** (after acceptance): verbatim result lines (path:line), gate outcomes, critic verdicts, allowed wording, limitations.
- Number cites sequentially (`C001` …). `logbook.py newcite` picks the next free ID and writes a CITE-LOG row: `| when | FILE-START | C067 | 02-citations/C067-<slug>-START.md | - | - | <slug> |`.
- **User instructions** are citable too. `logbook.py user <project> --quote "<exact words>"` appends them verbatim to `02-citations/USER-INSTRUCTIONS.md` under an ID `USER-YYYYMMDD-HHMM`; cite that ID in decisions. The audit checks that every USER ID referenced exists.
- Pipes inside quotes are escaped (`\|`), so verbatim text such as `|ΔE| ≤ 10` survives the tables.

Verify every literature cite before use: DOI resolves on Crossref and the authors, year and title match. Haiku field workers do this in bulk (critique-protocol §5); you check the failures. Project A once wrote an author list from memory, and it was wrong.

## 5. Decisions and the reasoning log

A decision is any choice that changes what runs, what is accepted, or what the paper says: a parameter outside an inherited set, a launch, a kill, a move, a gate, a scope cut, an acceptance, a wording. Each one gets an ID `D-YYYYMMDD-NN` and an entry:

```
### D-20261007-07 — Stop the two long tilted-cell probes? (2026-10-07 13:15 Berlin)
- Question: user scope cut, "no 1–2-day runs"; do the paper's claims need these probes?
- Options: (A) keep running ~1.5 d; (B) stop, keep outputs, state bounded arguments; (C) move to a bigger box.
- Evidence: the measured tilt gain of the competing ordering is far smaller than the margin each probe would need to
  overturn (numbers with path:line in the real entry), so neither probe can change a claim.
- Reviews: C067-scope-opus VERDICT DO=YES; C067-scope-codex VERDICT DO=YES CONDITIONS=state bound as argument.
- Choice: B.
- Why: claims stand on bounded arguments; probes cost ~$20 and 1.5 d for no change in any claim.
- Cites: C067, USER-20261007-1305 ("<the user's exact words, typos kept>").
- Reversal condition: a referee asks for one of the two probe endpoints.
```

- No entry is complete without **Choice, Why, Cites**. `logbook.py audit` flags missing fields.
- Technical calls the user delegated ("make the logical call") still get an entry. The user reads them afterwards.
- A decision that turns out wrong gets a new entry that supersedes it, citing the old ID. Never edit the old one.

## 6. Step folders

A suggested numbering (adapted from Project M; renumber freely, but keep it monotonic and documented in PROJECT.md):
`00-env` (build identity and validation) · `01-structure` (transcription, CIF, gates) · `02-cutoffs` · `03-kmesh` ·
`04-relax` · `05-force-check` · `06-reference-state` (functional and volume table) · `1x` electronic · `2x` elastic ·
`3x` phonons · `4x` optics · `5x` campaign queues (one folder per scheduler queue) · `8x` sensitivity studies ·
`9x` manuscript evidence. A scheduler queue folder is one work folder; the job directories inside it are covered
by its CITES.md.

`scripts/logbook.py step runs/NN-<name> --purpose "..."` creates:

```
runs/NN-<name>/
  README.md        purpose; inputs and their sources; GATES (copied from GATES.md, with declaration time); result;
                   acceptance state (DONE / ACCEPTED / HOLD ...); limitations; files
  RUNBOOK.md       this folder's action log
  CITES.md         this folder's parameter → cite table
  REASONING.md     this folder's decisions
  STATUS           QUEUED|RUNNING|DONE|FAILED <UTC stamps>   (machine-written by launch/qsched)
  run.sh           the exact commands (sources shared env), idempotent, fails loudly
  FORMULA-CHECK.md structure gate output for every input
  *.in *.out *.err *.dat   (the .dat or raw .out is authoritative over any prose)
```

Conventions from Project M worth keeping:
- **One launch per step**: launch refuses if STATUS is QUEUED or RUNNING. Two concurrent run.sh in one folder corrupted a phonon screen.
- `run.sh` skips work only when a good output exists **from this exact input + DEPS + UPFs** (md5 stamp next to the output).
- The README says what the result is *not* (e.g. "PBE Kohn–Sham gap on the sampled path; not optical, not quasiparticle").

## 7. Claims ledger and gates registry

`CLAIMS.md` connects runs to the paper. Every sentence with a number or a comparison in the manuscript has a row:

```
| # | Claim (as worded in the paper) | Evidence (path:line / DONE cite) | Status | Allowed wording / limits | Critic |
| 3 | Ordering I is <ΔE> meV/f.u. below ordering II, both tilted | C067-DONE; queue_d/p0_<job>_scF/pw.out:<l> | ACCEPTED | "at the PBE static level, matched settings; e80/d005 pair shifts < 1 meV/f.u." | C067-post-opus GO |
```

- Status values: ACCEPTED, HOLD, PROBE, WITHDRAWN. Only ACCEPTED rows may appear in the abstract or conclusions.
- Before any manuscript review, check every number in the text against this ledger. A number missing from the ledger is a finding.

`GATES.md` lists each step's gates with the time they were declared. A gate declared after its data is marked `POST-HOC`. Gates are never loosened silently (critique-protocol §7).

## 8. Hashes, manifests, backups

- Input cache stamps: md5 of input + DEPS + UPFs next to each output (`out.md5`).
- Deploy manifests (`ops/deploy-<what>.json`): SHA-256 of every script deployed to a box, verified on the box after copying. A pull once overwrote an unpushed local fix, so verify hashes both ways.
- Before a takeover, migration or cleanup: a git safety commit plus tag, an external `tar.gz` with SHA-256 and a file-by-file hash manifest, and a `git bundle` verified with `git bundle verify` (Project M's pre-takeover checkpoint). Archives on the same disk are not off-machine backups; say so.
- Archiving is not permission to delete. Remove remote originals only with the user's explicit permission, after a member-by-member path, size and hash comparison.

## 9. Git and secrets

- Commit reviewed controls (scripts, inputs, gates, READMEs) and completed results. Leave live partial outputs identifiable. Do not commit scratch (`*.save/`, `tmp/`, `*.wfc*`, `*.mix*`).
- Before a push: scan for secrets (every 64-hex string should be a checksum, not a key), check for files over 100 MB, and inspect merge conflicts one by one. Project A merged 50 remote night-sync commits without losing either side.
- `.gitignore` always includes `id_ed25519*`, `id_rsa*`, `*.pem`, `*.key`, `.env`.
- API keys: environment variable in-process only, never on disk, never in a log, memory or remote file. If a key was pasted in chat, tell the user to regenerate it.

## 10. Handoff and session start/end

`HANDOFF.md` (rewrite it whenever the setup changes):
1. Why this campaign exists (3–5 lines, with the numbers).
2. Boxes table: name, ssh (key name, never the key), cores, queue dir, status, $/h, release condition. Note that disks are not persistent.
3. Jobs: state, critical path, ETA in hours with spread, what runs automatically next (chains).
4. Results so far, synced, with paths.
5. How to check: exact commands (macOS and PowerShell forms).
6. Operating rules: how to pause (`touch STOP`), the never-do list (pattern kills, rsync into the working tree), how to restart the scheduler (uploaded script).
7. Monitors: what runs where, and **which die with this session or this machine**.
8. Pick-up checklist for a new machine: copy the key securely, regenerate exposed keys, choose who syncs, start a session with "read HANDOFF.md and the tail of MASTER-RUNBOOK.md, check the boxes, re-create the hourly check and alert monitor", and the release step.
9. Plan and the pre-registered decision rule, with the exact wording to use for each outcome.

**Session start** (any new session on the project):
1. Read PROJECT.md, HANDOFF.md, STATUS.md and the last 50 lines of MASTER-RUNBOOK.md.
2. Treat them as claims. Check the boxes live (status script, `ps`, `df`, memory).
3. Re-arm the monitors (cron plus alert Monitor) and confirm that the watchers run, one per box.
4. Log a `CHECK` line.

**Session end** (or before a long absence):
1. Rewrite STATUS.md and HANDOFF.md.
2. Log the state.
3. Commit and push if asked.
4. Tell the user which monitors stop with the session.

## 11. Using `scripts/logbook.py`

Always call the skill's copy (`LB=<skill-dir>/scripts/logbook.py`, e.g. `~/.claude/skills/dft-campaign` or `~/.agents/skills/dft-campaign`). A copy elsewhere finds the templates through `LOGBOOK_TEMPLATES` or the skill path.

```
python3 $LB init <project>                                   # skeleton (never overwrites)
python3 $LB step <project>/runs/31-tilt-I --purpose "fine-grid relax of the tilted ordering-I cell"
python3 $LB log  <project> CHECK "session start: boxes checked live"                 # master runbook only
python3 $LB user <project> --quote "<the user's exact words>" --context "scope cut"   # prints USER-YYYYMMDD-HHMM
python3 $LB newcite <project> --slug tilt-resolved-campaign --kind START               # next free Cnnn + template
python3 $LB cite <folder> --param "ecutwfc = 60.0" --type VERBATIM --source "\"...\" (02-citations/C008...:19)" --id C008
python3 $LB gate <folder> --gate "max force component, final static" --threshold "< 1e-4 Ry/bohr"   # BEFORE data
python3 $LB decide <folder> --question "..." --options "A ...; B ..." --evidence "..." \
        --reviews "C067-launch-opus LAUNCH=YES; C067-launch-codex LAUNCH=YES" \
        --choice B --why "..." --cites "C067, USER-20261007-1305" [--reversal "..."]  # prints the D-id
python3 $LB log  <folder> LAUNCH "qsched pid 12508; 36 ranks" --cite C067 --decision D-20261007-03
python3 $LB gate <folder> --gate "max force component, final static" --threshold "< 1e-4 Ry/bohr" \
        --outcome PASS --evidence "p0_x/pw.out:1846"
python3 $LB claim <project> --claim "..." --evidence "path:line" --status ACCEPTED --wording "..." \
        --critic "C067-post-opus GO" --decision D-...
python3 $LB audit <project>                                  # exit 1 on problems
```

What the audit checks:
- root files;
- every folder holding a `RUNBOOK.md` has README, RUNBOOK, CITES and REASONING;
- every namelist key and physics card of every `*.in` in a work folder is cited in its CITES.md (exempt keys: `prefix`, `outdir`, `pseudo_dir`, file names; per-folder extras in `.cite-exempt`);
- `*.in` files outside any work folder are listed;
- every referenced Cnnn and USER ID exists;
- every decision has Choice, Why, Cites and Reviews (Reviews says `none (<reason>)` if no critic was due), and the review IDs it names exist in `12-critique/`;
- LAUNCH/KILL/MOVE/ACCEPT/STOP/RELEASE lines carry an existing decision ID;
- METHOD cites carry a reason;
- runbook time never goes backwards.

Run it before every critic review, every push and every manuscript pass. Fix what it lists, or record why an item is exempt.
