"""Tools to explore/fetch Unicode characters in a user friendly way
"""

import re
import unicodedata

from collections import namedtuple
from functools import lru_cache


CHAR_BASE = None


class Character(str):
    __slots__ = "code char name category width".split()

    def __new__(cls, value, code, name, category, width):
        self = super().__new__(cls, value)
        self.code = code
        self.name = name
        self.category = category
        self.width = width

        return self

    def __repr__(self):
            return f"Character(code=0x{self.code:04X}, value='{self}', name='{self.name}', category='{self.category}', width='{self.width}')"


def _init_chars():
    global CHAR_BASE
    if CHAR_BASE:
        return
    CHAR_BASE = {}
    for code in range(0, 0x10ffff):
        char = chr(code)
        values = {}
        attrs = "name category east_asian_width"
        for attr in attrs.split():
            try:
                values[attr] = getattr(unicodedata, attr)(char)
            except ValueError:
                values[attr] = "undefined"
        CHAR_BASE[code] = Character(char, code, values["name"], values["category"], values["east_asian_width"])


def lookup(name_part, chars_only=False):
    _init_chars()
    results = [char for char in CHAR_BASE.values() if re.search(name_part, char.name, re.IGNORECASE)]
    if not chars_only:
        return results
    return [char.char for char in results]


CGJ = "\u034f" # character used to _separate_ graphemes that would otherwise be joined - combining grapheme joiner (CGJ) U+034F


class GraphemeIter:
    """Separates a string in a list of strings, each containing a single grapheme:
    the contiguous set of a character and combining characters to be applied to it.
    """

    def __init__(self, text):
        self.text = text

    def text_setter(self, value):
        if "text" in self.__dict__:
            raise TypeError(f"{self.__class__.__name__} is imutable")
        self.__dict__["text"] = value

    text = property(lambda s: s.__dict__["text"], text_setter)
    del text_setter

    @lru_cache()
    def __len__(self):
        return sum(1 for _ in self)

    def __iter__(self):
        category = unicodedata.category

        last_char = ""
        for char in self.text:
            if not category(char)[0] == 'M' and last_char:
                yield last_char
                last_char = ""
            last_char += char
        if last_char:
            yield last_char

split_graphemes = lambda text: list(GraphemeIter(text))


@lru_cache()
def char_width(char):
    from terminedia.subpixels import BlockChars, SextantChars

    if char in BlockChars.chars or char in SextantChars.chars:
        return 1
    if len(char) > 1:
        return max(char_width(combining) for combining in char)
    v = unicodedata.east_asian_width(char)
    return 1 if v in ("N", "Na", "A") else 2  # (?) include "A" as single width?
