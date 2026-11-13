"""Synthetic eligibility judgments for official NASA citations (Phase 1 section 8)."""

from nasa_fire_ai.ingestion.source_eligibility import assess, domain_relevance, nasa_involvement


def citation(title, abstract, **extra):
    return {"id": 1, "distribution": "PUBLIC", "title": title, "abstract": abstract, **extra}


def test_combustion_in_a_spacecraft_context_is_established_by_metadata():
    a = assess(citation("Flame spread in microgravity", "Combustion tests aboard the ISS."))
    assert a["domain_relevance"]["status"] == "ESTABLISHED"
    assert a["domain_relevance"]["basis"] == "METADATA"


def test_oxygen_compatibility_of_seal_materials_is_fire_safety_not_a_keyword_miss():
    # Neither "combustion" nor "microgravity" appears; the old gate rejected this.
    a = assess(
        citation(
            "Oxygen Compatibility of a Filled Polymer for Oxygen Systems",
            "Seal materials for high-pressure oxygen systems were evaluated.",
            center={"code": "MSFC", "name": "Marshall Space Flight Center"},
        )
    )
    assert a["domain_relevance"]["status"] == "ESTABLISHED"
    assert a["nasa_involvement"]["status"] == "ESTABLISHED"
    assert a["eligibility"] == "OFFICIAL_NASA_DOMAIN_DOCUMENT"


def test_fire_wording_without_context_is_uncertain_and_routed_to_review():
    a = assess(citation("Ignition of a laboratory sample", "Burning rates were measured."))
    assert a["domain_relevance"]["status"] == "UNCERTAIN"
    assert a["extraction_eligibility"] == "REVIEW_REQUIRED"
    assert a["eligibility"] == "OFFICIAL_NASA_DOCUMENT_DOMAIN_REVIEW_REQUIRED"


def test_document_pages_can_establish_what_thin_metadata_does_not():
    thin = citation("Technical report", "")
    assert assess(thin)["extraction_eligibility"] == "INELIGIBLE"
    content = "Flammability of cabin materials was tested in the spacecraft fire safety program."
    a = assess(thin, content)
    assert a["domain_relevance"]["status"] == "ESTABLISHED"
    assert a["domain_relevance"]["basis"] == "DOCUMENT_FIRST_PAGES"


def test_unrelated_research_and_non_public_citations_are_ineligible():
    unrelated = assess(citation("Planetary spectroscopy", "Infrared spectra of Titan."))
    assert unrelated["extraction_eligibility"] == "INELIGIBLE"
    private = citation("Flame spread in microgravity", "ISS combustion tests.")
    private["distribution"] = "RESTRICTED"
    assert assess(private)["extraction_eligibility"] == "INELIGIBLE"
    # Established metadata is not undone by unrelated page text.
    a = assess(citation("Flame spread in microgravity", "ISS tests."), "unrelated")
    assert a["domain_relevance"]["status"] == "ESTABLISHED"


def test_nasa_involvement_comes_from_citation_fields_not_topic():
    assert nasa_involvement({"title": "Fire safety"})["status"] == "NOT_ESTABLISHED_BY_METADATA"
    affiliation = {"meta": {"organization": {"name": "NASA Glenn Research Center"}}}
    assert nasa_involvement({"title": "x", "authorAffiliations": [affiliation]})["status"] == (
        "ESTABLISHED"
    )
    assert nasa_involvement({"title": "x", "center": {"code": "JSC"}})["status"] == "ESTABLISHED"


def test_metamorphic_wording_changes_keep_or_change_the_judgment():
    base = "Combustion of solid fuels in reduced gravity."
    assert domain_relevance(base, "METADATA")["status"] == "ESTABLISHED"
    assert domain_relevance(base.upper(), "METADATA")["status"] == "ESTABLISHED"
    furnace = base.replace("reduced gravity", "a furnace")
    assert domain_relevance(furnace, "METADATA")["status"] == "UNCERTAIN"
    spectra = base.replace("Combustion", "Spectroscopy")
    assert domain_relevance(spectra, "METADATA")["status"] == "NOT_ESTABLISHED"
