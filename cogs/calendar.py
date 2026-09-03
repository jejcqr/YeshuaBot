import datetime

import discord
from discord import option
from discord.utils import basic_autocomplete
import pytz

from database import get_all_daily_verse_settings
from bible_utils import get_timezone_suggestions
from liturgical_calendar import get_saints_for_date


class CalendarCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
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
        self,
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


def setup(bot: discord.Bot):
    bot.add_cog(CalendarCog(bot))
