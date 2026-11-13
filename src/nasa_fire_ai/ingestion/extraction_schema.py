"""The wire schema of a scientific proposal: the contract name and the strict models the model fills."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nasa_fire_ai.ingestion.scientific_facets import (
    EVIDENCE_BASES,
    ORIGIN_MARKS,
    quantity_roles,
    statement_roles,
)

CONTRACT = "contextual-scientific-ingestion-v3"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Span(Strict):
    evidence_id: str
    quote: str = Field(min_length=1)
    start: int | None = None


class ProposedTerm(Strict):
    """A term the approved vocabulary lacks, with the approved term it refines."""

    term: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9]*$")
    parent: str


# Chosen instead of an approved term when none fits; the proposed term is then
# staged for ontology review, never used as approved vocabulary.
PROPOSE_NEW_CLASS = "PROPOSE_NEW_CLASS"
PROPOSE_NEW_RELATION = "PROPOSE_NEW_RELATION"


# Facet dimensions a statement or quantity may state beside its role
# (``scientific_facets``); absent means the role's own, which is how every record
# written before facets reads.
Modality = Literal["actual", "proposed", "intended", "conditional", "hypothetical", "prescriptive"]


class Entity(Strict):
    key: str
    label: str = Field(min_length=1)
    class_id: str
    study: Literal["current", "cited", "unknown"] = "unknown"
    support: list[Span] = Field(min_length=1)
    proposed_class: ProposedTerm | None = None


class Statement(Strict):
    text: str
    class_id: str
    epistemic: Literal[statement_roles()]  # type: ignore[valid-type]
    subjects: list[str] = Field(default_factory=list)
    study: Literal["current", "cited", "unknown"] = "unknown"
    support: list[Span] = Field(min_length=1)
    modality: Modality | None = Field(
        default=None,
        description="Only when the source does not report something that happened: "
        "proposed, intended, conditional, hypothetical or prescriptive; null otherwise.",
    )
    # Background facets (SCIENCE_BACKGROUND_FACETS): offered to the model only with the
    # flag on, and dropped from every item while unset, so older outputs read unchanged.
    scope: Literal["background"] | None = Field(
        default=None,
        description="background only when the statement reports the state of the art or "
        "prior knowledge of the field, not a result of this study; null otherwise.",
    )
    execution: Literal["ongoing"] | None = Field(
        default=None,
        description="ongoing only when the source reports an activity as under way, "
        "neither completed nor planned; null otherwise.",
    )
    # Evidence basis (SCIENCE_ROLE_DEFINITIONS_V2): offered to the model only with the flag on and
    # dropped from every item while unset, so older outputs read unchanged.
    basis: Literal[EVIDENCE_BASES] | None = Field(  # type: ignore[valid-type]
        default=None,
        description="What the source rests the content on: measured, computed, simulated, "
        "predicted, stated or retained; null when it does not say.",
    )


class Relation(Strict):
    subject: str
    relation: str
    object: str
    support: list[Span] = Field(min_length=1)
    proposed_relation: ProposedTerm | None = None


class Quantity(Strict):
    subject: str
    label: str = Field(
        description="Original source name of the physical variable; never its number or unit."
    )
    expression: str
    unit: str | None = None
    epistemic: Literal[quantity_roles()]  # type: ignore[valid-type]
    support: list[Span] = Field(min_length=1)
    modality: Modality | None = Field(
        default=None,
        description="Only when the value is not one that was actually used or observed: "
        "proposed, intended, conditional, hypothetical or prescriptive; null otherwise.",
    )
    printed_name: str | None = Field(
        default=None,
        description="The words printed in the value's own clause that name it, copied exactly "
        "(for 'the holder was tilted at 15 degrees', 'tilted'); null when the label is printed.",
    )
    # The study that produced this value (SCIENCE_VALUE_ORIGIN_MARK): offered to the model only
    # with the flag on, and dropped from every item while unset, so older outputs read unchanged.
    # Evidence basis (SCIENCE_ROLE_DEFINITIONS_V2): offered to the model only with the flag on and
    # dropped from every item while unset, so older outputs read unchanged.
    basis: Literal[EVIDENCE_BASES] | None = Field(  # type: ignore[valid-type]
        default=None,
        description="What the source rests the content on: measured, computed, simulated, "
        "predicted, stated or retained; null when it does not say.",
    )
    study: Literal[ORIGIN_MARKS] | None = Field(  # type: ignore[valid-type]
        default=None,
        description="The study that produced this value: current, or cited when the source "
        "reports it from other work; it may differ from its subject's study; null otherwise.",
    )


class Concept(Strict):
    kind: Literal["class", "property", "relation", "alias"]
    term: str
    definition: str
    parent_or_existing: str | None = None
    why_existing_insufficient: str
    support: list[Span] = Field(min_length=1)


class Output(Strict):
    entities: list[Entity] = Field(default_factory=list)
    statements: list[Statement] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    quantities: list[Quantity] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
