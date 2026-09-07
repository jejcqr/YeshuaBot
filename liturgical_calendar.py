import datetime

import requests

SEASON_EN_TO_FR = {
    "advent": "Avent",
    "christmas": "Temps de Noël",
    "lent": "Carême",
    "triduum": "Triduum pascal",
    "easter": "Temps pascal",
    "ordinary time": "Temps ordinaire",
}

RANK_EN_TO_FR = {
    "solemnity": "Solennité",
    "sunday": "Dimanche",
    "feast": "Fête",
    "memorial": "Mémorial",
    "optional memorial": "Mémorial facultatif",
    "primary liturgical days": "Jour liturgique principal",
}

COLOUR_EN_TO_FR = {
    "green": "vert",
    "white": "blanc",
    "red": "rouge",
    "purple": "violet",
}

COLOUR_HEX = {
    "vert": 0x2ecc71,
    "blanc": 0xffffff,
    "rouge": 0xe74c3c,
    "violet": 0x9b59b6,
    "rose": 0xf1948a,
}

TITLE_EN_TO_FR = {
    "4th sunday of lent": "4ᵉ dimanche de Carême (Laetare)",
    "3rd sunday of lent": "3ᵉ dimanche de Carême",
    "2nd sunday of lent": "2ᵉ dimanche de Carême",
    "1st sunday of lent": "1er dimanche de Carême",
    "ash wednesday": "Mercredi des Cendres",
    "palm sunday of the passion of the lord": "Dimanche des Rameaux",
    "holy thursday of the lord's supper": "Jeudi saint",
    "good friday of the lord's passion": "Vendredi saint",
    "holy saturday": "Samedi saint",
    "the nativity of the lord": "Nativité du Seigneur (Noël)",
    "the resurrection of the lord": "Résurrection du Seigneur (Pâques)",
}


def translate_rank(rank_en: str) -> str:
    key = (rank_en or "").lower()
    return RANK_EN_TO_FR.get(key, rank_en)


def translate_colour(colour_en: str) -> str:
    key = (colour_en or "").lower()
    return COLOUR_EN_TO_FR.get(key, colour_en)


def translate_title(title_en: str) -> str:
    key = (title_en or "").lower()
    return TITLE_EN_TO_FR.get(key, title_en)


def get_saints_for_date(date_obj: datetime.date) -> tuple[list[dict], str]:
    """
    Utilise calapi.inadiutorium.cz (en) pour récupérer les célébrations du jour
    dans le calendrier romain général.
    Retourne (liste de célébrations, saison_fr).
    """
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    url = f"http://calapi.inadiutorium.cz/api/v0/en/calendars/general-en/{year}/{month}/{day}"

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print("Erreur API Church Calendar:", resp.status_code, resp.text)
            return [], ""

        data = resp.json()
        celebrations = data.get("celebrations", [])
        saints = []
        for c in celebrations:
            title_en = c.get("title", "").strip()
            rank_en = c.get("rank", "").strip()
            colour_en = c.get("colour", "").strip()

            if not title_en:
                continue

            saints.append({
                "title_fr": translate_title(title_en),
                "rank_fr": translate_rank(rank_en),
                "colour_fr": translate_colour(colour_en),
                "title_en": title_en,
                "rank_en": rank_en,
            })

        season_en = data.get("season", "").strip()
        season_fr = SEASON_EN_TO_FR.get((season_en or "").lower(), season_en)

        return saints, season_fr
    except Exception as e:
        print("Exception API Church Calendar:", e)
        return [], ""
