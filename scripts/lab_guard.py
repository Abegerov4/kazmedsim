"""Guard: an orderable lab must never duplicate a bedside vital sign.

SpO₂, ЧСС/HR, АД/BP, t°/temp and ЧДД/RR are already shown in the examination
panel (VITALS_META on the frontend). If one of them also appears in a
scenario's `lab_results_json`, it shows up in the "order tests" list AND is
fed to the grader as a `relevant_test` — so the student gets scored on
"ordering" a value that was visible from the start. Seed scripts call
`assert_not_vital` before writing labs so this can't regress.
"""

import re

# Normalised (lowercase, ₂→2) root names that belong to vitals, not labs.
VITAL_ROOTS = {
    "spo2", "sao2",
    "чсс", "hr", "пульс",
    "ад", "bp",
    "t°", "температура", "temp",
    "чдд", "rr",
}


def _norm(name: str) -> str:
    return (name or "").strip().lower().replace("₂", "2")


def is_vital(name: str) -> bool:
    n = _norm(name)
    if n in VITAL_ROOTS:
        return True
    # Also catch qualified variants — "АД (офисное)", "АД (лёжа/стоя)",
    # "Температура тела" — whose leading token is a vital root. These still
    # duplicate a bedside vital and don't belong in the orderable-labs list.
    first = re.split(r"[ (]", n, maxsplit=1)[0]
    return first in VITAL_ROOTS


def assert_not_vital(name: str, slug: str = "") -> None:
    """Raise if `name` is a bedside vital that must not be an orderable lab."""
    if is_vital(name):
        where = f" (scenario '{slug}')" if slug else ""
        raise ValueError(
            f"Lab '{name}' duplicates a bedside vital sign{where} and must not "
            f"be an orderable lab. Vitals belong in VITALS_META (frontend), "
            f"not in lab_results_json."
        )
