import datetime
import re

import requests

AELF_BASE_URL = "https://api.aelf.org/v1/messes"

TYPE_LABELS = {
    "lecture_1": "1ère lecture",
    "lecture_2": "2e lecture",
    "psaume": "Psaume",
    "evangile": "Évangile",
}

# Ordre liturgique d'affichage (le verset d'acclamation avant l'Évangile
# n'est pas repris, il fait doublon avec l'Évangile lui-même).
READING_ORDER = ["lecture_1", "psaume", "lecture_2", "evangile"]


def _clean_html(raw: str) -> str:
    text = raw.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    text = re.sub(r"</?p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def get_daily_readings(date_obj: datetime.date, zone: str = "france") -> dict | None:
    """
    Récupère les lectures de la messe du jour depuis l'API officielle AELF.
    Retourne {"informations": {...}, "lectures": [...]} (lectures triées dans
    l'ordre liturgique), ou None en cas d'erreur.
    """
    url = f"{AELF_BASE_URL}/{date_obj.isoformat()}/{zone}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print("Erreur API AELF:", resp.status_code, resp.text)
            return None

        data = resp.json()
        messes = data.get("messes", [])
        if not messes:
            return None

        raw_lectures = messes[0].get("lectures", [])
        by_type = {r.get("type"): r for r in raw_lectures}

        lectures = []
        for reading_type in READING_ORDER:
            r = by_type.get(reading_type)
            if not r:
                continue
            lectures.append({
                "type": reading_type,
                "label": TYPE_LABELS.get(reading_type, reading_type),
                "ref": (r.get("ref") or "").strip(),
                "titre": (r.get("titre") or "").strip(),
                "intro": (r.get("intro_lue") or "").strip(),
                "contenu": _clean_html(r.get("contenu") or ""),
            })

        if not lectures:
            return None

        return {
            "informations": data.get("informations", {}),
            "lectures": lectures,
        }
    except Exception as e:
        print("Exception API AELF:", e)
        return None


def get_gospel(date_obj: datetime.date, zone: str = "france") -> dict | None:
    """Retourne {"informations": {...}, "lecture": {...}} pour l'Évangile du jour, ou None."""
    data = get_daily_readings(date_obj, zone=zone)
    if not data:
        return None

    for lecture in data["lectures"]:
        if lecture["type"] == "evangile":
            return {
                "informations": data["informations"],
                "lecture": lecture,
            }
    return None
