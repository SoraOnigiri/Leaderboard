from tempfile import TemporaryFile
import discord
from discord.ext import commands
import requests
import json
import time
from settings import *
import math

# *******************************************************************
# print(truncate3(1.987999999999))
# print(truncate5(1.987129999999))
# *******************************************************************


class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cg_tokens = {}
        self.cg_tokens = self.get_coingecko_tokens()
        # self.trade_channel_id = []
        # self.trade_info_channel_id = []
        self.client = ""
        self.get_database()
        self.trade_channel = os.getenv("TRADE_CHANNEL")
        self.trade_info_channel = os.getenv("TRADE_INFO_CHANNEL")

    def setup(self, guild_id):
        DB = self.client[guild_id]
        tradeCol = DB["TRADES"]
        userCol = DB["USER"]
        return tradeCol, userCol

    def get_coingecko_tokens(self):
        # CoinGecko token database

        r = requests.get("https://api.coingecko.com/api/v3/coins/list")

        tokens = {}
        for token in r.json():
            if token["symbol"] not in tokens:
                tokens[token["symbol"]] = []
                tokens[token["symbol"]].append(token["id"])
                continue
            tokens[token["symbol"]].append(token["id"])
        return tokens

    def get_database(self):
        dbpass = os.getenv("DBPASS")
        dbuser = os.getenv("DBUSER")
        dbaddress = os.getenv("DBADDRESS")
        # Provide the mongodb atlas url to connect python to mongodb using pymongo
        CONNECTION_STRING = f"mongodb+srv://{dbuser}:{dbpass}@{dbaddress}"

        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
        from pymongo import MongoClient

        self.client = MongoClient(CONNECTION_STRING)

        # Create the database for our example (we will use the same database throughout the tutorial
        # return client[title]

    def isInitialized(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        if userCol.find_one({"userid": userid}) is None:
            return False
        return True

    def initialize_user(self, userid, name, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = {
            "userid": userid,
            "balance": 100000,
            "name": name,
            "debt": 0,
            "total_profit": 0,
        }
        userCol.insert_one(user)

    def get_token_price(self, ticker):

        # if len(self.cg_tokens[ticker]) > 1:
        #     print("get_token_price: There is more than 1 ticker that exists.")

        for i in self.cg_tokens[ticker]:

            r = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={i}&vs_currencies=usd"
            )
            results = r.json()

            try:
                price = float(results[i.lower()]["usd"])

                return round(price, 5)
            except:
                continue

    def trade_exists(self, trade_id, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": trade_id})
        if trade:
            if trade["deleted"]:
                return False
            return True
        return False

    def isTradingPost(self, guild_id):
        dblist = self.client.list_database_names()
        if str(guild_id) in dblist:
            return True
        return False

    def isOwner(self, trade_id, user_id, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": trade_id})
        if trade["userid"] == user_id:
            return True
        return False

    def isOpen(self, trade_id, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": trade_id})
        return trade["isOpen"]

    def isPoor(self, userid, price, quantity, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        balance = user["balance"]
        if balance <= 0:
            return True
        if (price * quantity) > balance:
            return True
        return False

    def check_short_position(self, trade_id, user_id, guild_id, ticker_price):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": trade_id})
        if trade["type"] == "long":
            return True
        user = userCol.find_one({"userid": user_id})
        balance = user["balance"]
        cost = ticker_price * trade["quantity"]

        if balance > cost:
            return True
        return False

    async def isAboveDebtLimit(self, userid, price, quantity, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        balance = user["balance"]
        debt = user["debt"]
        sale = price * quantity

        long_position = await self.get_long_position(userid, guild_id)
        if (price * quantity) < 0.0001:
            return True
        if ((balance + long_position - debt) * 0.5) < (sale):
            return True
        return False

    def isGameover(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        balance = user["balance"]
        if balance <= 0:
            # If balance is in the negatives, check if there are any long positions.
            trades = tradeCol.find({"userid": userid, "type": "long", "deleted": False})
            # No long positions, game over.
            if len(list(trades)) == 0:
                return True
            # Calculate balance if all long positions were sold, and see if balance still below 0
            liquidity = 0
            for i in trades:
                value = i["quantity"] * i["open_price"]
                liquidity = liquidity + value
            liquidity = balance + liquidity
            if liquidity <= 0:
                return True
        return False

    def truncate3(self, num):
        adjusted_num = num * 1000
        n = math.trunc(adjusted_num)
        return n / 1000

    def truncate5(self, num):
        adjusted_num = num * 100000
        n = math.trunc(adjusted_num)
        return n / 100000

    async def get_long_position(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        open_long = tradeCol.find(
            {"userid": userid, "isOpen": True, "deleted": False, "type": "long"}
        )

        long_position = 0
        length = len(list(open_long))
        open_long = tradeCol.find(
            {"userid": userid, "isOpen": True, "deleted": False, "type": "long"}
        )
        if length > 0:
            for trade in open_long:

                position = trade["quantity"] * trade["open_price"]
                long_position = long_position + position

        return long_position

    async def reset(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user_query = {"userid": userid}
        trade_query = {"userid": userid, "deleted": False}
        user_reset = {"$set": {"balance": 100000, "debt": 0, "total_profit": 0}}
        trade_reset = {"$set": {"deleted": True}}
        userCol.update_one(user_query, user_reset)
        tradeCol.update_many(trade_query, trade_reset)

    async def get_ticker(self, trade_id, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": trade_id})
        ticker = trade["ticker"]
        return ticker

    async def get_balance(self, userid, guild_id):

        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})

        return user["balance"]

    async def get_total_balance(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        long_position = await self.get_long_position(userid, guild_id)
        total = user["balance"] + long_position - user["debt"]
        return total

    async def get_debt(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        return user["debt"]

    async def open_trade(
        self, userid, quantity, time, price, ticker, reason, trade_type, guild_id
    ):
        tradeCol, userCol = self.setup(guild_id)
        # Create the Transaction record.
        deleted = False
        trade_id = tradeCol.find_one()["count"]
        trade = {
            "_id": trade_id + 1,
            "userid": userid,
            "open_date": time,
            "open_price": price,
            "quantity": quantity,
            "ticker": ticker,
            "open_reason": reason,
            "profit": 0,
            "percent": 0,
            "close_price": 0,
            "close_date": None,
            "close_reason": None,
            "deleted": False,
            "isOpen": True,
            "type": trade_type,
        }
        tradeCol.insert_one(trade)
        qcount = {"count": trade_id}
        updcount = {"$set": {"count": trade_id + 1}}
        tradeCol.update_one(qcount, updcount)

        # Get the user's account
        user = userCol.find_one({"userid": userid})
        # Calculate the cost/sale of the transaction
        cost = quantity * price
        # Update user balance depending on trade type.

        if trade_type == "long":
            balance = user["balance"]
            balance = balance - cost
            q = {"userid": userid}
            u = {"$set": {"balance": balance}}
            userCol.update_one(q, u)
        elif trade_type == "short":
            balance = user["balance"] + cost
            debt = user["debt"] + cost
            q = {"userid": userid}
            u = {"$set": {"balance": balance, "debt": debt}}
            userCol.update_one(q, u)
        else:
            return trade_id + 1

        return trade_id + 1

    async def close_trade(self, tradeid, price, reason, time, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trade = tradeCol.find_one({"_id": tradeid})
        cost = float(trade["open_price"]) * trade["quantity"]
        sale = float(price) * trade["quantity"]
        ticker = trade["ticker"]
        if trade["type"] == "long":
            profit = round(sale - cost, 5)
            percent = round((profit / cost) * 100, 3)
        else:  # if not long then short       for a short: open_price is price that it is purchased. sale price is price that it was bought back at.
            profit = round((cost - sale), 5)
            percent = round((profit / cost) * 100, 3)
        query = {"_id": tradeid}
        update = {
            "$set": {
                "profit": profit,
                "percent": percent,
                "close_price": price,
                "close_date": time,
                "close_reason": reason,
                "isOpen": False,
            }
        }
        tradeCol.update_one(query, update)
        # Get user
        user = userCol.find_one({"userid": trade["userid"]})
        # Update user balance and debt accordingly
        if trade["type"] == "long":
            quant = trade["quantity"]
            uid = user["userid"]
            new_balance = user["balance"] + (quant * price)
            q = {"userid": uid}
            upd = {"$set": {"balance": round(new_balance, 5)}}
            userCol.update_one(q, upd)
        elif trade["type"] == "short":
            old_debt = trade["open_price"] * trade["quantity"]
            new_debt = user["debt"] - old_debt
            new_balance = user["balance"] - (price * trade["quantity"])
            uid = user["userid"]
            q = {"userid": uid}
            upd = {
                "$set": {
                    "balance": round(new_balance, 5),
                    "debt": round(new_debt, 5),
                }
            }
            userCol.update_one(q, upd)
        # Retrieve other information
        seconds = time - trade["open_date"]  # in seconds
        days = int(seconds / 86400)
        hours = (seconds % 86400) / 3600
        duration = f"{int(days)} day(s) and {round(hours,1)} hour(s)"
        return (
            profit,
            ticker,
            percent,
            duration,
            trade["quantity"],
            price,
        )

    async def update_profit(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        total_profit = await self.get_total_profit(userid, guild_id)
        query = {"userid": userid}
        update = {"$set": {"total_profit": round(total_profit, 5)}}
        userCol.update_one(query, update)

    async def get_open_trades(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        open_trades = tradeCol.find(
            {"userid": userid, "isOpen": True, "deleted": False}
        )  # returns pymongo object. Must iterate through them.
        return open_trades

    async def get_closed_trades(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        closed_trades = tradeCol.find(
            {"userid": userid, "isOpen": False, "deleted": False}
        )

        return closed_trades

    async def get_user_total_profit(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        user = userCol.find_one({"userid": userid})
        return user["total_profit"]

    async def get_total_profit(self, userid, guild_id):
        try:
            tradeCol, userCol = self.setup(guild_id)
            total_profit = 0
            closed_trades = tradeCol.find(
                {"userid": userid, "isOpen": False, "deleted": False}
            )
            length = len(list(closed_trades))
            closed_trades = tradeCol.find(
                {"userid": userid, "isOpen": False, "deleted": False}
            )
            if length > 0:
                for trade_position in closed_trades:
                    total_profit = total_profit + trade_position["profit"]
            percentage = (round(total_profit, 5) / 100000) * 100
            return round(percentage, 3)
        except Exception as e:
            print(e)
            return 0

    async def delete_trade(self, trade_id, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        query = {"_id": trade_id}
        update = {"$set": {"deleted": True}}
        tradeCol.update_one(query, update)
        trade = tradeCol.find_one(query)
        uid = trade["userid"]
        user = userCol.find_one({"userid": uid})
        balance = user["balance"]
        debt = user["debt"]
        if trade["type"] == "long":
            if trade["isOpen"]:
                balance = balance + (trade["quantity"] * trade["open_price"])
            else:
                open = trade["quantity"] * trade["open_price"]
                close = trade["quantity"] * trade["close_price"]
                balance = balance + open - close
        elif trade["type"] == "short":
            if trade["isOpen"]:
                debt = debt - (trade["quantity"] * trade["open_price"])
                balance = balance - (trade["quantity"] * trade["open_price"])
            else:
                open = trade["quantity"] * trade["open_price"]
                close = trade["quantity"] * trade["close_price"]
                balance = balance - open + close
        total_profit_percentage = await self.get_total_profit(uid, guild_id)
        q2 = {"userid": uid}

        upd = {
            "$set": {
                "balance": balance,
                "debt": debt,
                "total_profit": total_profit_percentage,
            }
        }
        userCol.update_one(q2, upd)

    async def trade_leaderboard(self, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        users = userCol.find({}, {"_id": 0}).sort("total_profit", -1)
        return users

    async def get_trade_number(self, userid, guild_id):
        tradeCol, userCol = self.setup(guild_id)
        trades = tradeCol.find({"userid": userid, "deleted": False, "isOpen": False})

        return len(list(trades))

    @commands.command()
    async def join(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
            # if (
            #     ctx.message.channel.id not in self.trade_channel_id
            #     and ctx.message.channel.id not in self.trade_info_channel_id
            # ):
            # return
        if (
            ctx.message.channel.name not in self.trade_channel
            and ctx.message.channel.name not in self.trade_info_channel
        ):
            return
        if self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou've already joined the Trading Game.\n```",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            return
        try:
            self.initialize_user(
                ctx.message.author.id,
                ctx.message.author.name,
                str(ctx.message.guild.id),
            )
            embed = discord.Embed(
                description=f"```\nWelcome {ctx.message.author.name} , Where Lambo?\n```",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            return
        except:
            embed = discord.Embed(
                description=f"```\nFailed to join. Please contact the dev for more help.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

    @commands.command()
    async def patch_total_profits(self, ctx):
        guildid = str(ctx.message.guild.id)
        tradeCol, userCol = self.setup(guildid)
        for user in userCol.find():
            userid = user["userid"]
            total_profit = await self.get_total_profit(userid, guildid)
            query = {"userid": userid}
            update = {"$set": {"total_profit": total_profit}}
            userCol.update_one(query, update)

    @commands.command()
    async def buy(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if ctx.message.channel.id not in self.trade_channel_id:
        #     return
        if ctx.message.channel.name not in self.trade_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 4)
            input_count = len(var)
            ticker = var[0].lower()
            ticker_price = 0
            reason = ""
            quantity = 0

            # Ticker and Quantity are required
            if input_count == 1:
                embed = discord.Embed(
                    description="```\n!buy [Ticker],[Quantity],[Price(Optional)],[Reasoning(Optional)]\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            # 1. Check if Ticker is valid

            if ticker not in self.cg_tokens:

                self.cg_tokens = self.get_coingecko_tokens()

                if ticker not in self.cg_tokens:
                    embed = discord.Embed(
                        description=f"```\n{var[0]} is not a valid ticker.\n```",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return

            # input at this point is assumed to be >= 2
            # verify quantity    ***********************************************************  Need to update to take in percentages
            try:

                if var[1].endswith("%"):

                    try:

                        qnum = var[1].split("%", 1)[0]  # 20% / 100 = 0.2

                        qnum = float(qnum)
                        qnum = qnum / 100

                    except:
                        embed = discord.Embed(
                            description="```\nInvalid quantity.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return
                else:
                    quantity = float(var[1])
                    if quantity <= 0:
                        embed = discord.Embed(
                            description="```\nInvalid quantity.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return
            except:
                embed = discord.Embed(
                    description="```\nInvalid quantity.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Quantity verified. Verify token price or find it.
            if input_count == 2:

                ticker_price = self.get_token_price(ticker)

                reason = ""
            if input_count >= 3:
                if var[2] == "":
                    ticker_price = self.get_token_price(ticker)
                else:
                    try:
                        ticker_price = float(var[2])
                        if ticker_price <= 0:
                            embed = discord.Embed(
                                description="```\nInvalid price.\n```",
                                color=discord.Color.red(),
                            )
                            await ctx.send(embed=embed)
                            return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                    except:
                        embed = discord.Embed(
                            description="```\nInvalid price.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                if input_count == 4:
                    reason = var[3]
                else:
                    reason = ""

            # 5. Call open_trade function
            # At this point, we have the ticker, quantity, price, and reasoning. Need to build the trade now.
            userid = ctx.message.author.id
            opentime = int(time.time())
            trade_type = "long"

            # Adjust quantity if percentage was used.
            if var[1].endswith("%"):
                user_balance = await self.get_balance(userid, str(ctx.message.guild.id))
                portion = user_balance * qnum
                quantity = round(portion / ticker_price, 5)

            # Check if the user has enough money for this transaction
            if self.isPoor(userid, ticker_price, quantity, str(ctx.message.guild.id)):
                embed = discord.Embed(
                    description=f"```\n@{ctx.message.author.name}, insufficient funds.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            else:
                tradeid = await self.open_trade(
                    userid,
                    quantity,
                    opentime,
                    ticker_price,
                    ticker,
                    reason,
                    trade_type,
                    str(ctx.message.guild.id),
                )

            # 6. Give confirmation message
            message = f"{ctx.message.author.name} has opened a trade with ID: {tradeid}, Ticker: ${ticker.upper()} at Price: ${round(ticker_price,5)}"

            embed = discord.Embed(
                description=f"```\n{message}\n```",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except:

            embed = discord.Embed(
                description="```\n!buy [Ticker],[Quantity],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def sell(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if ctx.message.channel.id not in self.trade_channel_id:
        #     return
        if ctx.message.channel.name not in self.trade_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 4)
            input_count = len(var)
            ticker = var[0].lower()

            # description="```\n!buy [Ticker],[Price(Optional)],[Reasoning(Optional)]\n```",
            # if input_count < 1:

            #     embed = discord.Embed(
            #         description="```\n!buy [Ticker],[Price(Optional)],[Reasoning(Optional)]\n```",
            #         color=discord.Color.red(),
            #     )
            #     await ctx.send(embed=embed)
            #     return

            # 1. Check if Ticker is valid
            if ticker not in self.cg_tokens:
                self.cg_tokens = self.get_coingecko_tokens()
                if ticker not in self.cg_tokens:
                    embed = discord.Embed(
                        description=f"```\n{var[0]} is not a valid ticker.\n```",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return
            ticker_price = 0
            reason = ""
            quantity = 0

            # verify quantity    ***********************************************************  Need to update to take in percentages
            try:

                if var[1].endswith("%"):

                    try:

                        qnum = var[1].split("%", 1)[0]  # 20% / 100 = 0.2

                        qnum = float(qnum)
                        qnum = qnum / 100

                    except:
                        embed = discord.Embed(
                            description="```\nInvalid quantity.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return
                else:
                    quantity = float(var[1])
                    if quantity <= 0:
                        embed = discord.Embed(
                            description="```\nInvalid quantity.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return
            except:
                embed = discord.Embed(
                    description="```\nInvalid quantity.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # ticker already settled, check price
            if input_count == 2:
                ticker_price = self.get_token_price(ticker)
                reason = ""
            if input_count >= 3:
                if var[2] == "":
                    ticker_price = self.get_token_price(ticker)
                else:
                    try:
                        ticker_price = float(var[2])
                        if ticker_price <= 0:
                            embed = discord.Embed(
                                description="```\nInvalid price.\n```",
                                color=discord.Color.red(),
                            )
                            await ctx.send(embed=embed)
                            return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                    except:
                        embed = discord.Embed(
                            description="```\nInvalid price.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                if input_count == 4:
                    reason = var[3]
                else:
                    reason = ""

            userid = ctx.message.author.id
            opentime = int(time.time())
            trade_type = "short"

            # Adjust quantity if percentage was used.
            if var[1].endswith("%"):
                user_balance = await self.get_balance(userid, str(ctx.message.guild.id))
                user_total_balance = await self.get_total_balance(
                    userid, str(ctx.message.guild.id)
                )
                user_debt = await self.get_debt(userid, str(ctx.message.guild.id))
                available_debt_alllowance = (user_total_balance * 0.5) - user_debt
                portion = available_debt_alllowance * qnum
                quantity = portion / ticker_price

            # Check if the user has enough money for this transaction
            debt_limit = await self.isAboveDebtLimit(
                userid, ticker_price, quantity, str(ctx.message.guild.id)
            )
            if debt_limit:
                embed = discord.Embed(
                    description=f"```\n@{ctx.message.author.name}, cannot exceed 50% Debt to Balance ratio.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            else:
                tradeid = await self.open_trade(
                    userid,
                    quantity,
                    opentime,
                    ticker_price,
                    ticker,
                    reason,
                    trade_type,
                    str(ctx.message.guild.id),
                )
            # Update total profit to account for new debt
            try:
                await self.update_profit(
                    ctx.message.author.id, str(ctx.message.guild.id)
                )
            except Exception as e:
                print(e)
                embed = discord.Embed(
                    description="```\nError: Close Update Function.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

                return

            # 6. Give confirmation message
            message = f"{ctx.message.author.name} has opened a trade with ID: {tradeid}, Ticker: ${ticker.upper()} at Price: ${round(ticker_price,5)}"

            embed = discord.Embed(
                description=f"```\n{message}\n```",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except:

            embed = discord.Embed(
                description="```\n!sell [Ticker],[Quantity],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def close(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if ctx.message.channel.id not in self.trade_channel_id:
        #     return
        if ctx.message.channel.name not in self.trade_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 2)
            input_count = len(var)
            if var[0] == None:
                embed = discord.Embed(
                    description="```\n!close [TradeID],[Price(Optional)],[Reasoning(Optional)]\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 1. Check if TradeId is valid
            if not self.trade_exists(int(var[0]), str(ctx.message.guild.id)):
                embed = discord.Embed(
                    description="```\nInvalid Trade Id. Use the '!open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 2. Check if userid attached to tradeid matches userid
            if not self.isOwner(
                int(var[0]), ctx.message.author.id, str(ctx.message.guild.id)
            ):
                embed = discord.Embed(
                    description="```\nThis trade does not belong to you. Use the '!open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 3. Check if the trade is already closed.
            if not self.isOpen(int(var[0]), str(ctx.message.guild.id)):
                embed = discord.Embed(
                    description="```\nThis trade is already closed. Use the '!open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # If input count 1 => only tradeid is passed, calculate price and submit
            if input_count == 1:

                ticker = await self.get_ticker(int(var[0]), str(ctx.message.guild.id))
                close_price = self.get_token_price(ticker)
                reason = ""

            # If input count 2 => price is passed in. validate it.
            elif input_count >= 2:
                if var[1] == "":
                    ticker = await self.get_ticker(
                        int(var[0]), str(ctx.message.guild.id)
                    )
                    close_price = self.get_token_price(ticker)
                else:
                    try:
                        close_price = float(var[1])
                        if close_price <= 0:
                            embed = discord.Embed(
                                description="```\nInvalid Close price.\n```",
                                color=discord.Color.red(),
                            )
                            await ctx.send(embed=embed)
                            return
                    except:
                        embed = discord.Embed(
                            description="```\nClosing price was not a valid number.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return
                if input_count == 3:
                    reason = var[2]
                else:
                    reason = ""
            # if input count 3 => everything is passed in, validate price, pass in reasoning
            else:
                close_price = 0
                reason = ""

            # 4. Check if the price is valid float
            # try:
            #     close_price = float(var[1])
            # except:
            #     embed = discord.Embed(
            #         description="```\nClosing price was not a valid number.\n```",
            #         color=discord.Color.red(),
            #     )
            #     await ctx.send(embed=embed)
            #     return
            # 4a. We currently have the tradeid and price. Now check if reasoning is provided.
            # try:
            #     reason = var[2]
            # except:
            #     reason = ""

            # Before closing a short (sell) position, check if the available balance is enough to pay off the debt.
            if not self.check_short_position(
                int(var[0]),
                ctx.message.author.id,
                str(ctx.message.guild.id),
                close_price,
            ):
                embed = discord.Embed(
                    description=f"```\n{ctx.message.author.name}, you do not have the funds to close this short position.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return
            # 5. Call the close_trade function using tradeid, price, and reason.
            try:
                close_time = int(time.time())
                (
                    profit,
                    ticker,
                    percent,
                    duration,
                    quantity,
                    cp,
                ) = await self.close_trade(
                    int(var[0]),
                    close_price,
                    reason,
                    close_time,
                    str(ctx.message.guild.id),
                )

            except:
                embed = discord.Embed(
                    description="```\nError: Close Function\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

                return

            # 6. Update total profits for userid += profit
            try:
                await self.update_profit(
                    ctx.message.author.id, str(ctx.message.guild.id)
                )
            except:
                embed = discord.Embed(
                    description="```\nError: Close Update Function.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

                return

            # 7. send: Bot: Trade with ID 0 has been closed, ticker: $SNX profit: 100%, duration of trade: 1 day and 1 hour, with reasoning ???My work is done???
            embed = discord.Embed(
                description=f"```\nTrade with ID: {var[0]} has been closed. \nTicker: ${ticker.upper()}\nProfit: ${profit}({percent}%)\nDuration of trade: {duration}\nQuantity: {round(quantity,5)}\nClose Price: ${round(cp,3)}\nReasoning: '{reason}'\n```",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)

        except:

            embed = discord.Embed(
                description="```\n!close [TradeID],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def open_trades(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if not ctx.message.channel.id in self.trade_info_channel_id:
        if not ctx.message.channel.name in self.trade_info_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        open_trades = await self.get_open_trades(
            ctx.message.author.id, str(ctx.message.guild.id)
        )

        """
        User: !view-open-trades
        Bot output:
        A table with all trades currently open: 
        ID, Ticker, Price, Quantity, Date-and-time-opened, reason 
        """
        if len(list(open_trades)) == 0:
            embed = discord.Embed(
                description=f"```\nYou do not have any open trades.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        open_trades = await self.get_open_trades(
            ctx.message.author.id, str(ctx.message.guild.id)
        )
        disc = f"```\n@{ctx.message.author.name}\nType Trade_ID  Ticker Quantity Open_Price  Date/Time  Reason\n\n"
        for i in open_trades:
            tid = i["_id"]
            ticker = i["ticker"]
            price = i["open_price"]
            quantity = i["quantity"]
            open_time = i["open_date"]
            date = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(open_time))
            reason = i["open_reason"]
            trade_type = i["type"]
            disc = (
                disc
                + f"{trade_type.upper()}  {tid}  ${ticker}  {round(quantity,5)}  {round(price,5)}  {date}  {reason}\n\n"
            )
            if len(disc) + 123 >= 2000:
                footer = "```"
                disc = disc + footer
                await ctx.send(disc)
                disc = f"```\n@{ctx.message.author.name}\nType Trade_ID  Ticker Quantity Open_Price  Date/Time  Reason\n\n"

        footer = "```"
        disc = disc + footer

        await ctx.send(disc)

    @commands.command()
    async def closed_trades(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if not ctx.message.channel.id in self.trade_info_channel_id:
        if not ctx.message.channel.name in self.trade_info_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        closed_trades = await self.get_closed_trades(
            ctx.message.author.id, str(ctx.message.guild.id)
        )

        if len(list(closed_trades)) == 0:
            embed = discord.Embed(
                description=f"```\nYou do not have any closed trades.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        """
        User: !view-closed-trades
        A table with all trades closed in the past: 
        ID, Ticker, Price-opened, Price-Closed, Profit-trade, Date-and-time-opened, Date-and-time-closed        
        """
        closed_trades = await self.get_closed_trades(
            ctx.message.author.id, str(ctx.message.guild.id)
        )
        disc = f"```\n@{ctx.message.author.name}\nType  Trade_ID  Ticker  Quantity  Open_Price  Close_Price  Profit  Open_Date  Close_date\n\n"
        counter = 0
        ct_length = len(list(closed_trades))
        ct_start = ct_length - 50
        closed_trades = await self.get_closed_trades(
            ctx.message.author.id, str(ctx.message.guild.id)
        )

        for i in closed_trades:
            if counter < ct_start:

                counter += 1
            else:
                tid = i["_id"]
                ticker = i["ticker"]
                open_price = i["open_price"]
                closed_price = i["close_price"]
                percent = i["percent"]
                profit = round(open_price * percent, 3)
                open_time = i["open_date"]
                open_date = time.strftime(
                    "%Y-%m-%d %H:%M %Z", time.localtime(open_time)
                )
                close_time = i["close_date"]
                close_date = time.strftime(
                    "%Y-%m-%d %H:%M %Z", time.localtime(close_time)
                )
                reason = i["close_reason"]
                trade_type = i["type"]
                quantity = i["quantity"]
                disc = (
                    disc
                    + f"{trade_type.upper()}  {tid}  ${ticker}  {quantity}  {open_price}  {closed_price}  {profit}({round(percent,5)}%)  {open_date}  {close_date}  {reason}\n\n"
                )
                if len(disc) + 123 >= 2000:
                    footer = "```"
                    disc = disc + footer
                    await ctx.send(disc)
                    disc = f"```\n@{ctx.message.author.name}\nType  Trade_ID  Ticker  Quantity  Open_Price  Close_Price  Profit  Open_Date  Close_date\n\n"

        footer = "```"
        disc = disc + footer

        await ctx.send(disc)

    @commands.command()
    async def total_profit(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if not ctx.message.channel.id in self.trade_info_channel_id:
        if not ctx.message.channel.name in self.trade_info_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        total_profit = await self.get_user_total_profit(
            ctx.message.author.id, str(ctx.message.guild.id)
        )
        embed = discord.Embed(
            description=f"Total profit for {ctx.message.author.name}: {total_profit}%",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def delete(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if ctx.message.channel.id not in self.trade_channel_id:
        #     return
        if ctx.message.channel.name not in self.trade_channel:
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        # 1. Split content
        try:
            content = ctx.message.content.split(" ", 1)[1]

            # 3. Validate the trade id
            try:
                trade_id = int(content)
            except:
                embed = discord.Embed(
                    description="```\nInvalid Trade ID.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 4. Does the trade exist
            if not self.trade_exists(trade_id, str(ctx.message.guild.id)):
                embed = discord.Embed(
                    description=f"```\nCould not find Trade ID: {trade_id}\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 5. Does the trade belong to the caller
            if not self.isOwner(
                trade_id, ctx.message.author.id, str(ctx.message.guild.id)
            ):
                embed = discord.Embed(
                    description=f"```\nTrade: {trade_id} does not belong to you. Please view your trades using the '!open_trades' or '!closed_trades' commands\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 6. Set deleted flag to True
            await self.delete_trade(trade_id, str(ctx.message.guild.id))
            # 7. Give deleted message
            embed = discord.Embed(
                description=f"```\nTrade: {trade_id} has been successfully deleted.\n```",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
        except:
            embed = discord.Embed(
                description="```\n!delete [Trade ID]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

    @commands.command()
    async def leaderboard(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        # if not ctx.message.channel.id in self.trade_info_channel_id:
        if not ctx.message.channel.name in self.trade_info_channel:
            return
        users = await self.trade_leaderboard(
            str(ctx.message.guild.id)
        )  # users holds array of userid, name, total_profit in descending order

        # _leaderboard = "```\nUserAvailable BalanceDebtTotalProfitTradesUserAvailable BalanceDebtTotalP11234\n"
        _leaderboard = "```\n[ LEADERBOARD ]\nUser                Total        Debt        Avail Bal.   Profit   Trades\n"

        # Loop through each user and display the user, total profit, and number of trades.
        # Call a function that counts the number of trades made by the user.
        rank = 0

        for i in users:
            rank += 1

            user = i["name"]
            balance = round(i["balance"], 5)
            debt = round(i["debt"], 5)

            long_position = await self.get_long_position(
                i["userid"], str(ctx.message.guild.id)
            )

            # total = round(
            #     (((i["balance"] + long_position - i["debt"]) - 100000) / 100000) * 100
            # )
            total = i["total_profit"]
            trade = await self.get_trade_number(i["userid"], str(ctx.message.guild.id))
            total_balance = balance + long_position - debt
            # Calculate space for User              20
            user_space_num = 19 - len(user) - len(str(rank))

            user_space = ""
            for i in range(user_space_num):
                user_space = user_space + " "

            # Calculate total balance space 12
            total_balance_space = ""
            tbs_num = 12 - len(str(int(total_balance)))
            for i in range(tbs_num):
                total_balance_space = total_balance_space + " "

            # Calculate space for Total Profit      10 - 10000.000%
            total_space_num = 10 - len(str(round(total, 3)))
            total_space = ""
            for i in range(total_space_num):
                total_space = total_space + " "

            # # Calculate space for available Balance     18
            balance_space = " "
            balance_space_num = 11 - len(str(int(balance)))
            for i in range(balance_space_num):
                balance_space = balance_space + " "

            # # Calculate space for Debt     13
            debt_space = " "
            debt_space_num = 10 - len(str(int(debt)))
            for i in range(debt_space_num):
                debt_space = debt_space + " "

            # line = f"{rank}. {user}{user_space}${balance}{balance_space}${debt}{debt_space}{total}%{total_space}{trade}\n"
            line = f"{rank}.{user}{user_space}${int(total_balance)}{total_balance_space}${int(debt)}{debt_space}${int(balance)}{balance_space}{round(total,3)}%{total_space}{trade}\n"
            _leaderboard = _leaderboard + line
            if (len(_leaderboard) + 78) >= 2000:
                footer = "```"
                _leaderboard = _leaderboard + footer
                await ctx.send(_leaderboard)
                _leaderboard = "```\nUser                Total        Debt        Avail Bal.   Profit   Trades\n"

        footer = "```"
        _leaderboard = _leaderboard + footer

        # There is a send limit of 2000 bytes, we want to clear it and continue.

        # embed = discord.Embed(description=_leaderboard, title="Trading Leaderboard")
        await ctx.send(_leaderboard)

    @commands.command()
    async def help2(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        with open("help.txt", "r") as helper:
            lines = helper.readlines()
            blurp = "```"
            for i in lines:
                blurp = blurp + i + "\n"
            blurp = blurp + "```"
            await ctx.send(blurp)
            return

    @commands.command()
    async def help(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):

            return
        # if (
        #     ctx.message.channel.id not in self.trade_channel_id
        #     and ctx.message.channel.id not in self.trade_info_channel_id
        # ):

        #     return
        if (
            ctx.message.channel.name not in self.trade_channel
            and ctx.message.channel.name not in self.trade_info_channel
        ):
            return
        # if ctx.message.channel.id in self.trade_channel_id:
        if ctx.message.channel.name in self.trade_channel:
            with open("trade_commands.txt", "r") as bcmd:
                results = bcmd.readlines()
                blurb = ""
                for i in results:
                    blurb = blurb + i + "\n"
                embed = discord.Embed(
                    description=f"```\n{blurb}\n```",
                    color=discord.Color.blue(),
                    title="Trade Commands",
                )
                await ctx.send(embed=embed)
            return

        # if ctx.message.channel.id in self.trade_info_channel_id:
        if ctx.message.channel.name in self.trade_info_channel:
            print("match trade info channel")
            with open("trade_info_commands.txt", "r") as bcmd:
                results = bcmd.readlines()
                blurb = ""
                for i in results:
                    blurb = blurb + i + "\n"
                embed = discord.Embed(
                    description=f"```\n{blurb}\n```",
                    color=discord.Color.blue(),
                    title="Trade Info Commands",
                )
                await ctx.send(embed=embed)
            return
        # await ctx.send(f"Length of self.cg_tokens is: {len(self.cg_tokens)}")

    @commands.command()
    async def start_game(self, ctx):  # Completely restart a game in that server
        if not self.isTradingPost(str(ctx.message.guild.id)):
            db = self.client[str(ctx.message.guild.id)]
            db["TRADES"].insert_one({"count": 0})
            await ctx.send("Welcome Apes to the Trading Game.\n\n")

    # @commands.command()
    # async def set_trade_channel(self, ctx):
    #     if not self.isTradingPost(str(ctx.message.guild.id)):
    #         return
    #     if ctx.message.channel.id not in self.trade_channel_id:
    #         self.trade_channel_id.append(ctx.message.channel.id)
    #         await ctx.send("Trade Channel has been added.")

    # @commands.command()
    # async def set_trade_info_channel(self, ctx):
    #     if not self.isTradingPost(str(ctx.message.guild.id)):
    #         return
    #     if ctx.message.channel.id not in self.trade_info_channel_id:
    #         self.trade_info_channel_id.append(ctx.message.channel.id)
    #         await ctx.send("Trade Info Channel has been added.")

    # @commands.command()
    # async def remove_trade_channel(self, ctx):
    #     if not self.isTradingPost(str(ctx.message.guild.id)):
    #         return
    #     try:
    #         self.trade_channel_id.remove(ctx.message.channel.id)
    #         await ctx.send("Trade Channel removed.")
    #     except:
    #         pass

    # @commands.command()
    # async def remove_trade_info_channel(self, ctx):
    #     if not self.isTradingPost(str(ctx.message.guild.id)):
    #         return
    #     try:
    #         self.trade_info_channel_id.remove(ctx.message.channel.id)
    #         await ctx.send("Trade Info Channel has been removed.")
    #     except:
    #         pass

    # @commands.command()
    # async def end_game(self, ctx):  # End game in server     ==> Close every transaction with auto find prices, if not found, then 0. Produce leaderboard
    #     if not self.isTradingPost(str(ctx.message.guild.id)):
    #         return
    #     pass

    @commands.command()
    async def reset_account(self, ctx):  # Check for game over status before restarting
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return

        # if (
        #     ctx.message.channel.id not in self.trade_channel_id
        #     and ctx.message.channel.id not in self.trade_info_channel_id
        # ):
        #     return
        if (
            ctx.message.channel.name not in self.trade_channel
            and ctx.message.channel.name not in self.trade_info_channel
        ):
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        if not self.isGameover(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\n{ctx.message.author.name}, you're still in it to win it. Hang in there!\n```",
                color=discord.Color.dark_blue(),
            )
            await ctx.send(embed=embed)
            return

        await self.reset(ctx.message.author.id, str(ctx.message.guild.id))
        embed = discord.Embed(
            description=f"```\n{ctx.message.author.name}: Account Reset\n```",
            color=discord.Color.dark_purple(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def balance(self, ctx):
        if not self.isTradingPost(str(ctx.message.guild.id)):
            return
        if not self.isInitialized(ctx.message.author.id, str(ctx.message.guild.id)):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        user_balance = await self.get_balance(
            ctx.message.author.id, str(ctx.message.guild.id)
        )
        debt = await self.get_debt(ctx.message.author.id, str(ctx.message.guild.id))

        total = await self.get_total_balance(
            ctx.message.author.id, str(ctx.message.guild.id)
        )

        debt_space = ""
        for i in range(13):
            debt_space = debt_space + " "
        total_space = ""
        for i in range(4):
            total_space = total_space + " "

        embed = discord.Embed(
            description=f"```\nAvailable Balance: ${round(user_balance,5)}\nDebt: {debt_space}${round(debt,5)}\nTotal Balance: {total_space}${round(total,5)}\n```",
            color=discord.Color.dark_green(),
            title=f"{ctx.message.author.name}",
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def channelid(self, ctx):
        print(ctx.message.channel.name)
        print(ctx.message.channel.id)
