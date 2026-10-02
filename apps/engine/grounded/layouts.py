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

_WBR = frozenset({"cover", "big-number", "versus-target", "movers", "risk", "ask"})
_STEP = frozenset({"step"})

SKILL_LAYOUTS = {
    "weekly-ops-review": _WBR,
    "wbr-kpi-spine": _WBR,
    "wbr-executive": _WBR,
    "wbr-ops-deep-dive": _WBR,
    "wbr-ask-pack": _WBR,
    "wbr-exception-only": _WBR | {"statement"},
    "kpi-spotlight-deck": frozenset({"cover", "big-number", "versus-target"}),
    "comparison-versus-deck": frozenset({"cover", "versus-target"}),
    "risk-and-ask-deck": frozenset({"cover", "risk", "ask"}),
    "one-pager-summary-deck": _WBR,
    "leadership-brief": frozenset({"cover", "statement", "risk", "ask"}),
    "launch-announcement": frozenset({"cover", "statement", "ask"}),
    "product-walkthrough": _STEP,
    "sop-training": _STEP,
    "feature-delta": frozenset({"step", "statement"}),
    "chaptered-demo-cut": _STEP,
    "continuous-take-demo": _STEP,
    "carry-boundary-verify": _STEP,
    "still-sequence-slideshow": _STEP,
    "chapter-still-advance": _STEP,
    "sop-step-slideshow": _STEP,
    "cited-frame-hold": _STEP,
    "launch-still-carousel": _STEP,
    "before-after-still-show": _STEP,
    "caption-studio-local": _STEP,
    "local-video-assembly": _STEP,
    "storyboard-from-chapters": _STEP,
    "text-overlay-cards": _STEP,
    "narration-room-mix": _STEP,
    "identity-consistency-lock": _STEP,
    "localize": ALL_LAYOUTS,
}

SLIDESHOW_SKILLS = frozenset(
    {
        "still-sequence-slideshow",
        "chapter-still-advance",
        "sop-step-slideshow",
        "cited-frame-hold",
        "launch-still-carousel",
        "before-after-still-show",
    }
)

SKILL_RENDERER = {
    "weekly-ops-review": "deck",
    "wbr-kpi-spine": "deck",
    "wbr-executive": "deck",
    "wbr-ops-deep-dive": "deck",
    "wbr-ask-pack": "deck",
    "wbr-exception-only": "deck",
    "kpi-spotlight-deck": "deck",
    "comparison-versus-deck": "deck",
    "risk-and-ask-deck": "deck",
    "one-pager-summary-deck": "deck",
    "leadership-brief": "deck",
    "launch-announcement": "deck",
    "product-walkthrough": "recording",
    "sop-training": "recording",
    "feature-delta": "recording",
    "chaptered-demo-cut": "recording",
    "continuous-take-demo": "recording",
    "carry-boundary-verify": "recording",
    "still-sequence-slideshow": "recording",
    "chapter-still-advance": "recording",
    "sop-step-slideshow": "recording",
    "cited-frame-hold": "recording",
    "launch-still-carousel": "recording",
    "before-after-still-show": "recording",
    "caption-studio-local": "recording",
    "local-video-assembly": "recording",
    "storyboard-from-chapters": "recording",
    "text-overlay-cards": "recording",
    "narration-room-mix": "recording",
    "identity-consistency-lock": "recording",
    "localize": "deck",
}

FORBIDDEN_KEYS = frozenset({"style", "color", "font", "css", "theme", "background"})
