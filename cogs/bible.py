import datetime
from typing import List

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz
from apscheduler.triggers.cron import CronTrigger

from config import BOOK_MAP, BOOK_NUM_TO_NAME
from database import (
    get_verse_from_db,
    search_verses_by_text,
    get_chapter_from_db,
    get_daily_verse_for_date,
    get_random_verse,
    set_daily_verse_settings,
    get_all_daily_verse_settings,
    delete_daily_verse_settings,
)
from bible_utils import (
    make_bible_embed,
    ChapterPaginator,
    get_book_suggestions,
    get_timezone_suggestions,
    get_chapter_suggestions,
    get_verse_suggestions,
)


class BibleCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.schedule_all_jobs()
        if not self.bot.scheduler.running:
            self.bot.scheduler.start()
            print("Scheduler démarré.")

    def schedule_all_jobs(self):
        settings = get_all_daily_verse_settings()
        for guild_id, channel_id, hour, minute, tz_name in settings:
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC

            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.bot.scheduler.add_job(
                self.send_daily_verses, trigger,
                id=f"verse-{guild_id}", replace_existing=True
            )

    async def send_daily_verses(self):
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

            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Erreur d'envoi verset du jour pour guild {guild_id}: {e}")

    @discord.slash_command(
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
        self,
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

    @discord.slash_command(
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
    async def search(
        self,
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
            view.message = await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)

    @discord.slash_command(
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
    async def chapter(
        self,
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
            view.message = await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)

    @discord.slash_command(
        name="dailyverse",
        description="Affiche le verset du jour."
    )
    async def dailyverse(
        self,
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

    @discord.slash_command(
        name="setdailyverse",
        default_member_permissions=discord.Permissions(manage_guild=True),
        contexts={discord.InteractionContextType.guild},
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
    async def setdailyverse(
        self,
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
        self.schedule_all_jobs()

        await ctx.respond(
            f"Verset du jour configuré pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
            ephemeral=True
        )

    @discord.slash_command(
        name="removedailyverse",
        default_member_permissions=discord.Permissions(manage_guild=True),
        contexts={discord.InteractionContextType.guild},
        description="Annule l'envoi automatique du verset du jour sur ce serveur."
    )
    async def removedailyverse(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        removed = delete_daily_verse_settings(ctx.guild.id)
        try:
            self.bot.scheduler.remove_job(f"verse-{ctx.guild.id}")
        except Exception:
            pass

        if removed:
            await ctx.respond("Envoi automatique du verset du jour désactivé.", ephemeral=True)
        else:
            await ctx.respond("Aucune configuration active pour ce serveur.", ephemeral=True)

    @discord.slash_command(
        name="randomverse",
        description="Affiche un verset aléatoire de la Bible."
    )
    @option(
        "livre",
        description="(Optionnel) ex: Jean, Romains, Psaumes...",
        required=False,
        autocomplete=basic_autocomplete(get_book_suggestions)
    )
    async def randomverse(
        self,
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


def setup(bot: discord.Bot):
    bot.add_cog(BibleCog(bot))
