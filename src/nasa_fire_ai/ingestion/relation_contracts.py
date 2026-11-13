"""The endpoint classes each approved relation admits: one contract for every stage.

The approved ontology declares no ``rdfs:domain`` or ``rdfs:range``, so these
contracts are the only endpoint knowledge. Extraction validates proposals with
them, the model request states them, snippets and reuse analysis read them, and
curation checks package relations against them.
"""

EXPERIMENT_CLASSES = frozenset({"ExperimentalRun", "ExperimentFamily", "Investigation", "Sample"})

RELATION_ENDPOINTS = {
    "hasMaterial": (EXPERIMENT_CLASSES, frozenset({"Material"})),
    "usesSample": (EXPERIMENT_CLASSES, frozenset({"Sample"})),
    "hasGravityCondition": (EXPERIMENT_CLASSES, frozenset({"GravityCondition"})),
    "hasCondition": (EXPERIMENT_CLASSES, frozenset({"ExperimentalCondition"})),
    "hasIntervention": (EXPERIMENT_CLASSES, frozenset({"Intervention"})),
    "hasPhenomenon": (EXPERIMENT_CLASSES, frozenset({"CombustionPhenomenon"})),
    "belongsToInvestigation": (EXPERIMENT_CLASSES, frozenset({"Investigation"})),
    "belongsToExperimentFamily": (EXPERIMENT_CLASSES, frozenset({"ExperimentFamily"})),
    "madeOf": (
        frozenset({"Sample", "ExperimentFamily", "ExperimentalRun"}),
        frozenset({"Material"}),
    ),
}


def object_class(relation):
    """The single class a relation's object must have, when the contract names one."""
    _, objects = RELATION_ENDPOINTS.get(relation, ((), ()))
    return next(iter(objects)) if len(objects) == 1 else None
