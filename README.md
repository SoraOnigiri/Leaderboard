Concept 
Discord bot that keeps track of trades made by persons in a #trade channel. 
The bot would be present in two channels, #trades and #trade-info. #trades will be a channel used for people to report their trades that they entered in. #trades-info will be a channel where people can do certain commands to the bot to show e.g. the trades that they are in and leaderboard score (more on this below). 
Execution 
In the #trades channel, users will be able to open a trade and close a trade. There are two types of trades, a short-trade (you sell something) and a long-trade (you buy something). 

So in #trades channel:

Open Long-trade

User input
!BUY, $TICKER (required), PRICE(optional), “REASONING”(optional)
$TICKER: Ticker of the coin, so for example $ETH
PRICE: Price of $TICKER (e.g. ETH), if not filled in, use coingecko.com API to fetch price. If cannot find a fetch price or gives error, give output to user that trade cannot be opened and they need to fill in a price manually. 
Reasoning: Reasoning of entering the trade. If not filled in, leave blank

Bot will record the opening of a trade in a database, with each discord user having its own ID, and each discord user having its own set of trades. The following things should at minimum be record in the database: 
- User-ID
- Trade-ID
- Date-and-time-opened 
- Price-opened
- Ticker
- Reasoning


*Bot output in channel: *
USER has opened a trade with ID $ID, Ticker $TICKER at Price $PRICE

A user can have multiple trades open at the same time. 

Open Short-trade
Opening a short-trade is the same as a Long-trade, only the calculation of the profit is different upon closing the trade. 

Closing a trade
!close, ID, Close-Price, Reasoning(optional)
Closes trade with id of ID of the user with Close-Price
ID is the ID of the trade generated upon opening a trade. 

Upon closing a trade, the bot calculates and records in the database the following:
- Profit-trade:
For a long-trade that is: (close price – open-price)/(open price)
And for a short-trade that is: (open price –  close price) /(open price)
- Close-Price (optional/required): again Coingecko API, if not available provide error, and they gotta fill it in manually.
- Date-and-time-closed
- Duration-of-trade: Date-and-time-opened – date-and-time-closed
- Reasoning (optional)

*Bot-output: *
“Trade with ID $ID has been closed, ticker: $ticker profit: $profit, duration of trade: $Duration-of-trade

Example of a long-trade by user Alice: 
Alice: !buy, $SNX, 5, "bullish on SNX”
Bot: Alice has opened a trade with ID 0, Ticker $SNX at Price 5

Recorded in database:
User-ID: (i guess we make each user have a unique user id?, whatever you consider good design)
Trade-ID: 0
Date-and-time-opened: 1 January 2021 3:40 pm GMT
Price-opened: 5
Ticker: $SNX
reasoning: “bullish on SNX” 

2 january 4:40pm GMT, price of SNX is 10
Alice: !close 0 “My work is done” 
Bot: Trade with ID 0 has been closed, ticker: $SNX profit: 100%, duration of trade: 1 day and 1 hour, with reasoning “My work is done” 

*Recorded in database: *
Close-price: 10
Profit-trade: 100%
Date-and-time-closed: 2 January 4:40pm GMT
Duration-of-trade: 1 day and 1 hour
Reasoning: “My work is done” 

#trades-info channel:

User: !view-open-trades
Bot output:
A table with all trades currently open: 
ID, Ticker, Price, Date-and-time-opened 

User: !view-closed-trades
A table with all trades closed in the past: 
ID, Ticker, Price-opened, Price-Closed, Profit-trade, Date-and-time-opened, Date-and-time-closed

User: !total-profit
Sums up all the profit of all trades for that user

!delete ID
Deletes trade with ID. Trade should stay in the database but have a field DELETED: YES Deleted trades shouldn’t be included in any of the user commands like !view-open-trades and !view-closed-trades and !total-profit

!leaderboard
Creates a summary of each trader total profit and amount of trades taken