# Contributing

## The one hard rule

**Zero pip dependencies.** Every import must be Python stdlib. A PR that adds `requirements.txt` will be closed.

## Getting started

```bash
git clone https://github.com/prabhas0705/AuditRAG.git
cd AuditRAG
cp .env.example .env   # optional — project runs offline without it
python evaluate_sec.py  # should pass before and after your change
```

## Before opening a PR

1. Run `python -m py_compile indexer.py planner.py router.py engine.py server.py cli.py` — must exit 0
2. Run `python evaluate_sec.py` — Recall@3 must stay at 100%
3. No secrets, no hardcoded paths

## What to work on

Check [open issues](https://github.com/prabhas0705/AuditRAG/issues). Bug fixes and correctness improvements are prioritised over new features.

## Code style

Standard library conventions. No type-annotation frameworks. Docstrings on public functions. Comments explain *why*, not what.

## Commit messages

`type: description` — types are `fix`, `feat`, `docs`, `refactor`, `test`, `chore`.
