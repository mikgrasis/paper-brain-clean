"""Decode LaTeX accent escapes in bib fields to UTF-8: {\\'{e}} -> é, \\o -> ø. Math ($...$) is left alone."""
import re
import unicodedata

COMBINING = {"'": "́", "`": "̀", "^": "̂", '"': "̈", "~": "̃", "=": "̄", ".": "̇",
             "u": "̆", "v": "̌", "H": "̋", "c": "̧", "k": "̨", "r": "̊"}
SYMBOL = {"o": "ø", "O": "Ø", "l": "ł", "L": "Ł", "ss": "ß", "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ",
          "oe": "œ", "OE": "Œ", "i": "ı", "j": "ȷ"}
BASE = r"(?:\{\s*(\\[ij]|[A-Za-z])\s*\}|(\\[ij])(?![A-Za-z])|\s*([A-Za-z]))"
ACCENT = re.compile(r"(\{)?\\(?:([\"'`^~=.])|([uvHckr])(?![A-Za-z]))\s*" + BASE + r"(\})?")
SYM = re.compile(r"(\{)?\\(" + "|".join(sorted(SYMBOL, key=len, reverse=True)) + r")(?![A-Za-z])(?:\{\})?(\})?")


def _keep_unbalanced(lb, rb, ch):
    return "{" + ch if lb and not rb else ch + "}" if rb and not lb else ch


def _accent(m):
    lb, sym, word, b1, b2, b3, rb = m.groups()
    base = {"\\i": "i", "\\j": "j"}.get(b1 or b2 or b3, b1 or b2 or b3)
    return _keep_unbalanced(lb, rb, unicodedata.normalize("NFC", base + COMBINING[sym or word]))


def decode(text):
    parts = re.split(r"(\$[^$]*\$)", text)
    for i in range(0, len(parts), 2):
        parts[i] = ACCENT.sub(_accent, parts[i])
        parts[i] = SYM.sub(lambda m: _keep_unbalanced(m.group(1), m.group(3), SYMBOL[m.group(2)]), parts[i])
    return "".join(parts)
