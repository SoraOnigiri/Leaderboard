import discord
from discord.ext import commands
import requests
import json
import time


class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cg_tokens = {}
        self.setup()

    def get_coingecko_tokens(self):
        # CoinGecko token database
        r = requests.get("https://api.coingecko.com/api/v3/coins/list")
        tokens = {}
        for token in r.json():
            tokens[token["symbol"]] = {"id": token["id"], "name": token["name"]}
        return tokens

    def setup(self):
        self.cg_tokens = self.get_coingecko_tokens()

    def get_token_price(self, id):
        currency = "usd"
        pto = int(time.time())
        pfrom = pto - 1000

        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{id}/market_chart/range?vs_currency={currency}&from={str(pfrom)}&to={str(pto)}"
        )
        results = r.json()
        # {"prices":[1641567677939,3226.1455591491567],[1641568160652,3196.3101680587015],[1641568388161,3189.864689613417]}
        return results["prices"][-1][1]

    async def get_trade_id(self, userid):
        # 1. Retrieve last trade id from user
        return 0

    async def add_trade(self, userid, tradeid, openDate, openPrice, ticker, openReason):
        deleted = False
        isOpen = True

    async def update_user(self, userid, tradeid):
        pass

    async def get_open_trades(self, userid):
        pass

    async def get_closed_trades(self, userid):
        pass

    async def get_total_profit(self, userid):
        pass

    async def delete_id(self, userid, tradeid):
        pass

    async def leaderboard(self):
        pass

    @commands.command()
    async def buy(self, ctx):
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 2)
            input_count = len(var)
            ticker = var[0].lower()
            # Verify the Ticker
            if ticker not in self.cg_tokens:
                self.cg_tokens = get_coingecko_tokens(self.cg_tokens)
                if ticker not in self.cg_tokens:
                    await ctx.send(f"{var[0]} is not a valid ticker.")
                    return

            if input_count == 1:
                ticker_price = get_token_price(self.cg_tokens[ticker])
                reason = ""

            else:
                # Verify Amount or retrieve price from coingecko api
                # Retrieve price from coingecko db
                if var[1] == None:
                    ticker_price = get_token_price(self.cg_tokens[ticker])
                else:
                    try:
                        ticker_price = float(var[1])
                    except:
                        ctx.send(f"{var[1]} is not a valid number")
                        return
                if input_count == 3:
                    reason = var[2]
                else:
                    reason = ""

            # At this point, we have the ticker, price, and reasoning. Need to build the trade now.
            userid = ctx.message.author.id
            tradeid = await get_trade_id(userid)
            opentime = int(time.time())
            add_trade()
            update_user()

            message = f"{ctx.message.author.name} has opened a trade with ID: {tradeid}, Ticker: ${ticker.upper()} at Price: ${ticker_price}"

            embed = discord.Embed(
                description=f"```\n{message}\n```",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except:
            embed = discord.Embed(
                description="```\n!buy [Ticker],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def close(self, ctx):
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 2)
            input_count = len(var)
            if input_count < 2 or var[0] == None or var[1] == None:
                embed = discord.Embed(
                    description="```\n!close [TradeID],[Price],[Reasoning(Optional)]\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            # 1. Check if TradeId is valid
            # 2. Check if Price is valid float --- At this point all you have is Trade Id and Price
            # 3. Retrieve Trade dict and User dict
            # 4. Calculate Profit
            # 5. get close date, change isOpen to false
            # 6. Update total profits for userid += profit
            # 7. send: Bot: Trade with ID 0 has been closed, ticker: $SNX profit: 100%, duration of trade: 1 day and 1 hour, with reasoning “My work is done”

        except:
            embed = discord.Embed(
                description="```\n!close [TradeID],[Price],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def view_open_trades(self, ctx):
        await get_open_trades(ctx.message.author.id)

    @commands.command()
    async def view_closed_trades(self, ctx):
        await get_closed_trades(ctx.message.author.id)

    @commands.command()
    async def total_profit(self, ctx):
        await get_total_profit(ctx.message.author.id)

    @commands.command()
    async def delete_id(self, ctx):
        await delete_id(ctx.message.author.id, tradeid)

    @commands.command()
    async def leaderboard(self, ctx):
        await leaderboard()

    @commands.command()
    async def help(self, ctx):

        with open("bot_commands.txt", "r") as bcmd:
            results = bcmd.readlines()
            blurb = ""
            for i in results:
                blurb = blurb + i + "\n"
            embed = discord.Embed(
                description=f"```\n{blurb}\n```",
                color=discord.Color.blue(),
                title="Trading Leaderboard Commands",
            )
            await ctx.send(embed=embed)
        # await ctx.send(f"Length of self.cg_tokens is: {len(self.cg_tokens)}")
