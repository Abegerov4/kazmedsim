"""Run the grader against every fixture and report drift.

A "PASS" means every rubric score and the overall total landed inside the
fixture's expected range. A "FAIL" means at least one rubric drifted out of
range — the report says which.

Run as:
    .venv/bin/python -m evals.run

CI-friendly exit code: 0 if all PASS, 1 otherwise.
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

# Load env BEFORE importing grader (it needs ANTHROPIC_API_KEY).
load_dotenv(".env.local")

from backend.grader import grade_session
from evals.fixtures import Fixture, FIXTURES


# ── ANSI colours ─────────────────────────────────────────────────────────────

GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def run_one(fx: Fixture) -> tuple[Fixture, dict, list[str]]:
    """Grade one fixture and return (fixture, grade_result, list_of_failures)."""
    grade = grade_session(
        transcript=fx.transcript_text(),
        correct_diagnosis=fx.correct_diagnosis,
        student_diagnosis=fx.student_diagnosis,
        student_treatment=fx.student_treatment,
        language=fx.language,
        ordered_tests=fx.ordered_tests,
        examined=fx.examined,
        elapsed_seconds=fx.elapsed_seconds,
        patient_history=fx.patient_history,
        relevant_tests=fx.relevant_tests,
    )
    failures: list[str] = []
    # Per-rubric checks
    for key, (lo, hi) in fx.expected.items():
        actual = grade["total"] if key == "total" else grade["scores"][key]
        if not (lo <= actual <= hi):
            failures.append(f"{key}={actual} (expected {lo}–{hi})")
    return fx, grade, failures


def format_row(fx: Fixture, grade: dict, failures: list[str]) -> str:
    status = f"{GREEN}PASS{RESET}" if not failures else f"{RED}FAIL{RESET}"
    score_str = f"total={grade['total']}"
    parts = [
        f"{fx.name:30s} {status}  {score_str:14s}",
        f"  scores: anam={grade['scores']['anamnesis']:.0f}  "
        f"comm={grade['scores']['communication']:.0f}  "
        f"reas={grade['scores']['reasoning']:.0f}  "
        f"diag={grade['scores']['diagnosis']:.0f}  "
        f"tx={grade['scores']['treatment']:.0f}",
    ]
    if failures:
        for f in failures:
            parts.append(f"  {RED}✗{RESET} {f}")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run grader regression evals")
    parser.add_argument("--filter", "-k", help="Only run fixtures whose name contains this substring")
    parser.add_argument("--parallel", "-j", type=int, default=3,
                       help="How many fixtures to grade concurrently (default 3)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Print the rendered feedback for failed fixtures")
    args = parser.parse_args()

    selected = [f for f in FIXTURES if not args.filter or args.filter in f.name]
    if not selected:
        print(f"No fixtures match filter '{args.filter}'")
        return 1

    print(f"{BOLD}Running {len(selected)} eval(s){RESET}  "
          f"{DIM}(concurrency={args.parallel}){RESET}\n")

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        results = list(pool.map(run_one, selected))
    duration = time.time() - t0

    passed = sum(1 for _, _, fails in results if not fails)
    failed = len(results) - passed

    for fx, grade, fails in results:
        print(format_row(fx, grade, fails))
        if fails and args.verbose:
            print(DIM + grade["feedback"][:600] + "..." + RESET)
        print()

    summary_color = GREEN if failed == 0 else RED
    print(f"{BOLD}{summary_color}{passed} passed, {failed} failed{RESET}  "
          f"{DIM}in {duration:.1f}s{RESET}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
