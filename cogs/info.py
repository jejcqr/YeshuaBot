import discord
from discord import option
from discord.utils import basic_autocomplete

from config import BOOK_MAP, BOOK_NUM_TO_NAME
from database import get_book_stats, get_verse_count_for_chapter
from bible_utils import get_book_suggestions, get_chapter_suggestions


class InfoCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="infobook",
        description="Affiche le nombre de chapitres d'un livre."
    )
    @option(
        "livre",
        description="Ex: Jean, Romains, Psaumes...",
        required=True,
        autocomplete=basic_autocomplete(get_book_suggestions)
    )
    async def infobook(
        self,
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

    @discord.slash_command(
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
    async def infoverse(
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


def setup(bot: discord.Bot):
    bot.add_cog(InfoCog(bot))
