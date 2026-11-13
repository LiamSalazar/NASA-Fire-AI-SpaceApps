"""Query spellings derived from an already registered title and acronym.

These spellings resolve names only. They add no ontology vocabulary, entities,
scientific relationships, or permission to accept a factual claim.
"""

import re


def compound_spellings(title, aliases):
    tail = re.search(r"([A-Za-z]{4,})\s*$", title or "")
    if not tail:
        return set()
    word = tail[1]
    result = set()
    for alias in aliases:
        match = re.fullmatch(r"([A-Z][A-Z0-9]{1,20})-([A-Z]{1,3})", alias)
        if match and word.casefold().startswith(match[2].casefold()):
            result.add(match[1] + "-" + word)
    return result
