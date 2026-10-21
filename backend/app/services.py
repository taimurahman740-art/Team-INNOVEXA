from .schemas import Category, Priority

RULES: list[tuple[Category, tuple[str, ...]]] = [
    ("Electrical", ("wire", "electric", "socket", "outlet", "power", "light", "sparking")),
    ("Plumbing", ("pipe", "leak", "water", "drain", "sink", "toilet", "faucet")),
    ("Cleaning", ("trash", "garbage", "waste", "dirty", "clean", "spill", "bin")),
    ("Safety", ("glass", "sharp", "handrail", "stairs", "hazard", "fire", "smoke", "exposed")),
    ("Facility", ("air conditioner", "projector", "desk", "chair", "door", "window", "ceiling", "broken")),
]

def suggest_category(title: str, description: str) -> Category:
    text = f"{title} {description}".lower()
    for category, words in RULES:
        if any(word in text for word in words):
            return category
    return "Other"

def suggest_priority(title: str, description: str) -> Priority:
    text = f"{title} {description}".lower()
    if any(word in text for word in ("fire", "smoke", "sparking", "exposed wire", "electric shock", "gas leak", "broken glass", "injury")):
        return "High"
    if any(word in text for word in ("leak", "broken", "not working", "blocked", "overflow", "damaged")):
        return "Medium"
    return "Low"

def suggest_department(category: str) -> str:
    return {
        "Electrical": "Electrical Maintenance", "Plumbing": "Plumbing Maintenance",
        "Cleaning": "Cleaning Services", "Safety": "Campus Safety",
        "Facility": "Facilities Maintenance", "Other": "Campus Administration",
    }.get(category, "Campus Administration")
