"""
Smoke tests for emergency-readiness-forge engine.
Run: python3 test_engine.py
"""

import json
import sys
import traceback

import engine


def expect(cond: bool, msg: str) -> None:
    if not cond:
        print(f"  ✗ {msg}")
        sys.exit(1)
    else:
        print(f"  ✓ {msg}")


def test_parse_el_cajon() -> None:
    print("\n[test_parse_el_cajon]")
    sample = open("sample-brief.txt").read()
    p = engine.parse_household_profile(sample)
    expect(p["state"] == "CA", "state=CA")
    expect("san diego" in (p["county_or_city"] or ""), "county_or_city contains 'san diego'")
    expect(p["adults"] == 2, "adults=2")
    expect(p["kids"] == 2, "kids=2")
    expect(p["seniors"] == 1, "seniors=1")
    expect(any(pe["species"] == "dog" for pe in p["pets"]), "has dog")
    expect("asthma" in p["medical_flags"], "medical: asthma")
    expect("dialysis" not in p["medical_flags"], "medical negation: dialysis excluded")
    expect("oxygen_tank" not in p["medical_flags"], "medical negation: oxygen_tank excluded")
    expect(p["evac_pref"] == "leave_early", "evac_pref=leave_early")
    expect(p["has_out_of_area_contact"] is True, "out_of_area contact detected")
    expect(p["psps_zone"] is True, "PSPS zone detected")


def test_parse_houston() -> None:
    print("\n[test_parse_houston]")
    sample = open("sample-brief-2.txt").read()
    p = engine.parse_household_profile(sample)
    expect(p["state"] == "TX", "state=TX")
    expect("harris" in (p["county_or_city"] or ""), "county_or_city contains 'harris'")
    expect(p["adults"] == 3, "adults=3 (couple + 1 college)")
    expect(p["kids"] == 0, "kids=0 (college kid is adult)")
    expect(p["seniors"] == 0, "seniors=0")
    expect(any(pe["species"] == "cat" for pe in p["pets"]), "has cats")
    expect("cpap" in p["medical_flags"], "medical: cpap")
    expect(p["vehicle_count"] == 2, "vehicles=2")
    expect(p["psps_zone"] is False, "not a PSPS zone")
    expect("hurricane" in p["hazards_explicit"], "hurricane flagged explicit")


def test_score_el_cajon() -> None:
    print("\n[test_score_el_cajon]")
    sample = open("sample-brief.txt").read()
    result = engine.analyze(sample)
    score = result["score"]
    expect(score["score"] >= 50, f"score >= 50 (got {score['score']})")
    expect(score["score"] <= 100, f"score <= 100 (got {score['score']})")
    expect(score["verdict"] in {"fully_prepared", "mostly_ready", "needs_attention", "behind_schedule", "high_risk"}, "verdict in known bands")

    # hazards
    expect(result["hazards"]["wildfire"]["level"] >= 2, "wildfire level >= 2 (El Cajon)")
    expect(result["hazards"]["earthquake"]["level"] >= 2, "earthquake level >= 2 (CA)")
    expect(result["hazards"]["power-outage"]["level"] >= 2, "power-outage level >= 2 (PSPS explicit)")

    # risk flags
    flag_ids = [f["flag"] for f in result["risk_flags"]]
    expect("wildfire_zone_no_defensible_space" in flag_ids, "wildfire defensible-space flag")
    expect("medical_dependency_high" in flag_ids, "medical flag")
    expect("senior_mobility_plan_missing" in flag_ids, "senior mobility flag")

    # calendar
    total_tasks = sum(len(v) for v in result["calendar"].values())
    expect(total_tasks >= 25, f"calendar density >= 25 (got {total_tasks})")

    # kit
    expect(len(result["gobag"]["per_person"]) >= 8, "kit per-person items >= 8")
    expect("astura" in str(result["gobag"]["per_person"]).lower() or "spacer" in str(result["gobag"]["per_person"]).lower(), "kit includes spacer/inhaler")
    expect(any("blood_thinners" in str(item) for item in result["gobag"]["per_person"]) or any("Anticoagulant" in str(item) for item in result["gobag"]["per_person"]), "kit includes anticoagulant item for senior")

    # evac plan
    expect(result["evac_plan"]["primary_driver"] in result["hazards"], "primary_driver is a hazard key")


def test_score_houston() -> None:
    print("\n[test_score_houston]")
    sample = open("sample-brief-2.txt").read()
    result = engine.analyze(sample)
    expect(result["hazards"]["hurricane"]["level"] >= 2, "hurricane level high (Harris County)")
    expect(result["hazards"]["flood"]["level"] >= 2, "flood level high (Harvey history)")
    expect(result["hazards"]["power-outage"]["level"] >= 2, "power-outage (TX grid)")
    flag_ids = [f["flag"] for f in result["risk_flags"]]
    expect("hurricane_zone_no_evac_plan" in flag_ids, "hurricane no evac-plan flag")


def test_render_markdown() -> None:
    print("\n[test_render_markdown]")
    sample = open("sample-brief.txt").read()
    result = engine.analyze(sample)
    md = engine.render_markdown(result)
    expect("Emergency Readiness Report" in md, "Markdown has title")
    expect("Verdict:" in md, "Markdown has verdict")
    expect("Go-bag kit" in md, "Markdown has go-bag section")
    expect("Evacuation plan" in md, "Markdown has evac-plan section")
    expect("Communication tree" in md, "Markdown has comm section")
    expect("Risk flags" in md, "Markdown has risk-flags section")
    print(f"  (rendered {len(md)} chars)")


def test_negation_robustness() -> None:
    print("\n[test_negation_robustness]")
    sample = """HOUSEHOLD: 1 adult, no kids.
REGION: Colorado, Denver County.
HOME: small apartment.
HAZARDS: severe-storm.
MOBILITY: no mobility issues.
MEDICAL: no dialysis / oxygen / insulin / epipen.
VEHICLES: 1 car.
UTILITIES: electric.
PETS: none.
CONCERNS: nothing major."""
    p = engine.parse_household_profile(sample)
    expect("dialysis" not in p["medical_flags"], "dialysis excluded (negation)")
    expect("oxygen_tank" not in p["medical_flags"], "oxygen_tank excluded (negation)")
    expect("epipen" not in p["medical_flags"], "epipen excluded (negation)")


def test_round_trip() -> None:
    print("\n[test_round_trip]")
    sample = open("sample-brief.txt").read()
    r1 = engine.analyze(sample)
    md = engine.render_markdown(r1)
    r2 = engine.analyze(md)
    expect(r2["score"]["verdict"] is not None, "re-analyzing from markdown produces a verdict (not None)")


def main() -> None:
    tests = [
        test_parse_el_cajon,
        test_parse_houston,
        test_score_el_cajon,
        test_score_houston,
        test_render_markdown,
        test_negation_robustness,
        test_round_trip,
    ]
    print(f"Running {len(tests)} tests...")
    for t in tests:
        try:
            t()
        except Exception:
            print(f"  ✗ {t.__name__} raised:")
            traceback.print_exc()
            sys.exit(1)
    print("\n✓ All tests passed.")


if __name__ == "__main__":
    main()
