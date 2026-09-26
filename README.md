<p align="center"><img src="logo.png" width="140" alt="Football Matches"></p>

# Football Matches — Home Assistant Integration

Shows today's and upcoming fixtures for the top European football (soccer) leagues in Home Assistant, powered by the free [football-data.org](https://www.football-data.org) API.

## Leagues covered
- 🏴 English Premier League (`PL`)
- 🇫🇷 French Ligue 1 (`FL1`)
- 🇪🇸 Spanish La Liga (`PD`)
- 🇮🇹 Italian Serie A (`SA`)
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
