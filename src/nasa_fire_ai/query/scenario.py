"""Versioned internal simulator input; team output never enters the NASA corpus."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from nasa_fire_ai.query.v2 import EntityConstraintV2, PropertyConstraintV2, QueryIntentV2


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["scientific-scenario-v1"] = "scientific-scenario-v1"
    scenario_id: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=12000)
    provenance: Literal["team_simulator", "user_hypothesis"] = "user_hypothesis"
    entity_constraints: list[EntityConstraintV2] = Field(default_factory=list, max_length=32)
    property_constraints: list[PropertyConstraintV2] = Field(default_factory=list, max_length=32)
    unresolved_conditions: list[str] = Field(default_factory=list, max_length=32)
    simulator_results: list[dict] = Field(default_factory=list, max_length=100)

    def intent(self):
        return QueryIntentV2(
            targets=["ExperimentalRun", "Sample"],
            entity_constraints=self.entity_constraints,
            property_constraints=self.property_constraints,
            unresolved_mentions=self.unresolved_conditions,
        )


class ScenarioAnalysis(BaseModel):
    schema_version: Literal["scientific-scenario-analysis-v1"] = "scientific-scenario-analysis-v1"
    scenario: ScenarioInput
    snapshot_id: str
    provided_conditions: list[dict]
    unspecified_conditions: list[str]
    evidence: dict
    comparable_variables: list[dict]
    experimental_differences: list[dict]
    accredited_observations: list[dict]
    uncertainties: list[str]
    extrapolation_limits: list[str]
    sources: list[dict]
    additional_research: list[dict]
