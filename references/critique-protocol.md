# Agent roles and the critique protocol

Contents: 1 Roles · 2 When a critique is required · 3 Invoking an Opus critic · 4 Invoking Codex · 5 Haiku field workers · 6 Prompt templates (launch, stuck job, post-result, migration or kill, area audit) · 7 Recording verdicts and resolving disagreement · 8 Cost discipline

Default structure (override it in `LOCAL.md`):
- **A strong critic model reviews every meaningful step** (Claude Code: an Opus subagent).
- **Cheap, fast subagents do the field work and the mechanical work** (Claude Code: Haiku).
- **A reviewer from a second model family is added when one is installed** (e.g. Codex CLI).

Subagents and second-family reviews cost usage. Ask the user once per project before spawning them, unless `LOCAL.md` pre-authorises them.

---

## 1. Roles

| Role | Who | Does | Never does |
|---|---|---|---|
| **Orchestrator** | the main session | Plans, decides, runs commands on the box, edits files, keeps every log, applies verdicts | Skips a required critique, or self-approves its own launch |
| **Critic (primary)** | Opus subagent (`Agent`, `model: "opus"`, general-purpose), read-only | Hostile-but-fair review of a step: physics, inputs, gates, code, wording. Returns findings plus a one-line verdict | Edits files, SSHes to boxes, launches anything |
| **Critic (independent family)** | Codex CLI, read-only sandbox | A second, independent review of launches, pivots, area audits and manuscripts | Same as above |
| **Field workers** | Haiku subagents (`model: "haiku"`) | Bounded, checkable, high-volume work (see §5) | Decides anything, judges physics, or writes into the project's logs directly |
| **Extra ops check (optional)** | Sonnet subagent | An *additional* quick operational opinion next to the Opus critic | Never replaces the Opus critique; never scientific acceptance |

Why two critic families: in Project A and Project M the Codex and Claude reviewers caught different things. Codex found the scheduler crash and the stale-cache blocker. Claude subagents found the k-path weight-0 bug and robustness items. Their disagreements were resolved by evidence and logged. One reviewer alone would have missed real bugs.

If Codex is **not** installed (`command -v codex` fails), run two Opus critics with different briefs instead: one physics and claims, one operations and code. Record that the independent-family check was not available.

## 2. When a critique is required

A meaningful step is anything whose outcome later numbers depend on, or that costs money, compute hours or evidence. Opus critiques every row below. Codex joins where its column says yes, whenever `codex` is installed; elsewhere Opus alone is required.

| Step | Opus | Codex | Blocking? |
|---|---|---|---|
| Project charter and scope (Phase 0), including the pre-registered decision rule | yes | yes | yes |
| Pseudopotential and structure gates passed (Phase 1) | yes | – | yes |
| Convergence decision (kept cutoffs and mesh) | yes | yes | yes |
| Reference-state decision (functional, volume table) | yes | yes | yes |
| New box validated and benchmarked; job layout | yes (short) | – | yes |
| **Launch** of any new input set (a campaign, a probe, a single job). Chain children that the scheduler generates are covered by the launch review of their chain, as long as the chain logic and gates are unchanged | yes | yes | yes, with a STOP file until the verdict |
| Stuck or failed job: relaunch, mixing change or replacement | yes (mandatory; Sonnet may add, never replace) | yes | yes |
| Kill, pivot, migration, scope cut, box release with unfinished work | yes | yes | yes |
| Parser, gate or scheduler code change deployed to a live box | yes | yes | yes |
| Each important result before it enters STATUS, CLAIMS or the paper | yes | for headline numbers | yes, for acceptance |
| Whole-project audit before writing (one critic per area) | optional | yes, six areas | – |
| Manuscript or SI review | yes | yes | – |

"Blocking" means: do not act, and do not record the result as accepted, until the verdict file exists. Emergencies (disk about to fill, OOM) allow containment first (pause, SIGSTOP, STOP file). Record the review afterwards as **retrospective** and never backdate it.

## 3. Invoking an Opus critic

Use the Agent tool:

```
Agent(
  description = "<ID> Opus critique",
  subagent_type = "general-purpose",
  model = "opus",
  prompt = <contents of 12-critique/<ID>-opus-prompt.md>
)
```

- First write the prompt to `12-critique/<ID>-opus-prompt.md`, using a template from §6.
- Tell the critic that it is READ-ONLY: no edits, no SSH, no remote contact. Its final message is its whole deliverable.
- When it returns, save its full final message verbatim to `12-critique/<ID>-opus-review.md`. Then confirm it changed nothing: `git status --short`, or mtimes outside its scratch folder. Read-only is enforced by the prompt, because the critic needs Bash for recomputation. The subagent's report is not shown to the user, so relay the verdict and the must-fix items in your own message.
- Run critics in the background when the orchestrator has other independent work (e.g. reading the build log). Never act on a result you have not received. If the user asks while it runs, say it is still running.
- IDs: `<campaign>-<topic>-<YYYYMMDD-HHMM>`, e.g. `C067-launch-20261007-0140`. Project A used `C067-launch-review`; Project M used `RD24-takeover-launch`. Any scheme works as long as it is unique and sortable.

## 4. Invoking Codex

Check availability and the model once per session:

```bash
command -v codex && codex --version
```

Use the strongest model your Codex install offers at its highest reasoning effort, or the one named in `LOCAL.md` (set `CODEX_MODEL`; leave it unset for the config default). If the CLI rejects the model ID, rerun on the config default. Always record the exact model ID that ran.

Command (prompt from a file; full transcript and final message both saved):

```bash
cd <repo>
codex exec ${CODEX_MODEL:+-m "$CODEX_MODEL"} -c model_reasoning_effort='"xhigh"' -s read-only --skip-git-repo-check \
  -C <repo> -o 12-critique/<ID>-codex-review.md - < 12-critique/<ID>-codex-prompt.md \
  > 12-critique/<ID>-codex-full-stdout.txt 2>&1
```

- Use `-s read-only` for reviews: Codex can still read files and run read-only commands such as Python recomputations. Use `--dangerously-bypass-approvals-and-sandbox` only when the user explicitly asks for a "yolo" reviewer that must write scratch files, and then still forbid edits to project files and remote access in the prompt.
- Always give the prompt through `-` with stdin redirected from the prompt file. A `codex exec "<prompt>"` with an open stdin hung once (`codex exec without </dev/null`).
- Codex reviews take 5–30 minutes. Run them with Bash `run_in_background: true` and continue with independent work. You will be notified when it finishes.
- Literature checks: confirm web search works in the installed Codex (`codex features list`). Otherwise give it local copies of the papers in the repo.
- Parallel area audits (Project M RD19): one Codex process per area, each with the shared context file plus its area file, all in the background. Then write one triage table.

## 5. Haiku field workers

Haiku handles the volume work, so the orchestrator and the critics spend their attention on judgement. Good Haiku tasks are bounded, have an explicit output format, and can be checked mechanically.

| Task | Input you give | Output you demand | How you verify |
|---|---|---|---|
| Reference verification (Project M: 8 agents in parallel, about 6 references each) | batch file: cite key, bib entry, citing sentence(s) | per entry: Crossref match (title, authors, journal, year, volume, pages, DOI) yes/no with the Crossref record, and whether the abstract or full text supports the sentence (SUPPORTS / PARTIAL / NO / CAN'T-TELL) with a quote | Re-query DOIs for every NO and PARTIAL yourself. Verify the key experimental reference yourself from the local PDF; the orchestrator overruled one agent verdict |
| Verbatim quote harvesting for cite files | DOI or local PDF plus the parameter in question | the exact paragraph, page or line, URL or DOI | Spot-check 1 in 5 against the source; any mismatch means redo the batch |
| Literature sweep for comparable papers | journal, material class, years | table: DOI, material, code, functional, cutoffs, k, properties reported | Check DOIs resolve; you judge relevance |
| Output inventory and hash manifests | directory list | CSV: path, size, sha256, JOB DONE yes/no, converged yes/no | Re-run the hash on a random sample |
| Parsing many outputs into tables | output paths plus the exact regexes or `scripts/qe_status.py` | the table plus every line it parsed (path:line) | Re-derive 2–3 numbers yourself |
| Log and warning sweeps | outputs | list of every "eigenvalues not converged", "convergence NOT achieved", IEEE flags or "No symmetry found", with path:line | grep yourself for a count match |
| Cite coverage audit | step folders | every parameter in each `*.in` without a CITES.md entry | `scripts/logbook.py audit` |
| Figure inspection at print size | rendered PNGs per panel | overlaps (labels on data), fonts under 7 pt, clipped ticks, inconsistent colours | Look at every flagged panel yourself |
| Plagiarism n-gram scan | manuscript text plus reference PDFs (text) | matching 6-grams and fuzzy sentence pairs with scores | You decide what is boilerplate |

Haiku prompt skeleton:

```
You are a field worker on a DFT project. Do exactly this task and nothing else. READ-ONLY for the project: do not edit,
move or delete any file in <repo>; write only to <scratch>/<task>/. Do not SSH anywhere.
TASK: <one sentence>.
INPUT: <files or batch>.
METHOD: <exact steps, e.g. "query https://api.crossref.org/works/<DOI>; compare fields">.
OUTPUT: a markdown table with columns <...>, one row per item, then a line "COUNT: <n items> <n problems>".
For every claim give its evidence (URL, path:line or quoted text). If you cannot check something, write CAN'T-TELL,
never guess.
```

Never let a Haiku result enter the logs or the paper without the orchestrator's check. Save raw Haiku outputs under `12-critique/field/<task>/` or `evidence/` so the check can be audited.

## 6. Prompt templates

Every critic prompt has the same frame. Fill in the brackets and delete what does not apply.

```
You are an independent, hostile-but-fair second reviewer (project rule: second check) for a DFT campaign.
Repository: <repo> (read anything). REVIEW ONLY: do not SSH anywhere, do not contact remote boxes, do not modify,
create or delete any file. Your final message is saved verbatim as the review.

CONTEXT
- Paper / question: <title, journal>; claim at stake: <...>; pre-registered rule: <...>.
- Current evidence: <numbers with file:line>. Treat STATUS, handoffs and summaries as claims; verify from raw outputs.
- Budget and constraints: <box, cores, RAM, disk, hours, user scope rules: nothing half-baked, nothing overdone>.

FILES TO REVIEW
- <generator script>, <inputs>, <FORMULA-CHECK.md>, <scheduler>, <the cited parent inputs to compare against>.

QUESTIONS (answer each with evidence: file:line or verbatim lines)
 Q1 ...
 Qn Anything else that would make a referee reject the conclusion?

End with exactly one line:
VERDICT <KEY>=<value> MUST-FIX=<semicolon list or none> <OTHER>=<...>
```

### 6a. Launch review (Project A C067, the template that caught the crash bug)

```
QUESTIONS
 Q1 Inputs: does any physics parameter differ from the cited parent inputs (functional, pseudos, cutoffs, smearing,
    spin, starting magnetisation species index, thresholds, press, cell_dofree, k rule)? Any syntax this QE version
    rejects?
 Q2 Seeds and structure gates: correct and fair? Is the seed substitution sound? Is the restart geometry the last
    evaluated one?
 Q3 Protocol: is the lineage (coarse -> fine -> static) the one that matches the published endpoints? Anything that
    makes new energies not comparable with the reference table?
 Q4 Scheduler: bugs in liveness/zombie handling, outcome classification (exact QE strings), final-coordinate parsing,
    follow-up construction, npool choice (divides ranks, <= k count), cpu binding, scratch cleanup, restart safety if
    the scheduler dies. Exact lines and fixes.
 Q5 Allocation and priorities for <N> physical cores and <H> hours: is the critical path right? SMT or not?
 Q6 Scientific completeness for <journal>: which planned or "later" items are REQUIRED to avoid a half-baked claim and
    which are optional? Is the pre-registered rule sound?
 Q7 Anything else a referee would use to reject the campaign's conclusions.
VERDICT LAUNCH=YES|NO  MUST-FIX=<...>  ADD-JOBS=<...>
```

### 6b. Stuck or failed job

```
Job <name> on <box>: <symptom with raw lines: iteration, estimated scf accuracy trend, magnetisation, wall per
iteration>. Inputs: <path>. Earlier rescue that worked: <path>.
Options: (A) let it run to <limit>; (B) relaunch the same geometry and physics with numerical-only changes <list>;
(C) REPLACE with <alternative start> (state its scientific limitation); (D) stop and report as unconverged.
Which, and why? Any physics change hiding in the options?
VERDICT=A|B|C|D  CHANGES=<exact keys and values>  LIMITATION=<text for the paper>
```

### 6c. Post-result review (acceptance)

```
Result: <job>, claimed <number> <unit> (<path:line>). Gates declared before the run: <list, with the README path>.
 Q1 Recompute the number from the raw outputs yourself (show the arithmetic and the lines used).
 Q2 Is every declared gate met? Name any gate that could pass a wrong result or fail a right one.
 Q3 Is the comparison fair (matched settings, same structural freedom, per-f.u. normalisation, final-settings
    stationarity, spin state)?
 Q4 Wording: what may the paper say, exactly, and what limitations must accompany it?
VERDICT ACCEPT=GO|HOLD  WORDING=<sentence>  LIMITS=<...>
```

### 6d. Migration, kill, scope cut

```
Proposal: <move jobs X from box A to box B / kill job Y / stop probes Z>. State of each job: <SCF count, energy,
force, last evaluated geometry>. Cost of the alternative: <hours, $>.
 Q1 Does the proposal lose or bias any result the paper needs? Q2 Is the restart point legitimate, and how must the
 lineage be worded? Q3 What must be synced and verified before the old box or job goes?
VERDICT DO=YES|NO  CONDITIONS=<...>  WORDING=<...>
```

### 6e. Area audit (Project M RD19)

Shared context file `RD<n>-common.md`: project, Hamiltonian, final cells, trees, agreed scope, user rules ("match comparable papers — nothing half-baked, nothing overdone"), still-running steps. The job description:

```
1. For EVERY run in your area open the real inputs (and every shared script they source) and outputs. Hunt for small
   input or bookkeeping errors that could silently ruin a number: units (Ry/eV/Ha, bohr/Å, kbar/GPa, alat/tpiba/crystal),
   stale cells or positions, pseudopotential or valence mismatch between trees, ecut, k-mesh or shift, occupations or nbnd,
   thresholds, symmetry count, sign conventions, paths to the wrong compound or step, regex parsers grabbing the wrong
   line, off-by-one band or mode indices, md5 or DEPS gates that do not cover what they claim.
2. Recompute or spot-check the key numbers in READMEs or PLAN from raw outputs.
3. Literature: comparable papers (DOIs). Is our method at or above their standard, are our numbers plausible, is
   anything standard missing, is anything overdone?
4. Gate logic: can each gate pass a wrong result or fail a right one?
5. Verify that earlier review fixes actually landed; do not just repeat them.
Output: Verdict (2–3 lines); Findings ranked CRITICAL / MAJOR / MINOR (ID, file:line, what, why, fix, cost in box
hours or "analysis only"); Literature check; Verified OK list. If unsure, say what evidence would settle it.
```

Areas that worked for a materials-property paper:
- A: ground state, pseudopotentials, convergence, structure versus experiment
- B: electronic (bands, DOS/PDOS, HSE, masses)
- C: optics
- D: phonons and thermodynamics
- E: elastic constants
- F: EOS, pressure series and **cross-step consistency** (the same cell, pseudopotentials and settings used everywhere a step claims them)

For an energy-ranking paper (Project A), use: structures and gates; energies and convergence; spin and U; electronic properties; elastic and phonon data; literature and novelty.

Triage the audits into one file with three lists: **needs box time** (with estimated hours, user decision pending), **analysis or wording only**, and **gate and code hardening**.

## 7. Recording verdicts and resolving disagreement

- Files per review: `<ID>-<critic>-prompt.md`, `<ID>-<critic>-review.md`, and for Codex `<ID>-codex-full-stdout.txt`.
- Then write a REASONING entry (`scripts/logbook.py decide`) that cites the review IDs. Give the verdicts, what you accepted and rejected and why, and the action. Add a RUNBOOK line. Write the folder's REASONING.md and the master REASONING-LOG.
- When critics disagree (Project A, C067: Codex said REPLACE against an earlier relaunch), decide by evidence: raw lines, a small test, a literature quote. Record both positions and the deciding evidence. If the evidence cannot settle it, take the conservative option (pause or label) and tell the user.
- Must-fix items are fixed and **re-tested** before acting. If the fix is non-trivial, send the fixed version back to the same critic with "verify these fixes landed".
- Never weaken a gate to satisfy a schedule. If a critic says a gate was too strict, change it only with a written reason, label the change post hoc, and keep the original result on record.

## 8. Cost discipline

- Hourly checks stay short and use no critic unless something is wrong.
- Do not re-review unchanged material. Each review names exactly what is new.
- Haiku does the bulk reading, so give Opus and Codex the evidence files plus pointers, not whole trees.
- Batch questions: one launch review covers inputs, scheduler and plan together.
