import datetime
import random
import platform
import os
from typing import Callable, List

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

    async def send_upcoming_ops(self):
        await self.send_operations("OPSEC Operations", self.where_upcoming_opsec_ops)

    @staticmethod
    def where_upcoming_opsec_ops(operation_model: database.Operation, game: int):
        return [
            operation_model.game_id == game,
            operation_model.is_opsec == True,
            operation_model.is_completed == False
        ]

    async def send_30minutes_notification_task(self):
        # Get already notified data so that we can filter those out
        notification_model = database.Notification30
        future_ops = notification_model.select(notification_model.operation_id).where(notification_model.date_start >= datetime.datetime.now())
        future_ops_ids = list(map(lambda op: op.operation_id, future_ops))
        operations = await self.send_operations("Operations starting in 30 minutes!", self.where_ops_30minutes, False, future_ops_ids)

        # Save the data of those operations we notified
        if operations:
            op_data = []
            for op in operations:
                op_data.append({'operation_id': op.operation_id, 'date_start': op.date_start})

            with self.database.bot.atomic():
                notification_model.insert_many(op_data).execute()

    @staticmethod
    def where_ops_30minutes(operation_model: database.Operation, game: int):
        """Set of conditions that select records from the Operation model with a specific deadline"""
        # Mindful with boolean conditions here. We cannot use proper "pythonic" conditions like
        # `operation_model.is_complete is False` because it doesn't translate properly in the SQL query
        now = datetime.datetime.now()
        now = now.replace(second=0, microsecond=0)
        deadline = now + datetime.timedelta(minutes=30)

        return [operation_model.game_id == game,
                operation_model.is_completed == False,
                operation_model.date_start.truncate("minute") >= now,
                operation_model.date_start.truncate("minute") <= deadline]

    def create_operations_embed(self, title: str, operations: [database.Operation]):
        """Create the embed to be used by operation messages"""
        embed = discord.Embed(
            title=title,
            color=discord.Color.red(),
            type="rich"
        )

        for operation in operations:
            opserv_link = "https://www.the-bwc.com" #TODO: generate proper opserv link
            field_title = operation.operation_name
            lines = [
                f"**Leader:** {operation.leader_user_id.name}",
                f"**Start:** {operation.date_start}",
                f"_Go to [Opserv]({opserv_link}) for details_"
            ]

            embed.add_field(
                name=field_title,
                value='\n'.join(lines),
                inline=False
            )

        return embed

    async def send_operations(self, embed_title:str, conditions: Callable[[database.Operation, int], List[bool]], include_timestamp = True, operations_filter: List[int] = []) -> List[database.Operation]:
        """
        Send operation notifications in a message with the given title.
        :returns Array of operations that were processed
        """
        channels = self.config.OPSEC_CHANNELS_MAP
        operations_notified = []
        for game, channel in channels.items():
            text_channel = await self.fetch_channel(channel)

            if text_channel is None:
                self.logger.error(f"Channel {text_channel} not found.")
                return

            operation_model = database.Operation
            operations = operation_model.select().where(*conditions(operation_model, game)).order_by(operation_model.date_start)

            if len(operations_filter) > 0:
                operations = list(filter(lambda x: x.operation_id not in operations_filter, operations))

            if len(operations) == 0:
                return

            embed = self.create_operations_embed(embed_title, operations)

            if include_timestamp:
                # Get current timestamp
                timestamp = discord.utils.utcnow()
                embed.set_footer(text=f"Last updated: {timestamp}")

            await text_channel.send(embed=embed)
            operations_notified.extend(operations)

        return operations_notified


bot = DiscordBot()
bot.run(settings.DISCORD_BOT_TOKEN)
