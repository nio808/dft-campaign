# LOCAL.md: your working agreement (copy this file to LOCAL.md and edit; LOCAL.md is git-ignored)

The agent reads LOCAL.md before the defaults in SKILL.md, and it overrides them. Never put a key or password here:
write where the key FILE is, not the key.

## Time and messages
- Time zone: Europe/Berlin. New projects: `python3 <skill-dir>/scripts/logbook.py init <project> --tz Europe/Berlin`.
  In `watch.sh` set `TZ_NAME=Europe/Berlin`.
- ETAs: hours from now with a spread.
- Autonomous checks: short; message me only when a decision needs me.

## Machines and money
- Where compute may run: (e.g. "never on my laptop; only rented boxes or the cluster").
- Provider and key file: (e.g. "vast.ai; key in ~/.config/vast/.env as VAST_KEY, read in-process only").
- What needs my confirmation: (e.g. renting, destroying, deleting results, pushing, submitting).

## Agent roles
- Critic model, field-work model, second-family reviewer: (e.g. "Opus critic, Haiku field work, Codex if installed").

## Where things are
- My projects: (paths)
