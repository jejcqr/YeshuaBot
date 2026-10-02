import hashlib
import random

import mysql.connector
from mysql.connector import Error

from config import DB_CONFIG


# Tables de réglages créées au démarrage si elles n'existent pas encore.
SETTINGS_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS daily_verse_settings (
        guild_id   BIGINT UNSIGNED PRIMARY KEY,
        channel_id BIGINT UNSIGNED NOT NULL,
        hour       TINYINT UNSIGNED NOT NULL,
        minute     TINYINT UNSIGNED NOT NULL,
        timezone   VARCHAR(64) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_gospel_settings (
        guild_id   BIGINT UNSIGNED PRIMARY KEY,
        channel_id BIGINT UNSIGNED NOT NULL,
        hour       TINYINT UNSIGNED NOT NULL,
        minute     TINYINT UNSIGNED NOT NULL,
        timezone   VARCHAR(64) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS daily_readings_settings (
        guild_id   BIGINT UNSIGNED PRIMARY KEY,
        channel_id BIGINT UNSIGNED NOT NULL,
        hour       TINYINT UNSIGNED NOT NULL,
        minute     TINYINT UNSIGNED NOT NULL,
        timezone   VARCHAR(64) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def ensure_settings_tables():
    cnx = mysql.connector.connect(**DB_CONFIG)
    try:
        cursor = cnx.cursor()
        for statement in SETTINGS_TABLES:
            cursor.execute(statement)
        cnx.commit()
        cursor.close()
    finally:
        cnx.close()


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


def delete_daily_verse_settings(guild_id: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("DELETE FROM daily_verse_settings WHERE guild_id = %s", (guild_id,))
        cnx.commit()
        return cursor.rowcount > 0
    except Error as e:
        print("Erreur MySQL (delete verse settings):", e)
        return False
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def set_daily_gospel_settings(guild_id: int, channel_id: int, hour: int, minute: int, timezone: str):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO daily_gospel_settings (guild_id, channel_id, hour, minute, timezone)
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
        print("Erreur MySQL (set gospel settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_all_daily_gospel_settings():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT guild_id, channel_id, hour, minute, timezone FROM daily_gospel_settings")
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print("Erreur MySQL (get gospel settings):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def delete_daily_gospel_settings(guild_id: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("DELETE FROM daily_gospel_settings WHERE guild_id = %s", (guild_id,))
        cnx.commit()
        return cursor.rowcount > 0
    except Error as e:
        print("Erreur MySQL (delete gospel settings):", e)
        return False
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def set_daily_readings_settings(guild_id: int, channel_id: int, hour: int, minute: int, timezone: str):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO daily_readings_settings (guild_id, channel_id, hour, minute, timezone)
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
        print("Erreur MySQL (set readings settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_all_daily_readings_settings():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT guild_id, channel_id, hour, minute, timezone FROM daily_readings_settings")
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print("Erreur MySQL (get readings settings):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def delete_daily_readings_settings(guild_id: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("DELETE FROM daily_readings_settings WHERE guild_id = %s", (guild_id,))
        cnx.commit()
        return cursor.rowcount > 0
    except Error as e:
        print("Erreur MySQL (delete readings settings):", e)
        return False
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass
