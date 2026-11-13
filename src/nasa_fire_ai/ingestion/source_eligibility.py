"""Eligibility of an official NASA citation, judged on four separate questions.

An official NASA document is not rejected merely because a short keyword list
is missing from its title or abstract. Source identity, NASA involvement,
domain relevance and accessibility are assessed separately from the NTRS
metadata and, when the metadata is not enough, from the document's own first
pages. Uncertain relevance stays explicit and goes to review; research outside
the domain is not acquired. No part of this changes a document's content.
"""

import re

FIRE = re.compile(
    r"\b(?:combust\w*|flam\w*|fire\w*|ignit\w*|burn\w*|smolder\w*|extinguish\w*|autoignition"
    r"|heat\s+of\s+combustion|oxygen[-\s]compatib\w*|incompatible\s+with\s+oxygen)\b",
    re.IGNORECASE,
)
CONTEXT = re.compile(
    r"\b(?:micro-?gravity|partial[-\s]gravity|reduced[-\s]gravity|zero[-\s]g(?:ravity)?"
    r"|low[-\s]gravity|lunar|martian|mars|spacecraft|spacesuit|space\s+station|ISS"
    r"|space\s+fire|spaceflight|crew(?:ed|members?)?|cabin|habitat|exploration\s+vehicles?"
    r"|oxygen\s+systems?|high[-\s]pressure\s+oxygen|LOX|GOX|NASA-STD-6001|EMU|PLSS"
    r"|life[-\s]support|material\s+selection|drop\s+tower|sounding\s+rocket|orbit\w*)\b",
    re.IGNORECASE,
)
NASA = re.compile(
    r"\bNASA\b|National\s+Aeronautics\s+and\s+Space\s+Administration"
    r"|\b(?:Glenn|Marshall|Johnson|Kennedy|Ames|Langley|Goddard|Stennis|Armstrong)\s+"
    r"(?:Research|Space|Flight)\s+(?:Center|Facility)|White\s+Sands\s+Test\s+Facility",
    re.IGNORECASE,
)
ELIGIBILITY_LABELS = {
    "ELIGIBLE": "OFFICIAL_NASA_DOMAIN_DOCUMENT",
    "REVIEW_REQUIRED": "OFFICIAL_NASA_DOCUMENT_DOMAIN_REVIEW_REQUIRED",
    "INELIGIBLE": "DOMAIN_NOT_ESTABLISHED",
}


def _text(value):
    if isinstance(value, dict):
        return " ".join(_text(v) for v in value.values())
    if isinstance(value, list | tuple):
        return " ".join(_text(v) for v in value)
    return str(value or "")


def descriptive_text(metadata):
    """Title, abstract, keywords and subject categories as one string."""
    return " ".join(
        _text(metadata.get(key))
        for key in ("title", "abstract", "keywords", "subjectCategories", "subjectTerms")
    )


def official_identity(metadata):
    identifier = str(metadata.get("id", ""))
    public = identifier.isdecimal() and metadata.get("distribution") == "PUBLIC"
    return {
        "status": "NTRS_PUBLIC_CITATION" if public else "NOT_ESTABLISHED",
        "nasa_id": identifier or None,
        "distribution": metadata.get("distribution"),
    }


def nasa_involvement(metadata):
    """NASA involvement from the citation's own fields, never inferred from topic."""
    basis = []
    center = metadata.get("center") or {}
    if isinstance(center, dict) and (center.get("code") or center.get("name")):
        basis.append("center: " + str(center.get("name") or center.get("code")))
    for affiliation in metadata.get("authorAffiliations") or []:
        organization = (affiliation.get("meta") or {}).get("organization") or {}
        name = organization.get("name", "") if isinstance(organization, dict) else str(organization)
        if NASA.search(name):
            basis.append("author affiliation: " + name)
            break
    for key in ("organizations", "publisher", "otherReportNumbers", "publications"):
        if NASA.search(_text(metadata.get(key))):
            basis.append(key)
    if NASA.search(_text(metadata.get("title"))):
        basis.append("title")
    return {
        "status": "ESTABLISHED" if basis else "NOT_ESTABLISHED_BY_METADATA",
        "basis": basis,
    }


def domain_relevance(text, basis):
    """Fire/combustion wording plus a NASA fire-safety context establishes relevance.

    Fire wording alone is uncertain, never a rejection; no fire wording at all
    does not establish the domain.
    """
    fire = sorted({m.group().lower() for m in FIRE.finditer(text)})
    context = sorted({m.group().lower() for m in CONTEXT.finditer(text)})
    if fire and context:
        status = "ESTABLISHED"
    elif fire:
        status = "UNCERTAIN"
    else:
        status = "NOT_ESTABLISHED"
    return {"status": status, "basis": basis, "fire_terms": fire, "context_terms": context}


def content_text(data, pages=3):
    """Text of the document's first pages, read only to judge relevance."""
    import pymupdf

    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        return "\n".join(page.get_text() for page in list(pdf)[:pages])


def assess(metadata, content=None):
    """Four judgments and the extraction eligibility they imply."""
    identity = official_identity(metadata)
    involvement = nasa_involvement(metadata)
    relevance = domain_relevance(descriptive_text(metadata), "METADATA")
    if relevance["status"] != "ESTABLISHED" and content:
        by_content = domain_relevance(content, "DOCUMENT_FIRST_PAGES")
        if by_content["status"] == "ESTABLISHED" or (
            by_content["status"] == "UNCERTAIN" and relevance["status"] == "NOT_ESTABLISHED"
        ):
            relevance = by_content
    if identity["status"] != "NTRS_PUBLIC_CITATION" or relevance["status"] == "NOT_ESTABLISHED":
        eligibility = "INELIGIBLE"
    elif relevance["status"] == "UNCERTAIN" or involvement["status"] != "ESTABLISHED":
        eligibility = "REVIEW_REQUIRED"
    else:
        eligibility = "ELIGIBLE"
    return {
        "official_identity": identity,
        "nasa_involvement": involvement,
        "domain_relevance": relevance,
        "extraction_eligibility": eligibility,
        "eligibility": ELIGIBILITY_LABELS[eligibility],
    }


def explanation(assessment):
    relevance = assessment["domain_relevance"]
    return (
        f"domain relevance {relevance['status']} by {relevance['basis']} "
        f"(fire terms: {', '.join(relevance['fire_terms']) or 'none'}; "
        f"context terms: {', '.join(relevance['context_terms']) or 'none'}); "
        f"NASA involvement {assessment['nasa_involvement']['status']}"
    )
