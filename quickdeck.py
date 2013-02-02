#!/usr/bin/env python

import urllib2
import re
import pprint
import random
import os
outputdeck = open('decks.py', 'w')
pp = pprint.PrettyPrinter(indent = 2)


def name_to_url(name):
    req = urllib2.Request("http://magiccards.info/query?q=!%s&v=card&s=cname" % '+'.join(name.split()))
    stream = urllib2.urlopen(req)
    data = stream.read()
    match = re.search('"http://magiccards.info/scans/en/[a-z0-9]*/[0-9]*.jpg"', data)
    return match.group()[33:-1]

decklist = []
for filename in os.listdir('deckdir'):
    i = 0
    deck = open('deckdir/%s' %filename)
    deckdata = {
    'deck_name': filename,
    'urls': {},
    }
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
                deckdata['urls'][i] = url
                i += 1
            except Exception, e:
               print "failed", e
    decklist.append(deckdata)
        
data = pp.pformat(decklist)
outputdeck.write("decklist = ")
outputdeck.write(data)
outputdeck.close()
