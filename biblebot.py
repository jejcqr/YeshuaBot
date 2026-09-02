import os
import datetime
import hashlib
import random
from typing import List

import discord
from discord import option
from discord.utils import basic_autocomplete
import mysql.connector
from mysql.connector import Error
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import requests  # pour l'API Church Calendar


# =========================
# Config Discord
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise RuntimeError("DISCORD_TOKEN n'est pas défini.")

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

scheduler = AsyncIOScheduler(timezone="UTC")


# =========================
# Config MySQL / MariaDB
# =========================

if os.getenv("DB_PASSWORD") is None:
    raise RuntimeError("DB_PASSWORD n'est pas défini.")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "bibleuser"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "biblebot"),
}

BOOK_MAP = {
    "genese": 1,
    "genèse": 1,
    "exode": 2,
    "levitique": 3,
    "lévitique": 3,
    "nombres": 4,
    "deuteronome": 5,
    "deutéronome": 5,
    "josue": 6,
    "josué": 6,
    "juges": 7,
    "ruth": 8,
    "1 samuel": 9,
    "2 samuel": 10,
    "1 rois": 11,
    "2 rois": 12,
    "1 chroniques": 13,
    "2 chroniques": 14,
    "esdras": 15,
    "nehemie": 16,
    "néhémie": 16,
    "ester": 17,
    "esther": 17,
    "job": 18,
    "psaumes": 19,
    "psaume": 19,
    "proverbes": 20,
    "ecclesiaste": 21,
    "ecclésiaste": 21,
    "cantique des cantiques": 22,
    "esaie": 23,
    "esaïe": 23,
    "ésaïe": 23,
    "jeremie": 24,
    "jérémie": 24,
    "lamentations": 25,
    "ezechiel": 26,
    "ézéchiel": 26,
    "daniel": 27,
    "osee": 28,
    "osée": 28,
    "joel": 29,
    "joël": 29,
    "amos": 30,
    "abdias": 31,
    "jonas": 32,
    "michee": 33,
    "michée": 33,
    "nahum": 34,
    "habakuk": 35,
    "sophonie": 36,
    "aggee": 37,
    "aggée": 37,
    "zacharie": 38,
    "malachie": 39,
    "matthieu": 40,
    "marc": 41,
    "luc": 42,
    "jean": 43,
    "actes": 44,
    "romains": 45,
    "1 corinthiens": 46,
    "2 corinthiens": 47,
    "galates": 48,
    "ephesiens": 49,
    "éphésiens": 49,
    "philippiens": 50,
    "colossiens": 51,
    "1 thesaloniciens": 52,
    "1 thessaloniciens": 52,
    "2 thesaloniciens": 53,
    "2 thessaloniciens": 53,
    "1 timothee": 54,
    "1 timothée": 54,
    "2 timothee": 55,
    "2 timothée": 55,
    "tite": 56,
    "philemon": 57,
    "philémon": 57,
    "hebreux": 58,
    "hébreux": 58,
    "jacques": 59,
    "1 pierre": 60,
    "2 pierre": 61,
    "1 jean": 62,
    "2 jean": 63,
    "3 jean": 64,
    "jude": 65,
    "apocalypse": 66,
    "apoc": 66,
}

BOOK_NUM_TO_NAME = {
    1: "Genèse",
    2: "Exode",
    3: "Lévitique",
    4: "Nombres",
    5: "Deutéronome",
    6: "Josué",
    7: "Juges",
    8: "Ruth",
    9: "1 Samuel",
    10: "2 Samuel",
    11: "1 Rois",
    12: "2 Rois",
    13: "1 Chroniques",
    14: "2 Chroniques",
    15: "Esdras",
    16: "Néhémie",
    17: "Esther",
    18: "Job",
    19: "Psaumes",
    20: "Proverbes",
    21: "Ecclésiaste",
    22: "Cantique des cantiques",
    23: "Ésaïe",
    24: "Jérémie",
    25: "Lamentations",
    26: "Ézéchiel",
    27: "Daniel",
    28: "Osée",
    29: "Joël",
    30: "Amos",
    31: "Abdias",
    32: "Jonas",
    33: "Michée",
    34: "Nahum",
    35: "Habakuk",
    36: "Sophonie",
    37: "Aggée",
    38: "Zacharie",
    39: "Malachie",
    40: "Matthieu",
    41: "Marc",
    42: "Luc",
    43: "Jean",
    44: "Actes",
    45: "Romains",
    46: "1 Corinthiens",
    47: "2 Corinthiens",
    48: "Galates",
    49: "Éphésiens",
    50: "Philippiens",
    51: "Colossiens",
    52: "1 Thessaloniciens",
    53: "2 Thessaloniciens",
    54: "1 Timothée",
    55: "2 Timothée",
    56: "Tite",
    57: "Philémon",
    58: "Hébreux",
    59: "Jacques",
    60: "1 Pierre",
    61: "2 Pierre",
    62: "1 Jean",
    63: "2 Jean",
    64: "3 Jean",
    65: "Jude",
    66: "Apocalypse",
}


# =========================
# Utilitaire embeds Bible
# =========================

def make_bible_embed(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Bible Louis Segond (1910)")
    return embed


# =========================
# Fonctions MySQL
# =========================

def get_verse_from_db(book_num: int, chapter: int, verse: int) -> str | None:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        query = """
            SELECT text
            FROM bible_verses_segond_1910
            WHERE book = %s AND chapter = %s AND verse = %s
        """
        cursor.execute(query, (book_num, chapter, verse))
        row = cursor.fetchone()
        return row[0] if row else None
    except Error as e:
        print("Erreur MySQL :", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def search_verses_by_text(query: str, hard_limit: int = 100, book_num: int | None = None):
    """
    Recherche de versets par texte.
    Retourne (results, total) où:
      - results = liste tronquée à hard_limit max
      - total   = nombre total de correspondances dans la DB
    """
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        base_where = "LOWER(text) LIKE %s"
        params = [f"%{query.lower()}%"]

        if book_num is not None:
            base_where += " AND book = %s"
            params.append(book_num)

        count_sql = f"""
            SELECT COUNT(*)
            FROM bible_verses_segond_1910
            WHERE {base_where}
        """
        cursor.execute(count_sql, tuple(params))
        row = cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0

        data_sql = f"""
            SELECT book, chapter, verse, text
            FROM bible_verses_segond_1910
            WHERE {base_where}
            LIMIT %s
        """
        data_params = params + [hard_limit]
        cursor.execute(data_sql, tuple(data_params))
        rows = cursor.fetchall()

        results = []
        for book, chapter, verse, text in rows:
            results.append({
                "book": book,
                "chapter": chapter,
                "verse": verse,
                "text": text,
            })
        return results, total
    except Error as e:
        print("Erreur MySQL (search):", e)
        return [], 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_chapter_from_db(book_num: int, chapter: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        query = """
            SELECT verse, text
            FROM bible_verses_segond_1910
            WHERE book = %s AND chapter = %s
            ORDER BY verse ASC
        """
        cursor.execute(query, (book_num, chapter))
        rows = cursor.fetchall()

        return [{"verse": v, "text": t} for (v, t) in rows]
    except Error as e:
        print("Erreur MySQL (chapitre):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_max_chapter_for_book(book_num: int) -> int:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT MAX(chapter) FROM bible_verses_segond_1910 WHERE book = %s",
            (book_num,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Error as e:
        print("Erreur MySQL (max chapter):", e)
        return 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_verses_numbers_for_chapter(book_num: int, chapter: int) -> list[int]:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT DISTINCT verse
            FROM bible_verses_segond_1910
            WHERE book = %s AND chapter = %s
            ORDER BY verse ASC
            """,
            (book_num, chapter)
        )
        rows = cursor.fetchall()
        return [r[0] for r in rows]
    except Error as e:
        print("Erreur MySQL (verses numbers):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_book_stats(book_num: int) -> tuple[int, int]:
    """Retourne (nb_chapitres, nb_versets) pour un livre."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        cursor.execute(
            "SELECT COUNT(DISTINCT chapter) FROM bible_verses_segond_1910 WHERE book = %s",
            (book_num,)
        )
        row = cursor.fetchone()
        nb_chapitres = row[0] if row and row[0] is not None else 0

        cursor.execute(
            "SELECT COUNT(*) FROM bible_verses_segond_1910 WHERE book = %s",
            (book_num,)
        )
        row = cursor.fetchone()
        nb_versets = row[0] if row and row[0] is not None else 0

        return nb_chapitres, nb_versets
    except Error as e:
        print("Erreur MySQL (book stats):", e)
        return 0, 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_verse_count_for_chapter(book_num: int, chapter: int) -> int:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM bible_verses_segond_1910
            WHERE book = %s AND chapter = %s
            """,
            (book_num, chapter)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Error as e:
        print("Erreur MySQL (verse count):", e)
        return 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def parse_reference(ref: str):
    ref = ref.strip()
    try:
        temp = ref.replace(":", " ")
        parts = temp.split()
        if len(parts) < 3:
            return None, None, None

        verse = int(parts[-1])
        chapter = int(parts[-2])
        book_name = " ".join(parts[:-2]).lower()

        book_num = BOOK_MAP.get(book_name)
        if book_num is None:
            return None, None, None

        return book_num, chapter, verse
    except Exception:
        return None, None, None


def get_total_verses():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT COUNT(*) FROM bible_verses_segond_1910")
        total_rows = cursor.fetchone()[0]
        return total_rows
    except Error as e:
        print("Erreur MySQL (count verses):", e)
        return 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_daily_verse_for_date(date_str: str):
    total_rows = get_total_verses()
    if total_rows == 0:
        return None

    h = hashlib.sha256(date_str.encode("utf-8")).hexdigest()
    seed = int(h[:8], 16)
    rnd = random.Random(seed)
    offset = rnd.randint(0, total_rows - 1)

    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT book, chapter, verse, text
            FROM bible_verses_segond_1910
            LIMIT 1 OFFSET %s
            """,
            (offset,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        book, chapter, verse, text = row
        return {"book": book, "chapter": chapter, "verse": verse, "text": text}
    except Error as e:
        print("Erreur MySQL (daily verse for date):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_random_verse(book_num: int | None = None):
    """
    Verset aléatoire, éventuellement filtré par livre.
    """
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        if book_num is None:
            sql = """
                SELECT book, chapter, verse, text
                FROM bible_verses_segond_1910
                ORDER BY RAND()
                LIMIT 1
            """
            params = ()
        else:
            sql = """
                SELECT book, chapter, verse, text
                FROM bible_verses_segond_1910
                WHERE book = %s
                ORDER BY RAND()
                LIMIT 1
            """
            params = (book_num,)

        cursor.execute(sql, params)
        row = cursor.fetchone()
        if not row:
            return None

        book, chapter, verse, text = row
        return {"book": book, "chapter": chapter, "verse": verse, "text": text}
    except Error as e:
        print("Erreur MySQL (random verse):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def set_daily_verse_settings(guild_id: int, channel_id: int, hour: int, minute: int, timezone: str):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO daily_verse_settings (guild_id, channel_id, hour, minute, timezone)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                channel_id = VALUES(channel_id),
                hour = VALUES(hour),
                minute = VALUES(minute),
                timezone = VALUES(timezone)
            """,
            (guild_id, channel_id, hour, minute, timezone)
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (set settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_all_daily_verse_settings():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT guild_id, channel_id, hour, minute, timezone FROM daily_verse_settings")
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print("Erreur MySQL (get settings):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


# =========================
# Traductions calapi -> FR
# =========================

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


# =========================
# Saint / célébration du jour (API Church Calendar)
# =========================

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


# =========================
# Autocomplete livres & timezone & chapitres & versets
# =========================

async def get_book_suggestions(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").lower()
    all_books = list(BOOK_NUM_TO_NAME.values())

    if not user_input:
        suggestions = all_books[:25]
    else:
        suggestions = [name for name in all_books if user_input in name.lower()]
        if not suggestions:
            suggestions = all_books[:25]

    return suggestions[:25]


async def get_timezone_suggestions(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").lower()
    all_timezones = pytz.all_timezones

    if not user_input:
        suggestions = [
            "America/Martinique",
            "Europe/Paris",
            "UTC",
            "America/New_York",
            "America/Toronto",
            "America/Sao_Paulo",
            "Africa/Abidjan",
            "Africa/Dakar",
        ]
    else:
        suggestions = [tz for tz in all_timezones if user_input in tz.lower()]

    return suggestions[:25]


async def get_chapter_suggestions(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").strip()

    livre = ctx.options.get("livre")
    if not livre:
        return []

    key = str(livre).strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        return []

    max_chapter = get_max_chapter_for_book(book_num)
    if max_chapter <= 0:
        return []

    all_chapters = [str(i) for i in range(1, max_chapter + 1)]

    if user_input.isdigit():
        suggestions = [c for c in all_chapters if c.startswith(user_input)]
    else:
        suggestions = all_chapters

    return suggestions[:25]


async def get_verse_suggestions(ctx: discord.AutocompleteContext):
    user_input = (ctx.value or "").strip()

    livre = ctx.options.get("livre")
    chapitre = ctx.options.get("chapitre")

    if not livre or not chapitre:
        return []

    key = str(livre).strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        return []

    try:
        chapitre_int = int(str(chapitre))
    except ValueError:
        return []

    verse_numbers = get_verses_numbers_for_chapter(book_num, chapitre_int)
    if not verse_numbers:
        return []

    all_verses = [str(v) for v in verse_numbers]

    if user_input.isdigit():
        suggestions = [v for v in all_verses if v.startswith(user_input)]
    else:
        suggestions = all_verses

    return suggestions[:25]


# =========================
# Pagination pour /chapter et /search
# =========================

class ChapterPaginator(discord.ui.View):
    def __init__(self, pages: List[str], title: str):
        super().__init__(timeout=None)  # aucun timeout
        self.pages = pages
        self.title = title
        self.current = 0

    async def update_message(self, interaction: discord.Interaction):
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= len(self.pages) - 1

        embed = make_bible_embed(
            title=self.title + f" (page {self.current + 1}/{len(self.pages)})",
            description=self.pages[self.current]
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Précédent", style=discord.ButtonStyle.primary)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current > 0:
            self.current -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="Suivant", style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current < len(self.pages) - 1:
            self.current += 1
        await self.update_message(interaction)


# =========================
# Tâche planifiée : envoi automatique
# =========================

async def send_daily_verses():
    settings = get_all_daily_verse_settings()
    if not settings:
        return

    for guild_id, channel_id, hour, minute, tz_name in settings:
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        now_local = datetime.datetime.now(tz)
        today_str = now_local.date().isoformat()

        data = get_daily_verse_for_date(today_str)
        if not data:
            continue

        book_name = BOOK_NUM_TO_NAME.get(data["book"], f"Livre {data['book']}")
        ref = f"{book_name} {data['chapter']}:{data['verse']}"
        text = data["text"].strip()

        embed = make_bible_embed(
            title=f"Verset du jour — {ref}",
            description=text
        )

        channel = bot.get_channel(channel_id)
        if channel is None:
            continue
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Erreur d'envoi verset du jour pour guild {guild_id}: {e}")


def schedule_all_jobs():
    scheduler.remove_all_jobs()
    settings = get_all_daily_verse_settings()
    for guild_id, channel_id, hour, minute, tz_name in settings:
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC

        trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
        scheduler.add_job(send_daily_verses, trigger)


# =========================
# Events Discord
# =========================

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    await bot.sync_commands()
    print("Commandes slash synchronisées.")
    schedule_all_jobs()
    if not scheduler.running:
        scheduler.start()
        print("Scheduler démarré.")


# =========================
# Commandes
# =========================

@bot.slash_command(
    name="verse",
    description="Affiche un verset de la Bible."
)
@option(
    "livre",
    description="Ex: Jean, Romains, Psaumes...",
    required=True,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
@option(
    "chapitre",
    description="Numéro de chapitre, ex: 3",
    required=True,
    autocomplete=basic_autocomplete(get_chapter_suggestions)
)
@option(
    "verset",
    description="Numéro de verset, ex: 16",
    required=True,
    autocomplete=basic_autocomplete(get_verse_suggestions)
)
async def bible(
    ctx: discord.ApplicationContext,
    livre: str,
    chapitre: str,
    verset: str
):
    await ctx.defer()

    key = livre.strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        embed = discord.Embed(
            title="Erreur",
            description=f"Livre non reconnu : `{livre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    try:
        chapitre_int = int(chapitre)
    except ValueError:
        embed = discord.Embed(
            title="Erreur",
            description=f"Chapitre invalide : `{chapitre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    try:
        verset_int = int(verset)
    except ValueError:
        embed = discord.Embed(
            title="Erreur",
            description=f"Verset invalide : `{verset}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    text = get_verse_from_db(book_num, chapitre_int, verset_int)
    if not text:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucun verset trouvé pour : `{livre} {chapitre_int}:{verset_int}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(book_num, livre.strip())
    ref = f"{book_name} {chapitre_int}:{verset_int}"

    embed = make_bible_embed(
        title=ref,
        description=text.strip()
    )
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="infobook",
    description="Affiche le nombre de chapitres d'un livre."
)
@option(
    "livre",
    description="Ex: Jean, Romains, Psaumes...",
    required=True,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
async def info_book(
    ctx: discord.ApplicationContext,
    livre: str
):
    await ctx.defer()

    key = livre.strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        embed = discord.Embed(
            title="Erreur",
            description=f"Livre non reconnu : `{livre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    nb_chapitres, _ = get_book_stats(book_num)
    if nb_chapitres == 0:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucune donnée trouvée pour le livre `{livre}`.",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(book_num, livre.strip())

    embed = discord.Embed(
        title=f"{book_name} — Informations",
        description=f"Chapitres : **{nb_chapitres}**",
        color=0x3498db
    )
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="infoverse",
    description="Affiche le nombre de versets pour un livre et un chapitre donnés."
)
@option(
    "livre",
    description="Ex: Jean, Romains, Psaumes...",
    required=True,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
@option(
    "chapitre",
    description="Numéro de chapitre, ex: 3",
    required=True,
    autocomplete=basic_autocomplete(get_chapter_suggestions)
)
async def info_verse(
    ctx: discord.ApplicationContext,
    livre: str,
    chapitre: str
):
    await ctx.defer()

    key = livre.strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        embed = discord.Embed(
            title="Erreur",
            description=f"Livre non reconnu : `{livre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    try:
        chapitre_int = int(chapitre)
    except ValueError:
        embed = discord.Embed(
            title="Erreur",
            description=f"Chapitre invalide : `{chapitre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    nb_versets = get_verse_count_for_chapter(book_num, chapitre_int)
    if nb_versets == 0:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucun verset trouvé pour {livre} {chapitre_int}.",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(book_num, livre.strip())
    title = f"{book_name} {chapitre_int}"

    embed = discord.Embed(
        title=f"{title} — Informations",
        description=f"Versets : **{nb_versets}**",
        color=0x3498db
    )
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="search",
    description="Cherche un texte dans la Bible et affiche les références."
)
@option(
    "texte",
    description="Une partie du verset, ex: Dieu a tant aimé le monde",
    required=True
)
@option(
    "livre",
    description="(Optionnel) ex: Jean, Romains, Psaumes...",
    required=False,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
@option(
    "hardlimit",
    description="Nombre max de résultats à charger (1-501, défaut 100)",
    required=False
)
async def recherche(
    ctx: discord.ApplicationContext,
    texte: str,
    livre: str | None = None,
    hardlimit: int | None = None
):
    await ctx.defer()

    book_num = None
    livre_affiche = ""

    if livre:
        key = livre.strip().lower()
        book_num = BOOK_MAP.get(key)
        if book_num is None:
            embed = discord.Embed(
                title="Erreur",
                description=f"Livre non reconnu : `{livre}`",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return
        livre_affiche = f" dans {livre.strip()}"

    if hardlimit is None:
        hard_limit = 100
    else:
        hard_limit = max(1, min(hardlimit, 501))

    results, total = search_verses_by_text(texte, hard_limit=hard_limit, book_num=book_num)

    if not results:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucun verset trouvé contenant \"{texte}\"{livre_affiche}.",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    lines = []
    for r in results:
        book_name = BOOK_NUM_TO_NAME.get(r["book"], f"Livre {r['book']}")
        ref = f"{book_name} {r['chapter']}:{r['verse']}"
        snippet = r["text"].strip()

        block = f"**{ref}**\n{snippet}\n"
        lines.append(block)

    pages: List[str] = []
    current_lines: List[str] = []
    count_in_page = 0
    max_per_page = 5  # 5 versets par page

    for line in lines:
        block = line + "\n"
        if count_in_page >= max_per_page:
            pages.append("".join(current_lines).rstrip())
            current_lines = [block]
            count_in_page = 1
        else:
            current_lines.append(block)
            count_in_page += 1

    if current_lines:
        pages.append("".join(current_lines).rstrip())

    title = f"Résultats pour \"{texte}\"{livre_affiche}"

    embed = make_bible_embed(
        title=title + (f" (page 1/{len(pages)})" if len(pages) > 1 else ""),
        description=pages[0]
    )

    if total > len(results):
        embed.set_footer(text=f"{len(results)} premiers résultats sur {total} • Bible Louis Segond (1910)")
    else:
        embed.set_footer(text=f"{total} résultat(s) • Bible Louis Segond (1910)")

    if len(pages) > 1:
        view = ChapterPaginator(pages, title)
        await ctx.respond(embed=embed, view=view)
    else:
        await ctx.respond(embed=embed)


@bot.slash_command(
    name="chapter",
    description="Affiche un chapitre de la Bible."
)
@option(
    "livre",
    description="Ex: Jean, Romains, Psaumes...",
    required=True,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
@option(
    "chapitre",
    description="Numéro de chapitre, ex: 3",
    required=True,
    autocomplete=basic_autocomplete(get_chapter_suggestions)
)
async def chapitre_cmd(
    ctx: discord.ApplicationContext,
    livre: str,
    chapitre: str
):
    await ctx.defer()

    key = livre.strip().lower()
    book_num = BOOK_MAP.get(key)
    if book_num is None:
        embed = discord.Embed(
            title="Erreur",
            description=f"Livre non reconnu : `{livre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    try:
        chapitre_int = int(chapitre)
    except ValueError:
        embed = discord.Embed(
            title="Erreur",
            description=f"Chapitre invalide : `{chapitre}`",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    verses = get_chapter_from_db(book_num, chapitre_int)
    if not verses:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucun verset trouvé pour {livre} {chapitre_int}.",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(book_num, livre.strip())
    title = f"{book_name} {chapitre_int}"

    pages: List[str] = []
    current_lines: List[str] = []
    count_in_page = 0
    max_per_page = 10  # 10 versets par page

    for v in verses:
        line = f"{v['verse']}. {v['text'].strip()}\n"
        if count_in_page >= max_per_page:
            pages.append("".join(current_lines).rstrip())
            current_lines = [line]
            count_in_page = 1
        else:
            current_lines.append(line)
            count_in_page += 1

    if current_lines:
        pages.append("".join(current_lines).rstrip())

    embed = make_bible_embed(
        title=title + (f" (page 1/{len(pages)})" if len(pages) > 1 else ""),
        description=pages[0]
    )

    if len(pages) > 1:
        view = ChapterPaginator(pages, title)
        await ctx.respond(embed=embed, view=view)
    else:
        await ctx.respond(embed=embed)


@bot.slash_command(
    name="dailyverse",
    description="Affiche le verset du jour."
)
async def versetdujour(
    ctx: discord.ApplicationContext
):
    await ctx.defer()

    tz_name = "UTC"
    if ctx.guild:
        settings = get_all_daily_verse_settings()
        for guild_id, channel_id, hour, minute, tz in settings:
            if guild_id == ctx.guild.id:
                tz_name = tz
                break

    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC

    now_local = datetime.datetime.now(tz)
    today_str = now_local.date().isoformat()

    data = get_daily_verse_for_date(today_str)
    if not data:
        embed = discord.Embed(
            title="Erreur",
            description="Impossible de récupérer le verset du jour.",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(data["book"], f"Livre {data['book']}")
    ref = f"{book_name} {data['chapter']}:{data['verse']}"
    text = data["text"].strip()

    embed = make_bible_embed(
        title=f"Verset du jour — {ref}",
        description=text
    )
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="setdailyverse",
    description="Configure l'envoi automatique du verset du jour dans ce serveur."
)
@option(
    "heure",
    description="Heure (0-23) dans le fuseau choisi, ex: 8",
    required=True
)
@option(
    "minute",
    description="Minute (0-59), ex: 0",
    required=True
)
@option(
    "timezone",
    description="Fuseau horaire ex: Europe/Paris, America/Martinique",
    required=True,
    autocomplete=basic_autocomplete(get_timezone_suggestions)
)
async def set_versetdujour(
    ctx: discord.ApplicationContext,
    heure: int,
    minute: int,
    timezone: str
):
    await ctx.defer(ephemeral=True)

    if ctx.guild is None:
        await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return

    try:
        pytz.timezone(timezone)
    except Exception:
        await ctx.respond(f"Fuseau horaire invalide : `{timezone}`", ephemeral=True)
        return

    if not (0 <= heure <= 23 and 0 <= minute <= 59):
        await ctx.respond("Heure/minute invalides (0-23 pour heure, 0-59 pour minute).", ephemeral=True)
        return

    guild_id = ctx.guild.id
    channel_id = ctx.channel.id

    set_daily_verse_settings(guild_id, channel_id, heure, minute, timezone)
    schedule_all_jobs()

    await ctx.respond(
        f"Verset du jour configuré pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
        ephemeral=True
    )


@bot.slash_command(
    name="randomverse",
    description="Affiche un verset aléatoire de la Bible."
)
@option(
    "livre",
    description="(Optionnel) ex: Jean, Romains, Psaumes...",
    required=False,
    autocomplete=basic_autocomplete(get_book_suggestions)
)
async def verset_aleatoire(
    ctx: discord.ApplicationContext,
    livre: str | None = None
):
    await ctx.defer()

    book_num = None
    if livre:
        inv_map = {v.lower(): k for k, v in BOOK_NUM_TO_NAME.items()}
        book_num = inv_map.get(livre.strip().lower())

        if book_num is None:
            key = livre.strip().lower()
            book_num = BOOK_MAP.get(key)

        if book_num is None:
            embed = discord.Embed(
                title="Erreur",
                description=f"Livre non reconnu : `{livre}`",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

    data = get_random_verse(book_num=book_num)
    if not data:
        if livre:
            embed = discord.Embed(
                title="Aucun résultat",
                description=f"Aucun verset trouvé dans le livre `{livre}`.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="Erreur",
                description="Impossible de récupérer un verset aléatoire.",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
        return

    book_name = BOOK_NUM_TO_NAME.get(data["book"], f"Livre {data['book']}")
    ref = f"{book_name} {data['chapter']}:{data['verse']}"
    text = data["text"].strip()

    embed = make_bible_embed(
        title=f"Verset aléatoire — {ref}",
        description=text
    )
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="today",
    description="Affiche la célébration liturgique du jour (calendrier catholique)."
)
@option(
    "timezone",
    description="Fuseau horaire ex: Europe/Paris, America/Martinique (optionnel)",
    required=False,
    autocomplete=basic_autocomplete(get_timezone_suggestions)
)
async def today(
    ctx: discord.ApplicationContext,
    timezone: str | None = None
):
    await ctx.defer()

    if timezone:
        tz_name = timezone
    else:
        tz_name = "UTC"
        if ctx.guild:
            settings = get_all_daily_verse_settings()
            for guild_id, channel_id, hour, minute, tz in settings:
                if guild_id == ctx.guild.id:
                    tz_name = tz
                    break

    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC

    now_local = datetime.datetime.now(tz)
    today_local = now_local.date()

    saints, season_fr = get_saints_for_date(today_local)
    if not saints:
        embed = discord.Embed(
            title="Aucun résultat",
            description=f"Aucune célébration trouvée pour aujourd'hui ({today_local.isoformat()}).",
            color=0xe74c3c
        )
        await ctx.respond(embed=embed)
        return

    COLOUR_HEX = {
        "vert": 0x2ecc71,
        "blanc": 0xffffff,
        "rouge": 0xe74c3c,
        "violet": 0x9b59b6,
    }

    lines = []
    main_colour = None

    for s in saints:
        titre = s["title_fr"]
        rang = s["rank_fr"]
        couleur = s["colour_fr"]

        if rang and rang.lower() == "ferial":
            rang_affiche = "Jour de semaine ordinaire (sans fête particulière)"
        else:
            rang_affiche = rang

        if main_colour is None and couleur in COLOUR_HEX:
            main_colour = COLOUR_HEX[couleur]

        if rang_affiche:
            lines.append(f"• **{titre}** — {rang_affiche}")
        else:
            lines.append(f"• **{titre}**")

    desc = "\n".join(lines)

    if season_fr:
        desc += f"\n\n**{season_fr}**"

    embed_colour = main_colour if main_colour is not None else 0x3498db

    embed = discord.Embed(
        title=f"Célébration(s) du jour — {today_local.isoformat()}",
        description=desc,
        color=embed_colour
    )

    embed.set_footer(text=f"Fuseau horaire : {tz_name}")
    await ctx.respond(embed=embed)


@bot.slash_command(
    name="help",
    description="Affiche la liste des commandes."
)
async def biblehelp(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=False)

    lines = [
        "**Bible**",
        "• `/verse` — afficher un verset précis",
        "• `/chapter` — afficher un chapitre complet",
        "• `/search` — rechercher un passage à partir de mots ou d'une phrase",
        "• `/randomverse` — afficher un verset aléatoire (toute la Bible ou un livre précis)",
        "• `/dailyverse` — afficher le verset du jour",
        "• `/setdailyverse` — configurer l'envoi automatique du verset du jour dans ce salon",

        "",
        "**Infos liturgiques**",
        "• `/infobook` — afficher le nombre de chapitres d'un livre",
        "• `/infoverse` — afficher le nombre de versets d'un chapitre",
        "• `/today` — afficher les célébrations liturgiques catholiques du jour",
    ]

    embed = discord.Embed(
        title="Commandes",
        description="\n".join(lines),
        color=0x3498DB,
    )
    await ctx.respond(embed=embed, ephemeral=False)

# =========================
# Lancement du bot
# =========================

bot.run(TOKEN)
