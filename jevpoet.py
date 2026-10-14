#!/usr/bin/env python3

# Jev Poet
# They say Jev cannot generate text, so who wrote this poem?
# Date: 2026-10-14
# Contact: Roni Bandini, @ronibandini
# GitHub: https://github.com/ronibandini/JevPoet
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
# It is distributed in the hope that it will be useful, but comes WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See https://www.gnu.org/licenses/gpl-3.0.html for the full license.

import argparse
import csv
import math
import os
import random
import re
import sys
import textwrap
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:  # wordfreq is optional; when installed, it filters very rare words from the CSV lists.
    from wordfreq import zipf_frequency
except ImportError:  # pragma: no cover
    zipf_frequency = None

DEFAULT_URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "~typesafe/jev-latest"

# These categories give the poem concrete images to work with. 
CATEGORIES: dict[str, str] = {
    "animal": """moth heron fox owl wolf crow sparrow beetle salmon horse goat spider snail swan eel hare
        mule bat bee wasp crab seal whale cat dog rat lizard frog toad raven gull hawk deer bear ox camel
        octopus cricket firefly hen ram stag newt otter badger mole stork pigeon donkey mouse wren
        jackal viper carp sparrowhawk""",
    "object": """lantern ladder staircase key spoon bell clock umbrella window door mirror candle thimble
        suitcase kettle bucket violin piano chair table lamp bridge needle button envelope ribbon lock
        hammer saw anchor compass telescope pillow blanket bicycle teapot cup bottle drawer curtain stove
        radio typewriter balloon kite sack rope mask glove shoe coat hat cradle trumpet
        wheelbarrow lighthouse tent""",
    "body": """hand eye mouth tongue throat shoulder knee elbow finger spine rib heart ear lip tooth palm
        wrist hair skull ankle thumb chest forehead""",
    "weather": """rain snow fog wind frost storm hail thunder mist drizzle dew heat cloud moonlight sunlight
        dusk dawn twilight lightning""",
    "place": """kitchen attic orchard harbor cellar corridor meadow quarry station library market
        cathedral village desert garden roof field river lake canyon tunnel courtyard greenhouse church
        barn island pier cemetery balcony""",
    "substance": """salt honey ink milk ash sand dust wax smoke oil sugar tar clay rust ice mud vinegar soot
        petals gravel snowmelt""",
    "material": """glass paper wool bone iron copper straw lace porcelain velvet cotton stone wood tin silk
        linen leather brass""",
    "plant": """lemon fig pear olive rose thistle fern moss willow poppy clover lily onion apple reed ivy
        pine bramble dandelion""",
    "abstract": """silence memory hunger rumor shadow echo habit secret music laughter dream sorrow
        distance appetite""",
}

# The generic {noun} slot draws from these categories. "misc" contains nouns from the CSV.
NOUN_WEIGHTS = {"animal": 3.0, "object": 4.0, "body": 1.5, "weather": 1.0, "place": 1.5, "substance": 1.5,
                "material": 0.6, "plant": 1.0, "abstract": 0.8, "misc": 1.2}

CURATED_ADJECTIVES = """cold hollow salted rusted velvet slow bright paper tender sticky heavy thin crooked wet
dry hungry lost small enormous patient restless pale golden borrowed folded cracked sweet bitter quiet loud
smooth rough drowned tiny blind sleepless loose worn waxed bruised mossy feathered glassy narrow
forgotten buried burning trembling silver crumbling swollen sleepy unlit invisible lopsided damp frozen
threadbare translucent sunken hairless polished faded scarlet ashen rotting luminous drifting 
digital synthetic cybernetic mechanical virtual encrypted augmented holographic biometric electric industrial 
artificial neural robotic chrome-plated
""".split()

TRANSITIVE_VERBS = """carry swallow polish unfold bury drown wrap fold hide drag pour stir sweep follow count
borrow bite steal knit tie weigh lift unlock mend feed rinse paint open close fill empty hold keep wear
gather chase measure touch taste swing drop throw pull push wash light cover cross rub water shake
bend lose find draw""".split()

INTRANSITIVE_VERBS = """whisper rustle shiver tremble hover glow drip crawl hum sleep drift float sink melt
bloom wander linger ripple unravel wait kneel sway flicker creak dance fade vanish tumble rest
breathe burn sing collapse sparkle meander echo rise shine stumble dissolve ferment hesitate
evaporate sag unfold swim""".split()

NUMBER_WORDS = ["two", "three", "four", "seven", "nine", "twelve", "forty"]

ADJ_STOP = set("""a an any all each every either neither both few fewer many much more most other another
same such own several some enough next last first second third fourth fifth sixth eighth five four eight
her his their my your its our this that east west north south eastern western northern southern""".split())

ABSTRACT_NOUN_SUFFIXES = ("tion", "sion", "ment", "ness", "ity", "ism", "ance", "ence", "ship", "hood",
                          "ology", "ics", "ure", "ist", "ize", "ise")
ABSTRACT_ADJ_SUFFIXES = ("able", "ible", "ive", "ical", "ous", "ary", "ial", "ual", "ent", "ant", "ic",
                         "oid", "less", "al", "ed", "ing", "ness", "ful", "ish", "ly")

NON_NOUNS = set("""
a an the this that these those he she it we they you i me him her us them myself yourself himself
herself itself ourselves yourselves themselves everyone everybody everything anyone anybody anything
someone somebody something nobody no one nothing somewhere someplace anywhere nowhere everywhere
anywhere downstairs upstairs here there then now always never often seldom almost maybe perhaps quite
rather very too enough less fewer many much several few all both either neither each every another
such whoever whomever whose whom whatever whichever which what who where when why how yes no not
""".split())

SINGULAR_S_EXCEPTIONS = set("""
news species series means bus gas lens alias atlas canvas census campus virus status bonus chorus cactus
focus fungus syllabus radius stimulus analysis basis crisis thesis axis oasis diagnosis hypothesis
parenthesis synthesis emphasis metropolis apparatus headquarters jeans politics economics physics
mathematics athletics measles
""".split())

IRREGULAR_PLURALS = {"wolf": "wolves", "mouse": "mice", "knife": "knives", "leaf": "leaves", "ox": "oxen",
                     "fish": "fish", "sheep": "sheep", "deer": "deer", "shelf": "shelves", "thief": "thieves", "loaf": "loaves"}
IRREGULAR_VERBS = {
    "bite": ("bit", "bitten"), "steal": ("stole", "stolen"), "sink": ("sank", "sunk"),
    "sleep": ("slept", "slept"), "sweep": ("swept", "swept"), "feed": ("fed", "fed"),
    "hide": ("hid", "hidden"), "knit": ("knit", "knit"), "shake": ("shook", "shaken"),
    "throw": ("threw", "thrown"), "wear": ("wore", "worn"), "hold": ("held", "held"),
    "keep": ("kept", "kept"), "draw": ("drew", "drawn"), "find": ("found", "found"),
    "lose": ("lost", "lost"), "rise": ("rose", "risen"), "sing": ("sang", "sung"),
    "swim": ("swam", "swum"), "burn": ("burned", "burned"), "bend": ("bent", "bent"),
    "light": ("lit", "lit"),
}
DOUBLED_CONSONANT_VERBS = {"stir", "drag", "drip", "wrap", "drop", "hum", "rub", "tap", "slip"}


# Sentence templates
# Each template stores an ID, a structure family, the sentence pattern, and its verb frame.
# Slots name noun categories, adjectives, numbers, or verb forms. A numbered slot such as
# {object2} asks for a different word; {motif} can bring back an image from an earlier line.
TEMPLATES: list[tuple[str, str, str, str]] = [
    ("image", "adjective_subject_action", "The {adj} {noun} {verb3} the {adj2} {noun2}.", "transitive"),
    ("motion_beneath", "subject_action_location", "The {animal} {verb3} beneath the {adj} {object}.", "intransitive"),
    ("possibility", "modal_positive", "A {adj} {noun} can {base} the {noun2}.", "transitive"),
    ("impossibility", "modal_negative", "No {animal} can {base} a {adj} {object}.", "transitive"),
    ("contrast", "two_clause_contrast", "The {weather} is {adj}, but the {animal} {verb3} the {object}.", "transitive"),
    ("parallel", "while_parallel", "While the {animal} {verb3} the {object}, the {adj} {weather} {verb3_2} the {place}.", "transitive"),
    ("between", "between_opener", "Between the {object} and the {object2}, the {adj} {animal} {verb3}.", "intransitive"),
    ("passive", "passive_clause", "The {object} was {participle} by the {adj} {animal}.", "passive"),
    ("perhaps", "perhaps_opener", "Perhaps the {adj} {animal} will {base} again.", "intransitive"),
    ("below", "below_opener", "Below the {place}, a {adj} {noun} {verb3}.", "intransitive"),
    ("even_when", "concession_clause", "Even when the {weather} {verb3}, the {object} stays {adj}.", "intransitive"),
    ("found", "first_person_observation", "I found a {adj} {object} beside the {noun}.", "none"),
    ("fragment", "paired_fragment", "{Adj} {object}, {adj2} {animal}.", "none"),
    ("not_but", "not_but_fragment", "Not the {noun}, but the {adj} {noun2}.", "none"),
    ("question", "what_if_question", "What if the {adj} {animal} could {base} the {object}?", "transitive"),
    ("although", "although_clause", "Although the {weather} {verb3}, the {adj} {animal} is {adj2}.", "intransitive"),
    ("as_if", "as_if_comparison", "The {animal} moves as if the {adj} {object} {verb3}.", "intransitive"),
    ("without", "without_opener", "Without the {object}, a {adj} {animal} {verb3}.", "intransitive"),
    ("colon_list", "colon_list", "The {noun}: {adj}, {adj2}, and {adj3}.", "none"),
    ("without_object", "noun_without_object", "A {adj} {animal} without a {object}.", "none"),
    ("genitive_fragment", "genitive_fragment", "The {adj} {body} of the {adj2} {animal}.", "none"),
    ("when", "when_clause", "When the {weather} {verb3}, the {noun} is still {adj}.", "intransitive"),
    ("returns", "return_location", "The {animal} returns beneath the {adj} {object}.", "none"),
    ("after", "after_opener", "After the {weather}, the {adj} {object} remains.", "none"),
    ("becomes", "copular_change", "The {object} becomes {adj} beside the {animal}.", "none"),
    ("neither_nor", "neither_nor", "Neither the {object} nor the {animal} can {base}.", "intransitive"),
    ("somewhere_between", "somewhere_opener", "Somewhere between the {place} and the {place2}, the {adj} {animal} {verb3}.", "intransitive"),
    ("climbs_like", "climbs_simile", "A {animal} climbs the {object} like a {noun}.", "none"),
    ("asks_why", "embedded_question", "The {animal} asks why the {adj} {object} {verb3}.", "intransitive"),
    ("where_ends", "where_clause", "Where the {place} ends, the {adj} {noun} begins.", "none"),
    ("let", "imperative", "Let the {animal} {base} beside the {adj} {object}.", "intransitive"),
    ("while_waiting", "while_clause", "The {animal} waits for the {object}, while the {adj} {weather} {verb3}.", "intransitive"),
    ("to_a_noun", "to_opener", "To the {animal}, the {object} looks {adj}.", "none"),
    ("forgotten_how", "forgotten_how_clause", "The {animal} has forgotten how to {base}.", "intransitive"),
    ("smells_of", "smells_of", "The {object} smells of {substance}.", "none"),
    ("plural_inside", "plural_inside", "{Num} {animal_pl} {base} inside the {object}.", "intransitive"),
    ("woke_with", "woke_with", "I woke with a {object} in my {body}.", "none"),
    ("made_of", "made_of", "The {animal} is made of {material}.", "none"),
    ("left_full", "left_full", "Someone has left a {object} full of {substance} in the {place}.", "none"),
    ("every_small", "every_small", "Every {object} in the {place} is a small {animal}.", "none"),
    ("fills_with", "fills_with", "The {place} fills with {substance} when the {animal} {verb3}.", "intransitive"),
    ("body_became", "body_became", "My {body} became a {object}.", "none"),
    ("like_left", "like_left", "Like a {object} left in the {weather}, the {animal} {verb3}.", "intransitive"),
    ("dreams_of", "dreams_of", "The {object} dreams of {animal_pl}.", "none"),
    ("plural_and", "plural_and", "{Num} {object_pl} and a {animal}.", "none"),
    ("mouth_of", "has_a_body_part", "The {place} has a {material} {body}, and it {verb3}.", "intransitive"),
    ("keeps_full", "keeps_full", "The {animal} keeps a {object} full of {substance}.", "none"),
    ("weather_gives", "weather_gives", "The {weather} gives the {animal} a {adj} {object}.", "none"),
    ("not_the_one", "not_the_one", "It was the {animal}, not the {object}, that {verb3}.", "intransitive"),
    # These templates bring back an image from an earlier line.
    ("echo_again", "echo_again", "Again, the {motif} {verb3}.", "intransitive"),
    ("echo_same", "echo_same", "The same {motif} {verb3} beneath the {adj} {noun}.", "intransitive"),
    ("echo_all_along", "echo_all_along", "It was the {motif} all along, wearing a {adj} {noun}.", "none"),
    ("echo_its", "echo_its", "Its {body} is {adj}, and the {noun} {verb3}.", "intransitive"),
]
ECHO_FAMILIES = {"echo_again", "echo_same", "echo_all_along", "echo_its"}

SLOT_RE = re.compile(r"\{(\w+)\}")
VERB_FIELDS = {"verb3": ("v1", "third"), "verb3_2": ("v2", "third"), "base": ("v1", "base"),
               "past": ("v1", "past"), "participle": ("v1", "participle")}


# Small language helpers
def is_single_word(value: str) -> bool:
    value = value.strip()
    return bool(value) and not any(char.isspace() for char in value) and value not in {"-", "—", "..."}


def unique_words(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        word = item.strip().lower()
        if word and word.casefold() not in seen:
            seen.add(word.casefold())
            result.append(word)
    return result


def likely_plural_noun(word: str) -> bool:
    """Skip obvious plurals so singular templates get singular subjects."""
    word = word.lower()
    if word in SINGULAR_S_EXCEPTIONS or word.endswith(("ss", "us", "is", "os", "ics", "ness", "itis")):
        return False
    if word.endswith("ies") or word.endswith(("ches", "shes", "xes", "zes")):
        return True
    return word.endswith("s") and len(word) > 3


def pluralize(word: str) -> str:
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    return word + "s"


def conjugate(base: str) -> dict[str, str]:
    if re.search(r"(s|x|z|ch|sh)$", base):
        third = base + "es"
    elif re.search(r"[^aeiou]y$", base):
        third = base[:-1] + "ies"
    else:
        third = base + "s"
    if base in IRREGULAR_VERBS:
        past, participle = IRREGULAR_VERBS[base]
    else:
        if base.endswith("e"):
            past = base + "d"
        elif re.search(r"[^aeiou]y$", base):
            past = base[:-1] + "ied"
        elif base in DOUBLED_CONSONANT_VERBS:
            past = base + base[-1] + "ed"
        else:
            past = base + "ed"
        participle = past
    return {"base": base, "third": third, "past": past, "participle": participle}


def choose_article(phrase: str) -> str:
    """Choose a or an using the sound of the next word, not just its spelling."""
    word = phrase.strip().lower()
    if word.startswith(("honest", "honor", "honour", "hour", "heir", "herb")):
        return "an"
    if word.startswith(("user", "usual", "useful", "united", "union", "unique", "uniform", "unicorn",
                        "university", "universal", "utility", "utopian", "european", "eulogy", "euphem",
                        "one-", "once")):
        return "a"
    return "an" if word[:1] in "aeiou" else "a"


def tidy(line: str) -> str:
    def fix_article(match: re.Match[str]) -> str:
        old_article, next_word = match.group(1), match.group(2)
        article = choose_article(next_word)
        if old_article[0].isupper():
            article = article.capitalize()
        return f"{article} {next_word}"
    line = re.sub(r"\b(a|an) ([a-zA-Z'-]+)", fix_article, line, flags=re.IGNORECASE)
    line = re.sub(r"\s+([,.?!;:])", r"\1", line)
    return line[0].upper() + line[1:] if line else line


def zipf_of(word: str) -> float:
    return zipf_frequency(word, "en") if zipf_frequency else 4.0


# Build the word lists
class Lexicon:
    """Load the built-in vocabulary and useful words from the CSV files."""

    def __init__(self, adjective_path: Path, noun_path: Path, verb_path: Path,
                 concreteness_path: Path | None = None) -> None:
        self.cats: dict[str, list[str]] = {name: unique_words(words.split()) for name, words in CATEGORIES.items()}
        curated_nouns = {w for words in self.cats.values() for w in words}

        # Add common, sensory adjectives from the CSV to the short curated list.
        self.csv_adjectives: list[tuple[str, float]] = []
        with adjective_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                word = (row.get("Word") or "").strip().lower()
                if not (word.isalpha() and 3 <= len(word) <= 10) or word in ADJ_STOP or word in NON_NOUNS:
                    continue
                if word.endswith(ABSTRACT_ADJ_SUFFIXES):
                    continue
                self.csv_adjectives.append((word, zipf_of(word)))
        self.csv_adjectives = list({w: (w, z) for w, z in self.csv_adjectives}.values())
        self.curated_adjectives = unique_words(CURATED_ADJECTIVES)
        self.curated_adjective_set = set(self.curated_adjectives)
        self.csv_adjective_set = {w for w, _ in self.csv_adjectives}

        # Keep the extra CSV nouns short and concrete, and skip obvious plurals.
        conc: dict[str, float] = {}
        if concreteness_path is not None:
            with concreteness_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    try:
                        conc[(row.get("Word") or "").strip().lower()] = float(row.get("Conc.M") or "nan")
                    except ValueError:
                        pass
        self.misc_nouns: list[tuple[str, float]] = []
        with noun_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.reader(handle):
                word = (row[0].strip().lower() if row else "")
                if not (word.isalpha() and 3 <= len(word) <= 9) or word in NON_NOUNS or word in curated_nouns:
                    continue
                if likely_plural_noun(word) or word.endswith(ABSTRACT_NOUN_SUFFIXES):
                    continue
                if conc and not conc.get(word, 0.0) >= 3.8:
                    continue
                self.misc_nouns.append((word, zipf_of(word)))
        self.misc_nouns = list({w: (w, z) for w, z in self.misc_nouns}.values())

        # Use the CSV verb forms when available; conjugate the curated verbs otherwise.
        csv_forms: dict[str, dict[str, str]] = {}
        with verb_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                base = (row.get("Word") or "").strip().lower()
                values = {"base": base, "third": (row.get("3singular") or "").strip().lower(),
                          "past": (row.get("Simple Past") or "").strip().lower(),
                          "participle": (row.get("Past Participle") or "").strip().lower()}
                if all(is_single_word(v) for v in values.values()):
                    csv_forms[base] = values

        def forms(base: str) -> dict[str, str]:
            if base in csv_forms and base not in IRREGULAR_VERBS:
                return csv_forms[base]
            return conjugate(base)

        self.transitive = [forms(b) for b in unique_words(TRANSITIVE_VERBS)]
        self.intransitive = [forms(b) for b in unique_words(INTRANSITIVE_VERBS)]

        # Index singular and plural forms so the poem can reuse images later.
        self.noun_index: dict[str, tuple[str, str]] = {}
        for cat, words in self.cats.items():
            for word in words:
                self.noun_index[word] = (word, cat)
                self.noun_index.setdefault(pluralize(word), (word, cat))
        for word, _ in self.misc_nouns:
            self.noun_index.setdefault(word, (word, "misc"))

    @staticmethod
    def _draw(pool: list[tuple[str, float]], rng: random.Random, lo: float, hi: float) -> str:
        for _ in range(60):
            word, z = rng.choice(pool)
            if lo <= z <= hi:
                return word
        return rng.choice(pool)[0]

    def random_adjective(self, rng: random.Random, widen: int = 0) -> str:
        if self.csv_adjectives and rng.random() < 0.12 + 0.08 * widen:
            return self._draw(self.csv_adjectives, rng, 3.5 - 0.25 * widen, 5.7)
        return rng.choice(self.curated_adjectives)

    def random_noun(self, rng: random.Random, cat: str, widen: int = 0) -> str:
        if cat == "noun":
            names = [n for n in NOUN_WEIGHTS if n != "misc" or self.misc_nouns]
            weights = [NOUN_WEIGHTS[n] + (widen * 0.8 if n == "misc" else 0.0) for n in names]
            cat = rng.choices(names, weights)[0]
        if cat == "misc":
            return self._draw(self.misc_nouns, rng, 3.4 - 0.25 * widen, 5.6)
        return rng.choice(self.cats[cat])


# Track images as the poem grows
class Context:
    def __init__(self, lex: Lexicon, rng: random.Random) -> None:
        self.lex = lex
        self.rng = rng
        self.widen = 0
        self.recent: deque[tuple[str, str]] = deque(maxlen=14)  # Most recently used concrete images
        self.theme: list[tuple[str, str]] = []  # Images anchoring the current stanza
        self.noun_counts: Counter[str] = Counter()
        self.recent_adjectives: deque[str] = deque(maxlen=16)  # Avoid leaning on the same adjective

    def echo_pool(self, cat: str) -> list[str]:
        # Let an image return a few times, but retire it after three uses.
        pool = [w for w, c in self.theme if (cat == "noun" or c == cat or cat == "motif") and self.noun_counts[w] < 3] * 3
        pool += [w for w, c in self.recent if (cat in ("noun", "motif") or c == cat) and self.noun_counts[w] < 3]
        return pool

    def note_line(self, line: str) -> None:
        for token in re.findall(r"[a-z]+", line.lower()):
            if token in self.lex.curated_adjective_set or token in self.lex.csv_adjective_set:
                self.recent_adjectives.append(token)
        for token in re.findall(r"[a-z]+", line.lower()):
            hit = self.lex.noun_index.get(token)
            if hit and hit[1] not in ("abstract", "misc"):  # Only curated concrete words become recurring images.
                word, cat = hit
                self.noun_counts[word] += 1
                try:
                    self.recent.remove((word, cat))
                except ValueError:
                    pass
                self.recent.append((word, cat))

    def noun_for(self, cat: str, used: set[str], p_echo: float = 0.20) -> str:
        pool = [w for w in self.echo_pool(cat) if w not in used]
        if pool and self.rng.random() < p_echo:
            return self.rng.choice(pool)
        word = ""
        for _ in range(40):
            word = self.lex.random_noun(self.rng, cat, self.widen)
            if word not in used:
                return word
        return word

    def adjective_for(self, used: set[str]) -> str:
        word = ""
        for _ in range(40):
            word = self.lex.random_adjective(self.rng, self.widen)
            if word not in used and word not in self.recent_adjectives:
                return word
        return word

    def distinct_nouns(self, cat: str, used: set[str], count: int) -> list[str]:
        """Offer fresh nouns, with a chance to bring back one image from the poem."""
        options: list[str] = []
        pool = [w for w in self.echo_pool(cat) if w not in used]
        if pool and self.rng.random() < 0.5:
            options.append(self.rng.choice(pool))
        guard = 0
        while len(options) < count and guard < 200:
            guard += 1
            word = self.lex.random_noun(self.rng, cat, self.widen)
            if word not in used and word not in options:
                options.append(word)
        self.rng.shuffle(options)
        return options

    def distinct_adjectives(self, used: set[str], count: int) -> list[str]:
        options: list[str] = []
        guard = 0
        while len(options) < count and guard < 200:
            guard += 1
            word = self.lex.random_adjective(self.rng, self.widen)
            if word not in used and word not in options and word not in self.recent_adjectives:
                options.append(word)
        return options

    def distinct_verbs(self, frame: str, count: int) -> list[dict[str, str]]:
        pool = self.lex.intransitive if frame == "intransitive" else self.lex.transitive
        return self.rng.sample(pool, min(count, len(pool)))


# Fill and render templates
def parse_slot(token: str) -> dict[str, Any]:
    low = token.lower()
    if low in VERB_FIELDS:
        return {"token": token, "kind": "verb", "key": low, "name": low, "plural": False, "cap": token[0].isupper()}
    plural = low.endswith("_pl")
    if plural:
        low = low[:-3]
    match = re.fullmatch(r"([a-z]+)(\d*)", low)
    if not match:
        raise ValueError(f"Bad template slot: {{{token}}}")
    name, idx = match.group(1), match.group(2)
    if name == "adj":
        kind = "adj"
    elif name == "num":
        kind = "num"
    elif name in ("noun", "motif") or name in CATEGORIES:
        kind = "noun"
    else:
        raise ValueError(f"Unknown template slot: {{{token}}}")
    return {"token": token, "kind": kind, "key": name + idx, "name": name, "plural": plural,
            "cap": token[0].isupper()}


def template_slots(pattern: str) -> dict[str, dict[str, Any]]:
    slots: dict[str, dict[str, Any]] = {}
    for token in SLOT_RE.findall(pattern):
        slot = parse_slot(token)
        slots.setdefault(slot["key"], slot)
    return slots


def render(pattern: str, words: dict[str, str], verbs: dict[str, dict[str, str]], partial: bool = False) -> str:
    def sub(match: re.Match[str]) -> str:
        slot = parse_slot(match.group(1))
        if slot["kind"] == "verb":
            which, field = VERB_FIELDS[slot["key"]]
            entry = verbs.get(which)
            out = entry[field] if entry else "[verb]"
        else:
            out = words.get(slot["key"])
            if out is None:
                return f"[{slot['name']}]"
            if slot["plural"]:
                out = pluralize(out)
        return out[:1].upper() + out[1:] if slot["cap"] else out
    line = SLOT_RE.sub(sub, pattern)
    return line if partial else tidy(line)


def verb_pool_for(frame: str, ctx: Context) -> list[dict[str, str]]:
    return ctx.lex.intransitive if frame == "intransitive" else ctx.lex.transitive


def make_line(ctx: Context, template: tuple[str, str, str, str]) -> str:
    _name, _family, pattern, frame = template
    slots = template_slots(pattern)
    used: set[str] = set()
    words: dict[str, str] = {}
    verbs: dict[str, dict[str, str]] = {}
    if frame != "none":
        verbs["v1"] = ctx.rng.choice(verb_pool_for(frame, ctx))
        if "verb3_2" in pattern:
            verbs["v2"] = ctx.rng.choice([v for v in verb_pool_for(frame, ctx) if v is not verbs["v1"]])
    for key, slot in slots.items():
        if slot["kind"] == "noun":
            cat = "noun" if slot["name"] in ("noun", "motif") else slot["name"]
            words[key] = ctx.noun_for(cat, used, 0.85 if slot["name"] == "motif" else 0.20)
            used.add(words[key])
        elif slot["kind"] == "adj":
            words[key] = ctx.adjective_for(used)
            used.add(words[key])
        elif slot["kind"] == "num":
            words[key] = ctx.rng.choice(NUMBER_WORDS)
    return render(pattern, words, verbs)


def eligible_templates(recent_templates: list[str], recent_families: list[str], allow_echo: bool) -> list[tuple[str, str, str, str]]:
    recent_t, recent_f = set(recent_templates[-6:]), set(recent_families[-4:])
    pool = [t for t in TEMPLATES if t[0] not in recent_t and t[1] not in recent_f
            and (allow_echo or t[1] not in ECHO_FAMILIES)]
    return pool or [t for t in TEMPLATES if allow_echo or t[1] not in ECHO_FAMILIES]


def make_batch(ctx: Context, count: int, recent_templates: list[str], recent_families: list[str],
               templates_per_batch: int, allow_echo: bool, existing_lines: set[str]) -> list[dict[str, str]]:
    """Build a varied batch so Jev compares ideas, not copies of the same structure."""
    pool = eligible_templates(recent_templates, recent_families, allow_echo)
    by_family: dict[str, list[tuple[str, str, str, str]]] = {}
    for item in pool:
        by_family.setdefault(item[1], []).append(item)
    families = list(by_family)
    ctx.rng.shuffle(families)
    chosen = [ctx.rng.choice(by_family[f]) for f in families[:max(1, templates_per_batch)]]

    lines: list[dict[str, str]] = []
    seen = set(existing_lines)
    attempts = 0
    while len(lines) < count and attempts < count * 80:
        template = chosen[len(lines) % len(chosen)]
        attempts += 1
        line = make_line(ctx, template)
        if line.casefold() in seen:
            continue
        seen.add(line.casefold())
        lines.append({"line": line, "template": template[0], "family": template[1]})
    if len(lines) < count:
        raise RuntimeError(f"Could only generate {len(lines)} unique lines for a batch of {count}.")
    ctx.rng.shuffle(lines)
    for index, item in enumerate(lines, 1):
        item["id"] = f"O{index:02d}"
    return lines


# Talk to Jev
class ApiError(RuntimeError):
    pass


class StopRun(Exception):
    pass


def choice_question(instructions: str, options: dict[str, str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": options}


def extract_choice(answers: Any, valid_ids: set[str], question: str | None = None) -> str | None:
    """Pull a valid option ID from Jev's answer."""
    scope = answers
    if question and isinstance(answers, dict) and question in answers:
        scope = answers[question]
    preferred_keys = {"selection", "selected", "choice", "candidate", "decision", "answer", "value", "result"}
    strings: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            strings.append(value.strip())
        elif isinstance(value, dict):
            for key in sorted(value, key=lambda item: (str(item).lower() not in preferred_keys, str(item))):
                walk(value[key])
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(scope)
    for value in strings:
        upper = value.upper()
        if upper in valid_ids:
            return upper
        match = re.search(r"\b(?:OPTION|CHOICE|CANDIDATE|SELECTED|ANSWER)\s*(?:IS|:|#)?\s*([A-Z_]+\d*)\b", upper)
        if match and match.group(1) in valid_ids:
            return match.group(1)
    return None


class JevClient:
    def __init__(self, api_key: str, url: str, model: str) -> None:
        self.api_key, self.url, self.model = api_key, url, model

    def ask(self, state: dict[str, Any], questions: dict[str, Any]) -> tuple[Any, float | None]:
        response = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "state": state, "questions": questions},
            timeout=45,
        )
        if response.status_code != 200:
            detail = response.text[:400].replace("\n", " ")
            raise ApiError(f"Jev API returned HTTP {response.status_code}: {detail}")
        payload = response.json()
        raw_cost = (payload.get("usage") or {}).get("cost")
        try:
            cost = float(raw_cost) if raw_cost is not None else None
        except (TypeError, ValueError):
            cost = None
        return payload.get("answers", {}), cost


# Prompts sent with each decision
LINE_INSTRUCTIONS = (
    "You are co-writing a surrealist poem one line at a time. The candidates were assembled from random words, "
    "so many are grammatical nonsense. Choose the candidate that reads like a line a poet could have written: a "
    "concrete, visual image in which the nouns and the verb could plausibly meet in a dream (a heron swallowing "
    "lantern-light is a dream; an abstract vague phrase is just noise). Prefer concrete, sensory images over "
    "abstraction. Prefer lines that echo, answer or distort an image already in the poem, or that open a fresh "
    "image that sits comfortably beside it; a deliberate refrain is welcome. Vary sentence shapes and openings "
    "across the poem and avoid the formula of recent lines. Do not rewrite or invent lines. Select exactly one "
    "ID. NONE only if every candidate is merely grammatical but meaningless or awkward. BREAK (if offered) only "
    "if the stanza has reached a natural resting point; no line is added and a new stanza begins. END (if offered) "
    "only if the poem already feels complete."
)
NOUN_INSTRUCTIONS = (
    "You are choosing words for one line of a surrealist poem, one blank at a time. state.frame shows the sentence "
    "with [blanks]. Pick the word that, together with the other blanks, could form a striking, concrete, "
    "visualizable image that fits or answers the poem so far. Favor combinations that collide unexpectedly yet "
    "can still be pictured; avoid cliché; reuse a recurring image only when it adds a refrain. Select exactly "
    "one option ID."
)
VERB_ADJ_INSTRUCTIONS = (
    "The nouns for this poem line are already chosen; state.frame shows the sentence with the remaining [blanks]. "
    "Choose the verb or adjective that makes the line a vivid image that could plausibly occur in a dream: a verb "
    "must sensibly connect the nouns shown, and an adjective must be sensory or strange-but-visual rather than "
    "merely odd. Select exactly one option ID."
)
DECIDE_INSTRUCTIONS = (
    "Judge the assembled poem line in state.line. ADD keeps it. ADD_BREAK keeps it and starts a new stanza "
    "afterward. ADD_END (if offered) keeps it and finishes the poem; use it only if the poem feels complete. "
    "REJECT if the line is grammatical but meaningless, awkward, or repeats an existing image or structure "
    "without purpose. Consider how it sits with the poem so far and with the line before it."
)
THEME_INSTRUCTIONS = (
    "Choose the object that should anchor the next stanza of this surrealist poem: something concrete that can "
    "recur, transform and collide with other images over the next 3 to 6 lines. Prefer one that deepens, "
    "contrasts with, or surprises against the poem so far. Select exactly one ID."
)
TITLE_INSTRUCTIONS = (
    "Choose the best title for this finished surrealist poem: evocative, slightly strange, faithful to its "
    "recurring images. Select exactly one ID."
)


# Terminal display
def wrap(text: str, width: int = 74) -> list[str]:
    result: list[str] = []
    for raw_line in text.splitlines() or [""]:
        result.extend(textwrap.wrap(raw_line, width=width, break_long_words=True, break_on_hyphens=False) or [""])
    return result


def format_cost(value: float | None) -> str:
    return "UNKNOWN" if value is None else f"${value:.8f}"


def wait_for_next_batch(seconds: int = 2) -> bool:
    """Pause between decisions, unless the user presses Q."""
    if not sys.stdin.isatty():
        print("No interactive terminal detected; stopping instead of running unattended.")
        return False
    deadline = time.monotonic() + seconds
    if os.name == "nt":
        import msvcrt
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            print(f"\rNext step in {remaining:.1f}s — press Q to quit. ", end="", flush=True)
            if msvcrt.kbhit() and msvcrt.getwch().lower() == "q":
                print("\nStopped by user.")
                return False
            time.sleep(min(0.05, remaining))
    else:
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                print(f"\rNext step in {remaining:.1f}s — press Q to quit. ", end="", flush=True)
                ready, _, _ = select.select([sys.stdin], [], [], min(0.05, remaining))
                if ready and sys.stdin.read(1).lower() == "q":
                    print("\nStopped by user.")
                    return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print("\r" + " " * 56 + "\r", end="", flush=True)
    return True


# Run a poem session
class Session:
    def __init__(self, args: argparse.Namespace, ctx: Context, client: JevClient | None, output_path: Path) -> None:
        self.args, self.ctx, self.client, self.output_path = args, ctx, client, output_path
        self.dry = args.dry_run
        self.stanzas: list[list[str]] = []
        self.title = ""
        self.new_stanza = True
        self.recent_templates: list[str] = []
        self.recent_families: list[str] = []
        self.total_cost: float | None = 0.0
        self.last_cost: float | None = 0.0 if self.dry else None
        self.calls = 0
        self.reject_streak = 0
        self.fallbacks = 0
        self.status = ""
        self.frame_note = ""
        self.options_note: list[str] = []

    # Keep the poem text together for display and saving.
    @property
    def line_count(self) -> int:
        return sum(len(s) for s in self.stanzas)

    @property
    def stanza_len(self) -> int:
        return len(self.stanzas[-1]) if self.stanzas else 0

    def poem_text(self) -> str:
        return "\n\n".join("\n".join(s) for s in self.stanzas if s)

    def all_lines(self) -> set[str]:
        return {line.casefold() for s in self.stanzas for line in s}

    def save(self) -> None:
        body = self.poem_text()
        text = f"{self.title}\n\n{body}" if self.title else body
        self.output_path.write_text(text + "\n", encoding="utf-8")

    def show(self) -> None:
        width = 78
        print("\033[2J\033[H", end="")
        print("=" * width)
        print(f"Jev Poet - by Roni Bandini @ronibandini ({self.args.mode}{', dry run' if self.dry else ''})")
        print(f"Total cost: {format_cost(self.total_cost)}   |   Last request: {format_cost(self.last_cost)}"
              f"   |   Requests: {self.calls}")
        print(f"Saved to: {self.output_path}")
        theme = ", ".join(w for w, _ in self.ctx.theme) or "(none yet)"
        echoes = ", ".join(w for w, _ in list(self.ctx.recent)[-6:]) or "(none yet)"
        # The theme and recent images are available here if the display needs them later.
        print("=" * width)
        print("Poem so far...")
        print("-" * width)
        text = (f"{self.title}\n\n" if self.title else "") + self.poem_text()
        if text.strip():
            for line in wrap(text.rstrip(), width - 4):
                print(f"  {line}")
        else:
            print("  (no lines selected yet)")
        if self.frame_note:
            print(f"\nWORKING ON: {self.frame_note}")
        if self.options_note:
            print("\nOPTIONS")
            print("-" * width)
            for item in self.options_note:
                print(f"  {item}")
        print("-" * width)
        print(self.status)
        sys.stdout.flush()

    # Send requests and keep track of the reported cost.
    def _call(self, state: dict[str, Any], questions: dict[str, Any]) -> Any:
        if self.client is None:
            raise RuntimeError("No Jev client in dry-run mode.")
        if self.args.max_cost > 0 and self.calls > 0:
            if self.total_cost is None:
                raise StopRun("Cost was not reported; stopping to avoid untracked spending.")
            if self.total_cost >= self.args.max_cost:
                raise StopRun(f"Cost threshold reached (${self.args.max_cost:.6f}); no further request was sent.")
        answers, cost = self.client.ask(state, questions)
        self.calls += 1
        self.last_cost = cost
        if cost is None:
            self.total_cost = None
        elif self.total_cost is not None:
            self.total_cost += cost
        return answers

    def base_state(self) -> dict[str, Any]:
        return {
            "task": "exquisite_jev_surrealist_poetry",
            "poem_so_far": self.poem_text(),
            "poem_line_count": self.line_count,
            "stanza_line_count": self.stanza_len,
            "current_stanza_theme": [w for w, _ in self.ctx.theme],
            "recurring_images": [w for w, _ in list(self.ctx.recent)[-8:]],
            "recent_structure_families": self.recent_families[-4:],
        }

    def ask_one(self, state: dict[str, Any], name: str, instructions: str, options: dict[str, str]) -> str | None:
        answers = self._call(state, {name: choice_question(instructions, options)})
        return extract_choice(answers, set(options), name)

    def ask_words(self, state: dict[str, Any], instructions: str, slots: dict[str, tuple[str, list[str]]]) -> dict[str, str]:
        """Ask Jev to fill each blank, using unique IDs for every question."""
        questions: dict[str, Any] = {}
        id_maps: dict[str, dict[str, str]] = {}
        for index, (qname, (blank, words)) in enumerate(slots.items()):
            letter = chr(ord("A") + index)
            ids = {f"{letter}{i}": word for i, word in enumerate(words, 1)}
            id_maps[qname] = ids
            questions[qname] = choice_question(
                f"{instructions} This question fills the blank [{blank}].",
                {oid: f"Choose '{word}' for [{blank}]." for oid, word in ids.items()})
        state = dict(state)
        state["options"] = {q: ids for q, ids in id_maps.items()}
        answers = self._call(state, questions)
        result: dict[str, str] = {}
        for qname, ids in id_maps.items():
            choice = extract_choice(answers, set(ids), qname)
            if choice is None:
                self.fallbacks += 1
                result[qname] = self.ctx.rng.choice(list(ids.values()))  # Use a local fallback if Jev gave no usable ID
            else:
                result[qname] = ids[choice]
        return result

    # Choose an image to carry through the next stanza.
    def start_stanza(self) -> None:
        ctx = self.ctx
        cats = ["animal", "object", "body", "weather", "place", "substance", "plant"]
        ctx.rng.shuffle(cats)
        options: list[tuple[str, str]] = []
        used: set[str] = set()
        for cat in cats[:7]:
            word = ctx.noun_for(cat, used, 0.0)
            used.add(word)
            options.append((word, cat))
        recent = [(w, c) for w, c in ctx.recent if w not in used]
        if recent and self.stanzas:
            options.append(ctx.rng.choice(recent))
        ctx.rng.shuffle(options)
        ids = {f"T{i}": pair for i, pair in enumerate(options, 1)}
        self.options_note = [f"[{i}] {w}" for i, (w, _) in ids.items()]
        self.frame_note = "choosing an anchor image for the next stanza"
        self.status = "Jev is choosing the stanza theme..." if not self.dry else "DRY RUN — first theme option used."
        self.show()
        if self.dry:
            choice = "T1"
        else:
            state = self.base_state()
            state["options"] = {i: w for i, (w, _) in ids.items()}
            choice = self.ask_one(state, "theme", THEME_INSTRUCTIONS,
                                  {i: f"Choose '{w}' as the anchor image." for i, (w, _) in ids.items()})
        pair = ids.get(choice or "") or ctx.rng.choice(list(ids.values()))
        ctx.theme = [pair]
        self.stanzas.append([])
        self.new_stanza = False

    # Let Jev choose from finished lines.
    def step_lines(self) -> bool:
        batch = make_batch(self.ctx, self.args.options, self.recent_templates, self.recent_families,
                           self.args.templates_per_batch, self.line_count >= 2, self.all_lines())
        options = {c["id"]: f'Select candidate {c["id"]} exactly as written in state.candidate_options; do not rewrite it.'
                   for c in batch}
        options["NONE"] = "Reject this whole batch only if every candidate is weak, awkward, meaningless, or uninteresting."
        if self.stanza_len >= 3:
            options["BREAK"] = "End this stanza here and begin a new one; no line is added."
        if self.line_count >= self.args.min_end_lines:
            options["END"] = "The poem is complete; finish it now."
        self.options_note = [f"[{c['id']}] {c['line']}" for c in batch]
        self.frame_note = ""
        self.status = "Jev is selecting the strongest poetic line..." if not self.dry else "DRY RUN — first candidate used."
        self.show()
        if self.dry:
            choice: str | None = batch[0]["id"]
        else:
            state = self.base_state()
            state["candidate_options"] = [{"id": c["id"], "line": c["line"]} for c in batch]
            choice = self.ask_one(state, "selection", LINE_INSTRUCTIONS, options)
        selected = next((c for c in batch if c["id"] == choice), None)
        if selected is not None:
            self.accept(selected["line"], selected["template"], selected["family"])
            who = "Dry run: first candidate" if self.dry else "Jev selected"
            self.status = f"{who} [{selected['id']}] — line added and saved."
            return False
        if choice == "BREAK":
            self.new_stanza = True
            self.status = "Jev ended the stanza."
            self.reject_streak = 0
        elif choice == "END":
            self.status = "Jev ended the poem."
            return True
        else:
            self.rejected("Jev rejected the batch" if choice == "NONE" else "No valid candidate ID found")
        return False

    # Let Jev fill the blanks in a template.
    def step_words(self) -> bool:
        ctx = self.ctx
        pool = eligible_templates(self.recent_templates, self.recent_families, self.line_count >= 2)
        template = ctx.rng.choice(pool)
        name, family, pattern, frame = template
        slots = template_slots(pattern)
        words: dict[str, str] = {}
        verbs: dict[str, dict[str, str]] = {}
        used: set[str] = set()

        for key, slot in slots.items():  # A recurring image is already chosen.
            if slot["name"] == "motif":
                words[key] = ctx.noun_for("noun", used, 0.9)
                used.add(words[key])
            elif slot["kind"] == "num":
                words[key] = ctx.rng.choice(NUMBER_WORDS)

        # First, let Jev choose the nouns.
        noun_slots = {k: s for k, s in slots.items() if s["kind"] == "noun" and s["name"] != "motif"}
        if noun_slots:
            asks: dict[str, tuple[str, list[str]]] = {}
            for key, slot in noun_slots.items():
                cat = "noun" if slot["name"] == "noun" else slot["name"]
                options = ctx.distinct_nouns(cat, used, self.args.word_options)
                asks[f"noun_{key}"] = (slot["name"], options)
            self.frame_note = render(pattern, words, verbs, partial=True)
            self.options_note = [f"[{b}] " + ", ".join(w) for b, w in asks.values()]
            self.status = "Jev is choosing the nouns..." if not self.dry else "DRY RUN — first option used."
            self.show()
            if self.dry:
                picked = {q: opts[0] for q, (_b, opts) in asks.items()}
            else:
                state = self.base_state()
                state["frame"] = self.frame_note
                picked = self.ask_words(state, NOUN_INSTRUCTIONS, asks)
            for key in noun_slots:
                word = picked[f"noun_{key}"]
                if word in used:  # Keep the nouns distinct when two blanks get the same choice.
                    word = ctx.noun_for("noun" if noun_slots[key]["name"] == "noun" else noun_slots[key]["name"], used, 0.0)
                words[key] = word
                used.add(word)

        # Next, choose the verb and adjectives.
        asks = {}
        verb_options: list[dict[str, str]] = []
        if frame != "none":
            verb_options = ctx.distinct_verbs(frame, self.args.word_options)
            asks["verb"] = ("verb", [v["base"] for v in verb_options])
        adj_slots = {k: s for k, s in slots.items() if s["kind"] == "adj"}
        for key in adj_slots:
            asks[f"adj_{key}"] = ("adjective", ctx.distinct_adjectives(used, self.args.word_options))
        if asks:
            self.frame_note = render(pattern, words, verbs, partial=True)
            self.options_note = [f"[{b}] " + ", ".join(w) for b, w in asks.values()]
            self.status = "Jev is choosing the verb and adjectives..." if not self.dry else "DRY RUN — first option used."
            self.show()
            if self.dry:
                picked = {q: opts[0] for q, (_b, opts) in asks.items()}
            else:
                state = self.base_state()
                state["frame"] = self.frame_note
                picked = self.ask_words(state, VERB_ADJ_INSTRUCTIONS, asks)
            if "verb" in picked:
                chosen = next(v for v in verb_options if v["base"] == picked["verb"])
                verbs["v1"] = chosen
                if "verb3_2" in pattern:
                    verbs["v2"] = ctx.rng.choice([v for v in verb_pool_for(frame, ctx) if v["base"] != chosen["base"]])
            for key in adj_slots:
                words[key] = picked[f"adj_{key}"]
                used.add(words[key])

        # Finally, ask Jev whether the line belongs in the poem.
        line = render(pattern, words, verbs)
        if line.casefold() in self.all_lines():
            self.rejected("Duplicate line skipped locally")
            return False
        self.frame_note = line
        self.options_note = []
        self.status = "Jev is judging the assembled line..." if not self.dry else "DRY RUN — line accepted."
        self.show()
        if self.dry:
            decision: str | None = "ADD"
        else:
            options = {"ADD": "Keep this line.",
                       "ADD_BREAK": "Keep this line and begin a new stanza afterward.",
                       "REJECT": "Discard: meaningless, awkward, or a pointless repeat. :("}
            if self.line_count + 1 >= self.args.min_end_lines:
                options["ADD_END"] = "Keep this line and finish the poem now."
            state = self.base_state()
            state["line"] = line
            decision = self.ask_one(state, "decision", DECIDE_INSTRUCTIONS, options)
        if decision in ("ADD", "ADD_BREAK", "ADD_END"):
            self.accept(line, name, family)
            self.status = ("Dry run: line added locally." if self.dry else f"Jev accepted the line ({decision}). :)")
            if decision == "ADD_BREAK" and self.stanza_len >= 2:
                self.new_stanza = True
            return decision == "ADD_END"
        self.rejected("Jev rejected the line" if decision == "REJECT" else "No valid decision ID found")
        return False

    # Update the poem's history after each line.
    def accept(self, line: str, template: str, family: str) -> None:
        self.stanzas[-1].append(line)
        self.ctx.note_line(line)
        self.recent_templates = (self.recent_templates + [template])[-8:]
        self.recent_families = (self.recent_families + [family])[-6:]
        self.reject_streak = 0
        self.ctx.widen = 0
        if self.stanza_len >= self.args.max_stanza:
            self.new_stanza = True
        self.save()

    def rejected(self, message: str) -> None:
        """After three rejections, loosen the word filters to get more variety."""
        self.reject_streak += 1
        if self.reject_streak >= 3:
            self.ctx.widen = min(3, self.ctx.widen + 1)
            message += f"; vocabulary widened (level {self.ctx.widen})"
        self.status = message + " — nothing added."

    # Choose a title and save the finished poem.
    def title_options(self) -> list[str]:
        ctx = self.ctx
        top = [w for w, _ in ctx.noun_counts.most_common(6)]
        guard = 0
        while len(top) < 3 and guard < 50:
            guard += 1
            word = ctx.lex.random_noun(ctx.rng, "noun")
            if word not in top:
                top.append(word)
        patterns = ["The {a}", "{adj} {a}", "{a} and {b}", "Notes on a {a}", "{A}, Again", "Small {a}",
                    "Inventory of the {a}", "The {a} Before the {b}", "A {a} for the {b}", "What the {a} Kept"]
        titles: list[str] = []
        for pattern in ctx.rng.sample(patterns, len(patterns)):
            a = ctx.rng.choice(top)
            b = ctx.rng.choice([w for w in top if w != a] or [a])
            adj = ctx.rng.choice(ctx.lex.curated_adjectives)
            title = pattern.format(a=a, b=b, A=a.capitalize(), adj=adj.capitalize())
            title = " ".join(part.capitalize() if i == 0 or part not in ("of", "the", "a", "and", "for", "on", "before")
                             else part for i, part in enumerate(title.split()))
            titles.append(tidy(title))
        return titles[:8]

    def finish(self) -> None:
        if self.dry or not self.poem_text().strip():
            return
        titles = self.title_options()
        ids = {f"L{i}": t for i, t in enumerate(titles, 1)}
        self.options_note = [f"[{i}] {t}" for i, t in ids.items()]
        self.frame_note = "choosing a title"
        self.status = "Jev is choosing a title..."
        self.show()
        try:
            state = self.base_state()
            state["title_options"] = ids
            choice = self.ask_one(state, "title", TITLE_INSTRUCTIONS,
                                  {i: f'Choose the title "{t}".' for i, t in ids.items()})
        except StopRun as exc:
            self.status = f"{exc} Poem saved without a title."
            return
        if choice in ids:
            self.title = ids[choice]
            self.save()
            self.status = f'Title chosen by Jev: "{self.title}". Poem saved.'
        else:
            self.status = "No valid title ID found; poem saved without a title."

    def run(self) -> int:
        ended = False
        try:
            while True:
                if self.new_stanza:
                    self.start_stanza()
                ended = self.step_lines() if self.args.mode == "lines" else self.step_words()
                self.frame_note, self.options_note = "", []
                self.show()
                if self.dry:
                    break
                if self.args.max_lines and self.line_count >= self.args.max_lines:
                    ended = True
                if ended:
                    self.finish()
                    self.frame_note, self.options_note = "", []
                    self.show()
                    break
                if not wait_for_next_batch(self.args.delay):
                    break
        except StopRun as exc:
            self.frame_note, self.options_note = "", []
            self.status = str(exc)
            self.show()
        except ApiError as exc:
            self.frame_note, self.options_note = "", []
            self.status = f"Request failed: {exc}\nStopped without retrying to avoid duplicate charges."
            self.show()
            return 1
        if self.fallbacks:
            print(f"Note: {self.fallbacks} word choice(s) had no readable Jev answer and were picked randomly by the script.")
        return 0


# Command-line options
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exquisite Jev: random concrete words, Jev decides what becomes a poem.")
    script_dir = Path(__file__).resolve().parent
    parser.add_argument("--adjectives", default=str(script_dir / "adjectives.csv"), help="CSV containing a Word column")
    parser.add_argument("--nouns", default=str(script_dir / "nouns.csv"), help="CSV with one noun per line")
    parser.add_argument("--verbs", default=str(script_dir / "verbs.csv"), help="CSV containing verb forms")
    parser.add_argument("--concreteness", default=None,
                        help="Optional Brysbaert concreteness CSV (Word, Conc.M); keeps only CSV nouns scoring >= 3.8")
    parser.add_argument("--mode", choices=["words", "lines"], default="words",
                        help="words: Jev picks nouns, then verb/adjectives, then judges the line (3 requests/line). "
                             "lines: Jev picks one finished line from a batch (1 request/line)")
    parser.add_argument("--options", type=int, default=10, help="lines mode: candidate lines per request (default: 10)")
    parser.add_argument("--templates-per-batch", type=int, default=3,
                        help="lines mode: distinct sentence structures per batch; fewer = Jev compares ideas, not shapes (default: 3)")
    parser.add_argument("--word-options", type=int, default=6, help="words mode: options per blank (default: 6)")
    parser.add_argument("--max-stanza", type=int, default=6, help="Force a stanza break after this many lines (default: 6)")
    parser.add_argument("--min-end-lines", type=int, default=8, help="Jev may end the poem once it has this many lines (default: 8)")
    parser.add_argument("--max-lines", type=int, default=0, help="Stop and title the poem after this many lines (0 = no limit)")
    parser.add_argument("--max-cost", type=float, default=0.0, help="Optional cumulative USD threshold; default 0 disables it")
    parser.add_argument("--delay", type=int, default=2, help="Seconds between steps (default: 2)")
    parser.add_argument("--output", default=None, help="Output text file (default: timestamped exquisite_jev_*.txt)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable candidate generation")
    parser.add_argument("--dry-run", action="store_true", help="Run one step locally without calling Jev (first option is used)")
    parser.add_argument("--preview", type=int, default=0, metavar="N",
                        help="Print N local candidate batches to inspect generator quality; no Jev, no file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 2 <= args.options <= 80:
        print("--options must be between 2 and 80", file=sys.stderr)
        return 2
    if args.max_cost < 0 or args.max_lines < 0:
        print("--max-cost and --max-lines cannot be negative", file=sys.stderr)
        return 2
    if not 2 <= args.word_options <= 12 or args.templates_per_batch < 1:
        print("--word-options must be 2-12 and --templates-per-batch at least 1", file=sys.stderr)
        return 2
    try:
        lex = Lexicon(Path(args.adjectives), Path(args.nouns), Path(args.verbs),
                      Path(args.concreteness) if args.concreteness else None)
    except Exception as exc:
        print(f"Could not load word lists: {exc}", file=sys.stderr)
        return 2
    if zipf_frequency is None:
        print("Tip: pip install wordfreq to filter out rare words from the CSV lists (running without it).", file=sys.stderr)

    rng = random.Random(args.seed)
    ctx = Context(lex, rng)

    if args.preview:
        for number in range(1, args.preview + 1):
            batch = make_batch(ctx, args.options, [], [], args.templates_per_batch, False, set())
            print(f"--- batch {number} ---")
            for item in batch:
                print(f"[{item['id']}] {item['line']}")
        return 0

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        print("Set OPENROUTER_API_KEY before running, or use --dry-run / --preview to test locally.", file=sys.stderr)
        return 2
    script_dir = Path(__file__).resolve().parent
    output_path = Path(args.output) if args.output else script_dir / f"exquisite_jev_{datetime.now():%Y%m%d_%H%M%S}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("", encoding="utf-8")
    client = None if args.dry_run else JevClient(api_key, os.getenv("JEV_URL", DEFAULT_URL),
                                                 os.getenv("JEV_MODEL", DEFAULT_MODEL))
    return Session(args, ctx, client, output_path).run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nStopped by user. The latest compilation has been saved.")
        raise SystemExit(130)
