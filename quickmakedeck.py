#!/usr/bin/env python

import urllib2
import re
import pprint
import random
deck = open('decks.py', 'w')
pp = pprint.PrettyPrinter(indent = 2)

seq1 = range(0,60)
random.shuffle(seq1)
seq2 = range(60,120)
random.shuffle(seq2)

DEFAULT_MAGIC_DECK = {
    'deck_name': 'Test magic deck',
    'resource_prefix': 'http://magiccards.info/scans/en/',
    'default_back_url': '/third_party/images/mtg_detail.jpg',
    'board': {
        70321710: seq1,
        44892300: seq2
    },
    'hands': {
    },
    'zIndex': {
    },
    'orientations': {
    },
    'urls': {},
    'urls_small': {},
    'back_urls': {
    },
    'titles': {
    }
}

DECK = """
2 Burning-Tree Emissary
3 Druid of the Anima
4 Elvish Visionary
4 Flametongue Kavu
4 Horned Kavu
4 Llanowar Elves
4 Roaring Primadox
4 Shivan Wurm
2 Spike Feeder
3 Thornscape Battlemage
2 Electropotence
4 Kodama's Reach
8 Forest
4 Karplusan Forest
8 Mountain
"""
DECK2 = """
3 Maelstrom Djinn
4 Scornful Egotist
4 Dissipate
2 Go for the Throat
3 Immortal Coil
4 Mana Leak
4 Ponder
3 Puca's Mischief
4 Relic of Progenitus
3 Turn to Mist
4 Web of Inertia
3 Bojuka Bog
4 Dimir Aqueduct
9 Island
6 Swamp

"""
#1  Faith's Shield
#3  Oblivion Ring
def name_to_url(name):
  req = urllib2.Request("http://magiccards.info/query?q=!%s&v=card&s=cname" % '+'.join(name.split()))
  stream = urllib2.urlopen(req)
  data = stream.read()
  match = re.search('"http://magiccards.info/scans/en/[a-z0-9]*/[0-9]*.jpg"', data)
  return match.group()[33:-1]

i = 0
for line in DECK.strip().split('\n'):
  if line:
    num, name = line.split(' ', 1)
    num = int(num)
    try:
      url = name_to_url(name)
      for _ in range(num):
        DEFAULT_MAGIC_DECK['urls'][i] = url
        i += 1
    except Exception, e:
       print "failed", e
for line in DECK2.strip().split('\n'):
  if line:
    num, name = line.split(' ', 1)
    num = int(num)
    try:
      url = name_to_url(name)
      for _ in range(num):
        DEFAULT_MAGIC_DECK['urls'][i] = url
        i += 1
    except Exception, e:
       print "failed", e

data = pp.pformat(DEFAULT_MAGIC_DECK)
deck.write("DEFAULT_MAGIC_DECK = ")
deck.write(data)

deck.close()
