import random
import platform
import os

import settings
import botLogger
import database
import discord

from discord.ext import tasks


if settings.DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")


class DiscordBot(discord.Client):
    def __init__(self):
        super().__init__(
            intents=discord.Intents.default()
        )
        self.logger = botLogger.logger
        self.config = settings
        self.database = None

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        statuses = self.config.STATUS
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=random.choice(statuses)
            )
        )

    @status_task.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(f"Running on {platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------")
        self.status_task.start()
        self.database = database
        await self.create_operation_embed()

    async def create_operation_embed(self):
        channels = self.config.OPSEC_CHANNELS_MAP
        for game, channel in channels.items():
            text_channel = await self.fetch_channel(channel)

            if text_channel is None:
                self.logger.error(f"Channel {text_channel} not found.")
                return

            operation_model = self.database.Operation
            operations = operation_model.select().where(
                operation_model.game_id == game,
                operation_model.is_opsec == True,
                operation_model.is_completed == False
            )

            embed = discord.Embed(
                title="OPSEC Operations",
                color=discord.Color.red()
            )
            for operation in operations:
                embed.add_field(
                    name=operation.operation_name,
                    value=f"Start: <t:{operation.date_start}>\nEnd: <t:{operation.date_end}>",
                    inline=False
                )
            # Get current timestamp
            timestamp = discord.utils.utcnow()
            embed.set_footer(text=f"Last updated: {timestamp}")
            await text_channel.send(embed=embed)


bot = DiscordBot()
bot.run(settings.DISCORD_BOT_TOKEN)
