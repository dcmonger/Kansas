#!/usr/bin/env python3

import os
import pprint
import re
import urllib.request

pp = pprint.PrettyPrinter(indent=2)


def name_to_url(name):
    req = urllib.request.Request(
        "http://magiccards.info/query?q=!%s&v=card&s=cname" % "+".join(name.split())
    )
    stream = urllib.request.urlopen(req)
    data = stream.read().decode("utf-8", errors="ignore")
    match = re.search(r'"https?://magiccards.info/scans/en/[a-z0-9]*/[0-9]*.jpg"', data)
    if not match:
        raise ValueError(f"No image URL found for card: {name}")
    return match.group()[33:-1]


def main():
    decklist = []
    for filename in os.listdir("deckdir"):
        i = 0
        deckdata = {
            "deck_name": filename,
            "urls": {},
        }
        with open(f"deckdir/{filename}") as deck:
            for read in deck:
                for line in read.strip().split("\n"):
                    if line:
                        num, name = line.split(" ", 1)
                        num = int(num)
                        try:
                            url = name_to_url(name)
                            for _ in range(num):
                                deckdata["urls"][i] = url
                                i += 1
                        except Exception as e:
                            print("failed", e)
        decklist.append(deckdata)

    data = pp.pformat(decklist)
    with open("decks.py", "w") as outputdeck:
        outputdeck.write("decklist = ")
        outputdeck.write(data)


if __name__ == "__main__":
    main()
