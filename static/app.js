// emergency-readiness-forge frontend

const SAMPLE_BRIEFS = {
  "wildfire-psps": `HOUSEHOLD: 2 adults, 2 kids (ages 9 and 13), 1 dog (golden retriever, 4 yrs).
REGION: California, San Diego County, inland (El Cajon area).
HOME: Single-family, built 1998, no basement, attached garage.
HAZARDS WE CARE ABOUT: wildfire, power-outage (PSPS red-flag shutdowns), earthquake, severe-storm.
WORK FROM HOME: 1 adult WFH full-time, 1 commutes 14 miles.
MOBILITY: 1 senior parent lives with us (78 yo, walks with cane).
MEDICAL: kid 9 has asthma (inhaler); senior on blood thinners (rx refill every 90 days). No dialysis / oxygen / vents.
VEHICLES: 1 sedan, 1 SUV.
UTILITIES: gas (SDG&E), electric (SDG&E — PSPS risk), water, internet.
PETS: golden retriever, friendly with people but reactive to other dogs.
SCHOOL: kids at public elementary + middle school, both ~3 miles away.
EVAC PREFERENCE: leave early, we have a car and a place to stay in Temecula with my brother.
CONCERNS:
- PSPS blackouts happen 3-4x a year here
- Last big worry: 2024 wildfires, we were under evac warning twice
- Senior parent is on second floor — should we plan a downstairs bedroom?`,

  "hurricane-tx": `HOUSEHOLD: 3 adults (couple + 22yo college kid home for break).
REGION: Texas, Harris County (Houston metro).
HOME: 2-story townhome, built 2008, no basement, attached garage.
HAZARDS: hurricane, flood, severe-storm, power-outage (think Texas grid).
WORK: both adults commute, kid not currently employed.
MOBILITY: no mobility issues.
MEDICAL: husband has sleep apnea (CPAP).
VEHICLES: 2 sedans.
UTILITIES: gas, electric (TXU), water.
PETS: 2 cats (indoor, shy).
No seniors, no kids at home.
CONCERNS:
- Harvey flooding was bad. We're not in a high-risk zone but the streets flood.
- Long power outages after ice storms.
- What's the right amount of generator/generator-alternative to keep on hand?`,

  "tornado-alley": `HOUSEHOLD: 4 adults (parents + 2 teen kids), 1 medium dog.
REGION: Oklahoma, Oklahoma County (Oklahoma City metro).
HOME: Single-story ranch, built 1978, with crawlspace but no full basement, attached garage.
HAZARDS WE CARE ABOUT: tornado, severe-storm, ice storm, power-outage.
WORK FROM HOME: 1 adult WFH 3 days/week.
MOBILITY: no issues.
MEDICAL: dad has high blood pressure, on medication (rx every 30 days).
VEHICLES: 2 sedans.
UTILITIES: gas, electric (OG&E), water.
PETS: 1 medium dog (lab mix, 5 yrs), crate-trained.
SCHOOL: both teens at public high school.
EVAC PREFERENCE: shelter in place for tornadoes; evacuate for ice storms (drive to Texas).
CONCERNS:
- Tornado season (April-June) keeps us up at night
- Last ice storm had us without power 4 days`,

  "earthquake-ca": `HOUSEHOLD: 1 adult, 1 cat.
REGION: California, San Francisco County.
HOME: 3-story condo, built 1985, no basement, shared garage.
HAZARDS: earthquake.
WORK: commute 8 miles.
MOBILITY: no issues.
MEDICAL: none.
VEHICLES: 1 sedan.
UTILITIES: electric (PG&E — PSPS), gas, water, internet.
PETS: 1 cat, indoor.
No kids, no seniors.
CONCERNS:
- Loma Prieta anniversary always reminds me I'm not actually prepared`,

  "winter-mn": `HOUSEHOLD: 2 adults, 2 kids (7, 11).
REGION: Minnesota, Hennepin County (Minneapolis).
HOME: 2-story single-family, built 1952, unfinished basement, detached garage.
HAZARDS WE CARE ABOUT: winter-storm, ice storm, power-outage, severe-storm, tornado.
WORK FROM HOME: mom works remote full-time.
MOBILITY: no issues.
MEDICAL: kid 7 has peanut allergy (epipen).
VEHICLES: 1 minivan, 1 SUV.
UTILITIES: gas, electric (Xcel), water.
PETS: 1 goldendoodle (2 yrs).
SCHOOL: kids at public elementary.
EVAC PREFERENCE: shelter in place.
CONCERNS:
- 2021 ice storm took out power for 6 days in our neighborhood
- We're the only house on the block without a backup generator`,

  "suburb-default": `HOUSEHOLD: 2 adults, no kids, no pets.
REGION: Colorado, Denver County.
HOME: Suburban single-family, built 2002.
HAZARDS: want general readiness — power outage, severe storm, maybe wildfire smoke days.
WORK: 1 WFH, 1 commutes.
MOBILITY: no issues.
MEDICAL: dad on blood pressure medication.
VEHICLES: 2 cars.
UTILITIES: standard.
Not sure where to start.`,
};

let CURRENT_SESSION_ID = null;
let CURRENT_RATING = null;
let CURRENT_BRIEF = "";

document.addEventListener("DOMContentLoaded", () => {
  // render samples
  const samplesEl = document.getElementById("samples");
  Object.entries(SAMPLE_BRIEFS).forEach(([key, text]) => {
    const btn = document.createElement("button");
    btn.textContent = key.replace(/-/g, " ");
    btn.onclick = () => {
      document.getElementById("brief").value = text;
      CURRENT_BRIEF = text;
    };
    samplesEl.appendChild(btn);
  });

  document.getElementById("clear").onclick = () => {
    document.getElementById("brief").value = "";
    document.getElementById("results").classList.add("hidden");
    CURRENT_BRIEF = "";
    CURRENT_SESSION_ID = null;
    CURRENT_RATING = null;
  };
  document.getElementById("run").onclick = runAnalyze;

  // persistent
  document.getElementById("brief").addEventListener("input", (e) => {
    CURRENT_BRIEF = e.target.value;
  });

  // rating
  document.querySelectorAll(".rating button").forEach((btn) => {
    btn.onclick = () => setRating(parseInt(btn.dataset.r));
  });

  // save + export
  document.getElementById("save").onclick = patchSession;
  document.getElementById("export-md").onclick = () => doExport("md");
  document.getElementById("export-json").onclick = () => doExport("json");

  // initial load
  refreshSessions();
});

async function runAnalyze() {
  const brief = document.getElementById("brief").value.trim();
  if (!brief) {
    alert("paste a brief first");
    return;
  }
  document.getElementById("ts").textContent = "running...";
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({brief}),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "request failed");
    }
    const {session_id, result} = await res.json();
    CURRENT_SESSION_ID = session_id;
    document.getElementById("results").classList.remove("hidden");
    renderResult(result);
    document.getElementById("ts").textContent = new Date().toLocaleTimeString();
    CURRENT_RATING = null;
    setRating(0);
    document.getElementById("rating-current").textContent = "";
    document.getElementById("export-status").textContent = "";
    refreshSessions();
  } catch (e) {
    document.getElementById("ts").textContent = "error: " + e.message;
  }
}

function renderResult(result) {
  const sc = result.score;
  document.getElementById("score-card").innerHTML = `
    <div>
      <span class="verdict ${sc.verdict}">${labelVerdict(sc.verdict)}</span>
      <span class="num">${sc.score}/100</span>
    </div>
    <div class="axes">
      ${Object.entries(sc.axes).map(([k, v]) => `
        <div class="axis">
          <div class="label">${k.replace(/_/g, " ")}</div>
          <div class="bar"><div class="fill" style="width:${v}%;background:${axisColor(v)};"></div></div>
          <div class="value">${v}</div>
        </div>
      `).join("")}
    </div>
  `;

  // profile
  const p = result.profile;
  document.getElementById("profile").innerHTML = `
    <h3>Profile</h3>
    <div class="kv">
      <div class="k">State</div><div class="v">${p.state || "—"}</div>
      <div class="k">County / city</div><div class="v">${p.county_or_city || p.region_blob || "—"}</div>
      <div class="k">Adults / kids / seniors</div><div class="v">${p.adults || 0} / ${p.kids || 0} / ${p.seniors || 0}</div>
      <div class="k">Kid ages</div><div class="v">${p.kid_ages?.length ? p.kid_ages.join(", ") : "—"}</div>
      <div class="k">Pets</div><div class="v">${p.pets?.length ? p.pets.map(x => `${x.species} ×${x.quantity}`).join(", ") : "none"}</div>
      <div class="k">Home</div><div class="v">${p.home_type || "—"} (${p.stories || 1} story${p.stories > 1 ? "s" : ""})</div>
      <div class="k">Vehicles</div><div class="v">${p.vehicle_count || 0}</div>
      <div class="k">Utilities</div><div class="v">${(p.utilities || []).join(", ") || "—"}</div>
      <div class="k">WFH adults</div><div class="v">${p.wfh_adults || 0}</div>
      <div class="k">Commute (mi)</div><div class="v">${p.commute_miles || "—"}</div>
      <div class="k">Medical</div><div class="v">${(p.medical_flags || []).join(", ") || "—"}</div>
      <div class="k">Hazards user-flagged</div><div class="v">${(p.hazards_explicit || []).join(", ") || "—"}</div>
      <div class="k">Evac preference</div><div class="v">${p.evac_pref || "—"}</div>
      <div class="k">Out-of-area contact</div><div class="v">${p.has_out_of_area_contact ? "yes" : "no"}</div>
      <div class="k">PSPS zone</div><div class="v">${p.psps_zone ? "yes" : "no"}</div>
    </div>
    ${p.concerns?.length ? `<details><summary>User concerns (${p.concerns.length})</summary><ul>${p.concerns.map(c => `<li>${escapeHTML(c)}</li>`).join("")}</ul></details>` : ""}
  `;

  // hazards
  document.getElementById("hazards").innerHTML = `
    <h3>Hazard levels</h3>
    <div>
      ${Object.entries(result.hazards).sort((a, b) => b[1].level - a[1].level).map(([k, v]) => `
        <div class="hazard level-${v.level}">${k} ${levelLabel(v.level)}</div>
      `).join("")}
    </div>
    <table>
      <thead><tr><th>hazard</th><th>level</th><th>reason</th><th>guidance</th></tr></thead>
      <tbody>
      ${Object.entries(result.hazards).sort((a, b) => b[1].level - a[1].level).map(([k, v]) => `
        <tr>
          <td><b>${k}</b></td>
          <td>${levelLabel(v.level)}</td>
          <td>${escapeHTML(v.reason || "")}</td>
          <td>${escapeHTML(v.guidance || "")}</td>
        </tr>
      `).join("")}
      </tbody>
    </table>
  `;

  // calendar
  const cal = result.calendar;
  let totalTasks = 0;
  const calHTML = Object.entries(cal).map(([month, tasks]) => {
    totalTasks += tasks.length;
    return `
      <div class="calendar-month">
        <div class="label">${month} <span style="font-weight:400;color:#8b93a7;">(${tasks.length} task${tasks.length === 1 ? "" : "s"})</span></div>
        ${tasks.map(t => `<div class="task"><span class="cat">${t.category}</span>${escapeHTML(t.task)} <span style="color:#8b93a7;">— ${t.est_min} min</span></div>`).join("")}
      </div>
    `;
  }).join("");
  document.getElementById("calendar").innerHTML = `<h3>12-month calendar (${totalTasks} tasks)</h3>${calHTML}`;

  // go-bag
  const g = result.gobag;
  document.getElementById("gobag").innerHTML = `
    <h3>Go-bag kit (${g.totals.people} ppl / ${g.totals.pets} pets)</h3>
    <div class="kit-section">
      <div class="head">Per person</div>
      ${g.per_person.map(itm => `<div class="kit-item"><div class="name">${escapeHTML(itm.item)}</div><div class="qty">${escapeHTML(itm.qty)}</div></div>`).join("")}
    </div>
    <div class="kit-section">
      <div class="head">Family-shared</div>
      ${g.family_shared.map(itm => `<div class="kit-item"><div class="name">${escapeHTML(itm.item)}</div><div class="qty">${escapeHTML(itm.qty)}</div></div>`).join("")}
    </div>
    ${g.pet_items.length ? `
    <div class="kit-section">
      <div class="head">Pet-specific</div>
      ${g.pet_items.map(itm => `<div class="kit-item"><div class="name">${escapeHTML(itm.item)}</div><div class="qty">${escapeHTML(itm.qty)}</div></div>`).join("")}
    </div>` : ""}
    ${g.hazards_needs.length ? `
    <div class="kit-section">
      <div class="head">Hazard-specific additions</div>
      ${g.hazards_needs.map(itm => `<div class="kit-item"><div class="name">${escapeHTML(itm.item)}</div><div class="qty">${escapeHTML(itm.qty)}</div></div>`).join("")}
    </div>` : ""}
  `;

  // shelter
  const s = result.shelter;
  document.getElementById("shelter").innerHTML = `
    <h3>Shelter-in-place</h3>
    ${s.safe_rooms.length ? `
      <table>
        <thead><tr><th>safe room</th><th>where</th><th>why</th><th>essentials</th></tr></thead>
        <tbody>
          ${s.safe_rooms.map(r => `<tr>
            <td><b>${r.purpose}</b></td><td>${escapeHTML(r.where)}</td><td>${escapeHTML(r.why)}</td><td>${escapeHTML(r.essentials)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    ` : ""}
    ${s.utility_shutoff.length ? `
      <h3 style="margin-top:14px;">Utility shutoff</h3>
      <table>
        <thead><tr><th>utility</th><th>where</th><th>when</th></tr></thead>
        <tbody>${s.utility_shutoff.map(u => `<tr><td><b>${u.utility}</b></td><td>${escapeHTML(u.where)}</td><td>${escapeHTML(u.when)}</td></tr>`).join("")}</tbody>
      </table>
    ` : ""}
    <h3 style="margin-top:14px;">Shelter supplies (7 days)</h3>
    ${s.shelter_supplies_7days.map(itm => `<div class="kit-item"><div class="name">${escapeHTML(itm.item)}</div><div class="qty">${escapeHTML(itm.qty)}</div></div>`).join("")}
  `;

  // evac plan
  const e = result.evac_plan;
  document.getElementById("evac").innerHTML = `
    <h3>Evacuation plan</h3>
    <div><b>Primary driver:</b> ${e.primary_driver}</div>
    <div style="margin: 6px 0 12px;">
      <b>All drivers ≥med:</b>
      ${e.all_evac_drivers.length ? e.all_evac_drivers.map(d => `<span class="hazard level-${d.level}">${d.hazard} ${levelLabel(d.level)}</span>`).join("") : "(none)"}
    </div>
    <h3 style="margin-top:14px;">Meeting places</h3>
    ${e.meeting_places.map(mp => `<div class="kit-item"><div class="name"><b>${escapeHTML(mp.name)}</b>: ${escapeHTML(mp.where)}</div><div class="qty">${escapeHTML(mp.when)}</div></div>`).join("")}
    <h3 style="margin-top:14px;">Out-of-area contacts</h3>
    ${e.contacts.map(c => `<div class="kit-item"><div class="name"><b>${escapeHTML(c.role)}</b>: ${escapeHTML(c.what)}</div><div class="qty">${escapeHTML(c.tip)}</div></div>`).join("")}
    ${e.pet_evac_handling.length ? `<h3 style="margin-top:14px;">Pet evac</h3>${e.pet_evac_handling.map(x => `<div>• ${escapeHTML(x)}</div>`).join("")}` : ""}
    ${e.senior_evac_handling.length ? `<h3 style="margin-top:14px;">Senior evac</h3>${e.senior_evac_handling.map(x => `<div>• ${escapeHTML(x)}</div>`).join("")}` : ""}
    ${e.vehicle_readiness.length ? `<h3 style="margin-top:14px;">Vehicle</h3>${e.vehicle_readiness.map(x => `<div>• ${escapeHTML(x)}</div>`).join("")}` : ""}
  `;

  // comm tree
  const c = result.comm_tree;
  document.getElementById("comm").innerHTML = `
    <h3>Communication tree</h3>
    <table>
      <thead><tr><th>code</th><th>meaning</th></tr></thead>
      <tbody>
      ${c.keywords.map(k => `<tr><td><b>${k.code}</b></td><td>${escapeHTML(k.meaning)}</td></tr>`).join("")}
      </tbody>
    </table>
    <h3 style="margin-top:14px;">Family templates</h3>
    ${c.family_templates.map(t => `<div class="kit-item"><div class="name"><b>${escapeHTML(t.name)}</b></div><div class="qty">${escapeHTML(t.body)}</div></div>`).join("")}
    <h3 style="margin-top:14px;">Rules</h3>
    ${c.rules.map(r => `<div>• ${escapeHTML(r)}</div>`).join("")}
  `;

  // flags
  const flags = result.risk_flags;
  document.getElementById("flags").innerHTML = `
    <h3>Risk flags (${flags.length})</h3>
    ${flags.length === 0 ? `<div class="hint">none detected — clean</div>` : ""}
    ${flags.map(f => `
      <div class="flag severity-${f.severity}">
        <div class="head">[${f.severity}] ${f.flag}</div>
        <div class="evidence">${escapeHTML(f.evidence)}</div>
        <div class="fix"><b>fix:</b> ${escapeHTML(f.fix)}</div>
      </div>
    `).join("")}
  `;
}

function levelLabel(l) {
  return ["none", "low", "medium", "high"][l];
}

function axisColor(v) {
  if (v >= 85) return "var(--good)";
  if (v >= 70) return "var(--accent-2)";
  if (v >= 55) return "var(--warn)";
  if (v >= 40) return "#ff8a65";
  return "var(--bad)";
}

function labelVerdict(v) {
  return v.replace(/_/g, " ");
}

function escapeHTML(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setRating(r) {
  CURRENT_RATING = r;
  document.querySelectorAll(".rating button").forEach((btn) => {
    if (parseInt(btn.dataset.r) <= r) btn.classList.add("on");
    else btn.classList.remove("on");
  });
  document.getElementById("rating-current").textContent = r > 0 ? `(${r}/5)` : "";
}

async function patchSession() {
  if (!CURRENT_SESSION_ID) {
    alert("run an analysis first");
    return;
  }
  const notes = document.getElementById("notes").value;
  const body = {notes};
  if (CURRENT_RATING) body.rating = CURRENT_RATING;
  const res = await fetch(`/api/sessions/${CURRENT_SESSION_ID}`, {
    method: "PATCH",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  if (res.ok) {
    document.getElementById("export-status").textContent = "saved ✓";
    setTimeout(() => document.getElementById("export-status").textContent = "", 2000);
    refreshSessions();
  }
}

async function doExport(fmt) {
  if (!CURRENT_SESSION_ID) {
    alert("run an analysis first");
    return;
  }
  const url = `/api/export/${CURRENT_SESSION_ID}?fmt=${fmt}`;
  document.getElementById("export-status").textContent = "downloading...";
  const a = document.createElement("a");
  a.href = url;
  a.download = `emergency-readiness-${CURRENT_SESSION_ID}.${fmt === "md" ? "md" : "json"}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  document.getElementById("export-status").textContent = "downloaded ✓";
  setTimeout(() => document.getElementById("export-status").textContent = "", 2000);
}

async function refreshSessions() {
  const res = await fetch("/api/sessions");
  const {sessions} = await res.json();
  const list = document.getElementById("sessions-list");
  if (!sessions.length) {
    list.innerHTML = '<div class="hint">No saved sessions yet.</div>';
    return;
  }
  list.innerHTML = sessions.map(s => `
    <div class="row" data-id="${s.id}">
      <span class="verdict" style="color:${axisColor(s.score || 0)}">${s.verdict || "—"} (${s.score || 0})</span>
      <span style="flex:1;color:#8b93a7;font-size:12px;">${new Date(s.created_at * 1000).toLocaleString()}</span>
      <span style="color:#8b93a7;font-size:12px;">${s.brief.slice(0, 60).replace(/\s+/g, " ")}...</span>
      ${s.rating ? `<span style="color:var(--accent-2);">${"★".repeat(s.rating)}</span>` : ""}
    </div>
  `).join("");
  list.querySelectorAll(".row").forEach(row => {
    row.onclick = async () => {
      const id = row.dataset.id;
      const r = await fetch(`/api/sessions/${id}`);
      const data = await r.json();
      CURRENT_SESSION_ID = id;
      CURRENT_RATING = data.rating;
      setRating(data.rating || 0);
      document.getElementById("notes").value = data.notes || "";
      document.getElementById("brief").value = data.brief;
      document.getElementById("results").classList.remove("hidden");
      renderResult(data.result);
      document.getElementById("rating-current").textContent = data.rating ? `(${data.rating}/5)` : "";
    };
  });
}
