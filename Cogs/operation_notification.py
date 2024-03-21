import datetime
from typing import Callable, List, Any
import discord
from discord.ext import commands, tasks
import database
import settings

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

    async def send_operations(self, text_channel: discord.TextChannel, operations) -> None:
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
    async def send_operations(self,
                              embed_title:str,
                              conditions: Callable[[database.Operation, int], List[bool]],
                              exclude_operations: List[int] = [],
                              notification_options: OperationMessageOptions = NOTIFICATION_OPTIONS['UPCOMING_OPS']) -> List[
                                                                                                                                    database.Operation] | None:
        """
        Send operation notifications in a message with the given title.
        :returns Array of operations that were processed
        """
        channels = self.config.OPSEC_CHANNELS_MAP
        operations_notified = []
        for game, channel in channels.items():
            text_channel = await self.bot.fetch_channel(channel)

            if text_channel is None:
                self.logger.error(f"Channel {text_channel} not found.")
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


class Operation30Notifier(commands.Cog, OperationNotifier):
    def __init__(self, bot, config: Any, logger):
        self.bot = bot
        self.config = config
        self.logger = logger
        self.send.start()

    async def cog_unload(self) -> None:
        self.send.stop()

    @tasks.loop(minutes=3)
    async def send(self) -> [database.Operation]:
        # Get already notified data so that we can filter those out
        notification_model = database.Notification30
        future_ops = notification_model.select(notification_model.operation_id) \
            .where(notification_model.date_start >= datetime.datetime.now())
        future_ops_ids = list(map(lambda op: op.operation_id, future_ops))
        operations = await super().send_operations("Operations starting in 30 minutes!",
                                                self.where_ops_30minutes,
                                                future_ops_ids,
                                                NOTIFICATION_OPTIONS['30MIN_OPS'])

        # Save the data of those operations we notified
        if operations:
            op_data = []
            for op in operations:
                op_data.append({'operation_id': op.operation_id, 'date_start': op.date_start})

            return op_data

        return []

    @staticmethod
    def where_ops_30minutes(operation_model: database.Operation, game: int) -> List[bool]:
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


class UpcomingOperationsNotifier(commands.Cog, OperationNotifier):
    class OpservTimezone(datetime.tzinfo):
        def utcoffset(self, __dt: datetime.datetime | None) -> datetime.timedelta | None:
            return datetime.timedelta(hours=-5)

        def dst(self, __dt: datetime.datetime | None) -> datetime.timedelta | None:
            return datetime.timedelta(hours=-1)

        def tzname(self, __dt: datetime.datetime | None) -> str | None:
            return 'America/New York'

    schedule = datetime.time(hour=19)
    def __init__(self, bot, config: Any, logger):
        self.bot = bot
        self.config = config
        self.logger = logger
        self.send.start()

    async def cog_unload(self) -> None:
        self.send.stop()

    @tasks.loop(time=datetime.time(hour=19, tzinfo=OpservTimezone()))
    async def send(self) -> [database.Operation]:
        await super().send_operations("OPSEC Operations", self.where_upcoming_opsec_ops)

        # Return empty because there's nothing that needs to be saved to the db
        return []

    @staticmethod
    def where_upcoming_opsec_ops(operation_model: database.Operation, game: int) -> List[bool]:
        return [
            operation_model.game_id == game,
            operation_model.is_opsec == True,
            operation_model.is_completed == False
        ]
