from __future__ import annotations
from typing import TYPE_CHECKING, List

import logging
from datetime import datetime
import dateutil.tz
import html2text
import discord
import peewee
from discord import ScheduledEvent
from discord.ext import commands

from discord.ext.commands import Context

if TYPE_CHECKING:
    from bot import DiscordBot
    from database.xen_db import Operation
    from database.bot_db import DiscordEvents

log = logging.getLogger(__name__)


class ScheduledEvents(commands.Cog):
    """Cog for handling scheduled discord events from OpServ operations"""

    DEFAULT_TIMEZONE = dateutil.tz.gettz("America/New_York")

    def __init__(self, bot: DiscordBot):
        self.bot: DiscordBot = bot

    async def cog_load(self) -> None:
        await self.sync_operations()

    async def cog_command_error(
        self, ctx: Context, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.BadArgument):
            await ctx.send(str(error))
        if isinstance(error, commands.TooManyArguments):
            await ctx.send(f"Too many arguments provided. {error}")

    async def get_upcoming_operations(self) -> List[Operation]:
        """Get the upcoming operations from the database"""
        # Mindful with boolean conditions here. We cannot use proper "pythonic" conditions like
        # `operation_model.is_complete is False` because it doesn't translate properly in the SQL query
        now = datetime.timestamp(datetime.now())

        operation_model = self.bot.xen_db.Operation
        return (
            operation_model.select()
            .where(
                operation_model.is_completed == False,
                operation_model.is_opsec == 0,
                operation_model.date_start >= now,
            )
            .order_by(operation_model.date_start)
        )

    async def sync_operations(self):
        """Sync the operations with the discord events"""
        # Remove stale events
        # Get all events from the server
        guild = await self.bot.fetch_guild(self.bot.config.GUILD_ID)
        events = await guild.fetch_scheduled_events()

        await self.cleanup_stale_events(events)

        upcoming_operations = await self.get_upcoming_operations()

        for operation in upcoming_operations:
            await self.sync_operation(operation, events)

    async def sync_operation(self, operation: Operation, events: List[ScheduledEvent]):
        """Sync an operation with the discord events"""
        log.info(
            f"[sync_operation] Syncing operation {operation.operation_id} with discord events"
        )

        # Fetch the event from the database
        fetched_event = await self.get_operation_to_event(operation)
        if fetched_event:
            # Check if the db event has become stale
            if not discord.utils.get(events, id=int(fetched_event.event_id)):
                log.info(
                    f"[sync_operation] Event {fetched_event.event_id} not found in server."
                )
                await self.delete_discord_db_event(operation)
                await self.sync_operation(operation, events)
                return

            if operation.edited_date != fetched_event.operation_edited_date:
                # Update the event
                event = discord.utils.get(events, id=int(fetched_event.event_id))
                await self.update_event(event, operation)
        else:
            if operation.discord_voice_channel_id:
                # Create the event
                channel = self.bot.get_channel(operation.discord_voice_channel_id)
                await self.create_event(channel, operation)
                if not channel:
                    log.error(
                        f"[sync_operation] Channel {operation.discord_voice_channel_id} not found"
                    )
                    return
            else:
                # Create the event
                channel = operation.discord_event_location
                await self.create_event(channel, operation)

    async def get_operation_to_event(self, operation: Operation) -> DiscordEvents:
        """Get the discord event for the operation"""
        event_model = self.bot.bot_db.DiscordEvents
        return (
            event_model.select()
            .where(event_model.operation_id == operation.operation_id)
            .first()
        )

    async def delete_discord_event(self, operation: Operation):
        guild = await self.bot.fetch_guild(self.bot.config.GUILD_ID)

        event_db = await self.get_operation_to_event(operation)
        if not event_db:
            return

        event = await guild.fetch_scheduled_event(event_db.event_id)
        if event:
            try:
                await event.delete()
                event_model = self.bot.bot_db.DiscordEvents
                event_model.delete().where(
                    event_model.operation_id == operation.operation_id
                ).execute()
            except peewee.DatabaseError as e:
                log.error(
                    f"[delete_discord_event] Error deleting event from database: {e}"
                )

    async def delete_discord_db_event(self, operation: Operation):
        try:
            event_model = self.bot.bot_db.DiscordEvents
            event_model.delete().where(
                event_model.operation_id == operation.operation_id
            ).execute()
        except peewee.DatabaseError as e:
            log.error(
                f"[delete_discord_db_event] Error deleting event from database: {e}"
            )

    async def parse_html(self, html: str) -> str:
        """Parse the HTML from the operation description"""
        h = html2text.HTML2Text()
        return h.handle(html)

    async def cleanup_stale_events(self, events: List[ScheduledEvent]):
        """Remove stale events from the database"""
        log.info("[cleanup_stale_events] Cleaning up stale events")
        # Get all events from the database
        event_model = self.bot.bot_db.DiscordEvents
        db_events = event_model.select().execute()
        log.info(
            f"[cleanup_stale_events] Found {len(db_events)} events in the database"
        )

        # Check each event against its operation. If the event end_date is less than the current date, delete it.
        for db_event in db_events:
            event = discord.utils.get(events, id=int(db_event.event_id))
            log.info(
                f"[cleanup_stale_events] Checking event {db_event.event_id} for operation {db_event.operation_id}"
            )

            operation_model = self.bot.xen_db.Operation
            operation = operation_model.get(
                operation_model.operation_id == db_event.operation_id
            )
            log.info(
                f"[cleanup_stale_events] Operation {operation.operation_id} for event {db_event.event_id} found"
            )
            if event and operation.date_end < datetime.timestamp(datetime.now()):
                log.info(
                    f"[cleanup_stale_events] Event {event.id} for operation {operation.operation_id} has ended. Deleting event."
                )
                await event.delete()
                db_event.delete().execute()
            elif not event:
                log.info(
                    f"[cleanup_stale_events] Event {db_event.event_id} for operation {operation.operation_id} not found in server. Deleting event."
                )
                db_event.delete().execute()

    async def create_event(
        self, channel: discord.VoiceChannel or str, operation: Operation
    ):
        """Create a discord event for the operation"""
        guild = await self.bot.fetch_guild(self.bot.config.GUILD_ID)
        start_time = datetime.fromtimestamp(operation.date_start).astimezone(
            tz=self.DEFAULT_TIMEZONE
        )
        end_time = datetime.fromtimestamp(operation.date_end).astimezone(
            tz=self.DEFAULT_TIMEZONE
        )
        description = await self.parse_html(operation.description)
        if len(description) > 950:
            description = description[:950] + "..."

        try:
            if isinstance(channel, discord.VoiceChannel):
                event = await guild.create_scheduled_event(
                    name=operation.operation_name,
                    description=description,
                    channel=channel,
                    start_time=start_time,
                    end_time=end_time,
                )
                # Save the event to the database
                event_model = self.bot.bot_db.DiscordEvents
                event_model.create(
                    operation_id=operation.operation_id,
                    event_id=event.id,
                )
            else:
                if channel == "None" or channel == "":
                    channel = "Hmm..."
                event = await guild.create_scheduled_event(
                    name=operation.operation_name,
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    privacy_level=discord.PrivacyLevel.guild_only,
                    entity_type=discord.EntityType.external,
                    location=channel,
                )
                # Save the event to the database
                event_model = self.bot.bot_db.DiscordEvents
                event_model.create(
                    operation_id=operation.operation_id,
                    event_id=event.id,
                    operation_edited_date=operation.edited_date,
                )
        except discord.HTTPException as e:
            log.error(f"[create_event] Error creating event: {e}")
            return

    async def update_event(self, event: ScheduledEvent, operation: Operation):
        """Update the discord event for the operation"""
        try:
            if operation.date_start < datetime.timestamp(datetime.now()):
                await self.delete_discord_event(operation)

            start_time = datetime.fromtimestamp(operation.date_start).astimezone(
                tz=self.DEFAULT_TIMEZONE
            )
            end_time = datetime.fromtimestamp(operation.date_end).astimezone(
                tz=self.DEFAULT_TIMEZONE
            )
            description = await self.parse_html(operation.description)
            if len(description) > 950:
                description = description[:950] + "..."

            await event.edit(
                name=operation.operation_name,
                start_time=start_time,
                end_time=end_time,
                description=description,
            )
        except discord.HTTPException as e:
            log.error(f"[update_event] Error updating event: {e}")
            return

        log.info(
            f"[update_event] Updated event {event.id} for operation {operation.operation_id}"
        )


async def setup(bot):
    await bot.add_cog(ScheduledEvents(bot))
