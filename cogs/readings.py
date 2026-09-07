import datetime

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz
from apscheduler.triggers.cron import CronTrigger

from database import (
    get_all_daily_verse_settings,
    set_daily_gospel_settings,
    get_all_daily_gospel_settings,
    delete_daily_gospel_settings,
    set_daily_readings_settings,
    get_all_daily_readings_settings,
    delete_daily_readings_settings,
)
from bible_utils import ChapterPaginator, get_timezone_suggestions
from liturgical_readings import get_daily_readings, get_gospel

EMBED_COLOR = 0x3498db


def _resolve_timezone(ctx: discord.ApplicationContext, timezone: str | None) -> str:
    if timezone:
        return timezone

    tz_name = "UTC"
    if ctx.guild:
        settings = get_all_daily_verse_settings()
        for guild_id, channel_id, hour, minute, tz in settings:
            if guild_id == ctx.guild.id:
                tz_name = tz
                break
    return tz_name


def _liturgical_day_title(infos: dict) -> str:
    ligne1 = (infos.get("ligne1") or "").strip()
    ligne2 = (infos.get("ligne2") or "").strip()

    if not ligne1:
        return infos.get("jour_liturgique_nom") or "Lectures du jour"

    title = ligne1[0].upper() + ligne1[1:]
    if ligne2 and ligne2.lower() != "de la férie":
        title += f" — {ligne2}"
    return title


def _today_for_timezone(tz_name: str) -> datetime.date:
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.UTC
    return datetime.datetime.now(tz).date()


def _build_gospel_embed(data: dict, tz_name: str) -> discord.Embed:
    lecture = data["lecture"]
    infos = data["informations"]

    title = f"Évangile du jour — {lecture['ref']}"
    description = lecture["contenu"]
    if lecture["titre"]:
        description = f"*{lecture['titre']}*\n\n{description}"

    embed = discord.Embed(title=title, description=description, color=EMBED_COLOR)

    jour_nom = _liturgical_day_title(infos)
    embed.set_footer(text=f"{jour_nom} • Fuseau horaire : {tz_name}")
    return embed


def _build_readings_pages(data: dict) -> tuple[list[str], str]:
    infos = data["informations"]
    jour_nom = _liturgical_day_title(infos)

    pages = []
    for lecture in data["lectures"]:
        header = f"**{lecture['label']} — {lecture['ref']}**"
        if lecture["titre"]:
            header += f"\n*{lecture['titre']}*"
        pages.append(f"{header}\n\n{lecture['contenu']}")

    return pages, jour_nom


class ReadingsCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.schedule_all_jobs()

    def schedule_all_jobs(self):
        for guild_id, channel_id, hour, minute, tz_name in get_all_daily_gospel_settings():
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.bot.scheduler.add_job(
                self.send_daily_gospel, trigger,
                id=f"gospel-{guild_id}", replace_existing=True,
                kwargs={"channel_id": channel_id, "tz_name": tz_name}
            )

        for guild_id, channel_id, hour, minute, tz_name in get_all_daily_readings_settings():
            try:
                tz = pytz.timezone(tz_name)
            except Exception:
                tz = pytz.UTC
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            self.bot.scheduler.add_job(
                self.send_daily_readings, trigger,
                id=f"readings-{guild_id}", replace_existing=True,
                kwargs={"channel_id": channel_id, "tz_name": tz_name}
            )

    async def send_daily_gospel(self, channel_id: int, tz_name: str):
        today_local = _today_for_timezone(tz_name)

        data = get_gospel(today_local)
        if not data:
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        try:
            await channel.send(embed=_build_gospel_embed(data, tz_name))
        except Exception as e:
            print(f"Erreur d'envoi Évangile du jour pour channel {channel_id}: {e}")

    async def send_daily_readings(self, channel_id: int, tz_name: str):
        today_local = _today_for_timezone(tz_name)

        data = get_daily_readings(today_local)
        if not data:
            return

        pages, jour_nom = _build_readings_pages(data)
        embed = discord.Embed(
            title=jour_nom + (f" (page 1/{len(pages)})" if len(pages) > 1 else ""),
            description=pages[0],
            color=EMBED_COLOR
        )
        embed.set_footer(text=f"Fuseau horaire : {tz_name}")

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        try:
            if len(pages) > 1:
                view = ChapterPaginator(pages, jour_nom, footer_text=f"Fuseau horaire : {tz_name}", color=EMBED_COLOR)
                await channel.send(embed=embed, view=view)
            else:
                await channel.send(embed=embed)
        except Exception as e:
            print(f"Erreur d'envoi lectures du jour pour channel {channel_id}: {e}")

    @discord.slash_command(
        name="gospel",
        description="Affiche l'Évangile du jour (lectures liturgiques)."
    )
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique (optionnel)",
        required=False,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def gospel(
        self,
        ctx: discord.ApplicationContext,
        timezone: str | None = None
    ):
        await ctx.defer()

        tz_name = _resolve_timezone(ctx, timezone)
        today_local = _today_for_timezone(tz_name)

        data = get_gospel(today_local)
        if not data:
            embed = discord.Embed(
                title="Aucun résultat",
                description=f"Impossible de récupérer l'Évangile du jour ({today_local.isoformat()}).",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        await ctx.respond(embed=_build_gospel_embed(data, tz_name))

    @discord.slash_command(
        name="readings",
        description="Affiche les lectures complètes de la messe du jour."
    )
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique (optionnel)",
        required=False,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def readings(
        self,
        ctx: discord.ApplicationContext,
        timezone: str | None = None
    ):
        await ctx.defer()

        tz_name = _resolve_timezone(ctx, timezone)
        today_local = _today_for_timezone(tz_name)

        data = get_daily_readings(today_local)
        if not data:
            embed = discord.Embed(
                title="Aucun résultat",
                description=f"Impossible de récupérer les lectures du jour ({today_local.isoformat()}).",
                color=0xe74c3c
            )
            await ctx.respond(embed=embed)
            return

        pages, jour_nom = _build_readings_pages(data)
        title = jour_nom + (f" (page 1/{len(pages)})" if len(pages) > 1 else "")

        embed = discord.Embed(title=title, description=pages[0], color=EMBED_COLOR)
        embed.set_footer(text=f"Fuseau horaire : {tz_name}")

        if len(pages) > 1:
            view = ChapterPaginator(pages, jour_nom, footer_text=f"Fuseau horaire : {tz_name}", color=EMBED_COLOR)
            await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)

    @discord.slash_command(
        name="setdailygospel",
        description="Configure l'envoi automatique de l'Évangile du jour dans ce salon."
    )
    @option("heure", description="Heure (0-23) dans le fuseau choisi, ex: 8", required=True)
    @option("minute", description="Minute (0-59), ex: 0", required=True)
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique",
        required=True,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def setdailygospel(
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

        set_daily_gospel_settings(ctx.guild.id, ctx.channel.id, heure, minute, timezone)
        self.schedule_all_jobs()

        await ctx.respond(
            f"Évangile du jour configuré pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
            ephemeral=True
        )

    @discord.slash_command(
        name="removedailygospel",
        description="Annule l'envoi automatique de l'Évangile du jour sur ce serveur."
    )
    async def removedailygospel(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        removed = delete_daily_gospel_settings(ctx.guild.id)
        try:
            self.bot.scheduler.remove_job(f"gospel-{ctx.guild.id}")
        except Exception:
            pass

        if removed:
            await ctx.respond("Envoi automatique de l'Évangile du jour désactivé.", ephemeral=True)
        else:
            await ctx.respond("Aucune configuration active pour ce serveur.", ephemeral=True)

    @discord.slash_command(
        name="setdailyreadings",
        description="Configure l'envoi automatique des lectures du jour dans ce salon."
    )
    @option("heure", description="Heure (0-23) dans le fuseau choisi, ex: 8", required=True)
    @option("minute", description="Minute (0-59), ex: 0", required=True)
    @option(
        "timezone",
        description="Fuseau horaire ex: Europe/Paris, America/Martinique",
        required=True,
        autocomplete=basic_autocomplete(get_timezone_suggestions)
    )
    async def setdailyreadings(
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

        set_daily_readings_settings(ctx.guild.id, ctx.channel.id, heure, minute, timezone)
        self.schedule_all_jobs()

        await ctx.respond(
            f"Lectures du jour configurées pour ce salon à {heure:02d}:{minute:02d} ({timezone}).",
            ephemeral=True
        )

    @discord.slash_command(
        name="removedailyreadings",
        description="Annule l'envoi automatique des lectures du jour sur ce serveur."
    )
    async def removedailyreadings(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.respond("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        removed = delete_daily_readings_settings(ctx.guild.id)
        try:
            self.bot.scheduler.remove_job(f"readings-{ctx.guild.id}")
        except Exception:
            pass

        if removed:
            await ctx.respond("Envoi automatique des lectures du jour désactivé.", ephemeral=True)
        else:
            await ctx.respond("Aucune configuration active pour ce serveur.", ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(ReadingsCog(bot))
