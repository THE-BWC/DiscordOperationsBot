import random
import platform
import os
from typing import List

import discord
from discord.ext import tasks, commands

import settings
import bot_logger
import database

from Cogs.notifier_command import Notifier
from Cogs.operation_notification import Operation30Notifier, UpcomingOperationsNotifier

if settings.DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")


class DiscordBot(commands.Bot):
    notifier_30: Operation30Notifier
    notifier_upcoming: UpcomingOperationsNotifier

    intents = discord.Intents.default()
    command_prefix = '!'

    def __init__(self):
        self.intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or(self.command_prefix),
            intents=self.intents
        )
        self.logger = bot_logger.logger
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
        self.logger.info("Logged in as %s", self.user.name)
        self.logger.info("discord.py version: %s", discord.__version__)
        self.logger.info("Python version: %s", f"{platform.python_version()} ({platform.architecture()[0]})")
        self.logger.info("Running on %s", f"{platform.system()} {platform.release()} ({os.name})")
        self.logger.info("-------------------")
        self.status_task.start()
        self.database = database

        # Create notifiers
        self.notifier_30 = Operation30Notifier(self, self.config, self.logger)
        self.notifier_upcoming = UpcomingOperationsNotifier(self, self.config, self.logger)

        await self.add_cog(Notifier(self))


bot = DiscordBot()
bot.run(settings.DISCORD_BOT_TOKEN)
