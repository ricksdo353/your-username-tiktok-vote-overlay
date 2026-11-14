"""Turn transcript text into trade signals (entry long/short, exit).

Speech is messy, so this is deliberately strict: it only fires on first-person,
present-tense phrases ("I'm long", "we're short", "stopped out") and ignores
them after words like "if", "not", "would", "looking to", "was".
"""
import re

_NEG = {"not", "if", "would", "wouldn't", "want", "wanna", "wanted", "looking", "look", "could", "should",
        "might", "may", "never", "was", "were", "when", "until", "unless", "trying", "try", "planning", "gonna",
        "to", "don't", "didn't", "won't", "can't", "before", "whether", "or"}

_ME = r"(?:i'?m|i am|we'?re|we are|i got|we got|i just got|we just got|i'?m now|we'?re now)"
ENTRY = {
    "long": [rf"\b{_ME}\s+(?:in\s+)?long\b", r"\b(?:just\s+)?(?:entered|took|taking)\s+(?:a\s+|the\s+)?long\b",
             r"\bi\s+(?:just\s+)?longed\b", r"\b(?:i'?m|we'?re)\s+in\s+(?:a\s+)?long\b",
             r"\b(?:i|we)\s+(?:just\s+)?(?:got|went)\s+long\b"],
    "short": [rf"\b{_ME}\s+(?:in\s+)?short\b", r"\b(?:just\s+)?(?:entered|took|taking)\s+(?:a\s+|the\s+)?short\b",
              r"\bi\s+(?:just\s+)?shorted\b", r"\b(?:i'?m|we'?re)\s+in\s+(?:a\s+)?short\b",
              r"\b(?:i|we)\s+(?:just\s+)?(?:got|went)\s+short\b"],
}
EXIT = [r"\b(?:i\s+|we\s+)?(?:got|just got|just)?\s*stopped\s+out\b", rf"\b{_ME}\s+(?:out|flat)\b",
        r"\b(?:i|we)\s+(?:just\s+)?(?:closed|close)\s+(?:it|that|the trade|the position|my (?:trade|position)|out)\b",
        r"\b(?:hit|hitting|tagged)\s+(?:my\s+|our\s+|the\s+)?(?:tp|take profit|target|stop(?:\s+loss)?)\b",
        r"\b(?:tp|target|take profit)\s+(?:got\s+)?hit\b", r"\btook\s+(?:full\s+)?profits?\b(?!\s+partial)"]

_ENTRY_RX = {side: [re.compile(p) for p in ps] for side, ps in ENTRY.items()}
_EXIT_RX = [re.compile(p) for p in EXIT]


def normalize(text: str) -> str:
    t = text.lower().replace("’", "'").replace("`", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _negated(t: str, start: int) -> bool:
    before = t[:start].split()[-4:]
    return any(w in _NEG for w in before)


def detect(text: str):
    """Return a list of (kind, side, matched_phrase). kind is 'entry' or 'exit'; side is 'long'/'short'/None."""
    t = normalize(text)
    hits = []
    for side, rxs in _ENTRY_RX.items():
        for rx in rxs:
            for m in rx.finditer(t):
                if not _negated(t, m.start()):
                    hits.append((m.start(), "entry", side, m.group(0)))
    for rx in _EXIT_RX:
        for m in rx.finditer(t):
            if not _negated(t, m.start()):
                hits.append((m.start(), "exit", None, m.group(0).strip()))
    hits.sort()
    out = []
    for _, k, s, p in hits:                      # overlapping patterns: keep one per change of signal
        if not out or out[-1][:2] != (k, s):
            out.append((k, s, p))
    return out
