"""Constants for the Football Matches integration."""

DOMAIN = "football_matches"

CONF_API_TOKEN = "api_token"
CONF_UPCOMING_DAYS = "upcoming_days"
CONF_LIVE_API_TOKEN = "live_api_token"   # optional API-Football key for live scores

DEFAULT_UPCOMING_DAYS = 7
DEFAULT_SCAN_INTERVAL_MINUTES = 30

API_BASE = "https://api.football-data.org/v4"

# Competition code -> friendly name (football-data.org codes)
COMPETITIONS = {
    "PL": "Premier League",
    "FL1": "Ligue 1",
    "PD": "La Liga",
    "SA": "Serie A",
    "CL": "Champions League",
}
