import collections
import datetime
import random
import platform
import os
from typing import List

import discord
from discord.ext import tasks

import settings
import notification_settings
import bot_logger
import database

from operation_message import OperationMessageOptions, OperationsEmbed

if settings.DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables.")


class DiscordBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(
            intents=discord.Intents.default()
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
        self.send_30minutes_notification_task.start()
        self.database = database
        await self.send_upcoming_ops()

    async def send_upcoming_ops(self) -> None:
        await self.send_operations("OPSEC Operations", self.where_upcoming_opsec_ops)

    @staticmethod
    def where_upcoming_opsec_ops(operation_model: database.Operation, game: int) -> list[bool]:
        return [
            operation_model.game_id == game,
            operation_model.is_opsec == True,
            operation_model.is_completed == False
        ]

    @tasks.loop(minutes=3)
    async def send_30minutes_notification_task(self) -> None:
        # Get already notified data so that we can filter those out
        notification_model = database.Notification30
        future_ops = notification_model.select(notification_model.operation_id) \
            .where(notification_model.date_start >= datetime.datetime.now())
        future_ops_ids = list(map(lambda op: op.operation_id, future_ops))
        operations = await self.send_operations("Operations starting in 30 minutes!",
                                                self.where_ops_30minutes,
                                                future_ops_ids,
                                                notification_settings.NOTIFICATION_OPTIONS['30MIN_OPS'])

        # Save the data of those operations we notified
        if operations:
            op_data = []
            for op in operations:
                op_data.append({'operation_id': op.operation_id, 'date_start': op.date_start})

            with self.database.bot.atomic():
                notification_model.insert_many(op_data).execute(self.database.bot)

    @staticmethod
    def where_ops_30minutes(operation_model: database.Operation, game: int) -> list[bool]:
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

    async def send_operations(
            self,
            embed_title: str,
            conditions: collections.abc.Callable[[database.Operation, int], list[bool]],
            exclude_operations: list[int] = [],
            notification_options: OperationMessageOptions =
            notification_settings.NOTIFICATION_OPTIONS['UPCOMING_OPS']
    ) -> List[database.Operation] | None:
        """
        Send operation notifications in a message with the given title.
        :returns Array of operations that were processed
        """
        channels = self.config.OPSEC_CHANNELS_MAP
        operations_notified = []
        for game, channel in channels.items():
            text_channel = await self.fetch_channel(channel)

            if text_channel is None:
                self.logger.error("Channel %s not found.", text_channel)
                return

            operation_model = database.Operation
            operations = operation_model.select().where(*conditions(operation_model, game)) \
                .order_by(operation_model.date_start)

            if len(exclude_operations) > 0:
                operations = list(filter(lambda x: x.operation_id not in exclude_operations, operations))

            if len(operations) == 0:
                return

            embed = OperationsEmbed(embed_title, notification_options)
            await embed.send_operations(text_channel, operations)
            operations_notified.extend(operations)

        return operations_notified


bot = DiscordBot()
bot.run(settings.DISCORD_BOT_TOKEN)
