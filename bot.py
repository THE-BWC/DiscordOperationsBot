import random
import platform
import os

import cron_descriptor
import discord
from discord.ext import tasks, commands

import settings
import bot_logger
import database

from Cogs.notifier_command import Notifier, CronChangedEventArgs, CronRemovedEventArgs
from Cogs.operation_notification import Operation30Notifier, UpcomingOperationsNotifier

if settings.DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")


class DiscordBot(commands.Bot):
    notifier_30: Operation30Notifier
    notifier_upcoming: UpcomingOperationsNotifier

    intents = discord.Intents.default()
    command_prefix = '!'

    def __init__(self) -> None:
        self.intents.message_content = True
        super().__init__(command_prefix=self.command_prefix,
            intents=self.intents
        )
        self.logger = bot_logger.logger
        self.config = settings
        self.settings = settings.Settings()
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
        self.notifier_30 = Operation30Notifier(self, self.settings, self.logger)
        self.notifier_upcoming = UpcomingOperationsNotifier(self, self.settings, self.logger)

        # Setup commands
        notifier_command = Notifier(self, self.settings)
        await self.add_cog(notifier_command)
        notifier_command.on_cron_changed += self.on_cron_changed
        notifier_command.on_cron_removed += self.on_cron_removed

        # Trigger sync to update slash commands
        guild = discord.Object(id=settings.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_cron_removed(self, interaction: discord.Interaction, args: CronRemovedEventArgs) -> None:
        """Event callback used to modify the settings object to remove cron entries"""
        opsec_text = "OPSEC" if args.is_opsec else "PUBLIC"
        if not self.settings.remove_notification(args.game_id, args.is_opsec, args.channel_id):
            await interaction.response.send_message(f"Could not find {opsec_text} notification for game {args.game_id}")
            return

        self.notifier_upcoming.stop_task(args.game_id, args.is_opsec, args.channel_id)
        await interaction.response.send_message(f"{opsec_text} notification removed for game {args.game_id}")

    async def on_cron_changed(self, interaction: discord.Interaction, args: CronChangedEventArgs) -> None:
        """Event callback used to modify the settings object to add or update cron entries"""
        # Because here we will need a mix of both the crontab object AND the string, we should get the string instead
        # of the cron object and just recreate it
        is_new = self.settings.update_notification(args.game_id, args.is_opsec, args.channel_id, args.cron)
        self.notifier_upcoming.update_task(args.game_id, args.is_opsec, args.channel_id, args.cron)

        opsec_text = "OPSEC" if args.is_opsec else "PUBLIC"
        msg = f"Added {opsec_text} notification" if is_new == 1 else f"Updated {opsec_text} notification"
        cron_text = cron_descriptor.get_description(args.cron)
        await interaction.response.send_message(f"{msg}: {cron_text}")


bot = DiscordBot()
bot.run(settings.DISCORD_BOT_TOKEN)
