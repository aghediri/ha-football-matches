"""Team-name normalization to reliably match football-data.org <-> API-Football.

football-data.org uses long names ("Racing Club de Lens", "Paris Saint-Germain FC")
while API-Football uses short ones ("Lens", "Paris Saint Germain"). We normalize
both to a canonical key so live scores merge onto the right fixture.
"""
from __future__ import annotations

import re
import unicodedata

# Canonical mapping (normalized form -> canonical key). Includes BOTH the
# football-data.org long form and the API-Football short form so both sides
# resolve to the same key.
ALIASES = {
    # ---- Ligue 1 ----
    "racing club de lens": "lens", "lens": "lens",
    "olympique lyonnais": "lyon", "lyon": "lyon",
    "olympique de marseille": "marseille", "marseille": "marseille",
    "paris saint germain": "paris saint germain", "paris saint germain fc": "paris saint germain", "psg": "paris saint germain",
    "as monaco": "monaco", "monaco": "monaco",
    "losc lille": "lille", "lille osc": "lille", "lille": "lille",
    "stade brestois 29": "brest", "brest": "brest",
    "stade rennais 1901": "rennes", "rennes": "rennes",
    "ogc nice": "nice", "nice": "nice",
    "rc strasbourg alsace": "strasbourg", "strasbourg": "strasbourg",
    # ---- La Liga ----
    "fc barcelona": "barcelona", "barcelona": "barcelona",
    "real madrid cf": "real madrid", "real madrid": "real madrid",
    "club atletico de madrid": "atletico madrid", "atletico madrid": "atletico madrid", "atletico de madrid": "atletico madrid",
    "rcd espanyol de barcelona": "espanyol", "espanyol": "espanyol",
    "athletic club": "athletic club", "athletic": "athletic club",
    "real sociedad de futbol": "real sociedad", "real sociedad": "real sociedad",
    "sevilla fc": "sevilla", "sevilla": "sevilla",
    "valencia cf": "valencia", "valencia": "valencia",
    "villarreal cf": "villarreal", "villarreal": "villarreal",
    "real betis balompie": "real betis", "real betis": "real betis", "betis": "real betis",
    "deportivo alaves": "alaves", "alaves": "alaves",
    "rayo vallecano de madrid": "rayo vallecano", "rayo vallecano": "rayo vallecano",
    "getafe cf": "getafe", "getafe": "getafe",
    "malaga cf": "malaga", "malaga": "malaga",
    # ---- Serie A ----
    "fc internazionale milano": "inter", "internazionale": "inter", "inter": "inter",
    "ac milan": "milan", "milan": "milan",
    "juventus fc": "juventus", "juventus": "juventus",
    "as roma": "roma", "roma": "roma",
    "ssc napoli": "napoli", "napoli": "napoli",
    "ss lazio": "lazio", "lazio": "lazio",
    "acf fiorentina": "fiorentina", "fiorentina": "fiorentina",
    "atalanta bc": "atalanta", "atalanta": "atalanta",
    "bologna fc 1909": "bologna", "bologna": "bologna",
    "torino fc": "torino", "torino": "torino",
    # ---- Premier League ----
    "manchester united fc": "manchester united", "manchester united": "manchester united", "man united": "manchester united",
    "manchester city fc": "manchester city", "manchester city": "manchester city", "man city": "manchester city",
    "tottenham hotspur fc": "tottenham", "tottenham hotspur": "tottenham", "tottenham": "tottenham",
    "wolverhampton wanderers fc": "wolves", "wolves": "wolves", "wolverhampton wanderers": "wolves",
    "brighton hove albion fc": "brighton", "brighton hove albion": "brighton", "brighton": "brighton",
    "afc bournemouth": "bournemouth", "bournemouth": "bournemouth",
    "nottingham forest fc": "nottingham forest", "nottingham forest": "nottingham forest",
    "newcastle united fc": "newcastle", "newcastle united": "newcastle", "newcastle": "newcastle",
    "west ham united fc": "west ham", "west ham united": "west ham", "west ham": "west ham",
    "leeds united fc": "leeds", "leeds united": "leeds", "leeds": "leeds",
    "sunderland afc": "sunderland", "sunderland": "sunderland",
    "ipswich town fc": "ipswich", "ipswich town": "ipswich", "ipswich": "ipswich",
    "hull city afc": "hull city", "hull city": "hull city",
    "coventry city fc": "coventry", "coventry city": "coventry", "coventry": "coventry",
    "crystal palace fc": "crystal palace", "crystal palace": "crystal palace",
    "arsenal fc": "arsenal", "arsenal": "arsenal",
    "chelsea fc": "chelsea", "chelsea": "chelsea",
    "liverpool fc": "liverpool", "liverpool": "liverpool",
    "everton fc": "everton", "everton": "everton",
    "aston villa fc": "aston villa", "aston villa": "aston villa",
    "fulham fc": "fulham", "fulham": "fulham",
    "brentford fc": "brentford", "brentford": "brentford",
}

# Tokens safe to strip (NOTE: 'united'/'city'/'town' are NOT here — they distinguish clubs)
_STRIP_TOKENS = {
    "fc", "cf", "afc", "sc", "club", "de", "futbol", "calcio",
    "1909", "1901", "29", "balompie", "bc",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def normalize(name: str) -> str:
    """Normalize a team name to a canonical key for matching."""
    if not name:
        return ""
    s = _strip_accents(name).lower().strip()
    s = s.replace("&", " ").replace(".", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if s in ALIASES:
        return ALIASES[s]
    tokens = [t for t in s.split(" ") if t not in _STRIP_TOKENS]
    key = " ".join(tokens).strip()
    return ALIASES.get(key, key)


def match_key(home: str, away: str) -> str:
    """Build the canonical 'home|away' key used to merge live scores."""
    return f"{normalize(home)}|{normalize(away)}"
