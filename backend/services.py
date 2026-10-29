import re

from .schemas import Category, Priority

# Keywords are regular expressions. \b anchors the start of a word, so
# "bin" does not match "binding" and "ac" does not match "back".
RULES: list[tuple[Category, tuple[str, ...]]] = [
    ("Electrical", (r"\bwire", r"\bcables?\b", r"\belectric", r"\bsocket", r"\boutlet", r"\bswitch ?board", r"\bpower", r"\blight", r"\bsparking")),
    ("Plumbing", (r"\bpipe", r"\bleak", r"\bwater", r"\bdrain", r"\bsink", r"\btoilet", r"\bfaucet")),
    ("Cleaning", (r"\btrash", r"\bgarbage", r"\bwaste", r"\bdirty", r"\bclean", r"\bspill", r"\bbins?\b")),
    ("Safety", (r"\bglass", r"\bsharp", r"\bhandrail", r"\bstair", r"\bhazard", r"\bfire", r"\bsmoke", r"\bburn", r"\bexposed")),
    ("Facility", (r"\bair ?con", r"\bac\b", r"\bprojector", r"\bdesk", r"\bchair", r"\bdoor", r"\bwindow", r"\bceiling", r"\bbroken")),
]

HIGH_PRIORITY = (
    r"\bfire", r"\bsmoke", r"\bburn", r"\bsparking", r"\bexposed wire", r"\belectric shock",
    r"\bgas leak", r"\bbroken glass", r"\binjur",
)
MEDIUM_PRIORITY = (
    r"\bleak", r"\bbroken", r"\bnot working", r"\bblocked", r"\boverflow", r"\bdamaged",
)


def _matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def suggest_category(title: str, description: str) -> Category:
    text = f"{title} {description}".lower()
    for category, patterns in RULES:
        if _matches(text, patterns):
            return category
    return "Other"


def suggest_priority(title: str, description: str) -> Priority:
    text = f"{title} {description}".lower()
    if _matches(text, HIGH_PRIORITY):
        return "High"
    if _matches(text, MEDIUM_PRIORITY):
        return "Medium"
    return "Low"


def suggest_department(category: str) -> str:
    return {
        "Electrical": "Electrical Maintenance", "Plumbing": "Plumbing Maintenance",
        "Cleaning": "Cleaning Services", "Safety": "Campus Safety",
        "Facility": "Facilities Maintenance", "Other": "Campus Administration",
    }.get(category, "Campus Administration")
