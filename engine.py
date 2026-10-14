"""
Emergency readiness forge engine.

Parser + scoring + calendar + go-bag + communication tree + risk flags.

Pure-stdlib. No external calls.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------
# Lexicon / dictionaries
# ----------------------------------------------------------------------------

US_STATES = {
    "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
    "CA": "california", "CO": "colorado", "CT": "connecticut",
    "DE": "delaware", "FL": "florida", "GA": "georgia", "HI": "hawaii",
    "ID": "idaho", "IL": "illinois", "IN": "indiana", "IA": "iowa",
    "KS": "kansas", "KY": "kentucky", "LA": "louisiana", "ME": "maine",
    "MD": "maryland", "MA": "massachusetts", "MI": "michigan",
    "MN": "minnesota", "MS": "mississippi", "MO": "missouri",
    "MT": "montana", "NE": "nebraska", "NV": "nevada", "NH": "new hampshire",
    "NJ": "new jersey", "NM": "new mexico", "NY": "new york",
    "NC": "north carolina", "ND": "north dakota", "OH": "ohio",
    "OK": "oklahoma", "OR": "oregon", "PA": "pennsylvania",
    "RI": "rhode island", "SC": "south carolina", "SD": "south dakota",
    "TN": "tennessee", "TX": "texas", "UT": "utah", "VT": "vermont",
    "VA": "virginia", "WA": "washington", "WV": "west virginia",
    "WI": "wisconsin", "WY": "wyoming", "DC": "district of columbia",
}

# Heuristic hazard sensitivity by state (for fallback when region didn't specify)
# Each state gets a base "concern" vector 0..3 across the 14 categories
STATE_HAZARD_BASE: Dict[str, Dict[str, int]] = {
    "default": {"wildfire": 1, "hurricane": 0, "tornado": 1, "earthquake": 0, "flood": 1, "winter-storm": 1, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 1, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "CA": {"wildfire": 3, "hurricane": 0, "tornado": 0, "earthquake": 3, "flood": 1, "winter-storm": 0, "extreme-heat": 2, "power-outage": 3, "water-outage": 1, "severe-storm": 1, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "TX": {"wildfire": 1, "hurricane": 3, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 3, "power-outage": 3, "water-outage": 1, "severe-storm": 2, "chemical": 2, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "FL": {"wildfire": 0, "hurricane": 3, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 0, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "LA": {"wildfire": 0, "hurricane": 3, "tornado": 1, "earthquake": 0, "flood": 3, "winter-storm": 1, "extreme-heat": 3, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 2, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MS": {"wildfire": 0, "hurricane": 3, "tornado": 2, "earthquake": 0, "flood": 3, "winter-storm": 1, "extreme-heat": 3, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "AL": {"wildfire": 0, "hurricane": 2, "tornado": 3, "earthquake": 0, "flood": 2, "winter-storm": 1, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "GA": {"wildfire": 0, "hurricane": 2, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 0, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "SC": {"wildfire": 0, "hurricane": 3, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 0, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "NC": {"wildfire": 0, "hurricane": 3, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 1, "extreme-heat": 1, "power-outage": 2, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "OK": {"wildfire": 1, "hurricane": 0, "tornado": 3, "earthquake": 1, "flood": 2, "winter-storm": 2, "extreme-heat": 3, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "KS": {"wildfire": 1, "hurricane": 0, "tornado": 3, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 3, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "NE": {"wildfire": 1, "hurricane": 0, "tornado": 3, "earthquake": 0, "flood": 1, "winter-storm": 2, "extreme-heat": 2, "power-outage": 1, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "IA": {"wildfire": 0, "hurricane": 0, "tornado": 3, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 1, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MO": {"wildfire": 0, "hurricane": 0, "tornado": 3, "earthquake": 1, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "AR": {"wildfire": 0, "hurricane": 1, "tornado": 3, "earthquake": 1, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "TN": {"wildfire": 0, "hurricane": 1, "tornado": 3, "earthquake": 1, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "KY": {"wildfire": 0, "hurricane": 0, "tornado": 2, "earthquake": 1, "flood": 2, "winter-storm": 2, "extreme-heat": 1, "power-outage": 2, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "IL": {"wildfire": 0, "hurricane": 0, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 1, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "IN": {"wildfire": 0, "hurricane": 0, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 2, "power-outage": 1, "water-outage": 0, "severe-storm": 3, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "OH": {"wildfire": 0, "hurricane": 0, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MI": {"wildfire": 0, "hurricane": 0, "tornado": 1, "earthquake": 0, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 2, "water-outage": 1, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "WI": {"wildfire": 0, "hurricane": 0, "tornado": 1, "earthquake": 0, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 1, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MN": {"wildfire": 0, "hurricane": 0, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 1, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "ND": {"wildfire": 1, "hurricane": 0, "tornado": 2, "earthquake": 0, "flood": 2, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "SD": {"wildfire": 1, "hurricane": 0, "tornado": 2, "earthquake": 0, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "NY": {"wildfire": 0, "hurricane": 2, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "NJ": {"wildfire": 0, "hurricane": 2, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 2, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "PA": {"wildfire": 0, "hurricane": 0, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MA": {"wildfire": 0, "hurricane": 2, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "CT": {"wildfire": 0, "hurricane": 1, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 2, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "WA": {"wildfire": 1, "hurricane": 0, "tornado": 0, "earthquake": 3, "flood": 2, "winter-storm": 1, "extreme-heat": 0, "power-outage": 1, "water-outage": 0, "severe-storm": 1, "chemical": 1, "volcanic": 2, "civil-unrest": 0, "pandemic": 1},
    "OR": {"wildfire": 2, "hurricane": 0, "tornado": 0, "earthquake": 3, "flood": 1, "winter-storm": 1, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 1, "chemical": 0, "volcanic": 1, "civil-unrest": 0, "pandemic": 1},
    "NV": {"wildfire": 1, "hurricane": 0, "tornado": 0, "earthquake": 2, "flood": 0, "winter-storm": 1, "extreme-heat": 3, "power-outage": 1, "water-outage": 1, "severe-storm": 0, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "AZ": {"wildfire": 2, "hurricane": 0, "tornado": 0, "earthquake": 1, "flood": 1, "winter-storm": 0, "extreme-heat": 3, "power-outage": 1, "water-outage": 1, "severe-storm": 0, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "UT": {"wildfire": 1, "hurricane": 0, "tornado": 0, "earthquake": 2, "flood": 1, "winter-storm": 2, "extreme-heat": 2, "power-outage": 1, "water-outage": 1, "severe-storm": 1, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "HI": {"wildfire": 0, "hurricane": 2, "tornado": 0, "earthquake": 2, "flood": 1, "winter-storm": 0, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 1, "chemical": 0, "volcanic": 3, "civil-unrest": 0, "pandemic": 1},
    "AK": {"wildfire": 0, "hurricane": 0, "tornado": 0, "earthquake": 3, "flood": 1, "winter-storm": 3, "extreme-heat": 0, "power-outage": 1, "water-outage": 1, "severe-storm": 1, "chemical": 0, "volcanic": 1, "civil-unrest": 0, "pandemic": 1},
    "NM": {"wildfire": 2, "hurricane": 0, "tornado": 0, "earthquake": 1, "flood": 0, "winter-storm": 1, "extreme-heat": 2, "power-outage": 1, "water-outage": 1, "severe-storm": 1, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "CO": {"wildfire": 2, "hurricane": 0, "tornado": 1, "earthquake": 1, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "WY": {"wildfire": 1, "hurricane": 0, "tornado": 0, "earthquake": 1, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "ID": {"wildfire": 2, "hurricane": 0, "tornado": 0, "earthquake": 1, "flood": 1, "winter-storm": 2, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 1, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "MT": {"wildfire": 1, "hurricane": 0, "tornado": 0, "earthquake": 1, "flood": 1, "winter-storm": 3, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 0, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
    "VA": {"wildfire": 1, "hurricane": 2, "tornado": 1, "earthquake": 0, "flood": 2, "winter-storm": 1, "extreme-heat": 1, "power-outage": 1, "water-outage": 0, "severe-storm": 2, "chemical": 1, "volcanic": 0, "civil-unrest": 0, "pandemic": 1},
}

# Wildfire hot-county keywords
WILDFIRE_COUNTIES = ["el cajon", "san diego", "altadena", "malibu", "santa rosa", "paradise", "redding",
                     "medford", "boulder", "phoenix", "prescott", "reno", "maui", "lahaina", "gresham"]

# Hurricane hot-county keywords
HURRICANE_COUNTIES = ["harris", "galveston", "hancock", "miami-dade", "broward", "pinellas", "tampa",
                      "new orleans", "jefferson", "charleston", "beaufort", "outer banks", "dare",
                      "hyde", "palm beach", "lee", "collier"]

# Tornado alley keywords
TORNADO_COUNTIES = ["tornado alley", "oklahoma city", "wichita", "tulsa", "norman",
                    "amarillo", "lubbock", "joplin", "springfield"]

# Flood zone keywords
FLOOD_COUNTIES = ["houston", "harvey", "katrina", "sandy hook", "bayou", "river-bottoms",
                  "low-country", "outer banks", "floodplain"]

# Earthquake hot county keywords
EARTHQUAKE_COUNTIES = ["san andreas", "hayward fault", "santa cruz", "salinas", "parkfield",
                       "ridgecrest", "anchorage", "kodiak"]

# Power-outage (PSPS / grid) hot county keywords
PSPS_COUNTIES = ["el cajon", "san diego", "sonoma", "napa", "mendocino", "humboldt",
                 "santa rosa", "santa cruz", "sierra"]

# Region aliases
STATE_KEYWORD_BY_NAME = {v: k for k, v in US_STATES.items()}

# Month labels
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ----------------------------------------------------------------------------
# Parser
# ----------------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def parse_household_profile(text: str) -> Dict[str, Any]:
    """Parse the free-form brief into structured profile fields."""
    p = _norm(text)

    # ---- region (state + county/city)
    state_code: Optional[str] = None
    county_or_city: Optional[str] = None
    # explicit "Region: Texas, Harris County (Houston metro)" style first
    m = re.search(r"region[:\s]+([^.]+?)(?:\.|household:|home:|hazards|mobility|medical|vehicles|utilities|pets|school|evac|concerns|$)", p)
    if not m:
        # second-best: search "<State>," style in the first 300 chars
        m = re.search(r"\b(" + "|".join(re.escape(v) for v in US_STATES.values()) + r")\b", p)
    region_blob = (m.group(1).strip() if m else "").rstrip(".,")
    # split into state + county
    for name, code in STATE_KEYWORD_BY_NAME.items():
        if name in region_blob:
            state_code = code
            break
    # county/city extraction: text after the state name (more careful — only strip
    # the *first* matched state name, keep the rest as county/city context)
    if state_code:
        state_name = US_STATES[state_code]
        parts = region_blob.split(state_name, 1)
        county_or_city = parts[1].strip() if len(parts) > 1 else ""
        # strip leading comma + whitespace
        county_or_city = re.sub(r"^[,\s]+", "", county_or_city)
        # also strip trailing punctuation
        county_or_city = re.sub(r"[.,;]+$", "", county_or_city).strip()
        # remove leading "county:" / "state:" prefix if any
        county_or_city = re.sub(r"^(county|city|metro|metro area)\s*:?\s*", "", county_or_city).strip()
        # collapse whitespace
        county_or_city = re.sub(r"\s+", " ", county_or_city)
        if not county_or_city:
            county_or_city = None
    else:
        county_or_city = None

    # ---- adults count
    adults = 0
    m = re.search(r"\b(\d+|one|two|three|four|five|couple|several)\s+adults?\b", p)
    if m:
        word = m.group(1)
        adults = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "couple": 2, "several": 3
        }.get(word, int(word) if word.isdigit() else 0)
    if adults == 0:
        # fallback: search "couple" or "husband and wife" or "2 adults"
        if "couple" in p:
            adults = 2
        else:
            # count explicit numeric mentions
            nums = [int(x) for x in re.findall(r"\b(\d+)\s+adults?\b", p)]
            adults = nums[0] if nums else 0

    # ---- kids count and ages
    kids = 0
    kid_ages: List[int] = []
    m = re.search(r"\b(\d+)\s+kids?\b", p)
    if m:
        kids = int(m.group(1))
    # ages
    age_pattern = re.compile(r"\b(?:age[d]?\s*(\d{1,2})|(\d{1,2})(?:\s*(?:year|\s*yo))|\((\d{1,2})\))", re.I)
    for hit in age_pattern.findall(p):
        for x in hit:
            if x and x.isdigit():
                kid_ages.append(int(x))

    # seniors (negation-aware: "no seniors" must not count)
    seniors = 0

    def _has_unnegated_simple(needle: str, p_text: str) -> bool:
        idx = 0
        separators = r"[.?;\n]"
        while True:
            idx = p_text.find(needle, idx)
            if idx == -1:
                return False
            window = p_text[max(0, idx - 60):idx]
            last_sep = max((m.start() for m in re.finditer(separators, window)), default=-1)
            clause = window[last_sep + 1:] if last_sep >= 0 else window
            if re.search(r"\b(no|not|without|none)\b", clause):
                idx += len(needle)
                continue
            return True

    has_senior_pos = _has_unnegated_simple("senior", p) or _has_unnegated_simple("elderly", p)
    if has_senior_pos:
        seniors = 1
    if re.search(r"\b\d{2}\s*yo\s+parent\b", p) or re.search(r"\b\d{2}\s*yo\s+grandparent", p):
        seniors += 1
    m = re.search(r"(\d+|one|two|three)\s+senior", p)
    if m:
        seniors = {"one": 1, "two": 2, "three": 3}.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else 1)

    # ---- pets
    pets: List[Dict[str, Any]] = []
    pet_patterns = [
        (r"(\d+)\s+dog(?:s)?", "dog"),
        (r"(\d+|a|one|two|three)\s+cat(?:s)?", "cat"),
        (r"(\d+|a|one|two|three)\s+bird(?:s)?", "bird"),
        (r"(\d+|a|one|two|three)\s+rabbit(?:s)?", "rabbit"),
        (r"(\d+|a|one|two|three)\s+reptile(?:s)?", "reptile"),
        (r"(\d+|a|one|two|three)\s+fish\b", "fish"),
        (r"(\d+|a|one|two|three)\s+hampster(?:s)?|hamster", "hamster"),
    ]
    for pat, kind in pet_patterns:
        for m in re.finditer(pat, p):
            q = m.group(1)
            if not q.isdigit():
                q = {"a": 1, "one": 1, "two": 2, "three": 3}.get(q, 1)
            else:
                q = int(q)
            pets.append({"species": kind, "quantity": q})

    # dedupe by species (sum qty)
    pet_map: Dict[str, int] = {}
    for p_item in pets:
        pet_map[p_item["species"]] = pet_map.get(p_item["species"], 0) + p_item["quantity"]
    pets_summary = [{"species": k, "quantity": v} for k, v in pet_map.items()]

    # ---- home type
    home_type: Optional[str] = None
    if "townhome" in p or "townhouse" in p or "town home" in p:
        home_type = "townhome"
    elif "condo" in p:
        home_type = "condo"
    elif "apartment" in p:
        home_type = "apartment"
    elif "single-family" in p or "single family" in p or "single-family home" in p:
        home_type = "single-family"
    elif "mobile home" in p or "manufactured home" in p:
        home_type = "mobile-home"
    elif "duplex" in p:
        home_type = "duplex"

    # ---- floors / stories
    stories = 1
    m = re.search(r"(\d+)\s*stor(?:y|ies|y)\b", p)
    if m:
        stories = int(m.group(1))
    elif "second floor" in p or "second story" in p or "2nd floor" in p:
        stories = max(stories, 2)

    # ---- basement
    has_basement = "basement" in p and "no basement" not in p and "without basement" not in p

    # ---- garage
    has_garage = ("garage" in p) and ("no garage" not in p) and ("without garage" not in p)

    # ---- hazards user-cares-about list
    hazards_explicit = set()
    explicit_hazards = re.findall(
        r"\b(wildfire|hurricane|tornado|earthquake|flood|winter[- ]?storm|extreme[- ]?heat|"
        r"power[- ]?outage|water[- ]?outage|severe[- ]?storm|chemical|volcanic|"
        r"civil[- ]?unrest|pandemic)\b",
        p,
    )
    hazards_explicit = {h.replace(" ", "-") for h in explicit_hazards}

    # ---- work-from-home count
    wfh_adults = 0
    m = re.search(r"(\d+|one|two|three)\s+(?:adults?\s+)?(?:are\s+)?(?:wfh|work[- ]?from[- ]?home|remote)", p)
    if m:
        word = m.group(1)
        wfh_adults = {"one": 1, "two": 2, "three": 3}.get(word, int(word) if word.isdigit() else 1)
    else:
        # "1 adult WFH full-time"
        m = re.search(r"(\d+|one|two)\s+adults?\s+wfh", p)
        if m:
            word = m.group(1)
            wfh_adults = {"one": 1, "two": 2}.get(word, int(word) if word.isdigit() else 1)
        elif "wfh" in p or "work from home" in p or "remote work" in p:
            wfh_adults = 1

    # ---- commute distance
    commute_miles: Optional[float] = None
    m = re.search(r"commutes?\s+(\d+)\s*miles?\b", p)
    if m:
        commute_miles = float(m.group(1))
    m = re.search(r"(\d+)\s*miles?\s+(?:one-way|to work)", p)
    if m and commute_miles is None:
        commute_miles = float(m.group(1))

    # ---- mobility issues
    has_senior = seniors > 0
    has_mobility_issue = (
        "mobility" in p and "no mobility" not in p
        and ("cane" in p or "walker" in p or "wheelchair" in p or "limited mobility" in p or "second floor" in p)
    ) or ("walks with cane" in p)
    has_second_floor_bedroom = ("second floor" in p or "upstairs" in p or "second story" in p) and "bedroom" in p

    # ---- medical (negation-aware: "No dialysis / oxygen / vents" must not match)
    def _has_unnegated(needle: str, p_text: str) -> bool:
        """True if needle appears in p_text but NOT in a 'no X / Y / Z' clause.

        Algorithm: scan every occurrence of `needle`. For each, look back up to
        60 chars; if any of the tokens 'no', 'not', 'without', 'denies',
        'none', 'no need', 'no use', 'do not', 'haven't', 'don't have/use' is
        found *within the same slash- or comma-separated clause* (not separated
        by '.', ';', '?', or a newline), treat that occurrence as negated and
        continue scanning.
        """
        negation_words = (
            r"no(?!t)",
            r"not",
            r"without",
            r"denies",
            r"none",
            r"haven['’]t",
            r"don['’]t have",
            r"don['’]t use",
            r"don['’]t need",
            r"do\s+not",
            r"never",
            r"no\s+need",
            r"no\s+use",
        )
        separators = r"[.?;\n]"
        idx = 0
        while True:
            idx = p_text.find(needle, idx)
            if idx == -1:
                return False
            # look back 80 chars
            start = max(0, idx - 80)
            window = p_text[start:idx]
            # truncate window at the most recent sentence-separator (negation only spans within a clause)
            last_sep = max(
                (m.start() for m in re.finditer(separators, window)),
                default=-1,
            )
            clause = window[last_sep + 1:] if last_sep >= 0 else window
            if re.search(r"\b(" + "|".join(negation_words) + r")\b", clause):
                idx += len(needle)
                continue
            return True
    medical_flags: List[str] = []
    if _has_unnegated("asthma", p):
        medical_flags.append("asthma")
    if _has_unnegated("inhaler", p):
        medical_flags.append("inhaler")
    if _has_unnegated("dialysis", p):
        medical_flags.append("dialysis")
    if _has_unnegated("oxygen", p) and _has_unnegated("tank", p):
        medical_flags.append("oxygen_tank")
    if "cpap" in p or "sleep apnea" in p:
        medical_flags.append("cpap")
    if _has_unnegated("blood thinner", p) or _has_unnegated("anticoagulant", p):
        medical_flags.append("blood_thinners")
    if _has_unnegated("insulin", p) or _has_unnegated("diabetes", p) or _has_unnegated("diabetic", p):
        medical_flags.append("diabetes")
    if _has_unnegated("epipen", p) or _has_unnegated("epinephrine", p):
        medical_flags.append("epipen")
    if re.search(r"rx\s+refill(?:\s+every)?\s*\d+\s*day", p) or _has_unnegated("prescription refill", p):
        medical_flags.append("prescription_refill")

    # ---- vehicles (collect distinct matches within a VEHICLES section, or after
    # "vehicles:" prefix, to avoid matching "we have a car" qualitatively)
    vehicle_count = 0
    # Method 1: explicit "VEHICLES: 1 sedan, 1 SUV" line
    v_section = re.search(r"vehicles?[:\s]+(.+?)(?:\.|$)", text, re.I | re.M)
    if v_section:
        v_text = _norm(v_section.group(1))
        _vehicle_qty_by_kind: Dict[str, int] = {}
        for m in re.finditer(r"\b(\d+|a|one|two|three|four|five)\s+(sedan(?:s)?|suv(?:s)?|truck(?:s)?|car(?:s)?|vehicle(?:s)?|minivan(?:s)?|van(?:s)?)\b", v_text):
            q_word = m.group(1)
            kind = m.group(2)
            q = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.get(q_word, int(q_word) if q_word.isdigit() else 1)
            _vehicle_qty_by_kind[kind] = max(_vehicle_qty_by_kind.get(kind, 0), q)
        if _vehicle_qty_by_kind:
            vehicle_count = sum(_vehicle_qty_by_kind.values())
    if vehicle_count == 0:
        # Method 2: search the whole brief (catches pre-line "2 sedans in the garage" style)
        _vehicle_qty_by_kind = {}
        for m in re.finditer(r"\b(\d+|a|one|two|three|four|five)\s+(sedan(?:s)?|suv(?:s)?|truck(?:s)?|car(?:s)?|vehicle(?:s)?|minivan(?:s)?|van(?:s)?)\b", p):
            q_word = m.group(1)
            kind = m.group(2)
            q = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}.get(q_word, int(q_word) if q_word.isdigit() else 1)
            _vehicle_qty_by_kind[kind] = max(_vehicle_qty_by_kind.get(kind, 0), q)
        if _vehicle_qty_by_kind:
            vehicle_count = sum(_vehicle_qty_by_kind.values())

    # ---- utilities
    utilities: List[str] = []
    if "gas" in p and ("sdg&e" in p or "natural gas" in p or "utility" in p or "psps" in p or "txu" in p or "comed" in p):
        utilities.append("gas")
    if "electric" in p or "psps" in p:
        utilities.append("electric")
    if "water" in p:
        utilities.append("water")
    if "internet" in p or "wifi" in p:
        utilities.append("internet")
    if "septic" in p:
        utilities.append("septic")
    if "well" in p:
        utilities.append("well")

    # ---- power-outage specificity
    psps_zone = "psps" in p or "red-flag" in p or "red flag shutdown" in p or any(c in p for c in PSPS_COUNTIES)
    grid_zone = "texas grid" in p or "txu" in p or "long power outage" in p

    # ---- evac preference
    evac_pref: Optional[str] = None
    if "leave early" in p:
        evac_pref = "leave_early"
    elif "stay unless" in p or "shelter in place" in p or "shelter-in-place" in p:
        evac_pref = "shelter_in_place"
    elif "late evac" in p or "evacuate last" in p or "wait until" in p:
        evac_pref = "leave_late"

    # ---- kids in school
    has_school_kids = kids > 0 and ("school" in p)

    # ---- pets: reactive/friendly
    pet_reactive = "reactive" in p
    pet_big = any(item["species"] == "dog" for item in pets_summary) and "big dog" in p

    # ---- hurricane shutter
    has_shutters = "shutter" in p or "plywood pre-cut" in p
    # ---- generator
    has_generator = ("generator" in p) and ("no generator" not in p) and ("without generator" not in p)
    # ---- weather radio
    has_weather_radio = ("weather radio" in p or "noaa" in p) and "no weather radio" not in p
    # ---- alerrts/noaa app
    alerts_app = ("alert" in p or "noaa" in p or "fema app" in p)

    # ---- out-of-area contact
    has_out_of_area_contact = (
        ("out-of-area" in p or "out of area" in p) and "no out-of-area" not in p
    ) or ("place to stay" in p and ("temecula" in p or "with my brother" in p or "with family" in p or "stay with" in p))

    # ---- backup heat
    has_backup_heat = "backup heat" in p or "fireplace" in p or "wood stove" in p or "space heater" in p

    # ---- defensible space (wildfire)
    has_defensible_space = "defensible space" in p or "0-5 ft" in p or "zone 0" in p

    # ---- safe room (tornado / earthquake)
    has_safe_room = "safe room" in p or "shelter" in p

    # ---- strap / anchor (earthquake)
    has_strap = "strap" in p or "anchor" in p

    # ---- flood insurance
    has_flood_insurance = "flood insurance" in p or re.search(r"\bnfip\b", p) is not None

    # ---- concerns list (raw)
    concerns = []
    cm = re.search(r"concerns?:\s*(.+?)(?:\n\n|$)", text, re.I | re.S)
    if cm:
        concerns = [ln.strip("- ").strip() for ln in cm.group(1).splitlines() if ln.strip()]

    return {
        "state": state_code,
        "county_or_city": county_or_city,
        "region_blob": region_blob,
        "adults": adults,
        "kids": kids,
        "kid_ages": kid_ages,
        "seniors": seniors,
        "pets": pets_summary,
        "home_type": home_type,
        "stories": stories,
        "has_basement": has_basement,
        "has_garage": has_garage,
        "hazards_explicit": sorted(hazards_explicit),
        "wfh_adults": wfh_adults,
        "commute_miles": commute_miles,
        "has_mobility_issue": has_mobility_issue or has_second_floor_bedroom,
        "medical_flags": medical_flags,
        "vehicle_count": vehicle_count if vehicle_count else None,
        "utilities": utilities,
        "psps_zone": psps_zone,
        "grid_zone": grid_zone,
        "evac_pref": evac_pref,
        "has_school_kids": has_school_kids,
        "pet_reactive": pet_reactive,
        "has_shutters": has_shutters,
        "has_generator": has_generator,
        "has_weather_radio": has_weather_radio,
        "alerts_app": alerts_app,
        "has_out_of_area_contact": has_out_of_area_contact,
        "has_backup_heat": has_backup_heat,
        "has_defensible_space": has_defensible_space,
        "has_safe_room": has_safe_room,
        "has_strap": has_strap,
        "has_flood_insurance": has_flood_insurance,
        "concerns": concerns,
    }


# ----------------------------------------------------------------------------
# Hazard scoring (combines explicit hazards + region/state heuristic)
# ----------------------------------------------------------------------------

def score_hazards(profile: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict hazard -> { level (0..3), reason, guidance }.
    Level 0 none, 1 low, 2 med, 3 high.
    """
    hazards: Dict[str, Dict[str, Any]] = {}

    # explicit hazards from the brief get +2 (user-cares-about)
    explicit = set(profile.get("hazards_explicit") or [])
    county = (profile.get("county_or_city") or "").lower()
    state = profile.get("state")

    def _clamp(x: int) -> int:
        return max(0, min(3, x))

    # ---- wildfire
    wildfire_level = 0
    wildfire_reason_parts = []
    if "wildfire" in explicit:
        wildfire_level += 2
        wildfire_reason_parts.append("user flagged wildfire as primary concern")
    if state and STATE_HAZARD_BASE.get(state, {}).get("wildfire", 0) >= 2:
        wildfire_level += 1
        wildfire_reason_parts.append(f"state {state} is a documented wildfire zone")
    if any(c in county for c in WILDFIRE_COUNTIES):
        wildfire_level += 1
        wildfire_reason_parts.append(f"county/city '{county}' appears in wildfire-prone county list")
    hazards["wildfire"] = {
        "level": _clamp(wildfire_level),
        "reason": "; ".join(wildfire_reason_parts) or "low inherent risk",
        "guidance": "Defensible-space (Zone 0 / 5ft), 2 exit routes, go-bag ready, N95 respirators for smoke, ignition-resistant landscaping in Zone 1.",
    }

    # ---- hurricane
    hurricane_level = 0
    hp = []
    if "hurricane" in explicit:
        hurricane_level += 2
        hp.append("user flagged hurricane")
    if state in {"FL", "LA", "MS", "TX", "AL", "GA", "SC", "NC", "VA", "HI", "NY", "NJ", "MA"}:
        sb = STATE_HAZARD_BASE.get(state, {}).get("hurricane", 0)
        if sb >= 2:
            hurricane_level += 1
            hp.append(f"state {state} is coastline-adjacent")
    if any(c in county for c in HURRICANE_COUNTIES):
        hurricane_level += 1
        hp.append(f"county/city '{county}' is in a hurricane-prone county")
    hazards["hurricane"] = {
        "level": _clamp(hurricane_level),
        "reason": "; ".join(hp) or "low inherent risk",
        "guidance": "Shutter pre-cut plywood (or check accordion shutters), 7-day water + food, evac plan with 2 routes, generator or battery station.",
    }

    # ---- tornado
    tornado_level = 0
    tp = []
    if "tornado" in explicit:
        tornado_level += 2
        tp.append("user flagged tornado")
    if state in {"OK", "KS", "TX", "NE", "IA", "MO", "AR", "TN", "KY", "MS", "AL"}:
        sb = STATE_HAZARD_BASE.get(state, {}).get("tornado", 0)
        if sb >= 2:
            tornado_level += 1
            tp.append(f"state {state} in tornado alley / Dixie alley")
    if any(c in county for c in TORNADO_COUNTIES):
        tornado_level += 1
        tp.append(f"county '{county}' is on the tornado-alley list")
    hazards["tornado"] = {
        "level": _clamp(tornado_level),
        "reason": "; ".join(tp) or "low inherent risk",
        "guidance": "Interior-room shelter on lowest floor, away from windows. Helmets + shoes for everyone. NOAA weather radio. Practice drill quarterly.",
    }

    # ---- earthquake
    earthquake_level = 0
    ep = []
    if "earthquake" in explicit:
        earthquake_level += 2
        ep.append("user flagged earthquake")
    if state in {"CA", "AK", "WA", "OR", "HI", "NV", "UT"}:
        sb = STATE_HAZARD_BASE.get(state, {}).get("earthquake", 0)
        if sb >= 2:
            earthquake_level += 1
            ep.append(f"state {state} sits on a major fault")
    if any(c in county for c in EARTHQUAKE_COUNTIES):
        earthquake_level += 1
        ep.append(f"county '{county}' is on a fault line")
    hazards["earthquake"] = {
        "level": _clamp(earthquake_level),
        "reason": "; ".join(ep) or "low inherent risk",
        "guidance": "Strap water heater + tall furniture. Drop-cover-hold drills. Gas-shutoff wrench at meter. Knowledge of neighborhood gas-shutoff valve location.",
    }

    # ---- flood
    flood_level = 0
    fp = []
    if "flood" in explicit:
        flood_level += 2
        fp.append("user flagged flood")
    if state:
        sb = STATE_HAZARD_BASE.get(state, {}).get("flood", 0)
        if sb >= 2:
            flood_level += 1
            fp.append(f"state {state} has documented flooding history")
    if any(c in county for c in FLOOD_COUNTIES):
        flood_level += 1
        fp.append(f"county '{county}' is on a flood-prone-county list")
    if profile.get("home_type") in {"townhome", "condo", "apartment"} and profile.get("stories", 1) <= 1:
        flood_level += 1
        fp.append("single-story attached housing is more exposed to indoor flooding")
    hazards["flood"] = {
        "level": _clamp(flood_level),
        "reason": "; ".join(fp) or "low inherent risk",
        "guidance": "Flood insurance (separate from homeowners). Important docs on upper floor. Know evacuation route to high ground.",
    }

    # ---- winter storm
    winter_level = 0
    wp = []
    if "winter-storm" in explicit:
        winter_level += 2
        wp.append("user flagged winter storm")
    if state in {"MN", "WI", "MI", "ND", "SD", "MT", "WY", "CO", "NY", "MA"}:
        winter_level += 1
        wp.append(f"state {state} has severe winter weather")
    hazards["winter-storm"] = {
        "level": _clamp(winter_level),
        "reason": "; ".join(wp) or "low inherent risk",
        "guidance": "Backup heat (wood stove / space heater / generator with outdoor placement), insulating kit, vehicle winter emergency bag, calcium chloride for ice.",
    }

    # ---- extreme heat
    heat_level = 0
    hp2 = []
    if "extreme-heat" in explicit:
        heat_level += 2
        hp2.append("user flagged extreme heat")
    if state in {"AZ", "NV", "TX", "FL", "LA", "CA"}:
        heat_level += 1
        hp2.append(f"state {state} regularly exceeds 100°F")
    if profile.get("seniors", 0) > 0 or any(item["species"] == "dog" for item in profile.get("pets") or []):
        heat_level += 1
        hp2.append("household member (senior or dog) is heat-vulnerable")
    hazards["extreme-heat"] = {
        "level": _clamp(heat_level),
        "reason": "; ".join(hp2) or "low inherent risk",
        "guidance": "Cooling centers map, fans + battery station, pet cooling plan, hydration plan with electrolytes.",
    }

    # ---- power outage
    power_level = 0
    pp = []
    if "power-outage" in explicit:
        power_level += 2
        pp.append("user flagged power outage (PSPS / grid)")
    if profile.get("psps_zone"):
        power_level += 1
        pp.append("PSPS (public-safety power shutoff) is normal at the address")
    if profile.get("grid_zone"):
        power_level += 1
        pp.append("Texas-grid instability — long outages are documented")
    if not profile.get("has_generator"):
        power_level += 1
        pp.append("no on-site generator / battery station detected in brief")
    hazards["power-outage"] = {
        "level": _clamp(power_level),
        "reason": "; ".join(pp) or "low inherent risk",
        "guidance": "10-25 kWh battery station OR generator + outdoor placement + extension cords. Car-charger for phone + battery bank. Manual can opener. Cooler + ice strategy.",
    }

    # ---- water outage
    water_level = 0
    wp3 = []
    if "water-outage" in explicit:
        water_level += 2
        wp3.append("user flagged water outage")
    if state in {"CA", "AZ", "NV"}:
        water_level += 1
        wp3.append(f"state {state} has water-restriction / drought history")
    if profile.get("has_basement") and "well" not in (profile.get("utilities") or []):
        water_level += 0  # baseline
    hazards["water-outage"] = {
        "level": _clamp(water_level),
        "reason": "; ".join(wp3) or "low inherent risk",
        "guidance": "7 gallons / person / day × 3 days minimum for water-reserve. Fill bathtub at storm warning. Know building-fill valve on water heater.",
    }

    # ---- severe storm
    storm_level = 0
    sp = []
    if "severe-storm" in explicit:
        storm_level += 2
        sp.append("user flagged severe storm")
    if state and STATE_HAZARD_BASE.get(state, {}).get("severe-storm", 0) >= 3:
        storm_level += 1
        sp.append(f"state {state} is high frequency for severe storms")
    hazards["severe-storm"] = {
        "level": _clamp(storm_level),
        "reason": "; ".join(sp) or "low inherent risk",
        "guidance": "Trim trees near house, secure outdoor furniture, surge protector for sensitive electronics, NOAA weather radio.",
    }

    # ---- chemical
    chem_level = 0
    cp = []
    if "chemical" in explicit:
        chem_level += 2
        cp.append("user flagged chemical")
    if state in {"TX", "LA", "NJ", "OH"}:
        chem_level += 1
        cp.append(f"state {state} has documented chemical/petrochemical corridor")
    hazards["chemical"] = {
        "level": _clamp(chem_level),
        "reason": "; ".join(cp) or "low inherent risk",
        "guidance": "Shelter-in-place kit (duct tape, plastic sheeting, towels wet for door cracks), know Shelter-in-Place alert + drill.",
    }

    # ---- volcanic
    vol_level = 0
    vp = []
    if "volcanic" in explicit:
        vol_level += 2
        vp.append("user flagged volcanic")
    if state in {"HI", "AK", "WA", "OR"}:
        vol_level += 1
        vp.append(f"state {state} has active volcano presence")
    hazards["volcanic"] = {
        "level": _clamp(vol_level),
        "reason": "; ".join(vp) or "low inherent risk",
        "guidance": "N95 / P100 respirators for ash, goggles, plan for ashfall (do NOT drive), goggles for pets.",
    }

    # ---- civil unrest
    civil_level = 0
    cip = []
    if "civil-unrest" in explicit:
        civil_level += 2
        cip.append("user flagged civil unrest")
    hazards["civil-unrest"] = {
        "level": _clamp(civil_level),
        "reason": "; ".join(cip) or "low inherent risk",
        "guidance": "Stay-at-home protocol, off-grid comms plan, fuel + cash reserves.",
    }

    # ---- pandemic
    pandemic_level = 0
    pap = []
    if "pandemic" in explicit:
        pandemic_level += 2
        pap.append("user flagged pandemic")
    if profile.get("seniors", 0) > 0:
        pandemic_level += 1
        pap.append("senior household member is health-vulnerable")
    hazards["pandemic"] = {
        "level": _clamp(pandemic_level),
        "reason": "; ".join(pap) or "low inherent risk",
        "guidance": "60-day medication supply (call insurer for early refill), 4-week non-perishable food, mask / N95 stock, telehealth login pre-staged.",
    }

    return hazards


# ----------------------------------------------------------------------------
# 12-month readiness calendar
# ----------------------------------------------------------------------------

def build_calendar(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns month_label -> [task dicts]. Each task has:
    task, why, category, severity (drive), est_min.
    """
    cal: Dict[str, List[Dict[str, Any]]] = {m: [] for m in MONTHS}

    # baseline monthly tasks every household should do
    for month in MONTHS:
        # weather radio test on first Saturday — January=May etc., pick for each month
        cal[month].append({
            "task": "NOAA weather radio test + replace batteries if low",
            "why": "monthly test catches dead radios before storms",
            "category": "alerts",
            "est_min": 10,
        })
        cal[month].append({
            "task": "Confirm 1-gal water/person/day × 3 days stock (7 days ideal)",
            "why": "water is the #1 supply that quietly leaks when bottles expire",
            "category": "supplies",
            "est_min": 15,
        })

    # pet-tied
    if profile.get("pets"):
        for month in MONTHS:
            cal[month].append({
                "task": f"Check pet-evac kit: crates, leashes, vaccination records, 3-day food/water for {sum(p['quantity'] for p in profile['pets'])} pet(s)",
                "why": "shelters turn away uncrated/unvaxed pets",
                "category": "pets",
                "est_min": 20,
            })

    # medical
    if profile.get("medical_flags"):
        for month in MONTHS:
            cal[month].append({
                "task": "Confirm 30+ day medication supply; call insurer for early-refill if storm forecast",
                "why": f"pharmacies close in disasters; backup of {', '.join(profile['medical_flags'])} keeps the household stable",
                "category": "medical",
                "est_min": 15,
            })

    # generator-tied tasks
    if profile.get("has_generator"):
        for month in ["Mar", "Jun", "Sep", "Dec"]:
            cal[month].append({
                "task": "Run generator under load 30 min + check oil/fuel stabilizer",
                "why": "generators that sit fail to start when needed",
                "category": "generator",
                "est_min": 45,
            })
    elif hazards.get("power-outage", {}).get("level", 0) >= 2:
        cal["Feb"].append({
            "task": "Decide: buy battery station (10-25 kWh) vs portable generator vs whole-home standby. Set budget.",
            "why": "sizing power-backup is the biggest Q before storm season",
            "category": "power",
            "est_min": 90,
        })
        cal["Apr"].append({
            "task": "Order + test chosen power-backup",
            "why": "needs running-time track-record before wildfire/PSPS season",
            "category": "power",
            "est_min": 60,
        })

    # hurricane-tied
    if hazards.get("hurricane", {}).get("level", 0) >= 2:
        cal["Apr"].append({
            "task": "Order plywood + pre-cut to window dimensions; label panels by window",
            "why": "you can't find plywood 3 days before a hurricane",
            "category": "hurricane",
            "est_min": 120,
        })
        cal["Jun"].append({
            "task": "Hurricane pre-season: full-vehicle fuel, generator test, document-bag staged",
            "why": "Atlantic season opens June 1 — get ahead of the run",
            "category": "hurricane",
            "est_min": 90,
        })
        for month in ["Jul", "Aug", "Sep"]:
            cal[month].append({
                "task": "Verify evacuation route map + alternate; print paper copy",
                "why": "GPS cell networks fail in evacuations",
                "category": "hurricane",
                "est_min": 30,
            })

    # tornado-tied
    if hazards.get("tornado", {}).get("level", 0) >= 2:
        cal["Feb"].append({
            "task": "Identify + furnish interior safe room (lowest floor, no windows, closet/bathroom)",
            "why": "tornadoes give minutes of warning — already-knowing the spot saves lives",
            "category": "tornado",
            "est_min": 45,
        })
        cal["Mar"].append({
            "task": "Family tornado drill: 60 seconds from any room to safe room + bike helmets for kids",
            "why": "drill builds muscle memory; helmets are a real thing",
            "category": "tornado",
            "est_min": 30,
        })

    # earthquake-tied
    if hazards.get("earthquake", {}).get("level", 0) >= 2:
        cal["Apr"].append({
            "task": "Strap water heater to wall studs; secure tall furniture to studs (bookcases, dressers)",
            "why": "unsecured water heaters fall + rupture gas lines; bookcases become projectiles",
            "category": "earthquake",
            "est_min": 120,
        })
        cal["Oct"].append({
            "task": "Great ShakeOut drill: full-household Drop-Cover-Hold on a random day",
            "why": "October is Great-ShakeOut month — official drill builds the reflex",
            "category": "earthquake",
            "est_min": 20,
        })

    # wildfire-tied
    if hazards.get("wildfire", {}).get("level", 0) >= 2:
        cal["Mar"].append({
            "task": "Defensible-space: Zone 0 (0-5ft) cleared of combustible material; Zone 1 trimmed",
            "why": "Zone 0 is the single most-effective wildfire mitigation per CAL FIRE data",
            "category": "wildfire",
            "est_min": 180,
        })
        cal["Jun"].append({
            "task": "Pre-evac: stage 2 evac bags + map 2 evacuation routes + identify rendezvous point",
            "why": "California fires build rapidly at night; you leave in 5-15 minutes",
            "category": "wildfire",
            "est_min": 90,
        })
        if profile.get("seniors"):
            cal["May"].append({
                "task": "Senior mobility: stage go-bag on ground floor; pre-decide pickup-assist plan",
                "why": "elderly evac is the leading fatality demographic in wildfires",
                "category": "wildfire",
                "est_min": 60,
            })

    # winter-storm-tied
    if hazards.get("winter-storm", {}).get("level", 0) >= 2:
        cal["Oct"].append({
            "task": "Vehicle winter-emergency bag: blanket, shovel, sand/kitty-litter, flares, snacks",
            "why": "winter stranding is a top-of-list cause of cold-related fatalities",
            "category": "winter",
            "est_min": 60,
        })
        cal["Nov"].append({
            "task": "Backup-heat plan ready (wood stove / fireplace + cleared chimney / generator outdoor)",
            "why": "winter ice knocks power out for 3-7 days in northern US",
            "category": "winter",
            "est_min": 90,
        })

    # flood-tied
    if hazards.get("flood", {}).get("level", 0) >= 2:
        cal["Apr"].append({
            "task": "Verify flood insurance is active (separate from homeowners); check expiration",
            "why": "flood insurance has 30-day waiting period and 1 in 4 claims are not in high-risk zones",
            "category": "flood",
            "est_min": 30,
        })

    # extreme-heat-tied
    if hazards.get("extreme-heat", {}).get("level", 0) >= 2:
        cal["May"].append({
            "task": "Stage AC-window unit OR cooling-center map; check fan + extension cords",
            "why": "elderly heat-stroke is the highest-altitude danger in summer heat-domes",
            "category": "heat",
            "est_min": 60,
        })

    # PSPS-tied: California power shutoffs
    if profile.get("psps_zone"):
        cal["Sep"].append({
            "task": "PSPS season readiness: battery station 100% charged; phone-bank 100%; freezer filled with ice-packs",
            "why": "PSPS events are predictable in fall; pre-staging saves you the run on the gas cans",
            "category": "psps",
            "est_min": 90,
        })

    # pandemic-tied
    if hazards.get("pandemic", {}).get("level", 0) >= 2:
        cal["Jan"].append({
            "task": "Refresh 60-day medication supply (call insurer for early-refill allowance)",
            "why": "pharmacies close during outbreaks",
            "category": "pandemic",
            "est_min": 30,
        })

    # school-kid tied
    if profile.get("has_school_kids"):
        cal["Aug"].append({
            "task": "Confirm school-day pickup protocol + where-go-if-school-closes policy in writing",
            "why": "schools close at 6am under emergency — having a contract with the family avoids panic",
            "category": "family",
            "est_min": 30,
        })

    # annual go-bag rotation
    cal["Jan"].append({
        "task": "Audit go-bags: water expiration, batteries, lighters, kids shoes, pet leashes",
        "why": "go-bags rot quietly; annual audit catches everything",
        "category": "go-bag",
        "est_min": 60,
    })
    cal["Jul"].append({
        "task": "Mid-year drill: 5-minute grab-and-go exercise (entire family)",
        "why": "mid-year is calm enough to time the actual evacuation realistically",
        "category": "drill",
        "est_min": 30,
    })

    return cal


# ----------------------------------------------------------------------------
# Go-bag kit
# ----------------------------------------------------------------------------

def build_gobag(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Build a household go-bag kit. Per-person + per-pet, plus shared-family items."""
    people = (profile.get("adults") or 0) + (profile.get("kids") or 0) + (profile.get("seniors") or 0)
    if people == 0:
        people = 2  # safe default
    pets = sum(p["quantity"] for p in profile.get("pets") or []) if profile.get("pets") else 0

    days = 7  # 7-day go-bag

    # shared formulas (per person)
    water_gallons = 1 * days  # 1 gal per person per day
    food_kcal = 2000 * days  # 2000 kcal/person/day

    # ---- per-person
    per_person = [
        {"item": "Water (1 gal, sealed)", "qty": f"{days} gal"},
        {"item": "Ready-to-eat meals (MRE / energy bar / jerky)", "qty": f"{food_kcal} kcal × {days} d"},
        {"item": "Battery + crank NOAA weather radio + earbuds", "qty": "1 per 2 ppl"},
        {"item": "Headlamp + extra batteries", "qty": "1"},
        {"item": "Whistle", "qty": "1"},
        {"item": "Dust mask (N95 if smoke/locust/pandemic)", "qty": "4"},
        {"item": "Hand sanitizer + moist towelettes", "qty": "1 bottle each"},
        {"item": "Multi-tool / swiss army knife", "qty": "1"},
        {"item": "Cash (small bills)", "qty": "$200/person"},
        {"item": "First-aid kit (family-of-N size)", "qty": "1 / family"},
    ]

    # medical-specific
    if profile.get("medical_flags"):
        for flag in profile["medical_flags"]:
            if flag == "asthma":
                per_person.append({"item": "Spacer + rescue inhaler (multiple)", "qty": "2"})
            elif flag == "cpap":
                per_person.append({"item": "CPAP battery pack + spare mask", "qty": "1 (≥10h runtime)"})
            elif flag == "oxygen_tank":
                per_person.append({"item": "Portable oxygen tank + regulator + tubing", "qty": "extra full tank(s)"})
            elif flag == "dialysis":
                per_person.append({"item": "Dialysis contact card + extra supplies", "qty": "1 set"})
            elif flag == "epipen":
                per_person.append({"item": "EpiPen (current expiration)", "qty": "2 minimum"})
            elif flag == "diabetes":
                per_person.append({"item": "Insulin + cooler pouch + glucose tabs", "qty": "30+ day supply"})
            elif flag == "blood_thinners":
                per_person.append({"item": "Anticoagulant + ID card + dose schedule", "qty": "30+ day supply"})
            elif flag == "prescription_refill":
                per_person.append({"item": "Maintenance medication (full cycle)", "qty": "30-90 day supply"})

    # ---- per-pet
    pet_items: List[Dict[str, Any]] = []
    if profile.get("pets"):
        pet_items.append({"item": "Water", "qty": "1 qt/day × 7d × pet count"})
        pet_items.append({"item": "Dry food (sealed)", "qty": "1 cup/day × 7d × pet count"})
        pet_items.append({"item": "Vaccination records (paper + photo on phone)", "qty": "1 set"})
        pet_items.append({"item": "Leash + collar with ID + microchip confirmation", "qty": "1 per pet"})
        pet_items.append({"item": "Carrier or crate (if evacuation requires)", "qty": "1 per pet"})
        pet_items.append({"item": "Medication (if any)", "qty": "30-day supply"})
        for p in profile["pets"]:
            if p["species"] == "reptile":
                pet_items.append({"item": "Reptile: heat-pack + spare UVB bulb", "qty": "1 set"})
            if p["species"] == "fish":
                pet_items.append({"item": "Fish: portable battery air-pump + bucket", "qty": "1 set"})
            if p["species"] == "bird":
                pet_items.append({"item": "Bird: small travel cage + millet spray", "qty": "1 set"})

    # ---- family-shared
    family = [
        {"item": "Phone + battery bank (20+ Ah) + car charger", "qty": "2 banks"},
        {"item": "Important documents in ziplock (ID, insurance, deeds, prescriptions, vet records, kid immunization cards)", "qty": "1 pouch"},
        {"item": "Printed family photo + household member descriptions (paper)", "qty": "1 set"},
        {"item": "Out-of-area contact card (laminated paper backup)", "qty": "1 per family"},
        {"item": "Spare keys (house + cars + safe-deposit)", "qty": "1 set"},
        {"item": "Spare glasses / contacts", "qty": "1 per wearer"},
        {"item": "Change of clothes (seasonal)", "qty": "1 set / person"},
        {"item": "Sturdy shoes (everyone, packed)", "qty": "1 pair / person"},
        {"item": "Sleeping bag / emergency blanket (mylar ok)", "qty": "1 / person"},
        {"item": "Roll of duct tape + 6 mil plastic sheeting (shelter-in-place)", "qty": "1 roll + 10ft"},
        {"item": "Heavy work gloves", "qty": "2 pairs"},
        {"item": "Wrench for utility shutoff (gas + water)", "qty": "1"},
    ]

    # if any hazard needs specific kit
    hazards_needs = []
    if hazards.get("wildfire", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "N95 respirators (wildfire smoke)", "qty": "10 / person"})
        hazards_needs.append({"item": "Goggles", "qty": "1 / person"})
    if hazards.get("chemical", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "Full-face respirator (P100)", "qty": "1 / family"})
        hazards_needs.append({"item": "Plastic sheeting (4 mil) for door + window seal", "qty": "20 ft"})
    if hazards.get("tornado", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "Bike helmets (kids + adults) for tornado debri", "qty": "1 / person"})
    if hazards.get("winter-storm", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "Hand + foot warmers", "qty": "6 pairs / person"})
        hazards_needs.append({"item": "Insulated boots", "qty": "1 pair / person"})
    if hazards.get("earthquake", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "Work gloves + sturdy shoes", "qty": "kept on every bed"})
    if hazards.get("flood", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "Waterproof dry-bag for documents", "qty": "1"})
    if hazards.get("pandemic", {}).get("level", 0) >= 2:
        hazards_needs.append({"item": "60-day medication, surgical masks, gloves, disinfectant", "qty": "1 set"})

    return {
        "per_person": per_person,
        "family_shared": family,
        "pet_items": pet_items,
        "hazards_needs": hazards_needs,
        "totals": {
            "people": people,
            "pets": pets,
            "water_gallons_per": water_gallons,
            "kcal_per_person_per_day": 2000,
        },
    }


# ----------------------------------------------------------------------------
# Stay-at-home shelter plan
# ----------------------------------------------------------------------------

def build_shelter_in_place(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Stay-at-home shelter plan. Different scale than go-bag."""
    people = (profile.get("adults") or 0) + (profile.get("kids") or 0) + (profile.get("seniors") or 0)
    if people == 0:
        people = 2
    safe_room = []
    if hazards.get("tornado", {}).get("level", 0) >= 2:
        safe_room.append({
            "purpose": "tornado safe room",
            "where": "lowest floor, interior, no windows (bathroom / closet / bathtub)",
            "why": "tornados can take seconds; you want a known spot ready",
            "essentials": "Bike helmets, sturdy shoes, weather radio, charged phones",
        })
    if hazards.get("earthquake", {}).get("level", 0) >= 2:
        safe_room.append({
            "purpose": "earthquake drop-cover-hold spot",
            "where": "under a sturdy table, away from windows + heavy wall objects",
            "why": "windows + masonry + tall furniture are the primary killers",
            "essentials": "Sturdy shoes beside bed, work gloves beside bed, flashlight at bedside",
        })
    if hazards.get("chemical", {}).get("level", 0) >= 2:
        safe_room.append({
            "purpose": "shelter-in-place for chemical release",
            "where": "interior room with fewest doors/windows, ideally a bathroom",
            "why": "chemical plumes travel with wind — outside air is the danger",
            "essentials": "Duct tape, plastic sheeting 4 mil, wet towels for door cracks, scissors, P100 respirator",
        })
    if hazards.get("hurricane", {}).get("level", 0) >= 2:
        safe_room.append({
            "purpose": "hurricane interior shelter",
            "where": "interior room on lowest floor (NOT upper), away from windows",
            "why": "windows fail first; high winds make upper floors deadly",
            "essentials": "Helmets, sturdy shoes, weather radio, water for 7 days, charged phones",
        })

    shelter_supplies_7days = [
        {"item": "Water (1 gal / person / day)", "qty": f"{people * 7} gallons"},
        {"item": "Ready-to-eat food × 7d", "qty": f"{people * 14000} kcal"},
        {"item": "Battery-powered radio + extra batteries", "qty": "1 set"},
        {"item": "Flashlights + lanterns for entire household", "qty": f"{people + 1} lanterns"},
        {"item": "First-aid kit (family-of-N size)", "qty": "1"},
        {"item": "Fire extinguisher (ABC rating)", "qty": "1 main floor"},
        {"item": "Toilet paper + hygiene", "qty": "7-day supply"},
        {"item": "Garbage bags + plastic ties (sanitation)", "qty": "20 bags"},
        {"item": "Plastic sheeting + duct tape (shelter-in-place)", "qty": "see hazard"},
        {"item": "Wrench for utility shutoff (at meter)", "qty": "1 + accessible"},
    ]

    utility_shutoff = []
    if "gas" in profile.get("utilities", []):
        utility_shutoff.append({"utility": "gas", "where": "at meter (yellow handle)", "when": "smell of gas or shutoff order from utility"})
    if "electric" in profile.get("utilities", []):
        utility_shutoff.append({"utility": "electric", "where": "main breaker panel inside", "when": "flooding or storm-caused fire or extended outage requiring repair"})
    if "water" in profile.get("utilities", []):
        utility_shutoff.append({"utility": "water", "where": "main shutoff near street or meter", "when": "broken pipe / flooding / contamination order"})
    if "well" in profile.get("utilities", []):
        utility_shutoff.append({"utility": "well pump power", "where": "at the pump", "when": "extended power outage"})

    return {
        "safe_rooms": safe_room,
        "shelter_supplies_7days": shelter_supplies_7days,
        "utility_shutoff": utility_shutoff,
    }


# ----------------------------------------------------------------------------
# Evacuation plan
# ----------------------------------------------------------------------------

def build_evacuation_plan(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    people = (profile.get("adults") or 0) + (profile.get("kids") or 0) + (profile.get("seniors") or 0)
    if people == 0:
        people = 2
    pets = sum(p["quantity"] for p in profile.get("pets") or []) if profile.get("pets") else 0

    # pick primary hazard that drives evacuation order (most likely)
    evac_drivers: List[Tuple[str, int]] = sorted(
        ((k, v.get("level", 0)) for k, v in hazards.items() if v.get("level", 0) >= 2),
        key=lambda x: -x[1],
    )

    primary_driver = evac_drivers[0][0] if evac_drivers else "wildfire"

    # meeting places (2)
    meeting = [
        {
            "name": "Near Home meeting point",
            "where": "1-2 blocks away, somewhere visible + dry",
            "when": "if fire or earthquake separates us at home",
        },
        {
            "name": "Out-of-area meeting point",
            "where": "city/town >50 miles away (often relative)",
            "when": "if we must evacuate across the region",
        },
    ]

    contacts = [
        {"role": "Primary out-of-area contact", "what": "someone ≥100 miles away who family can call", "tip": "local lines jam; long-distance often clearer"},
        {"role": "Secondary out-of-area contact", "what": "fallback if primary is unreachable", "tip": "ideally in different state"},
        {"role": "Family group-text", "what": "set at start of household brief; share status as 'accounted for / need help / need transport'", "tip": "use SMS, not social apps — SMS uses minimal data"},
    ]

    # pets evac handling
    pet_evac = []
    if profile.get("pets"):
        pet_evac.append("Decide: shelter accepts pets? (most do not; check ahead)")
        pet_evac.append("Service animal vs emotional-support animal — different legal status in shelters")
        pet_evac.append("Birds/reptiles/exotic — call vet hospital for emergency boarding before storm")
        pet_evac.append("Cats: even friendly cats panic under stress — separate carriers required")
        if any(p["species"] == "dog" for p in profile.get("pets") or []):
            pet_evac.append("Dog crate even if 'crate-trained' — stress reduces reliability")

    # senior handling
    senior_evac = []
    if profile.get("seniors"):
        senior_evac.append(f"{profile.get('seniors')} senior(s): pre-strap go-bag to walker/wheelchair")
        senior_evac.append("Mobility: list vehicle-accessible shelters (most are not — call ahead)")
        senior_evac.append("Medication on immediate-body (not in go-bag) — never gets separated")

    # vehicle readiness
    vehicle_readiness = []
    if profile.get("vehicle_count"):
        vehicle_readiness.append(f"Both cars at ≥7/8 fuel when warning is in effect — evac lines + the run drains stations fast")
        vehicle_readiness.append("1 car designated as 'bug-out vehicle' with go-bags loaded at all times in season")
        vehicle_readiness.append("Tire pressure + spare + jumper cables — flat-tire evac = stranding")

    return {
        "primary_driver": primary_driver,
        "all_evac_drivers": [{"hazard": h, "level": l} for h, l in evac_drivers],
        "meeting_places": meeting,
        "contacts": contacts,
        "pet_evac_handling": pet_evac,
        "senior_evac_handling": senior_evac,
        "vehicle_readiness": vehicle_readiness,
        "people": people,
        "pets": pets,
    }


# ----------------------------------------------------------------------------
# Communication tree
# ----------------------------------------------------------------------------

def build_comm_tree(profile: Dict[str, Any], evac_plan: Dict[str, Any]) -> Dict[str, Any]:
    # SMS keyword protocol
    keywords = [
        {"code": "OK", "meaning": "I'm accounted for and safe"},
        {"code": "NEED HELP", "meaning": "I'm safe but stuck; need assistance"},
        {"code": "NEED TRANSPORT", "meaning": "I'm safe but need a ride"},
        {"code": "EVAC TO <LOCATION>", "meaning": "I'm heading to <location> — track me there"},
        {"code": "OFFLINE", "meaning": "I won't reply for X hours; assume unchanged"},
    ]
    family_templates = [
        {
            "name": "Family group SMS — initial",
            "body": "All: <hazard> warning issued for <area>. We are: (a) staying/sheltering in place, OR (b) evacuating to <city>. Reply OK / NEED HELP / NEED TRANSPORT. Out-of-area contact: <name, number>. Update every 3h.",
        },
        {
            "name": "School-pickup update",
            "body": "School: <student> pickup status changed. Parent-on-call: <name, phone>. Backup pick-up: <name, phone, relation>. ETA: <time>.",
        },
        {
            "name": "Work-status notice",
            "body": "Team: today/this week I'll be off-grid due to <hazard>. Replacement: <name>. I'll rejoin <date>. Email is queued daily when possible.",
        },
        {
            "name": "Group update on helper",
            "body": "Update — <person> is now with <person> at <address> until <date>. Out-of-area contact <name> has full status.",
        },
    ]
    return {
        "keywords": keywords,
        "family_templates": family_templates,
        "rules": [
            "Out-of-area contact should be someone ≥100 miles away — local cell lines jam first",
            "Text uses 200 bytes per message; calls fail, texts get through 80%+ of the time",
            "Family-group SMS once at warning start, then every 3-6 hours. Don't call storm hotline if you can text.",
            "If you must shelter away from home, leave a note on the door (or update group chat) — first-responders won't break down a door if they know where you went.",
        ],
    }


# ----------------------------------------------------------------------------
# Risk flags (14 patterns)
# ----------------------------------------------------------------------------

def detect_risk_flags(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    flags: List[Dict[str, Any]] = []

    def add(flag_id: str, severity: str, evidence: str, fix: str):
        flags.append({"flag": flag_id, "severity": severity, "evidence": evidence, "fix": fix})

    # 1. hurricane zone + no evac plan
    if hazards.get("hurricane", {}).get("level", 0) >= 2:
        if not profile.get("evac_pref"):
            add("hurricane_zone_no_evac_plan", "high",
                f"hurricane level {hazards['hurricane']['level']} but no evac preference stated",
                "write a 1-page evac plan: triggers, route, destinations, pet handling")
        if not profile.get("has_shutters") and not profile.get("home_type") in ("apartment",):
            add("hurricane_no_shutters", "medium",
                "no shutter or plywood pre-cut mentioned",
                "order ½-inch plywood pre-cut to window dimensions; label panels by window")

    # 2. wildfire zone + no defensible space
    if hazards.get("wildfire", {}).get("level", 0) >= 2 and not profile.get("has_defensible_space"):
        add("wildfire_zone_no_defensible_space", "high",
            f"wildfire level {hazards['wildfire']['level']} and no defensible-space mentioned",
            "create Zone 0 (0-5 ft) cleared of combustibles, trim Zone 1 (5-30 ft)")

    # 3. tornado alley + no safe room
    if hazards.get("tornado", {}).get("level", 0) >= 2 and not profile.get("has_safe_room"):
        add("tornado_alley_no_safe_room", "high",
            f"tornado level {hazards['tornado']['level']} but no safe-room mentioned",
            "identify lowest-floor interior room (bathroom or closet) and furnish it as shelter")

    # 4. earthquake zone + no strap
    if hazards.get("earthquake", {}).get("level", 0) >= 2 and not profile.get("has_strap"):
        add("earthquake_zone_no_strap", "medium",
            f"earthquake level {hazards['earthquake']['level']} but no strap/anchor mentioned",
            "strap water heater; anchor tall furniture to studs")

    # 5. cold-freeze + no backup heat
    if hazards.get("winter-storm", {}).get("level", 0) >= 2 and not profile.get("has_backup_heat"):
        add("cold_freeze_no_backup_heat", "medium",
            "winter-storm level high and no backup-heat mentioned",
            "add wood stove, fireplace (with inspected chimney), or generator for heater")

    # 6. flood zone + no flood insurance
    if hazards.get("flood", {}).get("level", 0) >= 2 and not profile.get("has_flood_insurance"):
        add("flood_zone_no_insurance", "medium",
            f"flood level {hazards['flood']['level']} but no flood insurance mentioned",
            "check NFIP standard or private flood insurance — 30-day waiting period")

    # 7. power outage + no generator
    if hazards.get("power-outage", {}).get("level", 0) >= 2 and not profile.get("has_generator"):
        add("power_outage_no_generator", "medium",
            f"power-outage level {hazards['power-outage']['level']} but no generator/battery mentioned",
            "buy 10-25 kWh battery station OR generator + outdoor placement + fuel storage")

    # 8. family unaccounted + no out-of-area contact
    if profile.get("adults", 0) + profile.get("kids", 0) + profile.get("seniors", 0) >= 2 and not profile.get("has_out_of_area_contact"):
        add("family_unaccounted_no_out_of_area_contact", "high",
            "multi-person household but no out-of-area contact specified",
            "nominate 1 primary + 1 fallback out-of-area contact (100+ miles)")

    # 9. medical dependency
    if any(f in profile.get("medical_flags", []) for f in ["oxygen_tank", "dialysis", "diabetes", "epipen", "blood_thinners", "cpap"]):
        add("medical_dependency_high", "high",
            f"medical flags: {', '.join(profile['medical_flags'])}",
            "60+ day medication + on-body backup; carrier file with insurer; emergency contacts know medical")

    # 10. pet + no evac kit
    if profile.get("pets") and not any(p["species"] for p in profile["pets"]):
        # always flagged if pets present
        pass
    if profile.get("pets"):
        add("pet_evac_kit_due", "low",
            f"{len(profile['pets'])} pet(s) detected — verify pet evac kit is current",
            "vaccination records + leash + crate + 3-day food/water per pet")

    # 11. kids + no school pickup protocol
    if profile.get("has_school_kids"):
        add("kids_school_pickup_protocol", "low",
            f"{profile.get('kids')} school-aged kids but pickup protocol unverified in brief",
            "write protocol: primary parent / secondary parent / fallback (grandparent + notarized authorization)")

    # 12. senior + mobility plan
    if profile.get("seniors", 0) > 0 and (profile.get("has_mobility_issue") or profile.get("stories", 1) > 1):
        add("senior_mobility_plan_missing", "high",
            f"{profile['seniors']} senior(s) + mobility issue or multi-story home",
            "downstairs bedroom plan + grab-bar + walker-accessible go-bag at bedside")

    # 13. WFH + no power-resilience
    if profile.get("wfh_adults", 0) > 0 and hazards.get("power-outage", {}).get("level", 0) >= 1:
        add("wfh_no_power_resilience", "low",
            f"WFH adults present + power-outage hazard — work will not survive outage",
            "internet backup (mobile hotspot) + battery station + offline-task list")

    # 14. no weather radio / no alert system
    if not profile.get("has_weather_radio") and not profile.get("alerts_app"):
        add("no_weather_radio_no_alerts", "low",
            "no weather radio + no alerts app mentioned",
            "buy NOAA weather radio + activate Wireless Emergency Alerts on every phone")

    # bonus 15. EV / electric vehicle + power-outage
    if "electric" in profile.get("utilities", []) and hazards.get("power-outage", {}).get("level", 0) >= 2:
        add("ev_charging_dependency", "low",
            "EV charging depends on grid; power-outage risk is meaningful",
            "keep EV at ≥80% during PSPS/hurricane season; identify backup stations outside PSPS-zone")

    # 16. pets reactive + others
    if profile.get("pet_reactive"):
        add("pet_reactive_evac_stress", "low",
            "reactive pet detected — stress increases reactivity in evacuation",
            "muzzle + extra crate + emergency-vet contact for sedation consult pre-disaster")

    return flags


# ----------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------

def compute_score(profile: Dict[str, Any], hazards: Dict[str, Dict[str, Any]],
                   calendar: Dict[str, List[Dict[str, Any]]],
                   gobag: Dict[str, Any],
                   flags: List[Dict[str, Any]]) -> Dict[str, Any]:
    # ---- axis 1: profile completeness (18%)
    profile_signals = [
        bool(profile.get("state")),
        bool(profile.get("county_or_city")),
        bool(profile.get("adults")),
        bool(profile.get("kids") is not None),
        bool(profile.get("pets") is not None),
        bool(profile.get("home_type")),
        bool(profile.get("stories")),
        bool(profile.get("hazards_explicit")),
        bool(profile.get("vehicle_count") is not None),
        bool(profile.get("utilities")),
        bool(profile.get("medical_flags") is not None),
    ]
    profile_score = round(100 * sum(1 for x in profile_signals if x) / len(profile_signals))

    # ---- axis 2: calendar density (15%)
    total_tasks = sum(len(v) for v in calendar.values())
    target_tasks = 25
    calendar_score = min(100, round(100 * total_tasks / target_tasks))

    # ---- axis 3: kit coverage (20%)
    kit_per = len(gobag.get("per_person", []))
    kit_family = len(gobag.get("family_shared", []))
    kit_pet = len(gobag.get("pet_items", []))
    kit_haz = len(gobag.get("hazards_needs", []))
    kit_score = min(100, round(100 * (kit_per + kit_family + kit_pet + kit_haz) / 30))

    # ---- axis 4: comms-and-evac (18%)
    evac_signals = [
        bool(profile.get("has_out_of_area_contact")),
        bool(profile.get("evac_pref")),
        profile.get("vehicle_count") is not None,
        bool(profile.get("has_shutters")) if hazards.get("hurricane", {}).get("level", 0) >= 2 else True,
        bool(profile.get("has_defensible_space")) if hazards.get("wildfire", {}).get("level", 0) >= 2 else True,
        bool(profile.get("has_safe_room")) if hazards.get("tornado", {}).get("level", 0) >= 2 else True,
        bool(profile.get("has_strap")) if hazards.get("earthquake", {}).get("level", 0) >= 2 else True,
    ]
    comm_evac_score = round(100 * sum(1 for x in evac_signals if x) / len(evac_signals))

    # ---- axis 5: hazard-zone fit (14%)
    # high-hazard zone (level>=2) = need to have at least 1 risk-mitigation added
    high_hazards = [h for h, v in hazards.items() if v.get("level", 0) >= 2]
    mitigations = 0
    if high_hazards:
        for h in high_hazards:
            if h == "wildfire" and (profile.get("has_defensible_space") or profile.get("has_out_of_area_contact")):
                mitigations += 1
            elif h == "hurricane" and (profile.get("has_shutters") or profile.get("evac_pref")):
                mitigations += 1
            elif h == "tornado" and profile.get("has_safe_room"):
                mitigations += 1
            elif h == "earthquake" and profile.get("has_strap"):
                mitigations += 1
            elif h == "power-outage" and profile.get("has_generator"):
                mitigations += 1
            elif h == "flood" and profile.get("has_flood_insurance"):
                mitigations += 1
            elif h == "winter-storm" and profile.get("has_backup_heat"):
                mitigations += 1
            elif h == "extreme-heat" and (profile.get("seniors") or any(p["species"] == "dog" for p in profile.get("pets") or [])):
                mitigations += 1
            else:
                mitigations += 0.5  # partial credit for naming/awareness
        hazard_fit = round(100 * mitigations / len(high_hazards))
    else:
        hazard_fit = 100  # no high-hazard — full credit

    # ---- axis 6: risk hygiene (15%)
    high_severity_flags = sum(1 for f in flags if f["severity"] == "high")
    medium_severity_flags = sum(1 for f in flags if f["severity"] == "medium")
    # 100 base, deduct per flag
    risk_score = max(0, 100 - high_severity_flags * 18 - medium_severity_flags * 8)

    total = (
        profile_score * 0.18
        + calendar_score * 0.15
        + kit_score * 0.20
        + comm_evac_score * 0.18
        + hazard_fit * 0.14
        + risk_score * 0.15
    )
    total = round(total)

    # verdict
    if total >= 85:
        verdict = "fully_prepared"
    elif total >= 70:
        verdict = "mostly_ready"
    elif total >= 55:
        verdict = "needs_attention"
    elif total >= 40:
        verdict = "behind_schedule"
    else:
        verdict = "high_risk"

    return {
        "score": total,
        "verdict": verdict,
        "axes": {
            "profile_completeness": profile_score,
            "calendar_density": calendar_score,
            "kit_coverage": kit_score,
            "comms_and_evac": comm_evac_score,
            "hazard_zone_fit": hazard_fit,
            "risk_hygiene": risk_score,
        },
    }


# ----------------------------------------------------------------------------
# Top-level analyze()
# ----------------------------------------------------------------------------

def analyze(brief: str) -> Dict[str, Any]:
    profile = parse_household_profile(brief)
    hazards = score_hazards(profile)
    calendar = build_calendar(profile, hazards)
    gobag = build_gobag(profile, hazards)
    shelter = build_shelter_in_place(profile, hazards)
    evac = build_evacuation_plan(profile, hazards)
    comm = build_comm_tree(profile, evac)
    flags = detect_risk_flags(profile, hazards)
    score = compute_score(profile, hazards, calendar, gobag, flags)

    return {
        "profile": profile,
        "hazards": hazards,
        "calendar": calendar,
        "gobag": gobag,
        "shelter": shelter,
        "evac_plan": evac,
        "comm_tree": comm,
        "risk_flags": flags,
        "score": score,
    }


# ----------------------------------------------------------------------------
# Markdown export
# ----------------------------------------------------------------------------

def render_markdown(result: Dict[str, Any]) -> str:
    profile = result["profile"]
    hazards = result["hazards"]
    score = result["score"]
    flags = result["risk_flags"]
    calendar = result["calendar"]
    gobag = result["gobag"]
    shelter = result["shelter"]
    evac = result["evac_plan"]
    comm = result["comm_tree"]

    lines = []
    lines.append(f"# Emergency Readiness Report")
    lines.append(f"")
    lines.append(f"**Verdict:** {score['verdict']}  |  **Score:** {score['score']}/100")
    lines.append(f"")
    lines.append(f"**Axes:**")
    lines.append(f"- Profile completeness: {score['axes']['profile_completeness']}")
    lines.append(f"- Calendar density: {score['axes']['calendar_density']}")
    lines.append(f"- Kit coverage: {score['axes']['kit_coverage']}")
    lines.append(f"- Comms + evac: {score['axes']['comms_and_evac']}")
    lines.append(f"- Hazard-zone fit: {score['axes']['hazard_zone_fit']}")
    lines.append(f"- Risk hygiene: {score['axes']['risk_hygiene']}")
    lines.append(f"")

    lines.append(f"## Household profile")
    lines.append(f"")
    lines.append(f"- State: {profile.get('state') or 'unknown'}")
    lines.append(f"- County/city: {profile.get('county_or_city') or 'unknown'}")
    lines.append(f"- Adults: {profile.get('adults') or 0}, Kids: {profile.get('kids') or 0}, Seniors: {profile.get('seniors') or 0}")
    lines.append(f"- Pets: " + (", ".join(f"{p['species']} x{p['quantity']}" for p in profile.get("pets") or []) or "none"))
    lines.append(f"- Home: {profile.get('home_type') or 'unknown'}, {profile.get('stories', 1)} stories, basement={'yes' if profile.get('has_basement') else 'no'}, garage={'yes' if profile.get('has_garage') else 'no'}")
    lines.append(f"- Utilities: " + (", ".join(profile.get("utilities") or []) or "unknown"))
    lines.append(f"- Vehicles: {profile.get('vehicle_count') or 0}")
    lines.append(f"- Medical: " + (", ".join(profile.get("medical_flags") or []) or "none"))
    if profile.get("concerns"):
        lines.append(f"- Concerns: " + "; ".join(profile["concerns"]))
    lines.append(f"")

    lines.append(f"## Hazard profile")
    lines.append(f"")
    for h, v in sorted(hazards.items(), key=lambda kv: -kv[1].get("level", 0)):
        level_label = {0: "low", 1: "low", 2: "medium", 3: "high"}[v.get("level", 0)]
        lines.append(f"- **{h}** ({level_label}): {v.get('reason', '')}")
    lines.append(f"")

    lines.append(f"## 12-Month Calendar (sample tasks per month)")
    lines.append(f"")
    for m in MONTHS:
        if calendar[m]:
            lines.append(f"### {m}")
            for t in calendar[m][:4]:  # top 4 per month for compactness
                lines.append(f"- {t['task']} ({t['est_min']} min, {t['category']})")
            if len(calendar[m]) > 4:
                lines.append(f"- _...and {len(calendar[m]) - 4} more tasks (full list in app)_")
            lines.append(f"")

    lines.append(f"## Go-bag kit ({gobag['totals']['people']} people / {gobag['totals']['pets']} pets)")
    lines.append(f"")
    lines.append(f"### Per person")
    for itm in gobag["per_person"]:
        lines.append(f"- {itm['item']} ({itm['qty']})")
    lines.append(f"")
    lines.append(f"### Family-shared")
    for itm in gobag["family_shared"]:
        lines.append(f"- {itm['item']} ({itm['qty']})")
    if gobag["pet_items"]:
        lines.append(f"")
        lines.append(f"### Pet-specific")
        for itm in gobag["pet_items"]:
            lines.append(f"- {itm['item']} ({itm['qty']})")
    if gobag["hazards_needs"]:
        lines.append(f"")
        lines.append(f"### Hazard-specific additions")
        for itm in gobag["hazards_needs"]:
            lines.append(f"- {itm['item']} ({itm['qty']})")
    lines.append(f"")

    lines.append(f"## Shelter-in-place")
    if shelter["safe_rooms"]:
        for s in shelter["safe_rooms"]:
            lines.append(f"- **{s['purpose']}**: {s['where']} — {s['why']}")
            lines.append(f"  - Essentials: {s['essentials']}")
    if shelter["utility_shutoff"]:
        lines.append(f"")
        lines.append(f"### Utility shutoff")
        for u in shelter["utility_shutoff"]:
            lines.append(f"- {u['utility']}: {u['where']} (when: {u['when']})")
    lines.append(f"")

    lines.append(f"## Evacuation plan")
    lines.append(f"")
    lines.append(f"Primary driver: **{evac['primary_driver']}**")
    lines.append(f"")
    lines.append(f"### Meeting places")
    for mp in evac["meeting_places"]:
        lines.append(f"- **{mp['name']}**: {mp['where']} — when: {mp['when']}")
    lines.append(f"")
    lines.append(f"### Out-of-area contacts")
    for c in evac["contacts"]:
        lines.append(f"- **{c['role']}**: {c['what']} — tip: {c['tip']}")
    if evac["pet_evac_handling"]:
        lines.append(f"")
        lines.append(f"### Pet evac")
        for x in evac["pet_evac_handling"]:
            lines.append(f"- {x}")
    if evac["senior_evac_handling"]:
        lines.append(f"")
        lines.append(f"### Senior evac")
        for x in evac["senior_evac_handling"]:
            lines.append(f"- {x}")
    if evac["vehicle_readiness"]:
        lines.append(f"")
        lines.append(f"### Vehicle")
        for x in evac["vehicle_readiness"]:
            lines.append(f"- {x}")
    lines.append(f"")

    lines.append(f"## Communication tree")
    lines.append(f"")
    lines.append(f"### SMS keyword protocol")
    for k in comm["keywords"]:
        lines.append(f"- **{k['code']}**: {k['meaning']}")
    lines.append(f"")
    lines.append(f"### Templates")
    for t in comm["family_templates"]:
        lines.append(f"- **{t['name']}**: {t['body']}")
    lines.append(f"")
    lines.append(f"### Rules")
    for r in comm["rules"]:
        lines.append(f"- {r}")
    lines.append(f"")

    lines.append(f"## Risk flags ({len(flags)})")
    if flags:
        for f in flags:
            lines.append(f"- [{f['severity']}] **{f['flag']}** — {f['evidence']}")
            lines.append(f"  - fix: {f['fix']}")
    else:
        lines.append(f"_none detected_")
    lines.append(f"")

    lines.append(f"---")
    lines.append(f"_Generated by emergency-readiness-forge (Flask + stdlib engine)._")
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# CLI sanity-test
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "HOUSEHOLD: 2 adults, 2 kids (ages 9 and 13), 1 dog (golden retriever, 4 yrs).\n"
        "REGION: California, San Diego County, inland (El Cajon area).\n"
        "HOME: Single-family, built 1998, no basement, attached garage.\n"
        "HAZARDS WE CARE ABOUT: wildfire, power-outage (PSPS red-flag shutdowns), earthquake, severe-storm.\n"
        "WORK FROM HOME: 1 adult WFH full-time, 1 commutes 14 miles.\n"
        "MOBILITY: 1 senior parent lives with us (78 yo, walks with cane).\n"
        "MEDICAL: kid 9 has asthma (inhaler); senior on blood thinners (rx refill every 90 days).\n"
        "VEHICLES: 1 sedan, 1 SUV.\n"
        "UTILITIES: gas, electric, water, internet.\n"
        "PETS: golden retriever, friendly with people but reactive to other dogs.\n"
        "SCHOOL: kids at public elementary + middle school, both ~3 miles away.\n"
        "EVAC PREFERENCE: leave early, we have a car and a place to stay in Temecula with my brother.\n"
        "CONCERNS: PSPS blackouts happen 3-4x a year. Senior on second floor.",

        "HOUSEHOLD: 3 adults (couple + 22yo college kid home for break).\n"
        "REGION: Texas, Harris County (Houston metro).\n"
        "HOME: 2-story townhome, built 2008, no basement, attached garage.\n"
        "HAZARDS: hurricane, flood, severe-storm, power-outage.\n"
        "MOBILITY: no mobility issues.\n"
        "MEDICAL: husband has sleep apnea (CPAP).\n"
        "VEHICLES: 2 sedans.\n"
        "UTILITIES: gas, electric, water.\n"
        "PETS: 2 cats (indoor, shy).\n"
        "No seniors, no kids at home.\n"
        "CONCERNS: streets flood; long power outages after ice storms.",
    ]

    for i, sample in enumerate(samples, 1):
        print(f"=== Sample {i} ===")
        result = analyze(sample)
        print(json.dumps({
            "verdict": result["score"]["verdict"],
            "score": result["score"]["score"],
            "axes": result["score"]["axes"],
            "hazard_top": sorted(
                ((k, v["level"]) for k, v in result["hazards"].items()),
                key=lambda x: -x[1]
            )[:5],
            "risk_flags": [f["flag"] for f in result["risk_flags"]],
            "calendar_tasks": sum(len(v) for v in result["calendar"].values()),
            "kit_per_person": len(result["gobag"]["per_person"]),
            "evac_primary_driver": result["evac_plan"]["primary_driver"],
            "pets": result["profile"].get("pets"),
            "region_blob": result["profile"].get("region_blob"),
            "hazards_explicit": result["profile"]["hazards_explicit"],
        }, indent=2))
        print()
