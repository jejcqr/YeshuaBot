import discord


class HelpCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="help",
        description="Affiche la liste des commandes."
    )
    async def help(self, ctx: discord.ApplicationContext):
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


def setup(bot: discord.Bot):
    bot.add_cog(HelpCog(bot))
