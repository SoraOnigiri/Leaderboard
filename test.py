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
# with open("coins.json", "r") as commands:
#     print(len(json.load(commands)))

# test = [0, 1, 2, 3, 4]
# if test[5]:
#     print("worked")
# else:
#     print("didnt work")

# words = "nospace in between"
# new = words.split(" ", 1)
# print(new)

num = 1111111

print(f"This is a string with num {num}")
