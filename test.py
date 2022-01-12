import requests
import json
import time

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

# num1 = 1
# num2 = 2

# test = 2
# test2 = 3

# if not test2 == num1 and not test2 == num2:
#     print("test did not match")
# else:
#     print("test matched")
# date = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(str(time)))

message = "1,2,3,4,5,6,,,,,,7,3"
content = message.split(",", 2)
count = len(content)
print(count)

for i in content:
    if i == "":
        print("None")
    else:
        print(i)
