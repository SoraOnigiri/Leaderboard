import requests
import json

# Returns an Array of dict coins
#   [{
#     "id": "01coin",
#     "symbol": "zoc",
#     "name": "01coin"
#   }]

# r = requests.get("https://api.coingecko.com/api/v3/coins/list")

# tokens = {}

# for token in r.json():
#     tokens[token["symbol"]] = {"id": token["id"], "name": token["name"]}

# with open("tokens.json", "w") as outfile:
#     json.dump(tokens, outfile)
with open("coins.json", "r") as commands:
    print(len(json.load(commands)))
