# Installing dft-campaign (instructions for coding agents)

If a user asked you, an AI coding agent, to install this skill, follow these steps exactly. They only clone files,
check syntax and run one offline self-test (its temporary files go to `$TMPDIR` and are removed). Nothing is rented,
launched or sent anywhere.

Each code block below is self-contained. Shell variables do not survive between separate tool calls, so every block
sets `DEST` itself: put the same folder in each.

Repository: `https://github.com/nio808/dft-campaign`. The repository root IS the skill folder (it holds `SKILL.md`).

## 1. Pick the install folder for the agent you are

| Agent | User-level folder (all projects) | Project-level folder |
|---|---|---|
| Claude Code | `~/.claude/skills/dft-campaign` | `.claude/skills/dft-campaign` |
| OpenAI Codex (CLI, IDE) | `~/.agents/skills/dft-campaign` | `.agents/skills/dft-campaign` |
| Gemini CLI | `~/.gemini/skills/dft-campaign` or `~/.agents/skills/dft-campaign` | `.gemini/skills/` or `.agents/skills/` |
| Cursor | `~/.cursor/skills/dft-campaign` or `~/.agents/skills/dft-campaign` | `.cursor/skills/` or `.agents/skills/` |
| GitHub Copilot (VS Code) | `~/.copilot/skills/dft-campaign` or `~/.agents/skills/dft-campaign` | `.github/skills/` or `.agents/skills/` |
| Any other agent | anywhere, e.g. `~/.agents/skills/dft-campaign` | see step 4 |

Use the user-level folder unless the user asked for one project only. Cursor and Copilot also read `~/.claude/skills/`,
so one copy there serves Claude Code, Cursor and Copilot together. Agent skill locations change; if the agent's own
documentation says otherwise, follow it.

## 2. Clone

```bash
DEST=~/.claude/skills/dft-campaign          # the folder chosen in step 1
if [ -e "$DEST" ]; then echo "exists: $DEST (update with: git -C $DEST pull)"; else
  mkdir -p "$(dirname "$DEST")" && git clone --depth 1 https://github.com/nio808/dft-campaign.git "$DEST"; fi
```

Gemini CLI alternative: `gemini skills install https://github.com/nio808/dft-campaign.git`. It shows a security
confirmation; pass `--consent` only after the user has agreed to install this skill.
Without git: download `https://github.com/nio808/dft-campaign/archive/refs/heads/main.zip` and unpack it so that
`$DEST/SKILL.md` exists.

## 3. Check it (seconds, read-only)

```bash
DEST=~/.claude/skills/dft-campaign          # the same folder as in step 2
DEST="$DEST" bash <<'CHECK'
fail=0
[ -f "$DEST/SKILL.md" ] || { echo "FAIL: $DEST/SKILL.md not found"; exit 1; }
head -4 "$DEST/SKILL.md"
python3 -c "import sys; assert sys.version_info >= (3, 9), sys.version" || fail=1
for f in "$DEST"/scripts/*.py; do
  python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$f" || { echo "FAIL $f"; fail=1; }; done
for f in "$DEST"/scripts/*.sh; do bash -n "$f" || { echo "FAIL $f"; fail=1; }; done
python3 "$DEST/scripts/logbook.py" --help > /dev/null || { echo "FAIL logbook.py --help"; fail=1; }
if python3 -c "import numpy" 2>/dev/null; then
  (cd "${TMPDIR:-/tmp}" && python3 "$DEST/scripts/fcheck.py" --check | tail -1) || fail=1
  python3 "$DEST/scripts/structure_gate.py" --check || fail=1
else echo "note: numpy missing (needed by structure_gate.py, fcheck.py, qsched.py)"; fi
python3 -c "import spglib" 2>/dev/null || echo "note: spglib missing (needed for symmetry checks)"
if [ "$fail" = 0 ]; then echo "INSTALL CHECK PASSED"; else echo "INSTALL CHECK FAILED"; fi
exit "$fail"
CHECK
```

Report the result line (`INSTALL CHECK PASSED` or `FAILED`) to the user. Notes about numpy or spglib are not failures:
report them and suggest `python3 -m pip install --user numpy spglib`, but do not install packages without asking. Quantum ESPRESSO itself is NOT needed on this machine: it runs on the compute box.

## 4. Agents without a skills folder

Add one line to the agent's always-read instruction file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules` or
the tool's equivalent) in the user's home or project:

```
For DFT / Quantum ESPRESSO work (inputs, convergence, rented compute boxes, runs, results, manuscripts), first read
<DEST>/SKILL.md and follow it; its paths are relative to <DEST>.
```

## 5. Personal settings (optional)

`DEST=<install folder>; cp "$DEST/LOCAL.example.md" "$DEST/LOCAL.md"`, then ask the user for their time zone, where their compute may run,
where their provider key FILE lives (never the key itself), and which models play critic and field worker. Fill those in.
`LOCAL.md` is git-ignored and overrides the defaults in SKILL.md.

## 6. Finish

- Tell the user where it is installed and that the agent may need a restart or a new session to discover it.
- In a new session, confirm the skill is listed (Claude Code: it appears in the skills list; Codex: `/skills`;
  Gemini: `gemini skills list --all`), or ask the agent "what does the dft-campaign skill do?".
- Update later with `git -C "$DEST" pull`. Uninstall by deleting `$DEST` (and the step-4 line, if added).
