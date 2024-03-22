import discord
from discord import app_commands
from discord.ext import commands
import crontab
from cron_descriptor import get_description


class Notifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_cron_changed(self, cron):
        return cron

    @app_commands.command()
    async def notifier(self, interaction: discord.Interaction, game_id: int, cron: str):
        if game_id == 0:
            await interaction.response.send_message("The provided game id is not valid")
            return

        try:
            schedule = crontab.CronTab(cron)
            await self.on_cron_changed(schedule)

            descriptor = get_description(cron)
            await interaction.response.send_message(f"Schedule changed: {descriptor}")
        except ValueError as e:
            await interaction.response.send_message(f"Invalid cron string: {e}")
            return
