from typing import Callable

import cron_descriptor
import crontab
import discord
from discord import app_commands
from discord.ext import commands

from settings import Settings


class Event:
    """Base event class"""
    callbacks: [Callable]

    def __init__(self) -> None:
        self.callbacks = []

    def __add__(self, other: Callable):
        if other is None:
            raise ValueError("Cannot add None to event")

        self.callbacks.append(other)
        return self

    def __sub__(self, other: Callable):
        if other is None:
            raise ValueError("Cannot remove None event")

        self.callbacks.remove(other)
        return self


class CronChangedEventArgs:
    game_id: int
    channel_id: int
    is_opsec: int
    cron: str

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if getattr(self, k):
                setattr(self, k, v)


class CronChangedEvent(Event):
    async def trigger(self, interaction: discord.Interaction, game_id: int, is_opsec: int, channel_id: int, cron: str) -> None:
        args = CronChangedEventArgs(game_id=game_id, channel_id=channel_id, is_opsec=is_opsec, cron=cron)
        for callback in self.callbacks:
            await callback(interaction, args)


class CronRemovedEventArgs:
    game_id: int
    channel_id: int
    is_opsec: int

    def __init__(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if getattr(self, k):
                setattr(self, k, v)


class CronRemovedEvent(Event):
    async def trigger(self, interaction: discord.Interaction, game_id: int, is_opsec: int, channel_id: int) -> None:
        args = CronRemovedEventArgs(game_id=game_id, is_opsec=is_opsec, channel_id=channel_id)
        for callback in self.callbacks:
            await callback(interaction, args)


class Notifier(commands.Cog):
    on_cron_changed: CronChangedEvent
    on_cron_removed: CronRemovedEvent

    def __init__(self, bot: commands.Bot, config: Settings) -> None:
        self.bot = bot
        self.config = config
        # Use these events to setting modifications from within this class, and instead leave that to the one
        # responsible for it
        self.on_cron_changed = CronChangedEvent()
        self.on_cron_removed = CronRemovedEvent()

    @app_commands.command(description="Display current notifications in this channel")
    async def notification_list(self, interaction: discord.Interaction) -> None:
        notifications = self.config.get_channel_notifications(interaction.channel_id)
        if not notifications:
            await interaction.response.send_message("There are no notifications in this channel")
            return

        pretty_notifications = [
            (
                game_id,
                "OPSEC" if is_opsec == self.config.OPSEC else "PUBLIC",
                cron_descriptor.get_description(cron)
             ) for game_id, is_opsec, cron in notifications
        ]
        message_lines = [f"Game: {game_id} - {opsec}: {cron_str}" for game_id, opsec, cron_str in pretty_notifications]
        message = "\n".join(message_lines)
        await interaction.response.send_message(message)

    @app_commands.command(description="Remove the notification with the provided arguments from this channel")
    async def notification_remove(self, interaction:discord.Interaction, game_id: int, is_opsec: bool) -> None:
        if not await self.validate_game_id(interaction, game_id):
            return

        await self.on_cron_removed.trigger(interaction, game_id, int(is_opsec), interaction.channel_id)

    @app_commands.command(description="Add or update a notification in this channel. Google `cron` for help on valid values.")
    async def notification(self, interaction: discord.Interaction, game_id: int, is_opsec: bool, cron_str: str) -> None:
        if not await self.validate_game_id(interaction, game_id):
            return

        try:
            # Validate our cron string here instead of failing down the pipeline
            crontab.CronTab(cron_str)
            await self.on_cron_changed.trigger(interaction, game_id, int(is_opsec), interaction.channel_id, cron_str)
        except ValueError as e:
            await interaction.response.send_message(f"""
Invalid cron string: {e}. Valid `cron` strings can be as follows:
```
5 * * * * - Every 5th minute of every hour
* 10 * * * - Every minute during 10AM
0 15 * * * - Once at 15:00 every day
*/30 * 1 * - Every 30 minutes on the first day of the week (Monday)
```
For more information, Google is your friend""")

    async def validate_game_id(self, interaction: discord.Interaction, game_id: int) -> bool:
        if game_id == 0:
            await interaction.response.send_message("The provided game id is not valid")
            return False

        return True
