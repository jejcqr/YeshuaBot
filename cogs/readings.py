import datetime

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz

from database import get_all_daily_verse_settings
from bible_utils import ChapterPaginator, get_timezone_suggestions
from liturgical_calendar import COLOUR_HEX
from liturgical_readings import get_daily_readings, get_gospel


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


class ReadingsCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

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

        lecture = data["lecture"]
        infos = data["informations"]

        couleur = (infos.get("couleur") or "").lower()
        embed_colour = COLOUR_HEX.get(couleur, 0x3498db)

        title = f"Évangile du jour — {lecture['ref']}"
        description = lecture["contenu"]
        if lecture["titre"]:
            description = f"*{lecture['titre']}*\n\n{description}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_colour
        )

        jour_nom = _liturgical_day_title(infos)
        embed.set_footer(text=f"{jour_nom} • Fuseau horaire : {tz_name}")

        await ctx.respond(embed=embed)

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

        infos = data["informations"]
        couleur = (infos.get("couleur") or "").lower()
        embed_colour = COLOUR_HEX.get(couleur, 0x3498db)

        jour_nom = _liturgical_day_title(infos)

        pages = []
        for lecture in data["lectures"]:
            header = f"**{lecture['label']} — {lecture['ref']}**"
            if lecture["titre"]:
                header += f"\n*{lecture['titre']}*"
            pages.append(f"{header}\n\n{lecture['contenu']}")

        title = jour_nom + (f" (page 1/{len(pages)})" if len(pages) > 1 else "")

        embed = discord.Embed(
            title=title,
            description=pages[0],
            color=embed_colour
        )
        embed.set_footer(text=f"Fuseau horaire : {tz_name}")

        if len(pages) > 1:
            view = ChapterPaginator(pages, jour_nom, footer_text=f"Fuseau horaire : {tz_name}", color=embed_colour)
            await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)


def setup(bot: discord.Bot):
    bot.add_cog(ReadingsCog(bot))
