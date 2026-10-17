#!/usr/bin/env python3
"""Project logbook for DFT projects: master + per-folder runbook, cite log and reasoning log, with a real clock.

Every entry is written to the work folder's own file AND mirrored to the project-root master file:
  folder RUNBOOK.md   <-> MASTER-RUNBOOK.md        folder CITES.md <-> CITE-LOG.md
  folder REASONING.md <-> REASONING-LOG.md         plus GATES.md, CLAIMS.md, 02-citations/USER-INSTRUCTIONS.md
Timestamps come from the clock at write time, in the project's time zone: LOGBOOK_TZ / LOGBOOK_TZ_LABEL if set, else
<project>/.logbook.json {"tz": "Area/City", "label": "..."} (written by 'init --tz'), else the machine's local zone.
Call it from the skill folder (python3 <skill-dir>/scripts/logbook.py ...); a copy elsewhere finds the templates
through LOGBOOK_TEMPLATES or the usual skill install paths.

Commands
  init     <project> [--name NAME] [--tz Area/City [--tz-label LABEL]]   create the skeleton (never overwrites)
  step     <folder> --purpose TEXT                create a work folder with README/RUNBOOK/CITES/REASONING
  log      <folder|project> TAG TEXT [--cite IDS] [--decision D-ID]      (project root: master runbook only)
  cite     <folder> --param "key = value" --type VERBATIM|SoT|METHOD|USER|QEDEF --source TEXT [--id ID]
  newcite  <project> --slug SLUG [--kind START|DONE] [--id Cnnn]         (START picks the next free Cnnn)
  user     <project> --quote "verbatim user words" [--context TEXT]      -> prints USER-YYYYMMDD-HHMM
  decide   <folder> --question Q --options O --evidence E --reviews R --choice C --why W --cites IDS [--reversal T]
  gate     <folder> --gate NAME --threshold T [--posthoc] [--outcome PASS|FAIL --evidence PATH:LINE]
  claim    <project> --claim TEXT --evidence E --status ACCEPTED|HOLD|PROBE|WITHDRAWN --wording W --critic C
  audit    <project> [--exempt k1,k2] [--quiet]   exit 1 if problems were found

Audit checks: root files; every folder holding a RUNBOOK.md is a work folder and needs README/RUNBOOK/CITES/REASONING;
every namelist key and physics card of every *.in inside a work folder is cited in that folder's CITES.md; *.in files
outside any work folder are listed; cite IDs (Cnnn) and USER IDs referenced anywhere exist; every REASONING entry has
Choice/Why/Cites/Reviews; review IDs named in Reviews exist in 12-critique/; every LAUNCH/KILL/MOVE/ACCEPT/STOP/RELEASE
runbook line carries a decision ID that exists; METHOD cites carry a reason; runbook time never goes backwards.
The project root is the nearest parent directory that contains MASTER-RUNBOOK.md.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_FILES = ["PROJECT.md", "RULES.md", "STATUS.md", "HANDOFF.md", "MASTER-RUNBOOK.md", "CITE-LOG.md",
              "REASONING-LOG.md", "CLAIMS.md", "GATES.md", "BOXES.md"]
ROOT_DIRS = ["02-citations/_sources", "12-critique/field", "pseudo", "runs", "scripts", "quarantine"]
STEP_FILES = ["README.md", "RUNBOOK.md", "CITES.md", "REASONING.md"]
TAGS = {"START", "INPUT", "GATE", "REVIEW", "LAUNCH", "CHECK", "ALERT", "FIX", "DONE", "FAILED", "KILL", "STOP",
        "ACCEPT", "HOLD", "MOVE", "SYNC", "RELEASE", "INCIDENT", "CORRECTION", "NOTE", "DECISION"}
NEEDS_DECISION = {"LAUNCH", "KILL", "MOVE", "ACCEPT", "STOP", "RELEASE"}
CITE_TYPES = {"VERBATIM", "SoT", "METHOD", "USER", "QEDEF"}
CLAIM_STATUS = {"ACCEPTED", "HOLD", "PROBE", "WITHDRAWN"}
EXEMPT_KEYS = {"prefix", "outdir", "pseudo_dir", "title", "wfcdir", "verbosity", "fildos", "filpdos", "filband",
               "filout", "fildyn", "flfrc", "flfrq", "flvec", "fleig", "fldos"}
SKIP_DIRS = {".git", "02-citations", "12-critique", "quarantine", "tmp", "SAVE", "__pycache__", ".venv", "node_modules"}
PIPE = re.compile(r"(?<!\\)\|")


def templates_dir():
    for c in (os.environ.get("LOGBOOK_TEMPLATES", ""), os.path.join(HERE, "..", "assets", "templates"),
              os.path.expanduser("~/.claude/skills/dft-campaign/assets/templates"),
              os.path.expanduser("~/.agents/skills/dft-campaign/assets/templates")):
        if c and os.path.isfile(os.path.join(c, "PROJECT.md")):
            return os.path.normpath(c)
    sys.exit("templates not found: run the skill's own logbook.py or set LOGBOOK_TEMPLATES")


def tz_config(root):
    """(tz, label): environment first, then <root>/.logbook.json, else (None, None) = machine local time."""
    tz, label = os.environ.get("LOGBOOK_TZ"), os.environ.get("LOGBOOK_TZ_LABEL")
    cfg = os.path.join(root, ".logbook.json") if root else ""
    if not tz and cfg and os.path.isfile(cfg):
        d = json.load(open(cfg, encoding="utf-8"))
        tz, label = d.get("tz"), label or d.get("label")
    return tz, label


def now(root=None):
    tz, label = tz_config(root)
    t = None
    if tz:
        try:
            from zoneinfo import ZoneInfo
            t = dt.datetime.now(ZoneInfo(tz))
        except Exception:
            print(f"warning: time zone {tz!r} unavailable here; using the machine's local time", file=sys.stderr)
            tz, label = None, None
    if t is None:
        t = dt.datetime.now().astimezone()
    if not label:
        label = tz.rsplit("/", 1)[-1] if tz else t.strftime("UTC%z")
    return t.strftime("%Y-%m-%d %H:%M"), label, t


def find_root(path):
    p = os.path.abspath(path)
    while True:
        if os.path.isfile(os.path.join(p, "MASTER-RUNBOOK.md")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            sys.exit(f"no project root (MASTER-RUNBOOK.md) above {path}; run 'logbook.py init' first")
        p = parent


def copy_template(src_rel, dst, **kw):
    if os.path.exists(dst):
        return False
    text = open(os.path.join(templates_dir(), src_rel), encoding="utf-8").read()
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    open(dst, "w", encoding="utf-8").write(text)
    return True


def append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")


def rel(root, folder):
    r = os.path.relpath(os.path.abspath(folder), root)
    return "." if r == "." else r


def one_line(s):
    """Single line, with table pipes escaped (\\|) so verbatim quotes such as |dE| survive."""
    return " ".join(str(s).split()).replace("|", "\\|")


def cells(line):
    return [c.strip() for c in PIPE.split(line)]


def require_step(folder):
    missing = [f for f in STEP_FILES if not os.path.isfile(os.path.join(folder, f))]
    if missing:
        sys.exit(f"{folder}: missing {missing}; run 'logbook.py step {folder} --purpose ...' first")


def runbook_line(root, folder, tag, text, cites="-", decision="-"):
    ts, label, _ = now(root)
    line = f"- {ts} {label} | {tag} | {rel(root, folder)} | {one_line(text)} | cites {cites or '-'} | {decision or '-'}"
    if os.path.abspath(folder) != root:
        append(os.path.join(folder, "RUNBOOK.md"), line)
    append(os.path.join(root, "MASTER-RUNBOOK.md"), line)
    return line


# ---------------------------------------------------------------- commands
def cmd_init(a):
    if a.tz:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(a.tz)
        except Exception:
            sys.exit(f"unknown time zone {a.tz!r}: use an IANA name such as Europe/Berlin or America/New_York")
    root = os.path.abspath(a.project)
    name = a.name or os.path.basename(root)
    os.makedirs(root, exist_ok=True)
    cfg = os.path.join(root, ".logbook.json")
    if a.tz:
        if os.path.exists(cfg):
            print(f"note: {cfg} already exists; --tz ignored (edit that file to change the zone)", file=sys.stderr)
    if a.tz and not os.path.exists(cfg):
        json.dump({"tz": a.tz, "label": a.tz_label or a.tz.rsplit("/", 1)[-1]}, open(cfg, "w", encoding="utf-8"))
    ts, label, _ = now(root)
    for d in ROOT_DIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    made = [f for f in ROOT_FILES if copy_template(f, os.path.join(root, f), PROJECT=name, NOW=ts, TZ=label)]
    if copy_template("pseudo-README.md", os.path.join(root, "pseudo", "README.md"), PROJECT=name, NOW=ts,
                     TZ=label):
        made.append("pseudo/README.md")
    if "MASTER-RUNBOOK.md" in made:
        runbook_line(root, root, "START", "project skeleton created by logbook.py init")
    print(f"project {name} at {root}; created: {', '.join(made) if made else 'nothing (all files existed)'}")


def cmd_step(a):
    folder = os.path.abspath(a.folder)
    root = find_root(os.path.dirname(folder))
    ts, label, _ = now(root)
    step = rel(root, folder)
    made = [f for f in STEP_FILES if copy_template(os.path.join("step", f), os.path.join(folder, f),
                                                   STEP=step, NOW=ts, TZ=label, PURPOSE=one_line(a.purpose))]
    runbook_line(root, folder, "START", f"work folder created: {a.purpose}")
    print(f"{step}: created {', '.join(made) if made else 'nothing new'}")


def cmd_log(a):
    folder = os.path.abspath(a.folder)
    root = find_root(folder)
    if folder != root:
        require_step(folder)
    tag = a.tag.upper()
    if tag not in TAGS:
        sys.exit(f"unknown tag {a.tag}; use one of {sorted(TAGS)}")
    if tag in NEEDS_DECISION and not a.decision:
        print(f"warning: {tag} lines need --decision D-... (audit will flag this line)", file=sys.stderr)
    print(runbook_line(root, folder, tag, a.text, a.cite, a.decision))


def cmd_cite(a):
    folder = os.path.abspath(a.folder)
    require_step(folder)
    root = find_root(folder)
    ctype = {t.lower(): t for t in CITE_TYPES}.get(a.type.lower())
    if not ctype:
        sys.exit(f"type must be one of {sorted(CITE_TYPES)}")
    if not a.source.strip():
        sys.exit("a cite needs a source (quote + DOI/URL, path:line, or the METHOD reason)")
    if ctype == "VERBATIM" and '"' not in a.source and "“" not in a.source:
        print("warning: VERBATIM source has no quoted text", file=sys.stderr)
    ts, _, _ = now(root)
    cid = a.id or "-"
    append(os.path.join(folder, "CITES.md"), f"| {one_line(a.param)} | {ctype} | {one_line(a.source)} | {cid} |")
    append(os.path.join(root, "CITE-LOG.md"),
           f"| {ts} | PARAM | {cid} | {rel(root, folder)} | {one_line(a.param)} | {ctype} | {one_line(a.source)} |")
    print(f"cited {a.param} [{ctype}] in {rel(root, folder)}")


def known_cites(root):
    ids = set()
    cdir = os.path.join(root, "02-citations")
    if os.path.isdir(cdir):
        for f in os.listdir(cdir):
            m = re.match(r"(C\d{3,})", f)
            if m:
                ids.add(m.group(1))
    log = os.path.join(root, "CITE-LOG.md")
    if os.path.isfile(log):
        for l in open(log, encoding="utf-8"):
            c = cells(l)
            if len(c) > 3 and c[2].startswith("FILE-") and re.fullmatch(r"C\d{3,}", c[3]):
                ids.add(c[3])
    return ids


def known_users(root):
    p = os.path.join(root, "02-citations", "USER-INSTRUCTIONS.md")
    return set(re.findall(r"^### (USER-\d{8}-\d{4}(?:-\d+)?)", open(p, encoding="utf-8").read(), re.M)) \
        if os.path.isfile(p) else set()


def cmd_newcite(a):
    root = find_root(a.project)
    kind = a.kind.upper()
    ids = known_cites(root)
    if kind == "START":
        cid = a.id or f"C{max([int(i[1:]) for i in ids] + [0]) + 1:03d}"
        if a.id and a.id in ids:
            sys.exit(f"{a.id} already exists")
    else:
        if not a.id:
            sys.exit("DONE needs --id of its START cite")
        cid = a.id
    ts, label, _ = now(root)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", a.slug).strip("-")
    path = os.path.join(root, "02-citations", f"{cid}-{slug}-{kind}.md")
    if not copy_template(f"cite-{kind}.md", path, ID=cid, SLUG=slug, NOW=ts, TZ=label):
        sys.exit(f"{path} exists")
    append(os.path.join(root, "CITE-LOG.md"),
           f"| {ts} | FILE-{kind} | {cid} | {os.path.relpath(path, root)} | - | - | {slug} |")
    runbook_line(root, root, "NOTE", f"cite file {cid} {kind} created ({slug})", cid)
    print(cid, os.path.relpath(path, root))


def cmd_user(a):
    root = find_root(a.project)
    ts, label, t = now(root)
    base = f"USER-{t.strftime('%Y%m%d-%H%M')}"
    have = known_users(root)
    uid, k = base, 2
    while uid in have:
        uid, k = f"{base}-{k}", k + 1
    p = os.path.join(root, "02-citations", "USER-INSTRUCTIONS.md")
    if not os.path.isfile(p):
        append(p, "# User instructions (verbatim, append-only; cite by ID)\n")
    append(p, f"\n### {uid} ({ts} {label})\n> {a.quote.strip()}\n\nContext: {one_line(a.context or '-')}\n")
    runbook_line(root, root, "NOTE", f"user instruction recorded as {uid}", uid)
    print(uid)


def next_decision_id(root, t):
    day = t.strftime("%Y%m%d")
    log = os.path.join(root, "REASONING-LOG.md")
    n = len(re.findall(rf"^### D-{day}-(\d+)", open(log, encoding="utf-8").read(), re.M)) if os.path.isfile(log) else 0
    return f"D-{day}-{n + 1:02d}"


def cmd_decide(a):
    folder = os.path.abspath(a.folder)
    root = find_root(folder)
    if folder != root:
        require_step(folder)
    for k in ("choice", "why", "cites", "reviews"):
        if not getattr(a, k).strip():
            sys.exit(f"--{k} must not be empty (reviews: give the review IDs, or 'none (<reason>)')")
    ts, label, t = now(root)
    did = next_decision_id(root, t)
    block = (f"\n### {did} — {one_line(a.question)} ({ts} {label})\n"
             f"- Folder: {rel(root, folder)}\n- Question: {one_line(a.question)}\n- Options: {one_line(a.options)}\n"
             f"- Evidence: {one_line(a.evidence)}\n- Reviews: {one_line(a.reviews)}\n- Choice: {one_line(a.choice)}\n"
             f"- Why: {one_line(a.why)}\n- Cites: {one_line(a.cites)}\n"
             f"- Reversal condition: {one_line(a.reversal) if a.reversal else '-'}\n")
    if folder != root:
        append(os.path.join(folder, "REASONING.md"), block)
    append(os.path.join(root, "REASONING-LOG.md"), block)
    runbook_line(root, folder, "DECISION", f"{a.question} -> {a.choice}", one_line(a.cites), did)
    print(did)


def cmd_gate(a):
    folder = os.path.abspath(a.folder)
    root = find_root(folder)
    ts, _, _ = now(root)
    posthoc = "POST-HOC" if a.posthoc else "no"
    append(os.path.join(root, "GATES.md"),
           f"| {rel(root, folder)} | {one_line(a.gate)} | {one_line(a.threshold)} | {ts} | {posthoc} | "
           f"{a.outcome or '-'} | {one_line(a.evidence or '-')} |")
    what = (f"gate '{a.gate}' ({a.threshold}) outcome {a.outcome}: {a.evidence or '-'}" if a.outcome
            else f"gate declared: '{a.gate}' threshold {a.threshold}" + (" (POST-HOC)" if a.posthoc else ""))
    print(runbook_line(root, folder, "GATE", what))


def cmd_claim(a):
    root = find_root(a.project)
    status = a.status.upper()
    if status not in CLAIM_STATUS:
        sys.exit(f"status must be one of {sorted(CLAIM_STATUS)}")
    p = os.path.join(root, "CLAIMS.md")
    n = sum(1 for l in open(p, encoding="utf-8") if re.match(r"^\|\s*\d+\s*\|", l)) + 1
    append(p, f"| {n} | {one_line(a.claim)} | {one_line(a.evidence)} | {status} | {one_line(a.wording)} | "
              f"{one_line(a.critic)} |")
    tag = {"ACCEPTED": "ACCEPT", "HOLD": "HOLD"}.get(status, "NOTE")
    print(runbook_line(root, root, tag, f"claim #{n} {status}: {a.claim}", decision=a.decision or "-"))


# ---------------------------------------------------------------- audit
def namelist_keys(text):
    keys, cards = set(), set()
    body = re.sub(r"!.*", "", text)
    for blk in re.findall(r"^\s*&\w+(.*?)^\s*/\s*$", body, re.S | re.M):
        for k in re.findall(r"([A-Za-z_][A-Za-z0-9_%]*)\s*(?:\([^)]*\))?\s*=", blk):
            keys.add(k.lower())
    for card in ("ATOMIC_SPECIES", "K_POINTS", "HUBBARD", "OCCUPATIONS", "CONSTRAINTS", "ADDITIONAL_K_POINTS"):
        if re.search(rf"^\s*{card}\b", body, re.M):
            cards.add(card)
    upfs = {os.path.basename(u) for u in re.findall(r"(\S+\.(?:upf|UPF))\b", body)}
    return keys, cards, upfs


def cite_refs(text):
    """Cite IDs referenced in text. 'C067' and '02-citations/C067-...' count; a review ID such as 'C067-launch-opus'
    (campaign-prefixed, not a cite file path) does not."""
    out = set()
    for m in re.finditer(r"(02-citations/)?(?<![\w-])(C\d{3,})(?![\w])(-?)", text):
        if m.group(1) or not m.group(3):
            out.add(m.group(2))
    return out


def parse_reasoning(text):
    out = []
    for m in re.finditer(r"^### (D-\d{8}-\d+)(.*?)(?=^### |\Z)", text, re.S | re.M):
        out.append((m.group(1), dict(re.findall(r"^- ([A-Za-z ]+):\s*(.*)$", m.group(2), re.M))))
    return out


def work_folders(root):
    found = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.endswith(".save") and not d.startswith(".")]
        if dp != root and "RUNBOOK.md" in fn:
            found.append(dp)
    return sorted(found)


def cmd_audit(a):
    root = find_root(a.project)
    exempt = EXEMPT_KEYS | {k.strip().lower() for k in (a.exempt or "").split(",") if k.strip()}
    problems, warnings = [], []
    for f in ROOT_FILES:
        if not os.path.isfile(os.path.join(root, f)):
            problems.append(f"root: missing {f}")
    cites, users = known_cites(root), known_users(root)
    crit = os.path.join(root, "12-critique")
    reviews = os.listdir(crit) if os.path.isdir(crit) else []
    steps = work_folders(root)
    step_set = set(steps)
    n_inputs, outside = 0, []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.endswith(".save") and not d.startswith(".")]
        for f in fn:
            if f.endswith(".in"):
                owner = next((s for s in sorted(step_set, key=len, reverse=True)
                              if dp == s or dp.startswith(s + os.sep)), None)
                if owner is None:
                    outside.append(os.path.relpath(os.path.join(dp, f), root))
    for sd in steps:
        tag = rel(root, sd)
        miss = [f for f in STEP_FILES if not os.path.isfile(os.path.join(sd, f))]
        if miss:
            problems.append(f"{tag}: missing {', '.join(miss)}")
            continue
        rows = [cells(l) for l in open(os.path.join(sd, "CITES.md"), encoding="utf-8")
                if l.startswith("|") and not re.match(r"\|\s*-+", l) and "Parameter = value" not in l]
        first_cols = " ".join(c[1].lower() for c in rows if len(c) > 2)
        for c in rows:
            if len(c) >= 5 and c[2] == "METHOD" and len(c[3]) < 10:
                problems.append(f"{tag}: METHOD cite without a reason: {c[1]}")
        ex_file = os.path.join(sd, ".cite-exempt")
        local_exempt = set(open(ex_file).read().lower().split()) if os.path.isfile(ex_file) else set()
        nested = [s for s in steps if s != sd and s.startswith(sd + os.sep)]
        for dp, dn, fn in os.walk(sd):
            dn[:] = [d for d in dn if d not in SKIP_DIRS and not d.endswith(".save")
                     and os.path.join(dp, d) not in nested]
            for f in fn:
                if not f.endswith(".in"):
                    continue
                p = os.path.join(dp, f)
                txt = open(p, encoding="utf-8", errors="replace").read()
                if "&" not in txt:
                    continue
                n_inputs += 1
                keys, cards, upfs = namelist_keys(txt)
                for k in sorted(keys - exempt - local_exempt):
                    if not re.search(rf"(?<![a-z0-9_]){re.escape(k)}(?![a-z0-9_])", first_cols):
                        problems.append(f"{tag}: {os.path.relpath(p, sd)}: uncited key '{k}'")
                for card in sorted(cards):
                    if card.lower() not in first_cols and not (card == "ATOMIC_SPECIES" and upfs and
                                                               all(u.lower() in first_cols for u in upfs)):
                        problems.append(f"{tag}: {os.path.relpath(p, sd)}: uncited card {card}")
        for fname in ("CITES.md", "REASONING.md", "RUNBOOK.md"):
            text = open(os.path.join(sd, fname), encoding="utf-8").read()
            for cid in sorted(cite_refs(text) - cites):
                problems.append(f"{tag}/{fname}: cite {cid} not found in 02-citations/ or CITE-LOG.md")
            for uid in sorted(set(re.findall(r"USER-\d{8}-\d{4}(?:-\d+)?", text)) - users):
                problems.append(f"{tag}/{fname}: {uid} not found in 02-citations/USER-INSTRUCTIONS.md")
    if outside:
        warnings.append(f"{len(outside)} *.in file(s) outside any work folder (no CITES.md covers them), e.g. "
                        + ", ".join(outside[:10]))
    decisions = set()
    rl = os.path.join(root, "REASONING-LOG.md")
    if os.path.isfile(rl):
        for did, fields in parse_reasoning(open(rl, encoding="utf-8").read()):
            decisions.add(did)
            for k in ("Question", "Options", "Evidence", "Reviews", "Choice", "Why", "Cites"):
                v = fields.get(k, "").strip()
                if not v or v == "-":
                    (problems if k in ("Choice", "Why", "Cites", "Reviews") else warnings).append(
                        f"REASONING-LOG {did}: empty '{k}'")
            for cid in sorted(cite_refs(fields.get("Cites", "")) - cites):
                problems.append(f"REASONING-LOG {did}: cite {cid} not found")
            for uid in sorted(set(re.findall(r"USER-\d{8}-\d{4}(?:-\d+)?", fields.get("Cites", ""))) - users):
                problems.append(f"REASONING-LOG {did}: {uid} not found in USER-INSTRUCTIONS.md")
            for rid in re.findall(r"[A-Za-z0-9._]+(?:-[A-Za-z0-9._]+)*-(?:opus|codex|sonnet)\b", fields.get("Reviews", "")):
                if not any(f.startswith(rid) for f in reviews):
                    problems.append(f"REASONING-LOG {did}: review '{rid}' has no file in 12-critique/")
    mr = os.path.join(root, "MASTER-RUNBOOK.md")
    if os.path.isfile(mr):
        last = ""
        for l in open(mr, encoding="utf-8"):
            m = re.match(r"- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ", l)
            if not m:
                continue
            if m.group(1) < last:
                warnings.append(f"MASTER-RUNBOOK: time goes backwards at '{l.strip()[:80]}'")
            last = max(last, m.group(1))
            c = cells(l)
            if len(c) >= 6 and c[1] in NEEDS_DECISION:
                did = c[-1]
                if not re.fullmatch(r"D-\d{8}-\d+", did):
                    problems.append(f"MASTER-RUNBOOK: {c[1]} line without a decision ID: '{l.strip()[:90]}'")
                elif did not in decisions:
                    problems.append(f"MASTER-RUNBOOK: {c[1]} line cites unknown {did}")
    if not a.quiet:
        print(f"audit {root}: {len(steps)} work folders, {n_inputs} namelist inputs, {len(cites)} cite IDs, "
              f"{len(users)} user instructions, {len(decisions)} decisions")
    for w in warnings:
        print("WARN ", w)
    for p in problems:
        print("PROBLEM", p)
    print(f"{len(problems)} problem(s), {len(warnings)} warning(s)")
    sys.exit(1 if problems else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.add_argument("project"); p.add_argument("--name")
    p.add_argument("--tz", help="IANA zone for log stamps, e.g. Europe/Berlin (default: machine local)")
    p.add_argument("--tz-label", help="short label written after each stamp (default: the city part of --tz)")
    p = sp.add_parser("step"); p.add_argument("folder"); p.add_argument("--purpose", required=True)
    p = sp.add_parser("log"); p.add_argument("folder"); p.add_argument("tag"); p.add_argument("text")
    p.add_argument("--cite"); p.add_argument("--decision")
    p = sp.add_parser("cite"); p.add_argument("folder"); p.add_argument("--param", required=True)
    p.add_argument("--type", required=True); p.add_argument("--source", required=True); p.add_argument("--id")
    p = sp.add_parser("newcite"); p.add_argument("project"); p.add_argument("--slug", required=True)
    p.add_argument("--kind", default="START", choices=["START", "DONE", "start", "done"]); p.add_argument("--id")
    p = sp.add_parser("user"); p.add_argument("project"); p.add_argument("--quote", required=True)
    p.add_argument("--context")
    p = sp.add_parser("decide"); p.add_argument("folder")
    for k in ("question", "options", "evidence", "reviews", "choice", "why", "cites"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--reversal")
    p = sp.add_parser("gate"); p.add_argument("folder"); p.add_argument("--gate", required=True)
    p.add_argument("--threshold", required=True); p.add_argument("--posthoc", action="store_true")
    p.add_argument("--outcome", choices=["PASS", "FAIL"]); p.add_argument("--evidence")
    p = sp.add_parser("claim"); p.add_argument("project")
    for k in ("claim", "evidence", "status", "wording", "critic"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--decision")
    p = sp.add_parser("audit"); p.add_argument("project"); p.add_argument("--exempt")
    p.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    {"init": cmd_init, "step": cmd_step, "log": cmd_log, "cite": cmd_cite, "newcite": cmd_newcite, "user": cmd_user,
     "decide": cmd_decide, "gate": cmd_gate, "claim": cmd_claim, "audit": cmd_audit}[a.cmd](a)


if __name__ == "__main__":
    main()
