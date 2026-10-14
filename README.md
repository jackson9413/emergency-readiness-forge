# emergency-readiness-forge

Local-first household emergency preparedness workbench. Paste a household
brief (region / hazards / home type / family / pets / work-from-home / mobility /
medical / vehicles / utilities), get back:

- **Hazard profile** across 14 hazard categories (wildfire / hurricane /
  tornado / earthquake / flood / winter-storm / extreme-heat / power-outage /
  water-outage / severe-storm / chemical / volcanic / civil-unrest / pandemic)
  with regional severity scoring from US state/county keywords
- **12-month readiness calendar** with month-by-month task lists (~25-45 tasks)
  covering go-bag maintenance, supply rotation, drills, document backups,
  vehicle readiness, weather-radio tests, generator maintenance, utility shutoff
  practice, and seasonal anchors (storm-season prep, wildfire-defensible-space,
  hurricane-shutter install, winter-storm-resupply, etc.)
- **Household go-bag kit** with 7-day supplies for N people + N pets, broken
  into 8 categories (water / food / first-aid / light-power / comms /
  documents / clothing-shelter / cash-keys-tools), each item with quantity logic
  (1 gal water/person/day, 2000 kcal/person/day, prescription refill notes)
- **Stay-at-home shelter plan** with 7-day supplies (different scale than
  go-bag), safe-room guidance, utility-shutoff checklist (gas / water / electric
  location + how-to), and chemical/wildfire indoor-air protocols
- **Evacuation plan** with roles per family member, 2 meeting places
  (neighborhood + out-of-area), 2 out-of-area contact nodes (primary +
  fallback), evacuation-route selection (pre-evac zone), pet-evacuation handling
  (sheltered pet? service animal? exotic?), and vehicle-readiness requirements
- **Communication tree** with out-of-area contact template + family group-text
  template + school-day pickup-status template + work-status template + group
  SMS keyword protocol (so people know if message is "accounted for / need help
  / need transport")
- **14-pattern risk-flag engine** with high/medium/low severity:
  hurricane_zone_no_evac_plan / wildfire_zone_no_defensible_space /
  tornado_alley_no_safe_room / earthquake_zone_no_strap /
  cold_freeze_no_backup_heat / flood_zone_no_insurance /
  power_outage_no_generator / family_unaccounted_no_out_of_area_contact /
  medical_dependency_high / pet_no_evac_kit / kids_no_school_pickup_protocol /
  senior_no_mobility_plan / wfh_no_know_grace_period /
  no_weather_radio_no_alerts
- **0-100 readiness score** across 6 weighted axes
  (profile completeness 18% / calendar density 15% / kit coverage 20% /
  comms-and-evac 18% / hazard-zone fit 14% / risk hygiene 15%) with verdict
  bands from `fully_prepared` (≥85) → `mostly_ready` (≥70) → `needs_attention`
  (≥55) → `behind_schedule` (≥40) → `high_risk` (<40)
- SQLite session log with 1-5 star ratings + notes
- Markdown + JSON export
- REST API (`/api/analyze` POST, `/api/sessions` GET,
  `/api/sessions/<id>` GET + PATCH for rating/notes, `/api/export/<id>` GET
  for markdown/json, `/api/health` GET)

## Why this exists

Car-keeper-forge knows your car needs brake fluid. home-keeper-forge knows your
roof needs gutter cleaning. But no tool covers the moment when the power goes
out for 5 days, the wildfire is 4 miles away, the family is scattered across
three workplaces, the dog needs evacuation, and the question is: **"are we
ready?"** This fills that operational moment.

## Run

```bash
cd ~/Desktop/OpenClaw_Daily/2026-10-13/emergency-readiness-forge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# → http://localhost:5031
```

## Stack

- **Backend:** Python 3 stdlib + Flask + sqlite3
- **Engine:** `engine.py` (parses briefs, scores household readiness)
- **Frontend:** `static/index.html`, `static/app.js`, `static/style.css`
- **No API keys. No LLM. No external network calls.**

## Repo

https://github.com/jackson9413/emergency-readiness-forge

## Domain rotation slot

`consumer / safety / emergency-preparedness`
