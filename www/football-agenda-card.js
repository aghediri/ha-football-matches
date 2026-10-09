/*
 * Football Agenda Card — Lovelace custom card for ha-football-matches.
 *
 * Shows the "Next Match" hero, then an agenda for ONE match-day at a time
 * (◀ / ▶ step between days that have fixtures), grouped by league.
 * Live/finished matches show the SCORE in the centre; upcoming show kickoff time.
 *
 * Install:
 *   Copy to <config>/www/football-agenda-card.js, then add the resource:
 *     url: /local/football-agenda-card.js
 *     type: module
 *
 * Card config:
 *   type: custom:football-agenda-card
 */

const DEFAULT_NEXT = "sensor.football_matches_next_match";
const DEFAULT_LEAGUES = [
  "sensor.football_matches_premier_league",
  "sensor.football_matches_ligue_1",
  "sensor.football_matches_la_liga",
  "sensor.football_matches_serie_a",
  "sensor.football_matches_bundesliga",
  "sensor.football_matches_champions_league",
];

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);

const pad = (n) => String(n).padStart(2, "0");

const dayKey = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

const keyToDate = (k) => {
  const [y, m, d] = k.split("-").map(Number);
  return new Date(y, m - 1, d);
};

const hhmm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

const fmtDayLabel = (k, lang) =>
  keyToDate(k).toLocaleDateString(lang, { weekday: "long", day: "numeric", month: "long" });

const fmtHeroDate = (d, lang) =>
  `${d.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" })} · ${hhmm(d)}`;

const fmtCountdown = (mins) => {
  if (mins === null || mins === undefined || mins === "" || isNaN(mins)) return "";
  mins = Number(mins);
  if (mins <= 0) return "now";
  if (mins >= 1440) {
    const days = Math.round(mins / 1440);
    return `in ${days} day${days === 1 ? "" : "s"}`;
  }
  if (mins >= 60) return `in ${Math.round(mins / 60)}h`;
  return `in ${Math.round(mins)} min`;
};

const fmtMinute = (m) => {
  if (m === null || m === undefined || m === "") return "LIVE";
  return /^\d+(\+\d+)?$/.test(String(m)) ? `${m}'` : String(m);
};

const hasScore = (m) =>
  m.home_score !== null && m.home_score !== undefined &&
  m.away_score !== null && m.away_score !== undefined;

// A match is "played or playing" if it is live, finished, or already has a score.
const isStarted = (m) => {
  const s = String(m.status || "").toUpperCase();
  return m.is_live || hasScore(m) ||
    ["IN_PLAY", "PAUSED", "LIVE", "FINISHED", "FT", "AET", "PEN"].includes(s);
};

class FootballAgendaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selected = null;
    this._lastStates = null;
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    const cfg = {
      next_match_entity: DEFAULT_NEXT,
      entities: DEFAULT_LEAGUES,
      ...(config || {}),
    };
    if (!Array.isArray(cfg.entities) || !cfg.entities.length) {
      throw new Error("football-agenda-card: 'entities' must be a non-empty list");
    }
    this._config = cfg;
    this._lastStates = null;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const ids = [this._config.next_match_entity, ...this._config.entities];
    const states = ids.map((id) => hass.states[id]);
    if (this._lastStates && states.every((s, i) => s === this._lastStates[i])) return;
    this._lastStates = states;
    this._render();
  }

  getCardSize() {
    return 10;
  }

  // ---- data -------------------------------------------------------------

  _allMatches() {
    const out = [];
    this._config.entities.forEach((id, order) => {
      const st = this._hass.states[id];
      const list = st && st.attributes && st.attributes.matches;
      if (!Array.isArray(list)) return;
      const fallbackName = st.attributes.friendly_name || id;
      for (const m of list) {
        if (!m || !m.utc_date) continue;
        const date = new Date(m.utc_date);
        if (isNaN(date)) continue;
        out.push({
          ...m,
          _date: date,
          _key: dayKey(date),
          _league: m.competition || fallbackName,
          _order: order,
        });
      }
    });
    return out;
  }

  _matchDays(matches) {
    return [...new Set(matches.map((m) => m._key))].sort();
  }

  // Prefer TODAY when today has matches; else nearest upcoming match-day;
  // else the last available. Preserve the user's chosen day across refreshes.
  _resolveSelected(days) {
    if (!days.length) return null;
    if (this._selected && days.includes(this._selected)) return this._selected;
    const today = dayKey(new Date());
    if (days.includes(today)) return today;              // today has matches -> open on today
    return days.find((k) => k >= today) || days[days.length - 1];
  }

  // ---- rendering --------------------------------------------------------

  _renderHero() {
    const st = this._hass.states[this._config.next_match_entity];
    const a = st && st.attributes;
    if (!a || !a.home) return "";
    const lang = this._hass.language || undefined;
    const d = a.utc_date ? new Date(a.utc_date) : null;
    const meta = [
      esc(a.competition),
      d && !isNaN(d) ? esc(fmtHeroDate(d, lang)) : "",
      esc(fmtCountdown(a.minutes_until)),
    ].filter(Boolean).join(" · ");
    return `
      <div class="hero">
        <div class="hero-label">Next Match</div>
        <div class="hero-teams">
          <div class="hero-team">
            ${a.home_crest ? `<img src="${esc(a.home_crest)}" alt="">` : ""}
            <span>${esc(a.home)}</span>
          </div>
          <div class="hero-vs">v</div>
          <div class="hero-team">
            ${a.away_crest ? `<img src="${esc(a.away_crest)}" alt="">` : ""}
            <span>${esc(a.away)}</span>
          </div>
        </div>
        <div class="hero-meta">${meta}</div>
      </div>`;
  }

  _renderRow(m) {
    const started = isStarted(m);
    const homeCrest = m.home_crest ? `<img class="crest" src="${esc(m.home_crest)}" alt="">` : "";
    const awayCrest = m.away_crest ? `<img class="crest" src="${esc(m.away_crest)}" alt="">` : "";

    // Left meta: kickoff time, live minute, or FT
    let tm;
    if (m.is_live) {
      tm = `<span class="livemin">\ud83d\udd34 ${esc(fmtMinute(m.minute))}</span>`;
    } else if (started && hasScore(m)) {
      tm = `<span class="ft">FT</span>`;
    } else {
      tm = `<span class="kick">${hhmm(m._date)}</span>`;
    }

    // Centre: score when started, else "v"
    let centre;
    if (started && hasScore(m)) {
      centre = `<span class="scorebox${m.is_live ? " live" : ""}">${esc(m.home_score)}&ndash;${esc(m.away_score)}</span>`;
    } else if (started) {
      centre = `<span class="scorebox${m.is_live ? " live" : ""}">0&ndash;0</span>`;
    } else {
      centre = `<span class="vs">v</span>`;
    }

    return `
      <div class="row ${started ? "started" : ""}">
        <div class="meta">${tm}</div>
        <div class="home"><span class="tn">${esc(m.home)}</span>${homeCrest}</div>
        <div class="mid">${centre}</div>
        <div class="away">${awayCrest}<span class="tn">${esc(m.away)}</span></div>
      </div>`;
  }

  _renderAgenda(dayMatches) {
    const groups = new Map();
    for (const m of dayMatches) {
      if (!groups.has(m._league)) {
        groups.set(m._league, { order: m._order, emblem: m.competition_emblem, rows: [] });
      }
      const g = groups.get(m._league);
      if (!g.emblem && m.competition_emblem) g.emblem = m.competition_emblem;
      g.rows.push(m);
    }
    return [...groups.entries()]
      .sort((a, b) => a[1].order - b[1].order)
      .map(([name, g]) => {
        g.rows.sort((a, b) => a._date - b._date);
        return `
          <div class="league">
            <h2>${g.emblem ? `<img src="${esc(g.emblem)}" alt="">` : ""}${esc(name)}</h2>
            <div class="rows">${g.rows.map((m) => this._renderRow(m)).join("")}</div>
          </div>`;
      })
      .join("");
  }

  _render() {
    if (!this._hass || !this._config) return;
    const lang = this._hass.language || undefined;
    const matches = this._allMatches();
    const days = this._matchDays(matches);
    this._selected = this._resolveSelected(days);

    let body;
    if (!this._selected) {
      body = `<div class="empty">No upcoming matches.</div>`;
    } else {
      const idx = days.indexOf(this._selected);
      const prev = idx > 0 ? days[idx - 1] : null;
      const next = idx < days.length - 1 ? days[idx + 1] : null;
      const isToday = this._selected === dayKey(new Date());
      const dayMatches = matches.filter((m) => m._key === this._selected);
      body = `
        <div class="day nav">
          <button class="arrow" data-go="${prev || ""}" ${prev ? "" : "disabled"}
                  aria-label="Previous match-day">◀</button>
          <div class="date">
            ${esc(fmtDayLabel(this._selected, lang))}
            ${isToday ? `<span class="today">Today</span>` : ""}
          </div>
          <button class="arrow" data-go="${next || ""}" ${next ? "" : "disabled"}
                  aria-label="Next match-day">▶</button>
        </div>
        ${this._renderAgenda(dayMatches)}`;
    }

    this.shadowRoot.innerHTML = `
      <style>${FootballAgendaCard.styles}</style>
      <ha-card>
        <div class="wrap">
          ${this._renderHero()}
          ${body}
        </div>
      </ha-card>`;

    this.shadowRoot.querySelectorAll("button[data-go]").forEach((b) =>
      b.addEventListener("click", () => {
        const key = b.dataset.go;
        if (!key || key === this._selected) return;
        this._selected = key;
        this._render();
      })
    );
  }
}

FootballAgendaCard.styles = `
  ha-card { overflow: hidden; }
  .wrap { padding: 16px; }

  .hero {
    background: linear-gradient(135deg, #1e3a5f, #2ec27e);
    border-radius: 16px; padding: 18px 22px; color: #fff;
    margin-bottom: 20px; text-align: center;
  }
  .hero-label { font-size: 12px; letter-spacing: .12em; text-transform: uppercase; opacity: .85; }
  .hero-teams { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 12px 0 10px; }
  .hero-team { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 22px; font-weight: 700; line-height: 1.15; }
  .hero-team img { width: 56px; height: 56px; object-fit: contain; }
  .hero-vs { font-size: 16px; opacity: .8; }
  .hero-meta { font-size: 14px; opacity: .92; }

  .day { background: var(--secondary-background-color); border-radius: 8px; padding: 6px 12px; margin: 14px 0 6px; font-weight: 700; font-size: 14px; }
  .nav { display: flex; align-items: center; justify-content: space-between; margin: 0 0 18px; }
  .date { font-size: 16px; text-align: center; flex: 1; }
  .arrow { background: none; border: none; color: var(--primary-text-color); font: inherit; font-size: 18px; padding: 4px 12px; border-radius: 8px; cursor: pointer; }
  .arrow:hover:not([disabled]) { background: var(--primary-color); color: #fff; }
  .arrow[disabled] { opacity: .25; cursor: default; }
  .today { margin-left: 6px; font-size: 11px; padding: 2px 6px; border-radius: 6px; background: #2ec27e; color: #fff; vertical-align: middle; }

  .league { background: var(--card-background-color); border-radius: 14px; padding: 14px 18px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.12); }
  .league h2 { display: flex; align-items: center; gap: 12px; font-size: 20px; margin: 0 0 10px; padding-bottom: 10px; border-bottom: 2px solid var(--divider-color); }
  .league h2 img { height: 30px; }

  .rows { display: flex; flex-direction: column; }
  /* Grid: [meta 56px] [home 1fr] [score 84px] [away 1fr] — identical on every row */
  .row {
    display: grid;
    grid-template-columns: 56px 1fr 84px 1fr;
    align-items: center;
    gap: 6px;
    padding: 9px 4px;
    border-bottom: 1px solid var(--divider-color);
  }
  .row:last-child { border-bottom: none; }
  .row:nth-child(even) { background: rgba(127,127,127,.05); }
  .row.started { font-weight: 600; }

  .meta { text-align: center; font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
  .kick { }
  .ft { font-weight: 700; font-size: 12px; }
  .livemin { color: #e5342b; font-weight: 700; font-size: 12px; white-space: nowrap; }

  .home { display: flex; align-items: center; justify-content: flex-end; gap: 6px; min-width: 0; }
  .away { display: flex; align-items: center; justify-content: flex-start; gap: 6px; min-width: 0; }
  .tn { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .crest { height: 24px; width: 24px; object-fit: contain; flex: none; }

  /* Centre score cell — fixed width, always dead-centre */
  .mid { display: flex; justify-content: center; align-items: center; }
  .vs { opacity: .45; }
  .scorebox {
    display: inline-block; min-width: 56px; text-align: center; box-sizing: border-box;
    background: var(--secondary-background-color); border-radius: 6px; padding: 4px 10px;
    font-weight: 800; font-size: 15px; letter-spacing: 1px; white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .scorebox.live { background: #e5342b; color: #fff; }

  .livemin { color: #e5342b; font-weight: 700; font-size: 12px; }
  .empty { text-align: center; padding: 24px 8px; color: var(--secondary-text-color); }
`;

if (!customElements.get("football-agenda-card")) {
  customElements.define("football-agenda-card", FootballAgendaCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "football-agenda-card",
  name: "Football Agenda Card",
  description: "Next match hero plus a match-day agenda grouped by league, with live scores.",
});
