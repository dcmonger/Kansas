#!/usr/bin/env python

import urllib2
import re
import pprint
import random
import os
outputdeck = open('decks.py', 'w')
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


def name_to_url(name):
  req = urllib2.Request("http://magiccards.info/query?q=!%s&v=card&s=cname" % '+'.join(name.split()))
  stream = urllib2.urlopen(req)
  data = stream.read()
  match = re.search('"http://magiccards.info/scans/en/[a-z0-9]*/[0-9]*.jpg"', data)
  return match.group()[33:-1]

i = 0
for filename in os.listdir('deckdir'):
    deck = open('deckdir/%s' %filename)
    while True:
        read = deck.readline()
        if not read: break
        for line in read.strip().split('\n'):
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
outputdeck.write("DEFAULT_MAGIC_DECK = ")
outputdeck.write(data)
outputdeck.close()
