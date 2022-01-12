from settings import *
from discord.ext import commands
import discord
from leaderboard import User


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")


async def setup():
    await bot.wait_until_ready()
    bot.add_cog(User(bot))


bot.loop.create_task(setup())

bot.run(os.getenv("LEADERBOT"))
