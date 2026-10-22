"""Exercise catalog: name -> muscle groups + metadata.

Primary muscles count fully toward muscle-group volume; secondary ones count
with SECONDARY_WEIGHT. `standard` tells standards.py which lift table to use
(None = no world-stats rating available for that movement).
"""

from dataclasses import dataclass, field

SECONDARY_WEIGHT = 0.5

MUSCLE_GROUPS = [
    "chest", "back", "shoulders", "biceps", "triceps",
    "quads", "hamstrings", "glutes", "calves", "core", "forearms",
]


@dataclass(frozen=True)
class Exercise:
    name: str
    primary: tuple[str, ...]
    secondary: tuple[str, ...] = ()
    bodyweight: bool = False          # reps-only, load is optional added weight
    standard: str | None = None       # key in standards.STANDARDS
    aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def muscles(self) -> dict[str, float]:
        out = {m: 1.0 for m in self.primary}
        for m in self.secondary:
            out.setdefault(m, SECONDARY_WEIGHT)
        return out


_CATALOG: list[Exercise] = [
    Exercise("Bench Press", ("chest",), ("triceps", "shoulders"), standard="bench", aliases=("bench", "bp")),
    Exercise("Incline Bench Press", ("chest",), ("triceps", "shoulders"), aliases=("incline",)),
    Exercise("Overhead Press", ("shoulders",), ("triceps", "core"), standard="ohp", aliases=("ohp", "press")),
    Exercise("Squat", ("quads", "glutes"), ("hamstrings", "core"), standard="squat", aliases=("back squat",)),
    Exercise("Front Squat", ("quads",), ("glutes", "core"), aliases=("fs",)),
    Exercise("Deadlift", ("hamstrings", "glutes", "back"), ("forearms", "core"), standard="deadlift", aliases=("dl",)),
    Exercise("Romanian Deadlift", ("hamstrings", "glutes"), ("back",), aliases=("rdl",)),
    Exercise("Barbell Row", ("back",), ("biceps", "forearms"), standard="row", aliases=("row", "bb row")),
    Exercise("Pull Up", ("back",), ("biceps", "forearms"), bodyweight=True, standard="pullup", aliases=("pullup", "chin up", "chinup")),
    Exercise("Dip", ("chest", "triceps"), ("shoulders",), bodyweight=True, standard="dip", aliases=("dips",)),
    Exercise("Push Up", ("chest",), ("triceps", "core"), bodyweight=True, aliases=("pushup",)),
    Exercise("Barbell Curl", ("biceps",), ("forearms",), standard="curl", aliases=("curl",)),
    Exercise("Lateral Raise", ("shoulders",), aliases=("lat raise",)),
    Exercise("Leg Press", ("quads", "glutes"), ("hamstrings",), aliases=("lp",)),
    Exercise("Leg Curl", ("hamstrings",)),
    Exercise("Calf Raise", ("calves",)),
    Exercise("Plank", ("core",), bodyweight=True),
    Exercise("Lat Pulldown", ("back",), ("biceps",), aliases=("pulldown",)),
    Exercise("Face Pull", ("shoulders", "back")),
    Exercise("Hip Thrust", ("glutes",), ("hamstrings",), standard="hipthrust"),
]

BY_NAME: dict[str, Exercise] = {e.name: e for e in _CATALOG}
_LOOKUP: dict[str, Exercise] = {}
for _e in _CATALOG:
    _LOOKUP[_e.name.lower()] = _e
    for _a in _e.aliases:
        _LOOKUP[_a.lower()] = _e


def resolve(name: str) -> Exercise:
    """Find an exercise by canonical name or alias (case-insensitive)."""
    key = name.strip().lower()
    if key in _LOOKUP:
        return _LOOKUP[key]
    # loose match: unique prefix
    hits = [e for k, e in _LOOKUP.items() if k.startswith(key)]
    uniq = {e.name: e for e in hits}
    if len(uniq) == 1:
        return next(iter(uniq.values()))
    raise KeyError(f"Unknown exercise: {name!r}" + (f" (ambiguous: {sorted(uniq)})" if uniq else ""))


def all_names() -> list[str]:
    return [e.name for e in _CATALOG]
