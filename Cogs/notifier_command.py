from discord.ext import commands


class Notifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def notifier(self, ctx, game_id: int, schedule: str):
        await ctx.send("You are here")
