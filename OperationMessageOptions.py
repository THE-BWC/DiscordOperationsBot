import discord


class OperationMessageOptions:
    def __init__(self, **kwargs):
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
