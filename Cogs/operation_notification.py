import asyncio
import datetime
from logging import Logger

import crontab
import discord
from discord.ext import commands, tasks
import database
from settings import Settings


class OperationMessageOptions:
    """ Options to configure an OperationsEmbed instance """
    def __init__(self, **kwargs) -> None:
        self.color = kwargs.get('color', discord.Color.red())
        self.show_leader = kwargs.get('show_leader', True)
        self.show_game = kwargs.get('show_game', True)
        self.show_date_start = kwargs.get('show_date_start', True)
        self.show_date_end = kwargs.get('show_date_end', True)
        self.show_opserv_link = kwargs.get('show_opserv_link', True)
        self.include_timestamp = kwargs.get('include_timestamp', True)

    color: discord.Color
    show_leader: bool
    show_game: bool
    show_date_start: bool
    show_date_end: bool
    show_opserv_link: bool
    include_timestamp: bool


# Moved to separate file to avoid circular imports
NOTIFICATION_OPTIONS = {
    'UPCOMING_OPS': OperationMessageOptions(),
    '30MIN_OPS': OperationMessageOptions(show_game=False, show_date_end=False, include_timestamp=False)
}


class OperationsEmbed:
    embed: discord.Embed
    options: OperationMessageOptions

    def __init__(self, title: str, notification_options: OperationMessageOptions) -> None:
        """Create the embed to be used by operation messages"""
        self.embed = discord.Embed(
            title=title,
            color=notification_options.color,
            type="rich"
        )

        self.options = notification_options

    async def send_operations(self, text_channel: discord.TextChannel, operations: list[database.Operation]) -> None:
        if self.options.include_timestamp:
            # Get current timestamp
            # TODO: Should this be opserv time to make this consistent?
            timestamp = discord.utils.utcnow()
            self.embed.set_footer(text=f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M')}")

        for operation in operations:
            field_title = operation.operation_name
            lines = []
            if self.options.show_game:
                lines.append(f"**{operation.game_id.game_name}**")

            if self.options.show_leader:
                lines.append(f"**Leader:** {operation.leader_user_id.username}")

            if self.options.show_date_start:
                lines.append(f"**Start:** <t:{operation.date_start}>")

            if self.options.show_date_end:
                lines.append(f"**End:** <t:{operation.date_end}>")

            if self.options.show_opserv_link:
                opserv_link = f"https://www.the-bwc.com/opserv/operation.php?id={operation.operation_id}&do=view"
                lines.append(f"_Go to [Opserv]({opserv_link}) for details_")

            self.embed.add_field(
                name=field_title,
                value='\n'.join(lines),
                inline=False
            )

        await text_channel.send(embed=self.embed)


class OperationNotifier:
    bot: commands.Bot
    logger: Logger
    async def send_operations(self,
                              embed_title:str,
                              channels: list[int],
                              operations: list[database.Operation],
                              notification_options: OperationMessageOptions = NOTIFICATION_OPTIONS['UPCOMING_OPS']
                              ) -> list[database.Operation]:
        """
        Send operation notifications in a message with the given title.
        :returns Array of operations that were processed
        """
        operations_notified = []
        if len(operations) == 0:
            return operations_notified

        for channel in channels:
            text_channel = await self.bot.fetch_channel(channel)

            if text_channel is None:
                self.logger.error(f"Channel {text_channel} not found.")
                continue

            embed = OperationsEmbed(embed_title, notification_options)
            await embed.send_operations(text_channel, operations)
            operations_notified.extend(operations)

        return operations_notified


class Operation30Notifier(commands.Cog, OperationNotifier):
    def __init__(self, bot: commands.Bot, config: Settings, logger: Logger) -> None:
        self.bot = bot
        self.config = config
        self.logger = logger
        self.send.start()

    async def cog_unload(self) -> None:
        self.send.stop()

    def get_operations(self, game_id: int, is_opsec: bool, exclude: list[int]) -> list[database.Operation]:
        # Mindful with boolean conditions here. We cannot use proper "pythonic" conditions like
        # `operation_model.is_complete is False` because it doesn't translate properly in the SQL query
        now = datetime.datetime.now()
        now = now.replace(second=0, microsecond=0)
        deadline = now + datetime.timedelta(minutes=30)

        operation_model = database.Operation
        return operation_model.select().where(operation_model.game_id == game_id,
                operation_model.is_completed == False,
                operation_model.is_opsec == is_opsec,
                operation_model.date_start.truncate("minute") >= now,
                operation_model.date_start.truncate("minute") <= deadline,
                operation_model.operation_id not in exclude).order_by(operation_model.date_start)

    @tasks.loop(minutes=3)
    async def send(self) -> [database.Operation]:
        # Get already notified data so that we can filter those out
        notification_model = database.Notification30
        notified_ops = notification_model.select(notification_model.operation_id) \
            .where(notification_model.date_start >= datetime.datetime.now())
        notified_ops_ids = list(map(lambda op: op.operation_id, notified_ops))

        notifications_sent = []
        for game, data in self.config.opsec_channels_map.items():
            for access, channels in data.items():
                # Here we are pasing the notified_ops_ids so that they are filtered from the pending notif
                pending_notifications = self.get_operations(game, access, notified_ops_ids)
                operations = await super().send_operations("Operations starting in 30 minutes!",
                                                           channels=channels,
                                                           operations=pending_notifications,
                                                           notification_options=NOTIFICATION_OPTIONS['30MIN_OPS'])

                notifications_sent.extend(operations)

        # Save the data of those operations we notified
        if notifications_sent:
            op_data = []
            for op in operations:
                op_data.append({'operation_id': op.operation_id, 'date_start': op.date_start})

            return op_data

        return []


class NotificationTask:
    """ Wrap an asyncio task to have a single access point to our custom notification task id logic"""
    game_id: int
    is_opsec: int
    channel: int
    task: asyncio.Task = None

    def __init__(self, game_id: int, is_opsec: int, channel: int, task: asyncio.Task) -> None:
        self.game_id = game_id
        self.is_opsec = is_opsec
        self.channel = channel
        self.task = task

    def set_task(self, task: asyncio.Task) -> None:
        if self.task is not None:
            self.task.cancel()

        self.task = task

    def id(self) -> str:
        return self.get_id(self.game_id, self.is_opsec, self.channel)

    def stop(self) -> None:
        self.task.cancel()

    def __str__(self) -> str:
        return self.id()

    @staticmethod
    def get_id(game_id: int, is_opsec: int, channel: int) -> str:
        """ Returns the custom id format we use for tasks"""
        return f"{game_id}-{is_opsec}-{channel}"


class UpcomingOperationsNotifier(commands.Cog, OperationNotifier):
    tasks: {str: asyncio.Task}

    def __init__(self, bot: commands.Bot, config: Settings, logger: Logger) -> None:
        self.bot = bot
        self.config = config
        self.logger = logger
        self.tasks = {}
        self.setup()

    def create_task(self, game: int, is_opsec: int, channel: int, cron: str) -> NotificationTask:
        # This creates and starts a task at the same time
        task = self.bot.loop.create_task(self.__send(game, is_opsec, cron, [channel]))
        # Encapsulate it in our own class just for ease of access later
        return NotificationTask(game, is_opsec, channel, task)

    def setup(self) -> None:
        for game, data in self.config.opsec_channels_map.items():
            for is_opsec, channels in data.items():
                for channel, cron in channels.items():
                    notification_task = self.create_task(game, is_opsec, channel, cron)
                    self.tasks[notification_task.id()] = notification_task

    def stop(self) -> None:
        for task in self.tasks.values():
            task.stop()

    async def cog_load(self) -> None:
        self.setup()

    async def cog_unload(self) -> None:
        self.stop()

    def get_operations(self, game_id: int, is_opsec: bool) -> list[database.Operation]:
        operation_model = database.Operation
        now = datetime.datetime.now().replace(second=0, minute=0)
        return operation_model.select().where(
            operation_model.game_id == game_id,
            operation_model.is_opsec == is_opsec,
            operation_model.is_completed == False,
            operation_model.date_start.truncate("minute") >= now
        )

    async def __send(self, game: int, is_opsec: int, schedule: str, channels: [int]) -> None:
        # This is the work for the task related to a single notification
        cron = crontab.CronTab(schedule)
        while True:
            # sleep until next execution to avoid using cpu cycles
            next_run = cron.next()
            await asyncio.sleep(next_run)

            ops = self.get_operations(game, is_opsec)
            title = "OPSEC" if is_opsec == self.config.OPSEC else "Public"
            await super().send_operations(f"{title} Operations", channels=channels, operations=ops)

    def update_task(self, game_id: int, is_opsec: int, channel: int, cron: str) -> None:
        """Stop any existing task with the same id and creates a new one"""
        self.stop_task(game_id, is_opsec, channel)
        notification_task = self.create_task(game_id, is_opsec, channel, cron)
        self.tasks[notification_task.id()] = notification_task

    def stop_task(self, game_id: int, is_opsec: int, channel: int) -> None:
        """Stop the task that matches the id of the provided arguments"""
        notification_id = NotificationTask.get_id(game_id, is_opsec, channel)
        notification_task = self.tasks.get(notification_id, None)

        if notification_task is not None:
            notification_task.stop()
