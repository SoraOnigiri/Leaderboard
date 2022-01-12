import discord
from discord.ext import commands
import requests
import json
import time
from settings import *


class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cg_tokens = {}
        self.setup()

    def setup(self):
        self.cg_tokens = self.get_coingecko_tokens()
        self.DB = self.get_database("Leaderboard")
        self.tradeCol = self.DB["TRADES"]
        self.userCol = self.DB["USER"]
        self.trade_channel_id = int(os.getenv("TRADE_CHANNEL"))
        self.trade_info_channel_id = int(os.getenv("TRADE_INFO_CHANNEL"))

    def get_coingecko_tokens(self):
        # CoinGecko token database
        r = requests.get("https://api.coingecko.com/api/v3/coins/list")
        tokens = {}
        for token in r.json():
            tokens[token["symbol"]] = {"id": token["id"], "name": token["name"]}
        return tokens

    def get_database(self, title):
        dbpass = os.getenv("DBPASS")
        dbuser = os.getenv("DBUSER")
        dbaddress = os.getenv("DBADDRESS")
        # Provide the mongodb atlas url to connect python to mongodb using pymongo
        CONNECTION_STRING = f"mongodb+srv://{dbuser}:{dbpass}@{dbaddress}"

        # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
        from pymongo import MongoClient

        client = MongoClient(CONNECTION_STRING)

        # Create the database for our example (we will use the same database throughout the tutorial
        return client[title]

    def isInitialized(self, userid):
        if self.userCol.find_one({"userid": userid}) is None:
            return False
        return True

    def initialize_user(self, userid, name):
        user = {"userid": userid, "total_profit": 0, "name": name}
        self.userCol.insert_one(user)

    def get_token_price(self, ticker):
        id = self.cg_tokens[ticker]["id"]
        currency = "usd"
        pto = int(time.time())
        pfrom = pto - 1000

        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{id}/market_chart/range?vs_currency={currency}&from={str(pfrom)}&to={str(pto)}"
        )
        results = r.json()
        # {"prices":[1641567677939,3226.1455591491567],[1641568160652,3196.3101680587015],[1641568388161,3189.864689613417]}
        price = float(results["prices"][-1][1])
        return price

    def trade_exists(self, trade_id):
        trade = self.tradeCol.find_one({"_id": trade_id})
        if trade:
            if trade["deleted"]:
                return False
            return True
        return False

    def isOwner(self, trade_id, user_id):
        trade = self.tradeCol.find_one({"_id": trade_id})
        if trade["userid"] == user_id:
            return True
        return False

    def isOpen(self, trade_id):
        trade = self.tradeCol.find_one({"_id": trade_id})
        return trade["isOpen"]

    async def get_ticker(self, trade_id):
        trade = self.tradeCol.find_one({"_id": trade_id})
        ticker = trade["ticker"]
        return ticker

    async def open_trade(self, userid, time, price, ticker, reason, trade_type):
        deleted = False
        trade_id = self.tradeCol.find_one()["count"]
        trade = {
            "_id": trade_id + 1,
            "userid": userid,
            "open_date": time,
            "open_price": price,
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
        self.tradeCol.insert_one(trade)
        qcount = {"count": trade_id}
        updcount = {"$set": {"count": trade_id + 1}}
        self.tradeCol.update_one(qcount, updcount)
        return trade_id + 1

    async def close_trade(self, tradeid, price, reason, time):
        trade = self.tradeCol.find_one({"_id": tradeid})
        cost = float(trade["open_price"])
        sale = float(price)
        ticker = trade["ticker"]
        if trade["type"] == "long":
            profit = round((sale - cost), 5)
            percent = round((profit / cost) * 100, 5)
        else:  # if not long then short       for a short: open_price is price that it is purchased. sale price is price that it was bought back at.
            profit = round((cost - sale), 5)
            percent = round((profit / cost) * 100, 5)
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
        self.tradeCol.update_one(query, update)
        seconds = time - trade["open_date"]  # in seconds
        days = int(seconds / 86400)
        hours = (seconds % 86400) / 3600
        duration = f"{int(days)} day(s) and {round(hours,1)} hour(s)"
        trade_type = trade["type"]
        return profit, ticker, percent, duration

    async def update_profit(self, userid, profit):
        user = self.userCol.find_one({"userid": userid})
        _profit = profit + user["total_profit"]
        query = {"userid": userid}
        update = {"$set": {"total_profit": _profit}}
        self.userCol.update_one(query, update)

    async def get_open_trades(self, userid):
        open_trades = self.tradeCol.find(
            {"userid": userid, "isOpen": True, "deleted": False}
        )  # returns pymongo object. Must iterate through them.
        return open_trades

    async def get_closed_trades(self, userid):

        closed_trades = self.tradeCol.find(
            {"userid": userid, "isOpen": False, "deleted": False}
        )
        return closed_trades

    async def get_total_profit(self, userid):
        user = self.userCol.find_one({"userid": userid})
        total = user["total_profit"]
        return total

    async def delete_trade(self, trade_id):
        query = {"_id": trade_id}
        update = {"$set": {"deleted": True}}
        self.tradeCol.update_one(query, update)
        trade = self.tradeCol.find_one(query)
        user = self.userCol.find_one({"userid": trade["userid"]})
        q2 = {"userid": trade["userid"]}
        upd = {"$set": {"total_profit": user["total_profit"] - trade["percent"]}}
        self.userCol.update_one(q2, upd)

    async def trade_leaderboard(self):
        users = self.userCol.find({}, {"_id": 0}).sort("total_profit", -1)
        return users

    async def get_trade_number(self, userid):
        trades = self.tradeCol.find(
            {"userid": userid, "deleted": False, "isOpen": False},
            {
                "_id": 1,
                "userid": 0,
                "open_date": 0,
                "open_price": 0,
                "ticker": 0,
                "open_reason": 0,
                "profit": 0,
                "percent": 0,
                "close_price": 0,
                "close_date": 0,
                "close_reason": 0,
                "deleted": 0,
                "isOpen": 0,
            },
        )

        return len(list(trades))

    @commands.command()
    async def join(self, ctx):
        if (
            not ctx.message.channel.id == self.trade_channel_id
            and not ctx.message.channel.id == self.trade_info_channel_id
        ):
            return
        if self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou've already joined the Trading Game.\n```",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            return
        try:
            self.initialize_user(ctx.message.author.id, ctx.message.author.name)
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
    async def buy(self, ctx):
        if not self.trade_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 3)
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
            # ticker already settled, check price
            if input_count == 1:
                ticker_price = self.get_token_price(ticker)
                reason = ""
            if input_count >= 2:
                if var[1] == "":
                    ticker_price = self.get_token_price(ticker)
                else:
                    try:
                        ticker_price = float(var[1])
                    except:
                        embed = discord.Embed(
                            description="```\nInvalid price.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                if input_count == 3:
                    reason = var[2]
                else:
                    reason = ""
            # 3. Check if there is Price
            # if input_count >= 3:
            #     try:
            #         ticker_price = float(var[2])
            #     except:
            #         embed = discord.Embed(
            #             description="```\nInvalid price.\n```",
            #             color=discord.Color.red(),
            #         )
            #         await ctx.send(embed=embed)
            #         return  # Get price from coingeckon_price(self.cg_tokens[ticker])
            # else:

            #     ticker_price = self.get_token_price(ticker)

            # 4. Check if there is Reason
            # if input_count == 4:
            #     reason = var[3]
            # else:
            #     reason = ""

            # 5. Call open_trade function
            # At this point, we have the ticker, quantity, price, and reasoning. Need to build the trade now.
            userid = ctx.message.author.id
            opentime = int(time.time())
            trade_type = "long"
            tradeid = await self.open_trade(
                userid, opentime, ticker_price, ticker, reason, trade_type
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
                description="```\n!buy [Ticker],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def sell(self, ctx):
        if not self.trade_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        try:
            content = ctx.message.content.split(" ", 1)[1]
            var = content.split(",", 3)
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
            # ticker already settled, check price
            if input_count == 1:
                ticker_price = self.get_token_price(ticker)
                reason = ""
            if input_count >= 2:
                if var[1] == "":
                    ticker_price = self.get_token_price(ticker)
                else:
                    try:
                        ticker_price = float(var[1])
                    except:
                        embed = discord.Embed(
                            description="```\nInvalid price.\n```",
                            color=discord.Color.red(),
                        )
                        await ctx.send(embed=embed)
                        return  # Get price from coingeckon_price(self.cg_tokens[ticker])
                if input_count == 3:
                    reason = var[2]
                else:
                    reason = ""

            userid = ctx.message.author.id
            opentime = int(time.time())
            trade_type = "short"
            tradeid = await self.open_trade(
                userid, opentime, ticker_price, ticker, reason, trade_type
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
                description="```\n!sell [Ticker],[Price(Optional)],[Reasoning(Optional)]\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command()
    async def close(self, ctx):
        if not self.trade_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
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
            if not self.trade_exists(int(var[0])):
                embed = discord.Embed(
                    description="```\nInvalid Trade Id. Use the '!view_open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 2. Check if userid attached to tradeid matches userid
            if not self.isOwner(int(var[0]), ctx.message.author.id):
                embed = discord.Embed(
                    description="```\nThis trade does not belong to you. Use the '!view_open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 3. Check if the trade is already closed.
            if not self.isOpen(int(var[0])):
                embed = discord.Embed(
                    description="```\nThis trade is already closed. Use the '!view_open_trades' command to see your open trades.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # If input count 1 => only tradeid is passed, calculate price and submit
            if input_count == 1:

                ticker = await self.get_ticker(int(var[0]))
                close_price = self.get_token_price(ticker)
                reason = ""

            # If input count 2 => price is passed in. validate it.
            elif input_count >= 2:
                if var[1] == "":
                    ticker = await self.get_ticker(int(var[0]))
                    close_price = self.get_token_price(ticker)
                else:
                    try:
                        close_price = float(var[1])
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

            # 5. Call the close_trade function using tradeid, price, and reason.
            try:
                close_time = int(time.time())
                profit, ticker, percent, duration = await self.close_trade(
                    int(var[0]), close_price, reason, close_time
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
                await self.update_profit(ctx.message.author.id, percent)
            except:
                embed = discord.Embed(
                    description="```\nError: Close Update Function.\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)

                return

            # 7. send: Bot: Trade with ID 0 has been closed, ticker: $SNX profit: 100%, duration of trade: 1 day and 1 hour, with reasoning “My work is done”
            embed = discord.Embed(
                description=f"```\nTrade with ID: {var[0]} has been closed. Ticker: ${ticker.upper()}, Profit: {percent}%, Duration of trade: {duration}, with reasoning '{reason}'\n```",
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
    async def view_open_trades(self, ctx):
        if not self.trade_info_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        open_trades = await self.get_open_trades(ctx.message.author.id)

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

        open_trades = await self.get_open_trades(ctx.message.author.id)
        disc = "```\nType Trade_ID  Ticker  Open_Price  Date/Time  Reason\n\n"
        for i in open_trades:
            tid = i["_id"]
            ticker = i["ticker"]
            price = i["open_price"]
            open_time = i["open_date"]
            date = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(open_time))
            reason = i["open_reason"]
            trade_type = i["type"]
            disc = (
                disc
                + f"{trade_type.upper()}  {tid}  ${ticker}  {round(price,5)}  {date}  {reason}\n\n"
            )
        footer = "```"
        disc = disc + footer
        embed = discord.Embed(
            description=disc,
            color=discord.Color.blue(),
        )
        await ctx.send(disc)

    @commands.command()
    async def view_closed_trades(self, ctx):
        if not self.trade_info_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        closed_trades = await self.get_closed_trades(ctx.message.author.id)

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
        closed_trades = await self.get_closed_trades(ctx.message.author.id)
        disc = "```\nType  Trade_ID  Ticker  Open_Price  Close_Price  Profit  Open_Date  Close_date\n\n"

        for i in closed_trades:
            tid = i["_id"]
            ticker = i["ticker"]
            open_price = i["open_price"]
            closed_price = i["close_price"]
            percent = i["percent"]
            open_time = i["open_date"]
            open_date = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(open_time))
            close_time = i["close_date"]
            close_date = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(close_time))
            reason = i["close_reason"]
            trade_type = i["type"]
            disc = (
                disc
                + f"{trade_type.upper()}  {tid}  ${ticker}  {open_price}  {closed_price}  {round(percent,5)}%  {open_date}  {close_date}  {reason}\n\n"
            )
        footer = "```"
        disc = disc + footer
        embed = discord.Embed(
            description=disc,
            color=discord.Color.blue(),
        )
        await ctx.send(disc)

    @commands.command()
    async def total_profit(self, ctx):
        if not self.trade_info_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        total_profit = await self.get_total_profit(ctx.message.author.id)
        embed = discord.Embed(
            description=f"Total profit for {ctx.message.author.name}: {total_profit}%",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def delete(self, ctx):
        if not self.trade_channel_id == ctx.message.channel.id:
            return
        if not self.isInitialized(ctx.message.author.id):
            embed = discord.Embed(
                description=f"```\nYou must first type '!join' to participate in the trading leaderboard.\n```",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        # 1. Split content
        try:
            content = ctx.message.content.split(" ", 1)[1]

            # # 2. Validate the command
            # if len(content) == 1:
            #     embed = discord.Embed(
            #         description="```\n!delete [Trade ID]\n```",
            #         color=discord.Color.red(),
            #     )
            #     await ctx.send(embed=embed)
            #     return

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
            if not self.trade_exists(trade_id):
                embed = discord.Embed(
                    description=f"```\nCould not find Trade ID: {trade_id}\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 5. Does the trade belong to the caller
            if not self.isOwner(trade_id, ctx.message.author.id):
                embed = discord.Embed(
                    description=f"```\nTrade: {trade_id} does not belong to you. Please view your trades using the '!view_open_trades' or '!view_closed_trades' commands\n```",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # 6. Set deleted flag to True
            await self.delete_trade(trade_id)
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
        if not self.trade_info_channel_id == ctx.message.channel.id:
            return
        users = (
            await self.trade_leaderboard()
        )  # users holds array of userid, name, total_profit in descending order

        _leaderboard = "```\nUser                     Total Profit        Trades\n"

        # Loop through each user and display the user, total profit, and number of trades.
        # Call a function that counts the number of trades made by the user.
        rank = 0

        for i in users:
            rank += 1

            user = i["name"]

            total = i["total_profit"]

            trade = await self.get_trade_number(i["userid"])

            # Calculate space for User              22
            user_space_num = 23 - len(user) - len(str(rank))

            user_space = ""
            for i in range(user_space_num):
                user_space = user_space + " "
                # Calculate space for Total Profit      20
            total_space_num = 19 - len(str(total))

            total_space = ""
            for i in range(total_space_num):
                total_space = total_space + " "
            line = f"{rank}. {user}{user_space}{total}%{total_space}{trade}\n"

            _leaderboard = _leaderboard + line

        footer = "```"
        _leaderboard = _leaderboard + footer

        embed = discord.Embed(description=_leaderboard, title="Trading Leaderboard")
        await ctx.send(embed=embed)

    @commands.command()
    async def help(self, ctx):
        if (
            not self.trade_info_channel_id == ctx.message.channel.id
            and not self.trade_channel_id == ctx.message.channel.id
        ):
            return
        if self.trade_channel_id == ctx.message.channel.id:
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

        if self.trade_info_channel_id == ctx.message.channel.id:
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
    async def channelid(self, ctx):
        print(ctx.message.channel.name)
        print(ctx.message.channel.id)
