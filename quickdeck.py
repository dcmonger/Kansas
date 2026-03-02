#!/usr/bin/env python3

import os
import pprint
import re
import urllib.parse
import urllib.request

pp = pprint.PrettyPrinter(indent=2)

CARD_IMAGE_RE = re.compile(r'"(https?://magiccards.info/scans/en/[a-z0-9]*/[0-9]*.jpg)"')


def name_to_url(name):
    encoded_name = urllib.parse.quote_plus(name)
    req = urllib.request.Request(
        f"http://magiccards.info/query?q=!{encoded_name}&v=card&s=cname",
        headers={"User-Agent": "Kansas quickdeck/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as stream:
        data = stream.read().decode("utf-8", errors="ignore")

    match = CARD_IMAGE_RE.search(data)
    if not match:
        raise ValueError(f"No image URL found for card: {name}")

    card_url = match.group(1)
    marker = "magiccards.info/scans/en/"
    if marker not in card_url:
        raise ValueError(f"Unexpected card URL format for card: {name}")
    return card_url.split(marker, 1)[1]


def main():
    decklist = []
    for filename in sorted(os.listdir("deckdir")):
        i = 0
        deckdata = {
            "deck_name": filename,
            "urls": {},
        }
        with open(f"deckdir/{filename}", encoding="utf-8") as deck:
            for read in deck:
                line = read.strip()
                if not line:
                    continue
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
    with open("decks.py", "w", encoding="utf-8") as outputdeck:
        outputdeck.write("decklist = ")
        outputdeck.write(data)


if __name__ == "__main__":
    main()
