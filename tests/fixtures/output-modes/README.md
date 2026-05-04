# Output-Mode Fixtures

Each fixture is a directory with three files:

- `prompt.txt` — the user input
- `default.md` — baseline response (no mode active)
- `concise.md` — expected response when `concise` mode is active
- `strict.md` — expected response when `strict` mode is active

`measure.py` reads each fixture, computes token counts (whitespace heuristic),
and reports per-fixture and aggregate ratios. Asserts:

- `concise` ≤ 60% of `default` tokens
- `strict` ≤ 40% of `default` tokens
- All facts (file paths, identifiers, numbers) from `default` appear in `concise` and `strict`
