# Grader regression evals

A small fixture-based test suite for the grader. Each fixture is a
hand-crafted student-patient transcript paired with the score ranges any
well-tuned grader should land within.

The point isn't to nail an exact score (LLM grading is noisy) — it's to
catch **qualitative regressions**: if a prompt edit makes the grader start
rewarding bad anamnesis or punishing correct diagnoses, this catches it
on the next run.

## Run

```bash
.venv/bin/python -m evals.run            # all fixtures, concurrent
.venv/bin/python -m evals.run -k pneumon # filter by name substring
.venv/bin/python -m evals.run -v         # print feedback for failures
.venv/bin/python -m evals.run -j 1       # sequential (useful for rate limits)
```

Exits with code 0 if all PASS, 1 otherwise — CI-ready.

## Adding a fixture

Edit `evals/fixtures.py`. Each fixture needs:

- `transcript` — list of `(role, message)` tuples (`"student"` or `"patient"`)
- All the anchor data the grader receives (`patient_history`, `relevant_tests`,
  `correct_diagnosis`, etc.) — these mirror what `main.py` would pass at
  runtime
- `expected` — score range per rubric plus `total`. Use **wide ranges**
  (±2 points) for the noise floor; only tighten if you have a reason to
- A descriptive `name` like `<scenario>_<quality>` so failures are obvious

When a fixture fails, decide whether:
- The grader regressed → fix the prompt and re-run
- The expected range was wrong → update the fixture

Never tighten an expected range to make a flaky fixture green — that
defeats the purpose.

## What this catches

- Score drift across prompt edits (e.g. grader getting harsher/softer)
- Language-specific bugs (does grading still work in `kk` and `en`?)
- Tool-schema regressions (a missing field would crash, not pass)
- Anchor-data handling bugs (does the grader actually use `relevant_tests`?)

## What this doesn't catch

- Wording quality of feedback (read the markdown by hand)
- Real-world model drift (Anthropic publishing a new Sonnet behind the
  same model ID) — for that, re-run evals occasionally and watch for
  silent regressions
