# Plugins for various board games compatible with Kansas.

import collections
import csv
import glob
import json
import logging
import os
import random
import re
import shlex
import time
import urllib.request, urllib.error, urllib.parse


_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))


def _server_path(*parts):
    return os.path.normpath(os.path.join(_SERVER_DIR, *parts))


kThemeBlacklist = { 'of', 'them', 'while', 'bad', 'size', 'share', 'combination', 'exactly', 'opponents', 'shuffles', 'attach', 'turned', 'lost', 'step', 'become', 'attacked', 'produces', 'shares', 'putting', 'second', 'storage', 'abilities', 'blockers', 'upkeep', 'evoke', 'rebound', 'players', 'already', 'tied', 'unpaired', 'unattached', 'deck', 'exchange', 'away', 'been', 'twice', 'returned', 'opening', 'text', 'once', 'leaves', 'leave', 'choice', 'stays', 'still', 'spent', 'returned', 'colorless', 'also', 'a', 'types', 'fewer', 'will', 'reveals', 'single', 'died', 'exchange' 'effect', 'nonbasic', 'word', 'words', 'kit', 'paid', 'random', 'sources', 'casts', 'the', 'in', 'remain', 'false', 'spend', 'total', 'move', 'played', 'entered', 'activated', 'greatest', 'affinity', 'instead', 'declare', 'which', 'attached', 'instead', 'play', 'increasing', 'does', 'assign', 'noncreature', 'unblocked', 'costs', 'kind', 'named', 'maximum', 'greatest', 'owner', 'take', 'remains', 'colors', 'common', 'rather', 'empty', 'there', 'untapped', 'form', 'source', 'flip', 'removed', 'both', 'nontoken', 'for', 'soon', 'much', 'nonwhite', 'nonblack', 'nonred', 'nonblue', 'nongreen', 'loss', 'after', 'before', 'same', 'could', 'begin', 'being', 'bottom', 'and', 'or', 'either', 'draws', 'lasts', 'comes', 'plays', 'change', 'instances', 'third', 'five', 'adds', 'since', 'targets', 'least', 'unattach', 'amount', 'game', 'they', 'one', 'pair', 'discarding', 'causes', 'convoke', 'cause', 'effects', 'back', 'most', 'enough', 'repeat', 'attackers', 'keeps', 'down', 'wins', 'blocks', 'regular', 'untaps', 'forces', 'chooses', 'many', 'enter', 'says', 'treated', 'name', 'call', 'every', 'must', 'though', 'cause', 'give' }


class DefaultPlugin(object):

    def GetBackUrl(self):
        return '/third_party/cards52/cropped/Blue_Back.png'

    def Complete(self, cards):
        return []

    def Fetch(self, name, exact, limit=None):
        return []

    def Sample(self):
        return []

    def SampleDeck(self, term, num_decks):
        return []


class PokerCardsPlugin(DefaultPlugin):
    def Sample(self):
        cards, _ = self.Fetch("", False)
        return ["1 " + c['name'] for c in random.sample(cards, 5)]

    def Fetch(self, name, exact, limit=None):
        stream = []
        for card in glob.glob("../third_party/cards52/cropped/[A-Z0-9][A-Z0-9]*.png"):
            abbrev = card.split("/")[-1].split(".")[0]
            if exact:
                if name.lower() == abbrev.lower():
                    stream.append({
                        'name': abbrev,
                        'img_url': card,
                        'info_url': card,
                    })
            else:
                if name.lower() in abbrev.lower():
                    stream.append({
                        'name': abbrev,
                        'img_url': card,
                        'info_url': card,
                    })
        return stream, {}


landsByColor = {
    'W': 'Plains',
    'R': 'Mountain',
    'U': 'Island',
    'B': 'Swamp',
    'G': 'Forest',
}

def sanitize(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8', errors='ignore')
    return value \
        .replace("Æ", "Ae") \
        .replace("á", "a") \
        .encode('ascii', errors='ignore') \
        .decode('ascii')

class MagicCard(object):

    def __init__(self, row):
        self.goodQuality = None  # if image is modern and not unhinged / unglued
        self.name = sanitize(row[0])
        self.type = row[1]
        self.subtype = row[2]
        self.searchtype = ' '.join([self.type, self.subtype]).lower()
        self.mana = row[3]
        self.cost = int(row[4]) if row[3] else None
        self.text = sanitize(row[5])
        self.set = row[6]
        self.rarity = row[7]
        if self.set in ['Unhinged', 'Unglued']:
            self.goodQuality = False
        coststring = ("mana=%d" % self.cost) if self.cost is not None else ""
        colorstring = ""
        numcolors = 0
        if 'U' in self.mana or ('Land' in self.type and '{U}' in self.text):
            colorstring += "mana=blue "
            numcolors += 1
        if 'B' in self.mana or ('Land' in self.type and '{B}' in self.text):
            colorstring += "mana=black "
            numcolors += 1
        if 'R' in self.mana or ('Land' in self.type and '{R}' in self.text):
            colorstring += "mana=red "
            numcolors += 1
        if 'G' in self.mana or ('Land' in self.type and '{G}' in self.text):
            colorstring += "mana=green "
            numcolors += 1
        if 'W' in self.mana or ('Land' in self.type and '{W}' in self.text):
            colorstring += "mana=white "
            numcolors += 1
        if numcolors > 1:
            colorstring += "mana=multi "
        if numcolors != 0:
            colorstring += "mana=colored "
        if numcolors == 0:
            colorstring += "mana=colorless "
        elif numcolors == 1:
            colorstring += "mana=mono mana=single "
        elif numcolors == 2:
            colorstring += "mana=dual mana=two "
        elif numcolors == 3:
            colorstring += "mana=tri mana=three "
        elif numcolors == 4:
            colorstring += "mana=quad mana=four "
        elif numcolors == 5:
            colorstring += "mana=five mana=all mana=rainbow "
        self.searchtext = ' '.join([self.name, self.type, self.text, self.subtype, coststring, colorstring, 'mana=' + self.mana]).lower()
        self.searchtokens = set(self.searchtext.split())
        self.tokens = (
            [x.lower() for x in set(self.name.split()) if len(x) > 2] +
            [x.lower() for x in set(self.type.split()) if len(x) > 2] +
            [x.lower() for x in set(self.subtype.split()) if len(x) > 2] +
            [x.lower() for x in set(self.text.split()) if len(x) > 3 and re.match('^[a-zA-Z]+$', x)])

        self.byLand = {
            'Plains': 'W',
            'Mountain': 'R',
            'Island': 'U',
            'Swamp': 'B',
            'Forest': 'G',
        }
        self.basicLands = ['Plains', 'Mountain', 'Island', 'Swamp', 'Forest']

    def colors(self):
        text_colors = set([c for c in 'WRBGU' if '{%s}' %c \
            if '{%s}' %c in self.text])

        if self.type == 'Land':
            text_colors = text_colors | set([self.byLand[land] \
                for land in self.basicLands if land in self.text])

        return set(self.mana).union(text_colors).intersection(set('WRBGU'))

    def __repr__(self):
        return str((self.name, self.type, self.mana, self.cost))


class CardCatalog(object):
    def __init__(self, catalogFile, classifyFile, dbPath):
        logging.info("Building card catalog.")
        self.catalogFile = catalogFile
        self.classifyFile = classifyFile
        self.dbPath = dbPath
        self.initialized = True
        self.byType = collections.defaultdict(list)
        self.byName = {}
        self.bySlug = {}
        self.byColor = collections.defaultdict(list)
        self.byCost = collections.defaultdict(list)
        self.byTokens = collections.defaultdict(list)
        try:
            if os.path.exists(classifyFile):
                self.newCards = set([sanitize(x[2:-1]) for x in
                    open(classifyFile).readlines() if x[0] == "0"])
                self.classifiedCards = set([sanitize(x[2:-1]) for x in
                    open(classifyFile).readlines()])
            else:
                raise FileNotFoundError(classifyFile)
        except Exception as e:
            logging.info("Failed to load classification: %s", e)
            self.newCards = set()
        try:
            for c in csv.reader(open(catalogFile), escapechar='\\'):
                try:
                    card = MagicCard(c)
                    if card.name in self.newCards:
                        card.goodQuality = True
                    self._register(card)
                except Exception as e:
                    logging.warning("Failed to parse %s: %s", c, e)
        except Exception as e:
            logging.info("Failed to load catalog: %s", e)
            self.initialized = False
        if not os.path.exists(self.dbPath):
            os.makedirs(self.dbPath, exist_ok=True)
        for c in os.listdir(self.dbPath):
            if not c.endswith(".jpg"):
                continue
            name = c[:-4]
            if name not in self.byName:
                print("WARNING: card missing metadata: " + name)
                card = MagicCard([name, '', '', '', '', '', '', ''])
                self._register(card)
        logging.info("Done building card catalog.")
        self.topTokens = []
        for k, v in self.byTokens.items():
            if len(v) >= 10 and len(v) < 170 and re.match('^[a-z]+$', k):
                if k not in kThemeBlacklist:
                    self.topTokens.append(k)
        logging.info("%d possible themes", len(self.topTokens))
        print(self.topTokens)

        self.byLand = {
            'Plains': 'W',
            'Mountain': 'R',
            'Island': 'U',
            'Swamp': 'B',
            'Forest': 'G',
        }
        self.basicLands = ['Plains', 'Mountain', 'Island', 'Swamp', 'Forest']

    def complement(self, land, lands, taken, theme=None):
        color = self.byLand[land]
        colors = set([self.byLand[l] for l in lands])
        return [
            "4 " + self.chooseSpell(color, colors, 1, 2, taken, theme),
            "3 " + self.chooseSpell(color, colors, 1, 3, taken, theme),
            "3 " + self.chooseSpell(color, colors, 2, 4, taken, theme),
            "3 " + self.chooseSpell(color, colors, 3, 4, taken, theme),
            "3 " + self.chooseSpell(color, colors, 5, 7, taken, theme),
            "1 " + self.chooseSpell(color, colors, 6, 99, taken, theme),
            "1 " + self.chooseSpell(color, colors, 6, 99, taken, theme),
        ]

    def chooseSpell(self, color, colors, minCost, maxCost, taken, theme=None):

        def valid(cand):
            if cand is None: return False
            if not cand.goodQuality: return False
            if cand.type == 'land': return False
            if cand.name in taken: return False
            if cand.cost < minCost: return False
            if cand.cost > maxCost: return False
            if len(cand.colors() - colors) > 0: return False
            return True

        cand = None

        if theme:
            tries = 10
            pool = Catalog.byTokens[random.choice(theme)]
            while not valid(cand) and tries > 0:
                tries -= 1
                cand = random.choice(pool)
            logging.debug(str(["chooseSpell", color, colors, minCost, maxCost, theme, len(taken), cand.name, tries]))

        tries = 30
        while not valid(cand) and tries > 0:
            tries -= 1
            if random.random() < 0.1:
                cand = random.choice(self.byColor['colorless'])
            else:
                cand = random.choice(self.byColor[color])

        taken.add(cand.name)
        return cand.name

    def chooseLand(self, colors):
        for _ in range(20):
            cand = random.choice(self.byType['Land'])
            if cand in self.basicLands: continue
            if len(cand.colors() - colors) == 0:
                break
        return cand.name

    def complete(self, cards):
        deck = {}
        total = 0
        for k, v in cards.items():
            total += v
            try:
                deck[k] = self.byName[k]
            except:
                pass
        logging.info("FOUND " + str(total))
        if total >= 60:
            return []
        colorVotes = collections.defaultdict(float)
        for card in list(deck.values()):
            colors = card.colors()
            for color in colors:
                colorVotes[color] += 1
        rankedColors = sorted([(v, k) for (k, v) in list(colorVotes.items())], reverse=True)
        if len(rankedColors) == 0:
            land1 = random.choice(self.basicLands)
            if random.random() > .5:
                land2 = random.choice(self.basicLands)
            else:
                land2 = land1
        else:
            land1 = landsByColor[rankedColors[0][1]]
            if len(rankedColors) > 1:
                land2 = landsByColor[rankedColors[1][1]]
            else:
                land2 = land1
        out = []
        if land1 == land2:
            if land1 not in cards:
                out.append("20 " + land1)
                total += 20
        else:
            if land1 not in cards:
                out.append("10 " + land1)
                total += 10
            if land2 not in cards:
                out.append("10 " + land2)
                total += 10
        colors = set([self.byLand[l] for l in [land1, land2]])
        taken = set(deck.keys())
        while total < 45:
            out.append("4 " + self.chooseSpell(random.choice(list(colors)), colors, 1, 4, taken))
            total += 4
        while total < 59:
            out.append("2 " + self.chooseSpell(random.choice(list(colors)), colors, 0, 99, taken))
            total += 2
        while total < 60:
            out.append("1 " + self.chooseSpell(random.choice(list(colors)), colors, 0, 99, taken))
            total += 1
        return out

    def makeDeck(self):
        if not self.initialized:
            return []
        land1 = random.choice(self.basicLands)
        land2 = random.choice(self.basicLands)
        if land1 == land2:
            base = ["24 " + land1]
        else:
            base = ["12 " + land1, "12 " + land2]
        cards = []
        taken = {land1, land2}
        cards.extend(self.complement(land1, [land1, land2], taken))
        cards.extend(self.complement(land2, [land1, land2], taken))
        return base + sorted(cards, reverse=True)

    def makeDecks(self, term, num_decks):
        if not self.initialized:
            return {}
        start = time.time()
        output = {}
        random.seed(hash(term))
        # TODO(ekl) dynamically chose the number of decks based on number of search
        # results and number of available combinations based on the input term.
        for i in range(num_decks):
            parts = [p for p in term.split() if p not in kThemeBlacklist]
            def gen():
                word = ''
                avail = list(set(parts))
                if avail:
                    word = random.choice(avail)
                if word not in Catalog.byTokens:
                    tokens = list(Catalog.byTokens)
                    random.shuffle(tokens)
                    for key in tokens:
                        if word in key:
                            word = key
                            break
                if word not in Catalog.byTokens:
                    word = Catalog.randomTheme()
                theme = [word]
                theme.insert(0, Catalog.randomTheme())
                if random.random() > 0.5:
                    theme.insert(0, Catalog.randomTheme())
                return theme
            if i == 0 and len(parts) > 1:
                if all([p in Catalog.byTokens for p in parts]):
                    theme = parts
                else:
                    theme = []
                    for word in parts:
                        if word not in Catalog.byTokens:
                            tokens = list(Catalog.byTokens)
                            random.shuffle(tokens)
                            for key in tokens:
                                if word in key:
                                    word = key
                                    break
                        if word in Catalog.byTokens:
                            theme.append(word)
                    if len(theme) < 2:
                        theme = gen()
            else:
                theme = gen()
            key = ' '.join([w[0].upper() + w[1:] for w in theme])
            theme = tuple(theme)
            random.seed(hash(theme) + i)
            output[key] = self.makeThemedDeck(theme)
        logging.info("Deck gen took %.2fms", 1000*(time.time() - start))
        return output

    def randomTheme(self):
        return random.choice(self.topTokens)

    def makeThemedDeck(self, theme):
        colorVotes = collections.defaultdict(float)
        for t in theme:
            pool = self.byTokens[t]
            for card in pool:
                colors = card.colors()
                for color in colors:
                    colorVotes[color] += 1.0 / (len(colors) + len(pool))
        rankedColors = sorted([(v, k) for (k, v) in list(colorVotes.items())], reverse=True)
        if len(rankedColors) > 0:
            land1 = landsByColor[rankedColors[0][1]]
        else:
            land1 = random.choice(self.basicLands)
        if len(rankedColors) > 1:
            ratio = rankedColors[1][0] / rankedColors[0][0]
            logging.info("%s ratio: %s/%s %f", ' '.join(theme), rankedColors[1][1], rankedColors[0][1], ratio)
            if ratio < 0.5:
                land2 = land1
            else:
                land2 = landsByColor[rankedColors[1][1]]
        else:
            land2 = random.choice(self.basicLands)
        if land1 == land2:
            base = ["24 " + land1]
        else:
            base = ["12 " + land1, "12 " + land2]
        colors = set([self.byLand[l] for l in [land1, land2]])
        cards = []
        taken = set()
        cards.extend(self.complement(land1, [land1, land2], taken, theme))
        cards.extend(self.complement(land2, [land1, land2], taken, theme))
        return base + sorted(cards, reverse=True)

    def _register(self, card):
        self.byName[card.name] = card
        self.bySlug[card.name.lower()] = card
        self.byType[card.type].append(card)
        for token in card.tokens:
            self.byTokens[token].append(card)
        for color in card.colors():
            self.byColor[color].append(card)
        if not card.colors():
            self.byColor['colorless'].append(card)
        self.byCost[card.cost].append(card)


Catalog = None
def initCatalog():
    global Catalog
    Catalog = CardCatalog(
        _server_path("..", "mtg_info.txt"),
        _server_path("..", "classification.txt"),
        _server_path("..", "localdb"),
    )


class LocalDBPlugin(DefaultPlugin):
    DB_PATH = _server_path('..', 'localdb')

    def __init__(self):
        initCatalog()
        self.catalog = {}
        self.index = {}
        self.fullnames = {}
        if not os.path.isdir(self.DB_PATH):
            return
        for f in os.listdir(self.DB_PATH):
            name = f.replace('_', '/').replace('.jpg', '')
            key = sanitize(name).lower()
            self.catalog[key] = urllib.parse.quote(os.path.join(self.DB_PATH, f))
            self.fullnames[key] = sanitize(name)
            self.index[key] = name

    def Complete(self, cards):
        return Catalog.complete(cards)

    def Sample(self):
        return Catalog.makeDeck()

    def SampleDeck(self, term, num_decks):
        return Catalog.makeDecks(term, num_decks)

    def GetBackUrl(self):
        return '/third_party/images/mtg_detail.jpg'

    def Fetch(self, name, exact, limit=None):
        start = time.time()
        stream, meta = [], {}
        if name == '':
            return stream, meta
        name = name.strip()
        needle = str(name.lower())
        if exact:
            if needle in self.catalog:
                card = Catalog.byName.get(name)
                card_type = None
                if card: card_type = card.type + " " + card.subtype
                stream.append({
                    'name': name,
                    'img_url': self.catalog[needle],
                    'info_url': self.catalog[needle],
                    'type': card_type,
                })
        else:
            range_expr = "(\d+)\s*(to|-)\s*(\d+)\s*(mana|cost|cmc)"
            mana_expr = "(mana|cost|cmc)\s*(>|<|>=|<=|=|==|)\s*(\d+)"
            mana_expr2 = "(\d+)\s*(mana|cost|cmc)"
            predicates = []
            def add_pred(op, val):
                if op == '==':
                    predicates.append(lambda c: c.cost == val)
                elif op == '>':
                    predicates.append(lambda c: c.cost > val)
                elif op == '>=':
                    predicates.append(lambda c: c.cost >= val)
                elif op == '<':
                    predicates.append(lambda c: c.cost < val)
                elif op == '<=':
                    predicates.append(lambda c: c.cost <= val)
                else:
                    assert False, op
            for match in re.finditer(range_expr, needle):
                needle = re.sub(range_expr, '', needle)
                lo, hi = int(match.group(1)), int(match.group(3))
                if lo > hi:
                    lo, hi = hi, lo
                logging.info("Using predicate: cost in [%d, %d]" % (lo, hi))
                add_pred(">=", lo)
                add_pred("<=", hi)
            for match in re.finditer(mana_expr, needle):
                needle = re.sub(mana_expr, '', needle)
                op, val = match.group(2), int(match.group(3))
                if op == '=' or op == '':
                    op = '=='
                logging.info("Using predicate: cost %s %d" % (op, val))
                add_pred(op, val)
            for match in re.finditer(mana_expr2, needle):
                needle = re.sub(mana_expr2, '', needle)
                op, val = '==', int(match.group(1))
                logging.info("Using predicate: cost %s %d" % (op, val))
                add_pred(op, val)
            mana = {'red', 'blue', 'white', 'black', 'green'}
            other_mana = {'dual', 'mono', 'multi', 'colored', 'colorless', 'single', 'two', 'three', 'tri', 'quad', 'four', 'five', 'all', 'rainbow'}
            def expand(parts):
                core = []
                out = []
                num_mana = 0
                num_other_mana = 0
                for p in parts:
                    if p in mana:
                        num_mana += 1
                    if p in other_mana:
                        num_other_mana += 1
                    if p in mana or p in other_mana or p == 'x':
                        out.append('mana=' + p)
                    else:
                        core.append(p)
                if num_other_mana == 0:
                    if num_mana == 1:
                        out.append('mana=mono')
                    elif num_mana == 2:
                        out.append('mana=dual')
                    elif num_mana == 3:
                        out.append('mana=tri')
                    elif num_mana == 4:
                        out.append('mana=quad')
                    elif num_mana == 5:
                        out.append('mana=all')
                return core, out
            ct = 0
            ranked = collections.defaultdict(list)
            try:
                parts = shlex.split(needle)
            except ValueError:
                parts = needle.split()
            parts, expanded = expand(parts)
            logging.info("Expanded query: " + str(parts) + " " + str(expanded))
            for title, url in self.catalog.items():
                card = Catalog.bySlug.get(title)
                rank = 0.0
                if card and predicates:
                    if all([ok(card) for ok in predicates]):
                        rank += 1
                    else:
                        continue
                if needle == title:
                    rank += 20
                def rankit(p, has):
                    rank = 0
                    if p in title or p in card.searchtype:
                        rank += 1
                    if p in card.searchtokens:
                        rank += 1
                    if p in card.searchtext:
                        if ' ' in p:
                            rank += len(p.split())
                        else:
                            rank += 1
                    else:
                        has[0] -= 1
                    return rank
                if card:
                    if card.goodQuality:
                        rank += 0.5
                    has_bonus = [len(parts)]
                    for p in parts:
                        rank += rankit(p, has_bonus)
                    rank += 3 * has_bonus[0]
                    for p in expanded:
                        rank += rankit(p, has_bonus)
                if rank >= 1:
                    ranked[rank].append(title)
            ranks = sorted(list(ranked.keys()), reverse=True)
            for r in ranks:
                for title in ranked[r]:
                    stream.append({
                        'name': self.fullnames[title],
                        'img_url': self.catalog[title],
                        'info_url': self.catalog[title],
                    })
                    ct += 1
                    if ct >= limit:
                        break
                if ct >= limit:
                    break
        meta = {
            'has_more': False,
            'more_url': "",
        }
        logging.info("search for '%s' took %.2f ms", needle,
                     1000*(time.time() - start))
        return stream, meta


class ScryfallPlugin(DefaultPlugin):

    API_ROOT = 'https://api.scryfall.com'

    def GetBackUrl(self):
        return '/third_party/images/mtg_detail.jpg'

    def Sample(self):
        return Catalog.makeDeck()

    def SampleDeck(self, term, num_decks):
        return Catalog.makeDecks(term, num_decks)

    def _open_json(self, url):
        logging.info("GET %s", url)
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'kansas/1.0 (+https://github.com/)'}
        )
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
        return json.loads(data)

    def _to_entry(self, card):
        image_uris = card.get('image_uris') or {}
        if not image_uris and 'card_faces' in card:
            for face in card['card_faces']:
                if face.get('image_uris'):
                    image_uris = face['image_uris']
                    break

        img_url = image_uris.get('normal') or image_uris.get('large') or image_uris.get('small')
        if not img_url:
            return None

        return {
            'name': card.get('name', ''),
            'img_url': img_url,
            'info_url': card.get('scryfall_uri', card.get('uri', '')),
        }

    def Fetch(self, name, exact, limit):
        if name == '':
            return [], {}

        if exact:
            url = '%s/cards/named?exact=%s' % (self.API_ROOT, urllib.parse.quote(name))
            try:
                payload = self._open_json(url)
            except urllib.error.HTTPError:
                return [], {'has_more': False, 'more_url': ''}
            entry = self._to_entry(payload)
            return ([entry] if entry else []), {'has_more': False, 'more_url': ''}

        q = name.strip()
        page_size = min(int(limit or 20), 175)
        url = '%s/cards/search?q=%s&order=name&unique=cards&include_multilingual=false&page=1' % (
            self.API_ROOT, urllib.parse.quote(q))
        payload = self._open_json(url)
        stream = []
        for card in payload.get('data', []):
            entry = self._to_entry(card)
            if entry:
                stream.append(entry)
            if len(stream) >= page_size:
                break

        meta = {
            'has_more': bool(payload.get('has_more', False)),
            'more_url': payload.get('next_page', ''),
        }
        return stream, meta


# Backwards-compatibility alias for existing saved source IDs.
MagicCardsInfoPlugin = ScryfallPlugin
