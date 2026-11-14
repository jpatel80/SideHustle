# Starting a new session

Paste this as the first message:

```text
Continue the Little Fox Paper Co KDP project. Read MEMORY.md (current state), CLAUDE.md (rules), TODO.md (next steps) and docs/AUTOPILOT.md before doing anything. Run `pip install -r requirements.txt` if packages are missing, then `python3 -m unittest discover -s tests`. Report: whether OPENROUTER_API_KEY is set (only "set" or "not set"), the total spend (`python3 scripts/book_factory.py spend books`) and what TODO.md says is waiting for me. Do not start new books without my approval.
```

The original first-build prompt (2026-11-05) is in git history; it is out of date and should not be reused.
