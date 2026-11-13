"""Evidence-linked semantic candidates and conservative reconciliation (SCION-style).

SCION (Hu et al., PMLR v306; github.com/wandugu/paper_scion, Apache-2.0) separates
*candidate generation* from *schema consolidation*: it mines candidate labels from the
documents with evidence pointers, reconciles them with the existing schema without
overwriting it, keeps only model-proposed schema items that link to a candidate, and
records every merge or removal. The mechanism is reimplemented here for scientific
vocabulary; no SCION code is copied.

Candidates come only from what the document itself prints as a term:

- a long form it defines with an acronym ("Main Feed Valve (MFV)");
- a table column header;
- a multiword term it repeats.

Each candidate is reconciled against the approved vocabulary (class names, aliases,
property and relation names and aliases) as COVERED (an approved term written
differently), QUALIFIES (a qualified form of an approved term: a characteristic,
subclass or instance for review) or UNCOVERED (a gap the approved vocabulary does
not name). A gap is a question for review, never a new term by itself; no proposal
is required merely because a candidate exists.
"""

import os
import re
from collections import Counter

from nasa_fire_ai.ingestion.document_memo import document_memo
from nasa_fire_ai.ingestion.document_structure import BACK_MATTER

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "in",
        "into",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "which",
        "with",
        "within",
        "without",
        "per",
        "than",
        "then",
        "each",
        "both",
        "all",
        "any",
        "some",
        "such",
        "other",
        "also",
        "not",
        "no",
        "only",
        "more",
        "most",
        "less",
        "very",
        "if",
        "can",
        "could",
        "will",
        "would",
        "may",
        "might",
        "should",
        "must",
        "shall",
        "do",
        "does",
        "did",
        "so",
        "up",
        "out",
        "over",
        "under",
        "above",
        "below",
        "after",
        "before",
        "during",
        "between",
        "about",
        "against",
        "there",
        "here",
        "when",
        "where",
        "while",
        "how",
        "what",
        "same",
        "these",
        "those",
        "such",
    ]
)


ACRONYM = re.compile(
    r"\b((?:[A-Za-z][A-Za-z-]*\s+){1,7}?[A-Za-z][A-Za-z-]*)\s*\(([A-Z][A-Za-z0-9]{1,9})\)"
)
WORD = re.compile(r"[A-Za-z][A-Za-z-]*[A-Za-z]|[A-Za-z]")


def normalize(label):
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", label or "")]
    # A final plural s only; "porous", "apparatus", "analysis", "glass" keep theirs.
    return " ".join(
        w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")) else w
        for w in words
    )


def _camel_words(term):
    return " ".join(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", term or "")).lower()


def acronym_definitions(text):
    """(long form, acronym) pairs whose initials spell the acronym, as printed."""
    found = []
    for match in ACRONYM.finditer(text):
        words = match.group(1).split()
        acronym = match.group(2)
        letters = [c for c in acronym if c.isalpha()]
        # The long form is the shortest suffix whose initials give the acronym.
        for size in range(len(letters), len(words) + 1):
            tail = words[-size:]
            initials = [w[0].upper() for w in tail if w.lower() not in STOPWORDS or w[0].isupper()]
            if "".join(initials) == "".join(c.upper() for c in letters):
                found.append((" ".join(tail), acronym, match.start(), match.end()))
                break
    return found


def repeated_terms(text, minimum=2, longest=4):
    """Multiword terms printed at least ``minimum`` times, without leading or trailing
    function words and without numbers, keyed by their first printed form."""
    counts, printed = Counter(), {}
    for sentence in re.split(r"[.;:\n•]+", text):
        words = WORD.findall(sentence)
        for size in range(2, longest + 1):
            for i in range(len(words) - size + 1):
                gram = words[i : i + size]
                # Structure, not word endings: a term holds no function word
                # ("cleaned and refurbished", "mass of oil required", "searching for
                # seals" are not terms; "burning rate", "flame speed" and "valve
                # assembly" are).
                if any(len(w) < 2 or w.lower() in STOPWORDS for w in gram):
                    continue
                key = normalize(" ".join(gram))
                counts[key] += 1
                printed.setdefault(key, " ".join(gram))
    # A term inside a longer term printed as often adds nothing of its own.
    kept = {t: n for t, n in counts.items() if n >= minimum}
    return {
        printed[t]: n
        for t, n in kept.items()
        if not any(t != o and f" {t} " in f" {o} " and kept[o] >= n for o in kept)
    }


def approved_vocabulary(semantic):
    """Normalized approved terms and aliases, each pointing at its approved term.

    Each entry also says whether it names the term itself (its identifier, label or
    a multiword alias) or is only a one-word query term or alias, which may confirm
    an exact match but never makes a longer label a qualified form of the term.
    """
    index = {}

    def add(name, kind, term, naming):
        key = normalize(name)
        if key and key not in index:
            index[key] = (kind, term, naming or len(key.split()) > 1)

    for cls, meta in semantic.class_metadata.items():
        for name in [cls, _camel_words(cls), meta.get("label") or ""]:
            add(name, "class", cls, True)
        for name in meta.get("query_terms") or []:
            add(name, "class", cls, False)
    for pid, prop in semantic.properties.items():
        for name in [pid, _camel_words(pid)]:
            add(name, "property", pid, True)
        for name in getattr(prop, "aliases", []):
            add(name, "property", pid, False)
    for rid, rel in semantic.relations.items():
        for name in [rid, _camel_words(rid)]:
            add(name, "relation", rid, True)
        for name in getattr(rel, "aliases", None) or []:
            add(name, "relation", rid, False)
    return index


def reconcile(label, vocabulary):
    """Conservative: an exact normalized match is COVERED; an approved term named in
    full as the head of the label is QUALIFIES (never an equivalence); otherwise
    UNCOVERED. A one-word query term or alias never makes a label qualify."""
    key = normalize(label)
    if key in vocabulary:
        kind, term, _naming = vocabulary[key]
        return {"coverage": "COVERED", "approved_kind": kind, "approved_term": term}
    words = key.split()
    for size in range(len(words) - 1, 0, -1):
        head = " ".join(words[-size:])
        if head in vocabulary and vocabulary[head][2]:
            kind, term, _naming = vocabulary[head]
            return {"coverage": "QUALIFIES", "approved_kind": kind, "approved_term": term}
    return {"coverage": "UNCOVERED"}


def _pattern(label):
    return re.compile(r"\b" + r"\W+".join(map(re.escape, label.split())) + r"\b", re.IGNORECASE)


def _evidence(package, needle):
    """Every printed occurrence of ``needle`` in the package's evidence."""
    pointers = []
    pattern = _pattern(needle)
    for item in package["evidence"]:
        for match in pattern.finditer(item.get("text") or ""):
            pointers.append(
                {
                    "evidence_id": item["evidence_id"],
                    "start": match.start(),
                    "end": match.end(),
                    "quote": item["text"][match.start() : match.end()],
                }
            )
    return pointers


# The line that ends the front matter: an abstract label or heading ("Abstract",
# "ABSTRACT: text"), an introduction heading or a nomenclature heading, numbered or not.
FRONT_MATTER_END = re.compile(
    r"(?im)^[ \t]*(?:#+[ \t]*|(?:\d+|[IVXLC]+)[.)]?[ \t]+)?"
    r"(?:abstract\b|introduction[ \t]*$|(?:\w+[ \t]+and[ \t]+)?nomenclature[ \t]*$)"
)


def _page_structure(document, texts):
    """Page order; per source, where its front matter ends, as (page order, offset):
    the first abstract, introduction or nomenclature line (a source without one has
    no front matter); and the running lines, printed identically on at least half
    of a source's pages and on three or more (a page header or footer)."""
    order = {
        key: i
        for i, key in enumerate(dict.fromkeys(s["evidence_id"] for s in document["segments"]))
    }
    sources = {s["evidence_id"]: s["source_id"] for s in document["segments"]}
    ends, pages, lines = {}, Counter(sources.values()), Counter()
    for evidence_id in sorted(order, key=order.get):
        text = texts.get(evidence_id, "")
        match = FRONT_MATTER_END.search(text)
        if match and sources[evidence_id] not in ends:
            ends[sources[evidence_id]] = (order[evidence_id], match.start())
        lines.update({(sources[evidence_id], line.strip()) for line in text.split("\n")})
    running = {
        line for (source, line), n in lines.items() if line and n >= 3 and 2 * n >= pages[source]
    }
    return order, ends, running


def _byline(line):
    """A line that lists names, places or organizations: fewer than two lowercase
    function words, where prose (a title or an abstract) has more."""
    return sum(w in STOPWORDS for w in WORD.findall(line)) < 2


def in_body(pointer, document, texts):
    """Whether a printed occurrence is in the document's body: not on a running page
    header or footer, not on a byline or affiliation line before the abstract,
    introduction or nomenclature (an unlabeled abstract is prose and stays in the
    body), and not in the back matter (references, acknowledgments), by the
    document's own structure. A document without structure is all body."""
    segments = document.get("segments")
    if not segments:
        return True
    order, ends, running = document_memo(
        document, "page_structure", lambda: _page_structure(document, texts)
    )
    text = texts[pointer["evidence_id"]]
    start = text.rfind("\n", 0, pointer["start"]) + 1
    stop = text.find("\n", pointer["end"])
    line = text[start : stop if stop >= 0 else len(text)]
    for segment in segments:
        if (
            segment["evidence_id"] == pointer["evidence_id"]
            and segment["start"] <= pointer["start"] < segment["end"]
        ):
            if BACK_MATTER.search(segment["section"]) or line.strip() in running:
                return False
            end = ends.get(segment["source_id"])
            if end is None or (order[segment["evidence_id"]], pointer["start"]) >= end:
                return True
            return not _byline(line)
    return True


def term_like(candidate):
    """A candidate offered as a term. A long form the document defines or a table
    header always is; a repeated word sequence is when the body prints it, whatever
    its form: a sequence printed only in the front matter, the back matter or the
    page furniture (a byline, an affiliation, a reference entry, a running footer) is
    not. Relevance is left to the
    window's ordering by occurrences."""
    if set(candidate["origins"]) - {"REPEATED_TERM"}:
        return True
    return candidate.get("body_occurrences", 1) > 0


def candidate_inventory(package, document, semantic, minimum=2):
    """The document's printed terms with evidence pointers and their reconciliation.

    ``evidence`` keeps the first three printed occurrences as the trace;
    ``document_occurrences`` counts all of them.
    """
    vocabulary = approved_vocabulary(semantic)
    text = "\n".join(item.get("text") or "" for item in package["evidence"])
    texts = {item["evidence_id"]: item.get("text") or "" for item in package["evidence"]}
    candidates = {}

    def add(label, origin, **extra):
        key = normalize(label)
        if not key or len(key) < 3:
            return
        if key not in candidates:
            found = _evidence(package, label)
            candidates[key] = {
                "label": label,
                "origins": [],
                "evidence": found[:3],
                "document_occurrences": len(found),
                "body_occurrences": sum(in_body(p, document, texts) for p in found),
            }
        entry = candidates[key]
        if origin not in entry["origins"]:
            entry["origins"].append(origin)
        entry.update(extra)

    for item in package["evidence"]:
        for long_form, acronym, _start, _end in acronym_definitions(item.get("text") or ""):
            add(long_form, "ACRONYM_DEFINITION", acronym=acronym)
    for table in document.get("detected_tables") or []:
        for header in (table.get("cells") or [[]])[0]:
            first = (header or "").split("\n")[0].strip()
            if first and not re.search(r"\d", first) and len(first.split()) <= 6:
                add(first, "TABLE_HEADER")
    for term, count in repeated_terms(text, minimum).items():
        add(term, "REPEATED_TERM", occurrences=count)
    inventory = []
    for key in sorted(candidates):
        entry = candidates[key]
        if not entry["evidence"]:
            continue  # nothing printed to point at: not a candidate
        inventory.append(
            {
                "id": "candidate-" + re.sub(r"\W+", "-", key),
                **entry,
                "term_like": term_like(entry),
                **reconcile(entry["label"], vocabulary),
            }
        )
    return inventory


def window_candidates(inventory, members, limit=40):
    """The candidates a window prints, chosen by the window's own evidence, and how
    many were eligible before the cut.

    Eligible: not covered, printed as a term, and printed in the window's own text.
    Order: a defined long form or a table header first, then the occurrences in the
    window, then in the document; the label only breaks ties.
    """
    texts = [m.get("text") or "" for m in members]
    ranked = []
    for candidate in inventory:
        if candidate["coverage"] == "COVERED" or not candidate.get("term_like", True):
            continue
        pattern = _pattern(candidate["label"])
        local = sum(len(pattern.findall(t)) for t in texts)
        if not local:
            continue
        structural = bool(set(candidate["origins"]) & {"ACRONYM_DEFINITION", "TABLE_HEADER"})
        ranked.append(
            (
                (
                    not structural,
                    -local,
                    -candidate.get("document_occurrences", 0),
                    normalize(candidate["label"]),
                ),
                candidate,
            )
        )
    ranked.sort(key=lambda pair: pair[0])
    return [c for _key, c in ranked[:limit]], len(ranked)


def _overlap(a, b):
    ta, tb = set(normalize(a).split()), set(normalize(b).split())
    return len(ta & tb) / max(len(ta), len(tb)) if ta and tb else 0.0


def link_proposals(proposals, inventory, threshold=0.75):
    """Link each staged extension proposal to the candidate it names, or flag it.

    A proposal names a candidate when one of its printed labels, instances or its term
    matches a candidate label (token overlap at least ``threshold``, SCION's rule). An
    unlinked proposal is not removed: it stays staged, flagged, with the trace.
    """
    trace = []
    for proposal in proposals:
        names = [
            *proposal.get("printed_labels", []),
            *proposal.get("instances", []),
            _camel_words(proposal.get("term")),
        ]
        best = max(
            (
                (max((_overlap(n, c["label"]) for n in names if n), default=0.0), c["id"])
                for c in inventory
            ),
            default=(0.0, None),
        )
        candidate = next((c for c in inventory if c["id"] == best[1]), {})
        if best[0] >= threshold and candidate.get("coverage") == "COVERED":
            # The printed term the proposal names is already an approved term: a
            # duplicate of approved vocabulary, never a new term linked to the source.
            proposal.setdefault("structural_validation", {}).setdefault("warnings", []).append(
                "TERM_PRINTED_AS_AN_APPROVED_TERM"
            )
            trace.append(
                {
                    "proposal": proposal["id"],
                    "decision": "DUPLICATE_OF_APPROVED",
                    "candidate": best[1],
                    "approved_term": candidate.get("approved_term"),
                }
            )
        elif best[0] >= threshold:
            proposal["source_candidate"] = best[1]
            trace.append({"proposal": proposal["id"], "decision": "LINKED", "candidate": best[1]})
        else:
            proposal.setdefault("structural_validation", {}).setdefault("warnings", []).append(
                "NOT_LINKED_TO_A_PRINTED_SOURCE_TERM"
            )
            trace.append({"proposal": proposal["id"], "decision": "NOT_LINKED"})
    return trace


# --- Candidate hygiene (SCIENCE_CANDIDATE_HYGIENE) ----------------------------------------------------
# Every rule is by class or by structure, never by a word list of the sources:
#   H1 zone      a candidate printed only outside the body (title block, byline, running line,
#                reference list) is dropped;
#   H2 fragment  a candidate whose every occurrence lies inside a longer candidate's occurrence, or
#                that ends at a line break its sentence continues over, is dropped;
#   H3 head      a candidate qualifies a class only when its last word is the head of the printed
#                noun phrase: a following word that continues the phrase (not punctuation, a
#                preposition, a determiner, a subordinator, a coordinator or an auxiliary) makes it
#                a pre-modifier fragment (Huddleston and Pullum 2002, ch. 5, 7);
#   H4 name      a candidate whose every word is capitalised names an individual and qualifies no
#                class by its head word (Huddleston and Pullum 2002, ch. 5).


def candidate_hygiene_enabled():
    """Inventory use (the missing-fact report): flag SCIENCE_CANDIDATE_HYGIENE."""
    return os.getenv("SCIENCE_CANDIDATE_HYGIENE", "0") == "1"


def candidate_hygiene_request_enabled():
    """Request use (Track B): the candidates sent to the model are the cleaned ones."""
    return os.getenv("SCIENCE_CANDIDATE_HYGIENE_REQUEST", "0") == "1"


def _evidence_texts(document):
    texts = {}
    for segment in document.get("segments", []):
        texts[segment["evidence_id"]] = texts.get(segment["evidence_id"], "") + segment.get(
            "text", ""
        )
    return texts


def _continues(text, pointer):
    """Whether the line break right after an occurrence is a wrap inside the sentence."""
    after = text[pointer["end"] : pointer["end"] + 80]
    return bool(re.match(r"[ \t]*\n[ \t]*[a-z0-9(]", after))


def _last_word_is_head(text, pointer):
    """Whether the word after an occurrence leaves its last word the head of the phrase."""
    from nasa_fire_ai.ingestion import clause_cues

    after = re.match(r"[ \t]*([A-Za-z][\w-]*)", text[pointer["end"] : pointer["end"] + 60])
    if not after:
        return True
    word = after.group(1).lower()
    closed = (
        clause_cues.PREPOSITIONS
        | clause_cues.DETERMINERS
        | clause_cues.SUBORDINATORS
        | clause_cues.COORDINATORS
        | clause_cues.FINITE_AUXILIARIES
    )
    return word in closed or after.group(1)[0].isupper()


def clean_candidates(candidates, document, dropped=None):
    """The candidates that survive the hygiene rules; pure, the input is not changed.

    A candidate that qualifies a class but fails H3 or H4 is kept as uncovered, with ``hygiene``
    naming the rule. Dropped candidates are appended to ``dropped`` (with the rule) when given.
    """
    texts = _evidence_texts(document)
    occurrences = [
        (c, p) for c in candidates for p in c.get("evidence", []) if p["evidence_id"] in texts
    ]
    kept = []
    for candidate in candidates:
        places = [p for p in candidate.get("evidence", []) if p["evidence_id"] in texts]
        reason = None
        if places and not any(in_body(p, document, texts) for p in places):
            reason = "H1_ZONE"
        elif places and all(
            any(
                other is not candidate
                and len(other["label"]) > len(candidate["label"])
                and q["evidence_id"] == p["evidence_id"]
                and q["start"] <= p["start"]
                and p["end"] <= q["end"]
                for other, q in occurrences
            )
            or _continues(texts[p["evidence_id"]], p)
            for p in places
        ):
            reason = "H2_FRAGMENT"
        if reason:
            if dropped is not None:
                dropped.append({**candidate, "hygiene": reason})
            continue
        entry = dict(candidate)
        if candidate.get("coverage") == "QUALIFIES":
            words = candidate["label"].split()
            if len(words) >= 2 and all(w[:1].isupper() for w in words):
                entry.update(coverage="UNCOVERED", hygiene="H4_PROPER_NAME")
            elif places and not any(_last_word_is_head(texts[p["evidence_id"]], p) for p in places):
                entry.update(coverage="UNCOVERED", hygiene="H3_NOT_THE_HEAD")
        kept.append(entry)
    return kept
