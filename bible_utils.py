from typing import List

import discord
import pytz

from config import BOOK_MAP, BOOK_NUM_TO_NAME
from database import get_max_chapter_for_book, get_verses_numbers_for_chapter


def make_bible_embed(title: str, description: str, color: int = 0x3498db) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Bible Louis Segond (1910)")
    return embed


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


class ChapterPaginator(discord.ui.View):
    def __init__(
        self,
        pages: List[str],
        title: str,
        footer_text: str = "Bible Louis Segond (1910)",
        color: int = 0x3498db,
    ):
        super().__init__(timeout=None)  # aucun timeout
        self.pages = pages
        self.title = title
        self.current = 0
        self.footer_text = footer_text
        self.color = color

    async def update_message(self, interaction: discord.Interaction):
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current >= len(self.pages) - 1

        embed = discord.Embed(
            title=self.title + f" (page {self.current + 1}/{len(self.pages)})",
            description=self.pages[self.current],
            color=self.color,
        )
        embed.set_footer(text=self.footer_text)
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
