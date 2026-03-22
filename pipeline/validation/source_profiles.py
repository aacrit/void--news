"""
Source profile reference data for cross-reference validation.

Maps AllSides ratings to expected lean score ranges for the 0-100 scale
used by the void --news political lean analyzer.
"""

# AllSides rating -> expected score range on 0-100 scale
# (0 = far-left, 50 = center, 100 = far-right)
ALLSIDES_TO_LEAN_RANGE: dict[str, tuple[int, int]] = {
    "left":       (0, 30),
    "lean left":  (25, 45),
    "center":     (40, 60),
    "lean right": (55, 75),
    "right":      (70, 100),
}

# AllSides ratings for known outlets (as of 2026)
OUTLET_ALLSIDES: dict[str, str] = {
    "ap-news":             "center",
    "reuters":             "center",
    "upi":                 "center",
    "nyt":                 "lean left",
    "washington-post":     "lean left",
    "npr":                 "lean left",
    "pbs":                 "lean left",
    "cnn":                 "lean left",
    "msnbc":               "left",
    "jacobin":             "left",
    "the-intercept":       "left",
    "mother-jones":        "left",
    "the-nation":          "left",
    "huffpost":            "left",
    "daily-kos":           "left",
    "occupy-democrats":    "left",
    "guardian":            "lean left",
    "bbc":                 "center",
    "bloomberg":           "center",
    "wsj":                 "lean right",
    "fox-news":            "right",
    "breitbart":           "right",
    "daily-wire":          "right",
    "daily-caller":        "lean right",
    "newsmax":             "right",
    "national-review":     "lean right",
    "propublica":          "lean left",
    "bellingcat":          "lean left",
    "rt":                  "right",      # state-affiliated, right-coded for geopolitical alignment
    "cgtn":                "right",      # state-affiliated
    "sputnik":             "right",      # state-affiliated
    "global-times":        "right",      # state-affiliated
    "the-economist":       "center",
    "associated-press":    "center",
    "abc-news":            "lean left",
    "nbc-news":            "lean left",
    "cbs-news":            "lean left",
    "hill":                "center",
    "politico":            "lean left",
    "axios":               "center",
    "washington-examiner": "lean right",
    "new-york-post":       "lean right",
    "reason":              "center",
    "the-atlantic":        "lean left",
    "vox":                 "left",
    "slate":               "left",
}


def get_expected_range(allsides_rating: str) -> tuple[int, int] | None:
    """Return the expected lean score range for an AllSides rating, or None."""
    return ALLSIDES_TO_LEAN_RANGE.get(allsides_rating.lower().strip())


def get_outlet_rating(outlet_slug: str) -> str | None:
    """Return the AllSides rating for an outlet slug, or None if unknown."""
    return OUTLET_ALLSIDES.get(outlet_slug.lower().strip())
