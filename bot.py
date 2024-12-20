import logging
import random
from typing import Any

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context

import settings
from database import bot_db, xen_db


log = logging.getLogger(__name__)

initial_extensions = [
    "cogs.scheduled_events",
]

# Add Sentry
if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.RELEASE,
        integrations=[sentry_logging],
    )


class DiscordBot(commands.Bot):
    user: discord.ClientUser
    bot_db: bot_db
    xen_db: xen_db
    logging_handler: Any
    bot_app_info: discord.AppInfo

    def __init__(self):
        self.uptime = None
        allowed_mentions = discord.AllowedMentions(
            everyone=False, roles=True, users=True
        )
        intents = discord.Intents(
            guild_scheduled_events=True,
        )
        super().__init__(
            command_prefix="",
            allowed_mentions=allowed_mentions,
            intents=intents,
        )

        self.client_id = settings.DISCORD_CLIENT_ID
        self.config = settings
        self.settings = settings.Settings()
        self.bot_db = bot_db
        self.xen_db = xen_db

    async def setup_hook(self) -> None:
        self.bot_app_info = await self.application_info()
        self.owner_id = self.bot_app_info.owner.id

        # Start status task
        self.status_task.start()

        # Load cogs
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception:
                log.exception(f"Failed to load extension {extension}.")

    async def on_command_error(
        self, ctx: Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("Sorry. This command is disabled and cannot be used.")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                log.exception("In %s:", ctx.command.qualified_name, exc_info=original)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(str(error))

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        log.info("Ready: %s (ID: %s)", self.user, self.user.id)

    async def start(self) -> None:
        await super().start(settings.DISCORD_BOT_TOKEN)

    # async def setup_hook(self) -> None:
    #     # Bot information
    #     self.logger.info("Logged in as %s", self.user.name)
    #     self.logger.info("discord.py version: %s", discord.__version__)
    #     self.logger.info(
    #         "Python version: %s",
    #         f"{platform.python_version()} ({platform.architecture()[0]})",
    #     )
    #     self.logger.info(
    #         "Running on %s", f"{platform.system()} {platform.release()} ({os.name})"
    #     )
    #     self.logger.info("-------------------")
    #
    #     # Start status task
    #     self.status_task.start()
    #
    #     # Create notifiers
    #     self.notifier_30 = Operation30Notifier(self, self.settings, self.logger)
    #     self.notifier_upcoming = UpcomingOperationsNotifier(
    #         self, self.settings, self.logger
    #     )
    #
    #     # Setup commands
    #     notifier_command = Notifier(self, self.settings)
    #     await self.add_cog(notifier_command)
    #     notifier_command.on_cron_changed += self.on_cron_changed
    #     notifier_command.on_cron_removed += self.on_cron_removed
    #
    #     # Trigger sync to update slash commands
    #     guild = discord.Object(id=settings.GUILD_ID)
    #     self.tree.copy_global_to(guild=guild)
    #     await self.tree.sync(guild=guild)

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        statuses = self.config.STATUS
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name=random.choice(statuses)
            ),
        )

    @status_task.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    # async def on_cron_removed(
    #     self, interaction: discord.Interaction, args: CronRemovedEventArgs
    # ) -> None:
    #     """Event callback used to modify the settings object to remove cron entries"""
    #     opsec_text = "OPSEC" if args.is_opsec else "PUBLIC"
    #     if not self.settings.remove_notification(
    #         args.game_id, args.is_opsec, args.channel_id
    #     ):
    #         await interaction.response.send_message(
    #             f"Could not find {opsec_text} notification for game {args.game_id}"
    #         )
    #         return
    #
    #     self.notifier_upcoming.stop_task(args.game_id, args.is_opsec, args.channel_id)
    #     await interaction.response.send_message(
    #         f"{opsec_text} notification removed for game {args.game_id}"
    #     )
    #
    # async def on_cron_changed(
    #     self, interaction: discord.Interaction, args: CronChangedEventArgs
    # ) -> None:
    #     """Event callback used to modify the settings object to add or update cron entries"""
    #     # Because here we will need a mix of both the crontab object AND the string, we should get the string instead
    #     # of the cron object and just recreate it
    #     is_new = self.settings.update_notification(
    #         args.game_id, args.is_opsec, args.channel_id, args.cron
    #     )
    #     self.notifier_upcoming.update_task(
    #         args.game_id, args.is_opsec, args.channel_id, args.cron
    #     )
    #
    #     opsec_text = "OPSEC" if args.is_opsec else "PUBLIC"
    #     msg = (
    #         f"Added {opsec_text} notification"
    #         if is_new == 1
    #         else f"Updated {opsec_text} notification"
    #     )
    #     cron_text = cron_descriptor.get_description(args.cron)
    #     await interaction.response.send_message(f"{msg}: {cron_text}")
