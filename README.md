<p align="center"><img src="logo.png" width="140" alt="Football Matches"></p>

# Football Matches — Home Assistant Integration

Shows today's and upcoming fixtures for the top European football (soccer) leagues in Home Assistant, powered by the free [football-data.org](https://www.football-data.org) API and api-football.com   

## Leagues covered
- 🏴 English Premier League (`PL`)
- 🇫🇷 French Ligue 1 (`FL1`)
- 🇪🇸 Spanish La Liga (`PD`)
- 🇮🇹 Italian Serie A (`SA`)
- 🇩🇪 German Bundesliga (`BL1`)
- 🇪🇺 UEFA Champions League (`CL`)

## Sensors created
| Sensor | State | Attributes |
|---|---|---|
| `sensor.football_matches_today` | # matches today | `matches` (full list) |
| `sensor.football_matches_upcoming` | # upcoming (in window) | `matches` |
| `sensor.football_matches_next_match` | "Home vs Away" | full match + `minutes_until`, `hours_until` |
| `sensor.football_matches_premier_league` | # PL matches | `matches` |
| `sensor.football_matches_ligue_1` | # FL1 matches | `matches` |
| `sensor.football_matches_la_liga` | # PD matches | `matches` |
| `sensor.football_matches_serie_a` | # SA matches | `matches` |
| `sensor.football_matches_champions_league` | # CL matches | `matches` |

Each match in `matches` includes: `competition`, `utc_date`, `kickoff_local`, `status`, `home`, `away`, `home_score`, `away_score`, `home_crest`, `away_crest`, `matchday`.

## Installation (HACS custom repository)
1. Get a free API token: https://www.football-data.org/client/register
2. HACS → ⋮ → **Custom repositories** → add this repo URL, category **Integration**
3. Install **Football Matches** → restart Home Assistant
4. Settings → Devices & Services → **Add Integration** → *Football Matches* → paste your API token
5. (Optional) Configure how many upcoming days to show (default 7)

## Manual installation
Copy `custom_components/football_matches/` into your HA `config/custom_components/` folder, restart HA, then add the integration.

## Notes
- Free tier is rate-limited (~10 req/min); the integration polls every 30 minutes.
- Times are stored in UTC (`utc_date`); use `as_timestamp`/`as_local` in dashboard templates to display local time.


## Dashboard (optional)

A ready-made styled dashboard is included: [`dashboard.yaml`](dashboard.yaml).

It shows a gradient **Next Match** hero, then one card per league with club
crests, league logos, matches grouped under date headers, and a score column
(shows `—` until played).

**Requires** the [HTML Jinja2 Template card](https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Jinja2-Template-card):
1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-Jinja2-Template-card`,
   category **Dashboard** → Download → restart HA → hard-refresh.

**Apply the dashboard:**
1. Settings → Dashboards → **+ Add Dashboard** → *New dashboard from scratch*.
2. Open it → **⋮ → Edit → ⋮ → Raw configuration editor**.
3. Paste the contents of [`dashboard.yaml`](dashboard.yaml) → **Save**.

> Entity IDs assume the default config-entry name *Football Matches*
> (`sensor.football_matches_*`). Adjust the template if yours differ.

A simpler **no-extra-card** variant using only the built-in Markdown card is
also possible (logos + grouped dates, less styling) — see the wiki/issues.


## Agenda card (interactive, optional)

An interactive alternative to the static dashboard: [`www/football-agenda-card.js`](www/football-agenda-card.js).
It keeps the gradient **Next Match** hero on top, then shows an **agenda for one
match-day at a time** — the matches on that date across all five leagues,
grouped by league. A top nav bar (◀ / date / ▶) steps only through days that
actually have fixtures (empty days are skipped), with a **Today** badge on the
current date. Your selected day is preserved across the 30-minute sensor refresh.

**Install the card:**
1. Copy `www/football-agenda-card.js` into your HA `config/www/` folder
   (so it is served at `/local/football-agenda-card.js`).
2. Settings → Dashboards → ⋮ → **Resources** → **+ Add Resource**
   → URL `/local/football-agenda-card.js`, type **JavaScript Module** → Create.
3. Hard-refresh the browser (Ctrl+Shift+R).

**Add it to a view:**
```yaml
type: custom:football-agenda-card
# optional overrides (defaults shown):
# next_match_entity: sensor.football_matches_next_match
# entities:
#   - sensor.football_matches_premier_league
#   - sensor.football_matches_ligue_1
#   - sensor.football_matches_la_liga
#   - sensor.football_matches_serie_a
#   - sensor.football_matches_champions_league
```

No extra dependencies — this card is self-contained (unlike the `dashboard.yaml`
variant, which needs the HTML Jinja2 Template card).
