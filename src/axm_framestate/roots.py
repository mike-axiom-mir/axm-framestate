from __future__ import annotations

from typing import Any

ROOTS = ("truth", "agency", "continuity", "wisdom-before-speed")


def evaluate_root_fit(value: Any) -> dict[str, Any]:
    """Evaluate an explicit, inspectable declaration against the four AXM roots.

    This is not a moral classifier and does not invent a score. A candidate only
    passes when every root is explicitly marked fit with a non-empty basis.
    """
    if not isinstance(value, dict):
        return {"fit": False, "reason": "missing root declaration", "roots": {}}
    checked: dict[str, Any] = {}
    overall = True
    for root in ROOTS:
        item = value.get(root)
        valid = (
            isinstance(item, dict)
            and item.get("fit") is True
            and isinstance(item.get("basis"), str)
            and bool(item["basis"].strip())
        )
        checked[root] = {
            "fit": bool(valid),
            "basis": item.get("basis") if isinstance(item, dict) else None,
        }
        overall = overall and valid
    return {
        "fit": overall,
        "reason": "all four roots have explicit positive basis" if overall else "one or more roots lack explicit positive basis",
        "roots": checked,
    }
