"""Layout ids the renderers implement. A skill may use only its own set."""

DECK_LAYOUTS = frozenset(
    {
        "cover",
        "big-number",
        "versus-target",
        "movers",
        "risk",
        "ask",
        "statement",
        "step",
    }
)

RECORDING_LAYOUTS = frozenset({"step", "statement"})

ALL_LAYOUTS = DECK_LAYOUTS | RECORDING_LAYOUTS

SKILL_LAYOUTS = {
    "weekly-ops-review": frozenset(
        {"cover", "big-number", "versus-target", "movers", "risk", "ask"}
    ),
    "leadership-brief": frozenset({"cover", "statement", "risk", "ask"}),
    "launch-announcement": frozenset({"cover", "statement", "ask"}),
    "product-walkthrough": frozenset({"step"}),
    "sop-training": frozenset({"step"}),
    "feature-delta": frozenset({"step", "statement"}),
    "localize": ALL_LAYOUTS,
}

SKILL_RENDERER = {
    "weekly-ops-review": "deck",
    "leadership-brief": "deck",
    "launch-announcement": "deck",
    "product-walkthrough": "recording",
    "sop-training": "recording",
    "feature-delta": "recording",
    "localize": "deck",
}

FORBIDDEN_KEYS = frozenset({"style", "color", "font", "css", "theme", "background"})
