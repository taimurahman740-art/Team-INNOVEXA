"""Final category overrides for immediate campus-safety hazards."""

FIRE_OR_GAS_HAZARD_REASON = "Possible fire, smoke, gas or explosion"


def apply_safety_category_override(category: str, risk_reasons: list[str]) -> str:
    """Route active fire, smoke, gas, or explosion hazards to Campus Safety.

    The override relies on the safety triage reasons, not merely words such as
    "fire" in a title. This preserves ordinary inspection reports and negated
    hazards while ensuring active emergencies are not sent only to maintenance.
    """
    if FIRE_OR_GAS_HAZARD_REASON in risk_reasons:
        return "Safety"
    return category
