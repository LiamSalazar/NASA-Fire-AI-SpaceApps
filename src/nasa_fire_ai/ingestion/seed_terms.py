"""Seed vocabulary kept out of the prompt (SCIENCE_EXCLUDE_SEED_TERMS, off by default).

domain/lexicon.yaml is the MVP seed: it names a few materials, investigations and gravity
levels. A term whose only origin is that seed is not part of the approved ontology or the
approved registry, so a request that lists it names vocabulary the document may not use.
The filter runs when the request is built; the lexicon and the registry are untouched.
"""

import os
import re
from pathlib import Path

import yaml


def exclude_seed_terms():
    return os.getenv("SCIENCE_EXCLUDE_SEED_TERMS", "0") == "1"


def _key(term):
    return re.sub(r"[^a-z0-9]+", " ", str(term).casefold()).strip()


def seed_term_keys(root):
    """Normalized labels, aliases and abbreviations of the seed lexicon."""
    path = Path(root) / "domain/lexicon.yaml"
    if not path.exists():
        return set()
    keys = set()
    for concept in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("concepts", []):
        for term in [
            concept.get("canonical_label"),
            *concept.get("aliases", []),
            *concept.get("abbreviations", []),
        ]:
            if term:
                keys.add(_key(term))
    return keys


def approved_term_keys(semantic):
    """Normalized terms the approved ontology and registry name (any origin but the seed)."""
    keys = set()
    for cls, meta in semantic.class_metadata.items():
        keys.update(
            _key(t) for t in [cls, meta.get("label"), *(meta.get("query_terms") or [])] if t
        )
    for pid, prop in semantic.properties.items():
        keys.update(_key(t) for t in [pid, *(getattr(prop, "aliases", None) or [])])
    for rid, rel in semantic.relations.items():
        keys.update(_key(t) for t in [rid, *(getattr(rel, "aliases", None) or [])])
    return keys


def seed_only_keys(root, semantic):
    return seed_term_keys(root) - approved_term_keys(semantic)


def without_seed_aliases(entries, root, semantic):
    """Alias entries ({"aliases": [...], ...}) without the seed-only terms; an entry left
    with no alias is dropped."""
    seed = seed_only_keys(root, semantic)
    kept = []
    for entry in entries:
        aliases = [a for a in entry["aliases"] if _key(a) not in seed]
        if aliases:
            kept.append({**entry, "aliases": aliases})
    return kept
