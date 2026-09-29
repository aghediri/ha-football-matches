/*
 * Football Agenda Card — Lovelace custom card for ha-football-matches.
 *
 * Shows the "Next Match" hero, then an agenda for ONE match-day at a time
 * (◀ / ▶ step between days that have fixtures), grouped by league.
 *
 * Install:
 *   Copy to <config>/www/football-agenda-card.js, then add the resource:
 *     url: /local/football-agenda-card.js
 *     type: module
 *
 * Card config:
 *   type: custom:football-agenda-card
 *   # optional overrides:
 *   next_match_entity: sensor.football_matches_next_match
 *   entities:
 *     - sensor.football_matches_premier_league
 *     - sensor.football_matches_ligue_1
 *     - sensor.football_matches_la_liga
 *     - sensor.football_matches_serie_a
 *     - sensor.football_matches_champions_league
 */

const DEFAULT_NEXT = "sensor.football_matches_next_match";
const DEFAULT_LEAGUES = [
  "sensor.football_matches_premier_league",
  "sensor.football_matches_ligue_1",
  "sensor.football_matches_la_liga",
  "sensor.football_matches_serie_a",
  "sensor.football_matches_champions_league",
];

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);

const pad = (n) => String(n).padStart(2, "0");

// Local-date key (YYYY-MM-DD) in the browser's timezone.
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

class FootballAgendaCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selected = null; // YYYY-MM-DD, survives hass polling updates
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
    // Only re-render when one of our entities actually changed.
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

  // Keep the user's selected day across refreshes. If it's gone from the
  // data (or nothing is selected yet), snap to the nearest upcoming match-day.
  _resolveSelected(days) {
    if (!days.length) return null;
    if (this._selected && days.includes(this._selected)) return this._selected;
    const anchor = this._selected || dayKey(new Date());
    return days.find((k) => k >= anchor) || days[days.length - 1];
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
    const hasScore =
      m.home_score !== null && m.home_score !== undefined &&
      m.away_score !== null && m.away_score !== undefined;
    const tm = m.is_live
      ? `🔴 <span class="livemin">${esc(fmtMinute(m.minute))}</span>`
      : hhmm(m._date);
    const homeCrest = m.home_crest ? `<img class="crest" src="${esc(m.home_crest)}" alt="">` : "";
    const awayCrest = m.away_crest ? `<img class="crest" src="${esc(m.away_crest)}" alt="">` : "";
    const score = hasScore ? `${esc(m.home_score)} - ${esc(m.away_score)}` : "–";
    return `
      <tr>
        <td class="tm">${tm}</td>
        <td class="home">${esc(m.home)}${homeCrest}</td>
        <td class="vs">v</td>
        <td class="away">${awayCrest}${esc(m.away)}</td>
        <td class="score${m.is_live ? " live" : ""}"><span>${score}</span></td>
      </tr>`;
  }

  _renderAgenda(dayMatches) {
    // Group by league, keeping the configured sensor order.
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
            <table>${g.rows.map((m) => this._renderRow(m)).join("")}</table>
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

  /* Next Match hero */
  .hero {
    background: linear-gradient(135deg, #1e3a5f, #2ec27e);
    border-radius: 16px;
    padding: 18px 22px;
    color: #fff;
    margin-bottom: 20px;
    text-align: center;
  }
  .hero-label {
    font-size: 12px; letter-spacing: .12em; text-transform: uppercase; opacity: .85;
  }
  .hero-teams {
    display: flex; align-items: center; justify-content: center; gap: 14px; margin: 12px 0 10px;
  }
  .hero-team {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
    font-size: 22px; font-weight: 700; line-height: 1.15;
  }
  .hero-team img { width: 56px; height: 56px; object-fit: contain; }
  .hero-vs { font-size: 16px; opacity: .8; }
  .hero-meta { font-size: 14px; opacity: .92; }

  /* Day navigation (uses the dashboard's .day look) */
  .day {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 6px 12px;
    margin: 14px 0 6px;
    font-weight: 700;
    font-size: 14px;
  }
  .nav {
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 0 18px;
  }
  .date { font-size: 16px; text-align: center; flex: 1; }
  .arrow {
    background: none; border: none; color: var(--primary-text-color);
    font: inherit; font-size: 18px; padding: 4px 12px; border-radius: 8px; cursor: pointer;
  }
  .arrow:hover:not([disabled]) { background: var(--primary-color); color: #fff; }
  .arrow[disabled] { opacity: .25; cursor: default; }
  .today {
    margin-left: 6px; font-size: 11px; padding: 2px 6px; border-radius: 6px;
    background: #2ec27e; color: #fff; vertical-align: middle;
  }

  /* League blocks */
  .league {
    background: var(--card-background-color);
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,.12);
  }
  .league h2 {
    display: flex; align-items: center; gap: 12px;
    font-size: 20px; margin: 0 0 10px; padding-bottom: 10px;
    border-bottom: 2px solid var(--divider-color);
  }
  .league h2 img { height: 30px; }

  /* Match rows */
  table { width: 100%; border-collapse: collapse; }
  tr:nth-child(even) { background: rgba(127,127,127,.06); }
  tr:hover { background: var(--primary-color); color: #fff; }
  td { padding: 10px; vertical-align: middle; }
  .tm { color: var(--secondary-text-color); width: 64px; white-space: nowrap; }
  .home { text-align: right; }
  .crest { height: 24px; width: 24px; object-fit: contain; vertical-align: middle; margin: 0 6px; }
  .vs { text-align: center; opacity: .5; width: 34px; }
  .score { text-align: center; width: 78px; }
  .score span {
    background: var(--secondary-background-color);
    border-radius: 6px; padding: 3px 10px; font-weight: 700;
  }
  .live span { background: #e5342b; color: #fff; }
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
  description: "Next match hero plus a match-day agenda grouped by league.",
});
