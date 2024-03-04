import discord
import database


class OperationMessageOptions(object):
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


class OperationsEmbed:
    embed: discord.Embed
    options: OperationMessageOptions

    def __init__(self, title: str, notification_options: OperationMessageOptions):
        """Create the embed to be used by operation messages"""
        self.embed = discord.Embed(
            title=title,
            color=notification_options.color,
            type="rich"
        )

        self.options = notification_options

    def send_operations(self, text_channel: discord.TextChannel, operations: [database.Operation]):
        if self.options.include_timestamp:
            # Get current timestamp
            timestamp = discord.utils.utcnow()  # TODO: Should this be opserv time to make this consistent?
            self.embed.set_footer(text=f"Last updated: {timestamp.strftime('%Y-%m-%d %H:%M')}")

        for operation in operations:
            field_title = operation.operation_name
            lines = []
            if self.options.show_game:
                lines.append(f"**{operation.game_id.name}**")

            if self.options.show_leader:
                lines.append(f"**Leader:** {operation.leader_user_id.name}")

            if self.options.show_date_start:
                lines.append(f"**Start:** {operation.date_start}")

            if self.options.show_date_end:
                lines.append(f"**End:** {operation.date_end}")

            if self.options.show_opserv_link:
                opserv_link = f"https://www.the-bwc.com/opserv/operation.php?id={operation.operation_id}&do=view"
                lines.append(f"_Go to [Opserv]({opserv_link}) for details_")

            self.embed.add_field(
                name=field_title,
                value='\n'.join(lines),
                inline=False
            )
        await text_channel.send(self.embed)